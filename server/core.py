import csv
import hashlib
import io
import ipaddress
import json
import re
import socket
import ssl
import http.client
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import phonenumbers
import pycountry
import tldextract

EXTRACT_DOMAIN = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)

ROOT = Path(__file__).resolve().parents[1]
PIPELINES = ['Baru', 'Dihubungi', 'Follow-up', 'Deal', 'Tolak']
CONSENTS = ['none', 'invited', 'opted_in', 'replied', 'opted_out']
CSV_FIELDS = 'business_name phone_normalized whatsapp_number whatsapp_status emails category address city province country_origin_code country_origin_name export_countries export_products website_url rating review_count pipeline_status consent_basis eligible_to_send source first_query first_seen_at maps_url'.split()
GOSOM_HEADERS = 'input_id link title category address open_hours popular_times website phone plus_code review_count review_rating reviews_per_rating latitude longitude cid status descriptions reviews_link thumbnail timezone price_range data_id street_view_url place_id images reservations order_online menu owner complete_address credit_cards_accepted about user_reviews user_reviews_extended emails'.split()
ALIASES = {'ID': ['Indonesia'], 'US': ['United States', 'USA', 'Amerika Serikat', 'America'], 'GB': ['United Kingdom', 'UK', 'Inggris'], 'NL': ['Netherlands', 'Holland', 'Belanda'], 'DE': ['Germany', 'Jerman'], 'JP': ['Japan', 'Jepang'], 'AU': ['Australia'], 'SG': ['Singapore', 'Singapura'], 'MY': ['Malaysia'], 'CN': ['China', 'Tiongkok'], 'AE': ['United Arab Emirates', 'UAE', 'Uni Emirat Arab'], 'SA': ['Saudi Arabia', 'Arab Saudi'], 'FR': ['France', 'Prancis'], 'KR': ['South Korea', 'Korea Selatan'], 'IN': ['India'], 'CA': ['Canada', 'Kanada']}
NAMES = {code: names[-1] for code, names in ALIASES.items()}
NAMES.update({'US': 'Amerika Serikat', 'GB': 'Inggris', 'NL': 'Belanda', 'AE': 'Uni Emirat Arab'})
COUNTRIES = [{'code': c.alpha_2, 'name': NAMES.get(c.alpha_2, c.name), 'aliases': list(set([c.name, getattr(c, 'official_name', c.name)] + ALIASES.get(c.alpha_2, [])))} for c in pycountry.countries]
GEO = json.loads((ROOT / 'data/countries.geojson').read_text())['features']


def now():
    return datetime.now(timezone.utc).isoformat()


def clean(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def normalized(value):
    return clean(value).casefold()


def website(value):
    value = clean(value)
    if not value:
        return '', ''
    parsed = urlsplit(value if '://' in value else 'https://' + value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        return '', ''
    host = parsed.hostname.lower().removeprefix('www.')
    extracted = EXTRACT_DOMAIN(host)
    return parsed.geturl(), extracted.top_domain_under_public_suffix or host


def in_ring(x, y, ring):
    inside = False
    for i, (x1, y1, *_) in enumerate(ring):
        x2, y2 = ring[i-1][:2]
        if (y1 > y) != (y2 > y) and x < (x2-x1) * (y-y1) / (y2-y1) + x1:
            inside = not inside
    return inside


def origin(address, lat=None, lon=None):
    tail = normalized(address.split(',')[-1])
    for country in COUNTRIES:
        if tail in [normalized(a) for a in country['aliases']]:
            return country['code'], country['name'], 'address_tail', 'high'
    provinces = r'jawa|yogyakarta|jakarta|bali|sumatera|sumatra|kalimantan|sulawesi|papua|maluku|banten|aceh|riau|lampung|bengkulu|jambi|gorontalo|nusa tenggara|bangka belitung'
    if re.search(provinces, address, re.I) and re.search(r'\b\d{5}\b', address):
        return 'ID', 'Indonesia', 'postal_province', 'medium'
    if lat is not None and lon is not None:
        for feature in GEO:
            geometry = feature['geometry']
            polygons = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
            if any(in_ring(float(lon), float(lat), p[0]) and not any(in_ring(float(lon), float(lat), h) for h in p[1:]) for p in polygons):
                props = feature['properties']
                code = props.get('ISO_A2')
                if not code or code == '-99':
                    match = pycountry.countries.get(alpha_3=props.get('ADM0_A3', ''))
                    code = match.alpha_2 if match else ''
                country = next((c for c in COUNTRIES if c['code'] == code), None)
                if country:
                    return code, country['name'], 'coordinates', 'medium'
    return '', '', '', ''


def phone(value, country):
    try:
        parsed = phonenumbers.parse(value, country or None)
        if not phonenumbers.is_valid_number(parsed):
            return '', ''
        number = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        # A fixed-line-or-mobile type is ambiguous, so leave WhatsApp empty.
        mobile = phonenumbers.number_type(parsed) == phonenumbers.PhoneNumberType.MOBILE
        return number, number if mobile else ''
    except phonenumbers.NumberParseException:
        return '', ''


def number(value, integer=False):
    if value is None or value == '':
        return None
    return int(float(value)) if integer else float(value)


def parse_emails(value):
    if isinstance(value, list):
        value = ' '.join(str(v) for v in value)
    return sorted(set(re.findall(r'[a-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[a-z0-9.-]+\.[a-z]{2,}', str(value or '').lower())))


def map_row(row, job):
    name = clean(row.get('title'))
    if not name:
        raise ValueError('Nama bisnis kosong / header title tidak tersedia.')
    address = clean(row.get('address'))
    complete = row.get('complete_address', {})
    if isinstance(complete, str):
        try:
            complete = json.loads(complete)
        except (ValueError, TypeError):
            complete = {}
    complete = complete if isinstance(complete, dict) else {}
    lat, lon = number(row.get('latitude')), number(row.get('longitude'))
    code, country_name, method, confidence = origin(address, lat, lon)
    tel, wa = phone(clean(row.get('phone')), code)
    site, domain = website(row.get('website'))
    emails = parse_emails(row.get('emails')) if job.get('email_enabled', True) and site else []
    city = clean(complete.get('city') or complete.get('municipality'))
    province = clean(complete.get('state') or complete.get('province'))
    if not city:
        city = next((clean(p) for p in address.split(',') if re.search(r'\b(kota|kabupaten|kab\.)\b', p, re.I)), '')
    return dict(business_name=name, place_id=clean(row.get('place_id')), cid=clean(row.get('cid')), category=clean(row.get('category')), categories=row.get('categories', []), address=address, city=city, province=province, latitude=lat, longitude=lon, plus_code=row.get('plus_code', ''), maps_url=row.get('link', ''), country_origin_code=code, country_origin_name=country_name, country_origin_method=method, country_origin_confidence=confidence, country_origin_missing=not bool(code), phone_raw=clean(row.get('phone')), phone_normalized=tel, whatsapp_number=wa, whatsapp_status='derived_unverified' if wa else 'unknown', emails=emails, email_status='unverified', website_url=site, website_domain=domain, has_phone=bool(tel), has_whatsapp=bool(wa), has_email=bool(emails), rating=number(row.get('review_rating')), review_count=number(row.get('review_count'), True), open_hours=row.get('open_hours', {}), business_status=row.get('status', ''), pipeline_status='Baru', source='google_maps', consent_basis='none', consent_at=None, consent_source='', eligible_to_send=False, first_query=job.get('queries', [''])[0], first_seen_at=now(), last_seen_at=now(), seen_count=1)


def fingerprint(lead):
    if lead.get('place_id'):
        return 'place:' + lead['place_id']
    identity = normalized(lead['business_name'])
    contact = lead.get('phone_normalized') or lead.get('website_domain')
    # No shared identifier: avoid collapsing unrelated shops with the same name.
    return hashlib.sha256((identity + '|' + (contact or normalized(lead.get('address')))).encode()).hexdigest()


def read_rows(raw):
    text = raw.decode('utf-8-sig')
    if text.lstrip().startswith('['):
        rows = json.loads(text)
        return rows, list(rows[0]) if rows else []
    if text.lstrip().startswith('{'):
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        return rows, list(rows[0]) if rows else []
    reader = csv.DictReader(io.StringIO(text))
    return list(reader), reader.fieldnames or []


def csv_export(leads):
    buf = io.StringIO(newline='')
    writer = csv.writer(buf)
    writer.writerow(CSV_FIELDS)
    for lead in leads:
        values = []
        for key in CSV_FIELDS:
            value = lead.get(key, '')
            if isinstance(value, list):
                value = ';'.join(str(x) for x in value)
            if isinstance(value, bool):
                value = str(value).lower()
            # Prevent spreadsheet formula execution from untrusted Maps text.
            if isinstance(value, str) and value.startswith(('=', '+', '-', '@', '\t', '\r')):
                value = "'" + value
            values.append(value)
        writer.writerow(values)
    return '\ufeff' + buf.getvalue()


def fetch_public(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 80, 443):
        raise ValueError('URL website tidak diizinkan.')
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Alamat jaringan privat tidak diizinkan.')
    # Pin the connection to the validated address. TLS still verifies the original hostname.
    sock = socket.create_connection(addresses[0][4], timeout=12)
    if parsed.scheme == 'https':
        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=parsed.hostname)
    conn = http.client.HTTPConnection(parsed.hostname, timeout=12)
    conn.sock = sock
    try:
        conn.request('GET', (parsed.path or '/') + ('?' + parsed.query if parsed.query else ''), headers={'User-Agent': 'PokoScrap-Discovery/1.0', 'Host': parsed.hostname})
        response = conn.getresponse()
        if response.status != 200:
            raise ValueError(f'Website merespons HTTP {response.status}; redirect tidak diikuti.')
        if 'text/html' not in response.getheader('Content-Type', ''):
            raise ValueError('Halaman bukan HTML.')
        data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise ValueError('Halaman melebihi batas 2 MB.')
        return data.decode('utf-8', errors='replace')
    finally:
        conn.close()
