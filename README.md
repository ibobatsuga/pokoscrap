# PokoScrap

Dashboard scraping bisnis sesuai PRD v2.0 SaaS Model A. Nama produk dan logo mengikuti koreksi pengguna. Tampilan mengikuti keluarga PokoMail, PokoBot, dan PokoWeb: sidebar putih, latar abu muda, kartu membulat, tombol hitam, aksen hijau. Teks merek 16 px, bobot 700.

Ada dua cara membuka aplikasi:

- **Pratinjau hosted**: antarmuka interaktif dengan label data contoh. `dist/config.js` mengaktifkan demo. Data tersimpan di browser; tidak menjalankan scraping, mengirim undangan, membuat API key nyata, atau menagih pembayaran.
- **Self-host**: antarmuka yang sama, FastAPI, PostgreSQL dengan RLS, worker gosom, worker enrichment, arsip mentah, dan ledger kredit. `/config.js` dari server menonaktifkan demo. Database baru dimulai kosong.

Status: implementasi beta teknis. Lihat [VALIDASI.md](VALIDASI.md) untuk bukti uji dan pekerjaan yang belum terverifikasi. Jangan menyebutnya selesai produksi sebelum seluruh AC PRD dan gerbang beta berbayar lulus.

## Menjalankan self-host

Prasyarat: Docker Engine/Compose aktif dan Python 3 untuk membuat konfigurasi.

```sh
cd /path/to/pokoscrap
python3 scripts/configure.py
docker compose up -d --build
docker compose exec dashboard-web python -m server.manage
```

Perintah terakhir membuat Admin SaaS dan organisasi Free melalui terminal tepercaya. Kata sandi dimasukkan lewat prompt tersembunyi, tanpa akun bawaan. Buka [dashboard lokal](http://127.0.0.1:8877), lalu masuk.

Untuk pendaftar biasa, gunakan halaman Daftar. Verifikasi email diperlukan sebelum login. Tanpa SMTP, pesan pengembangan ada di `runtime/outbox/`; buka tautan verifikasinya secara lokal. Setelah masuk, buat organisasi untuk mendapat 30 kredit Free. Untuk email sungguhan, isi SMTP pada `.env` dan mulai ulang layanan. Undangan anggota memerlukan paket Pro dan akun dengan email terverifikasi yang sama dengan undangan.

`HOST_DATA_PATH` harus merupakan jalur absolut folder runtime pada mesin Docker; folder ini dipasang pada container gosom per job. Di Colima, socket yang dipasang tetap `/var/run/docker.sock` milik VM Docker. Socket Docker hanya diberikan kepada `gosom-worker`.

Pengaturan `WEB_PORT` dapat diganti jika 8877 sudah dipakai. Sesuaikan `BASE_URL` dengan alamat yang diakses pengguna. Untuk deployment HTTPS, pakai reverse proxy, `COOKIE_SECURE=1`, dan `BASE_URL=https://domain-anda`. Port database dan Redis tidak diekspos ke host.

## Fitur

- 14 area kerja: login (Google & Email), daftar/onboarding, ringkasan, daftar/buat/detail job, daftar/detail lead, review enrichment, **API Key & MCP Server**, pengaturan, billing, kredit, Admin SaaS.
- **Login dengan Google**: Mendukung otentikasi Google OAuth 2.0 / Google Identity Services dan simulasi login instan siap pakai untuk pengujian produksi lokal.
- **Model Context Protocol (MCP)**: Sambungkan database lead dan scraper PokoScrap secara native ke **Claude Desktop**, **Cursor**, **Antigravity**, **Windsurf**, atau AI Agent kustom via endpoint HTTP JSON-RPC 2.0 (`/api/mcp`) atau stdio (`server/mcp_server.py`) dengan 7 tool bawaan (`pokoscrap_search_leads`, `pokoscrap_get_lead`, `pokoscrap_update_lead_pipeline`, `pokoscrap_create_scrape_job`, `pokoscrap_get_job_status`, `pokoscrap_get_stats`, `pokoscrap_export_leads`).
- **Menu API Key & MCP**: Antarmuka visual untuk membuat key, mencabut akses, menyalin snippet integrasi cURL / Python / Node.js, dan menyalin konfigurasi MCP Claude/Cursor dengan 1 klik.
- **Desain & Tipografi Poko Series**: Tipografi General Sans (Fontshare), palet warna `#f4f4f4` (canvas), `#ffffff` (card), `#1f1f1f` (charcoal), `#e5e7eb` (border), `#10b981` (emerald accent), topbar 64px dengan backdrop blur, sidebar 256px dengan pengelompokan menu rapi.
- Job asinkron, titik/radius atau grid, query unik, email bawaan aktif, draft/edit/duplikasi/arsip, stop, log Admin, unduh mentah, dan resume arsip.
- Pemetaan 36 header gosom terpusat, dedupe per tenant, E.164, WhatsApp hanya dari nomor seluler yang valid, email terdedupe, nilai kosong tetap kosong.
- Negara asal dari akhir alamat, provinsi + kode pos Indonesia, lalu poligon negara offline Natural Earth. Koreksi manual dilindungi saat ingestion ulang.
- Filter AND antarkelompok, negara multi OR/semua, produk, lokasi, kontak, rating/review, pipeline, consent, job, tanggal, pengurutan, halaman 25/50/100, segmen bernama.
- Pipeline massal transaksional, catatan, aktivitas, formulir consent terpisah, dan pencatatan pemeriksaan WA dengan tanggal/metode. Status WA aktif tidak melewati consent gate.
- Worker enrichment terbatas pada domain yang sama, maksimum 10 halaman; temuan selalu suspected. Review dan bukti manual divalidasi di API. Impor direktori CSV menghasilkan suspected.
- CSV analisis berurutan 23 kolom PRD, mengikuti filter dan urutan aktif. Daftar kirim ditolak bila satu lead belum opted_in/replied. CSV melindungi dari formula spreadsheet; nomor `+62…` diberi apostrof sebagai penanda teks saat export.
- Tenant aktif diambil dari sesi, bukan parameter klien. Dedupe unik `(tenant_id, place_id)`; role keanggotaan berlaku per organisasi. Akses dicabut pada permintaan berikutnya.
- PostgreSQL memakai role web nonsuperuser, tanpa BYPASSRLS. RLS melindungi tabel inti tenant. Worker memakai koneksi terpisah. Platform Admin hanya melihat ringkasan tenant dan mengubah kredit/status dengan alasan tercatat, tanpa jalur mengedit lead tenant lain.
- API key Pro ditampilkan sekali, disimpan sebagai hash, dibatasi 600 permintaan/jam, dan hanya memiliki kemampuan Operator/Reviewer tenant. Pencabutan anggota atau downgrade menonaktifkan aksesnya.

## Kredit beta dan Tripay Sandbox

Free mendapat **30 kredit**. Harga Starter Rp99.000 dan Pro Rp249.000 serta definisi kredit tetap **usulan**, sesuai PRD. Halaman paket menampilkan status ini.

Aturan yang diimplementasikan untuk uji teknis:

- Lead baru dengan telepon: 1 kredit. Email yang benar-benar ditemukan: +1 kredit. Duplikat tidak ditagih lagi.
- Job mencadangkan `max_credits` dalam transaksi terkunci sebelum antrean. Setelah hasil tersedia, seluruh kebutuhan dihitung sebelum ingestion. Bila melebihi reservasi, ingestion ditahan seluruhnya, arsip tetap ada, dan reservasi dikembalikan. Tidak ada import sebagian karena kehabisan kredit.
- Kredit terpakai diselesaikan melalui ledger consume/refund append-only. Job gagal total mengembalikan reservasi. Resume hanya menghitung lead baru pada percobaan berikutnya.
- Export CSV tidak memotong kredit lagi pada build beta ini; Free dibatasi 30 baris dan filter dasar. Definisi biaya export final belum diputuskan.
- Upgrade aktif hanya setelah callback PAID yang sah. Callback divalidasi HMAC-SHA256 dari raw body, event, invoice, referensi, dan nominal; pengiriman ulang tidak menggandakan kredit.
- Downgrade dijadwalkan pada akhir periode. Default sandbox: periode 30 hari, masa tenggang past_due 7 hari, kredit tersisa tidak kedaluwarsa otomatis. Kebijakan produksi belum final.

Gateway yang dipilih pengguna: **Tripay Sandbox**. Isi `TRIPAY_API_KEY`, `TRIPAY_PRIVATE_KEY`, `TRIPAY_MERCHANT_CODE`, dan `BASE_URL` HTTPS. Channel diambil dari merchant, bukan diasumsikan aktif. Setelah aturan beta disepakati, set `BILLING_BETA_ENABLED=1`. Tidak ada URL atau mode pembayaran produksi pada kode ini. Credentials dan callback dari merchant sungguhan belum diuji.

## Backup dan pemulihan

Service `backup` membuat dump harian pada folder `backups/` di luar container. Tidak ada penghapusan otomatis karena retensi masih keputusan terbuka.

Untuk backup saat diperlukan:

```sh
docker compose exec -T postgres pg_dump -U postgres -d pokoscrap -Fc > backups/manual.dump
```

Untuk uji pemulihan ke database terpisah:

```sh
docker compose exec postgres createdb -U postgres pokoscrap_restore_test
docker compose exec -T postgres pg_restore -U postgres -d pokoscrap_restore_test --no-owner < backups/manual.dump
docker compose exec postgres psql -U postgres -d pokoscrap_restore_test -c 'SELECT count(*) FROM leads;'
```

Jangan menimpa database aktif saat menguji restore. Arsip mentah dan outbox tidak termasuk pg_dump; cadangkan folder runtime terpisah sesuai kebijakan akses dan retensi.

## Pengujian

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=. POKO_WORKERS=0 .venv/bin/pytest tests -q
```

Tests memakai database SQLite sementara untuk kontrak dan kasus kegagalan. Deployment memakai PostgreSQL. Uji PostgreSQL/RLS, worker gosom, dan restore dilakukan terpisah; ringkasannya ada di VALIDASI.md. Gunakan satu replika untuk tiap worker pada build ini; antrean database belum mendukung klaim job oleh banyak replika.

## Batas yang masih terbuka

- Mode cepat gosom tersedia. Mode manager gosom belum diimplementasikan. Redis disediakan oleh Compose; antrean dashboard saat ini memakai tabel PostgreSQL yang persisten.
- Batas hasil per sel belum dapat diukur andal dari semua log gosom. `hit_result_cap` hanya aktif bila log menyatakan cap. UI menyatakan keterbatasan cakupan; jangan menganggap false sebagai bukti cakupan lengkap.
- Worker mencari produk melalui kosakata awal dan alias negara; reviewer tetap memutuskan. Normalisasi sinonim produk lintas bahasa belum lengkap.
- Natural Earth resolusi 110m memberi fallback kasar, terutama di pesisir/pulau kecil; hasil tanpa kecocokan dibiarkan kosong.
- Belum ada migrasi dari database aplikasi lama; paket ini untuk database baru. Belum ada integrasi Next.js/Better Auth/Supabase. PRD mencantumkannya sebagai acuan; implementasi ini memakai FastAPI dan sesi server dengan PostgreSQL RLS.
- Hosting produksi, domain, harga/kredit final, refund/rollover, retensi, wawancara, syarat layanan yang ditinjau, dan beta berbayar nyata belum selesai. Billing publik tetap ditutup.

## Sumber dan aset

- [gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper): engine MIT. Digest yang diuji dipin pada Compose.
- [Dokumentasi Tripay](https://tripay.co.id/developer?tab=callback): kontrak sandbox dan callback.
- [Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/): poligon negara public domain, dibundel offline dari repositori resminya.
- Plus Jakarta Sans, SIL Open Font License; lisensi ada di `dist/assets/FONT-LICENSE.txt`.
- `dist/assets/logo.svg`: logo yang diberikan pengguna, dipakai utuh.
- `dist/demo.js`: seluruh bisnis, kontak tersamar, bukti `.example`, job, dan angka pratinjau bersifat sintetis. Data gosom nyata tidak dipublikasikan pada pratinjau.

Desain memakai skill design-taste-frontend, arah Accent ladder, seed 504196339, warna dan tipografi disesuaikan keluarga Poko. Elemen khas: tiga kontak utama dan alur consent. Shadow hanya untuk dialog dan toast yang mengambang.
