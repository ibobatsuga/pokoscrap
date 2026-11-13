const googleIcon = `<svg class="google-icon" viewBox="0 0 24 24" aria-hidden="true"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/></svg>`;
import {initialDemo,filterDemo,demoCountries} from './demo.js';

const DEMO=window.POKO_DEMO===true;
if(!DEMO&&new URLSearchParams(location.search).get('invite'))sessionStorage.setItem('pokoscrap-invite',new URLSearchParams(location.search).get('invite'));
const $=s=>document.querySelector(s);
const e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>Number(n||0).toLocaleString('id-ID');
const date=s=>s?new Date(s).toLocaleDateString('id-ID',{day:'numeric',month:'short',year:'numeric'}):'—';
const safeUrl=s=>{try{const u=new URL(s);return ['https:','http:'].includes(u.protocol)?u.href:'#';}catch{return '#';}};
const PIPE=['Baru','Dihubungi','Follow-up','Deal','Tolak'];
const LABEL={done:'Selesai',draft:'Draft',queued:'Antrean',running:'Berjalan',ingesting:'Memproses',failed:'Gagal',stopped:'Dihentikan',confirmed:'Terkonfirmasi',suspected:'Perlu review',rejected:'Ditolak',none:'Belum ada consent',invited:'Diundang',opted_in:'Opt-in',replied:'Membalas',opted_out:'Opt-out'};
const paths={grid:'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',search:'m21 21-4.3-4.3M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0',leads:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M16 3a4 4 0 0 1 0 8M22 21v-2a4 4 0 0 0-3-3.87M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0',jobs:'M8 4h8v4H8zM8 6H5v15h14V6h-3M8 12h8M8 16h5',review:'m9 12 2 2 4-4M20 12a8 8 0 1 1-16 0 8 8 0 0 1 16 0',settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2',plus:'M12 5v14M5 12h14',chevron:'m9 5 7 7-7 7',arrow:'M5 12h14m-5-5 5 5-5 5',external:'M14 3h7v7m0-7L10 14M10 3H4v17h17v-6',download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',phone:'M6 3h4l2 5-3 2c2 3 3 4 5 5l2-3 5 2v4c-1 4-8 2-12-2S2 5 6 3',mail:'M3 5h18v14H3zM3 6l9 7 9-7',chat:'M21 11a9 9 0 0 1-9 9H3l2-5a9 9 0 1 1 16-4M8 10h8M8 14h5',globe:'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0M3 12h18M12 3c-6 6-6 12 0 18 6-6 6-12 0-18',pin:'M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0M15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0',shield:'m12 2 9 4v6c0 6-9 10-9 10S3 18 3 12V6zM8 12l3 3 5-6',info:'M12 8h.01M12 11v6M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',clock:'M12 7v5l3 2M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',refresh:'M20 7v5h-5M4 17v-5h5M20 12a8 8 0 0 0-14-5M4 12a8 8 0 0 0 14 5',filter:'M3 5h18M6 12h12M10 19h4M8 3v4M15 10v4M12 17v4',menu:'M4 6h16M4 12h16M4 18h16',close:'m6 6 12 12M18 6 6 18',logout:'M9 3H4v18h5M9 12h12m-5-5 5 5-5 5',check:'m5 12 4 4L19 6',file:'M14 2H4v20h16V8zM14 2v6h6M8 13h8M8 17h5',star:'m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9z',credit:'M3 5h18v14H3zM3 9h18M7 15h3',chart:'M4 3v18h17M8 16v-5M13 16V7M18 16v-8',building:'M5 21V3h14v18M9 7h1M14 7h1M9 11h1M14 11h1M9 15h1M14 15h1M10 21v-3h4v3',copy:'M9 9h12v12H9zM15 5V3H3v12h2',stop:'M5 5h14v14H5z',archive:'M3 3h18v5H3zM5 8v13h14V8M9 12h6',key:'M14 5a5 5 0 1 1-3 8L3 21v-5l6-6a5 5 0 0 1 5-5'};
const icon=n=>`<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[n]||paths.info}"/></svg>`;
const button=(text,action,ico='',cls='',id='')=>`<button class="button ${cls}" data-action="${action}" ${id?`data-id="${e(id)}"`:''}>${ico?icon(ico):''}${e(text)}</button>`;
const link=(text,path,ico='',cls='button')=>`<a class="${cls}" href="#/${path}">${ico?icon(ico):''}${e(text)}</a>`;
const tag=(value,label)=>`<span class="tag ${e(value)}">${e(label||LABEL[value]||value)}</span>`;
const initials=s=>s.split(' ').slice(0,2).map(s=>s[0]).join('');
const empty=(title,text,action='')=>`<div class="empty">${icon('search')}<h3>${e(title)}</h3><p>${e(text)}</p>${action}</div>`;
let demo;try{demo=JSON.parse(localStorage.getItem('pokoscrap-demo-v2'))||initialDemo();}catch{demo=initialDemo();}
let state={user:null,countries:demoCountries,filters:{},page:1,size:25,selected:new Set(),showFilters:false,jobStatus:'',orgs:[],credits:{balance:30},route:'',pendingInvite:DEMO?null:sessionStorage.getItem('pokoscrap-invite')};
const persist=()=>localStorage.setItem('pokoscrap-demo-v2',JSON.stringify(demo));
let toastTimer;
function toast(message){$('#toast').textContent=message;$('#toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('show'),4500);}
function human(error){const detail=error.detail??error.message??error;if(typeof detail==='object')return detail.message||Object.values(detail).join(' ');return String(detail);}
async function api(path,method='GET',body){const response=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json','X-Poko-Request':'1'},...(body?{body:JSON.stringify(body)}:{})});if(!response.ok){let err;try{err=await response.json();}catch{err={detail:'Server tidak merespons.'};}if(response.status===401&&path!=='/login'){state.user=null;render();}throw err;}return response.headers.get('content-type')?.includes('text/csv')?response.text():response.json();}
const country=code=>state.countries.find(c=>c.code===code)?.name||code||'Belum diketahui';
const isAdmin=()=>state.user?.roles.some(r=>['Admin','Owner'].includes(r));
const canOperate=()=>state.user?.roles.some(r=>['Admin','Owner','Operator'].includes(r));
const canReview=()=>state.user?.roles.some(r=>['Admin','Owner','Reviewer'].includes(r));
function activity(lead,type,payload){lead.activities.unshift({id:crypto.randomUUID(),actor:state.user.name,type,created_at:new Date().toISOString(),payload});persist();}
function modal(title,html){$('#modal').innerHTML=`<div class="modal-head"><h2>${e(title)}</h2><button class="icon-button" data-action="close-modal" aria-label="Tutup dialog">${icon('close')}</button></div><div class="modal-body">${html}</div>`;$('#modal').showModal();}
function options(values,selected='',placeholder='Semua'){return `<option value="">${e(placeholder)}</option>`+values.map(v=>{let value=typeof v==='string'?v:v.value,label=typeof v==='string'?v:v.label;return `<option value="${e(value)}" ${String(selected)===String(value)?'selected':''}>${e(label)}</option>`;}).join('');}
const selectField=(label,name,values,value='',placeholder='Semua')=>`<div class="field"><label for="${e(name)}">${e(label)}</label><select id="${e(name)}" name="${e(name)}">${options(values,value,placeholder)}</select></div>`;
function head(title,subtitle,actions=''){return `<div class="page-head"><div><h1>${e(title)}</h1><p>${e(subtitle)}</p></div><div class="actions">${actions}</div></div>`;}
function shell(content,title){
  const reviewCount = DEMO ? 0 : state.reviewCount;
  const route = state.route.split('/')[0] || 'overview';
  const nav = (name,path,ico,badge='') => `<a class="nav-item ${route===path?'active':''}" href="#/${path}">${icon(ico)}${e(name)}${badge?`<span class="count">${badge}</span>`:''}</a>`;
  return `<div class="shell">
    <div class="mobile-overlay" data-action="menu-close"></div>
    <aside class="sidebar" aria-label="Navigasi utama">
      <a class="brand" href="#/overview">
        <img src="/assets/logo.svg" alt="Logo PokoScrap">
        <div>
          <div class="brand-name">PokoScrap</div>
          <small>by FLUXY.ID</small>
        </div>
      </a>
      <nav>
        <div class="nav-label">Discovery & Scraping</div>
        ${nav('Ringkasan','overview','grid')}
        ${nav('Job Scraping','jobs','search')}
        ${nav('Database Lead','leads','leads')}
        ${nav('Review Enrichment','review','review',reviewCount)}

        <div class="nav-label second">Integrasi & Developer</div>
        ${nav('API Key & MCP','api-mcp','key')}

        <div class="nav-label second">Organisasi & Billing</div>
        ${nav('Billing & Paket','billing','credit')}
        ${nav('Pemakaian Kredit','credits','chart')}
        ${isAdmin()?nav('Pengaturan','settings','settings'):''}
        ${state.user?.platform_admin?nav('Admin SaaS','admin','building'):''}
      </nav>
      <a class="nav-extra" href="#/billing">
        ${icon('credit')}
        <div>
          <strong>${e(state.credits.plan||'Free')} · ${fmt(state.credits.balance)} kredit</strong>
          <p>Lihat paket & pemakaian</p>
        </div>
        ${icon('chevron')}
      </a>
      <div class="account">
        <div class="avatar">${e(initials(state.user.name))}</div>
        <div>
          <strong>${e(state.user.name)}</strong>
          <small>${e(state.user.roles.join(' / '))}</small>
        </div>
        <button class="icon-button" data-action="logout" aria-label="Keluar akun">${icon('logout')}</button>
      </div>
    </aside>
    <div class="main">
      <header class="topbar">
        <div class="topbar-left">
          <button class="icon-button menu-toggle" data-action="menu-open" aria-label="Buka menu navigasi">${icon('menu')}</button>
          <div class="crumb"><span>Workspace</span>${icon('chevron')}<b>${e(title)}</b></div>
        </div>
        <div class="top-actions">
          <span class="source"><i class="dot"></i>Google Maps Engine</span>
          <span class="divider"></span>
          <button class="button small" data-action="switch-org">${icon('building')}<span>${e(state.user.organization_name||'Workspace')}</span>${icon('chevron')}</button>
          <div class="avatar">${e(initials(state.user.name))}</div>
        </div>
      </header>
      <main class="content" id="content">
        ${state.pendingInvite?`<div class="alert"><span>Undangan organisasi tersedia untuk akun ini.</span>${button('Terima undangan','accept-invite','check','small')}</div>`:''}
        ${content}
        <footer class="footer">
          <span>PokoScrap · Bagian dari ekosistem SaaS Poko series · Google Maps Discovery</span>
          <span>Telepon, WhatsApp, email. Siap produksi.</span>
        </footer>
      </main>
    </div>
  </div>`;
}
function loginScreen(register=false){
  return `<div class="login-page">
    <section class="login-story">
      <a class="brand" href="#/">
        <img src="/assets/logo.svg" alt="Logo PokoScrap">
        <div>
          <div class="brand-name">PokoScrap</div>
          <small>by FLUXY.ID</small>
        </div>
      </a>
      <div>
        <h2>Temukan bisnis.<br>Bangun peluang baru.</h2>
        <p>Ubah pencarian Google Maps menjadi database lead bisnis siap prospek. Nomor telepon, WhatsApp terverifikasi, dan email dalam satu workspace.</p>
        <div class="login-features">
          <div class="login-feature-item">${icon('check')} <span>Scraping Google Maps presisi dengan gosom</span></div>
          <div class="login-feature-item">${icon('check')} <span>Ekstraksi otomatis nomor telepon, WhatsApp & email</span></div>
          <div class="login-feature-item">${icon('check')} <span>Filter komoditas produk & verifikasi negara tujuan ekspor</span></div>
          <div class="login-feature-item">${icon('check')} <span>Terhubung ke Claude, Cursor & AI via MCP Server & API Key</span></div>
        </div>
      </div>
      <small style="color: #6b7280;">PokoScrap · Bagian dari ekosistem SaaS Poko series.</small>
    </section>

    <section class="login-form-container">
      <h1>${register?'Buat Workspace Baru':'Masuk ke Workspace'}</h1>
      <p>${register?'Mulai dari paket Free dengan 30 kredit awal.':'Kelola pencarian, kontak bisnis terverifikasi, dan ekspor CRM.'}</p>

      <button class="google-button" data-action="google-login" type="button">
        ${googleIcon}
        <span>${register?'Daftar dengan Google':'Masuk dengan Google'}</span>
      </button>

      <div class="auth-divider">atau masuk dengan email</div>

      <form id="auth-form" data-register="${register}">
        ${register?'<div class="field"><label for="auth-name">Nama lengkap</label><input id="auth-name" name="name" required autocomplete="name" placeholder="Nama lengkap Anda"></div>':''}
        <div class="field">
          <label for="auth-email">Email bisnis</label>
          <input id="auth-email" name="email" type="email" required autocomplete="email" placeholder="nama@perusahaan.com">
        </div>
        <div class="field">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <label for="auth-password" style="margin: 0;">Kata sandi</label>
            ${!register?'<button type="button" class="text-button" data-action="forgot" style="font-size: 11px; padding: 0;">Lupa sandi?</button>':''}
          </div>
          <input id="auth-password" name="password" type="password" required minlength="${register?12:1}" autocomplete="${register?'new-password':'current-password'}" placeholder="${register?'Minimal 12 karakter':'Masukkan kata sandi'}">
        </div>
        <div id="auth-error" role="alert"></div>
        <button class="button primary" style="width: 100%; min-height: 42px; margin-top: 8px;" type="submit">
          ${register?'Daftar & Verifikasi Email':'Masuk ke PokoScrap'} ${icon('arrow')}
        </button>
      </form>

      <div class="login-footer">
        ${register?'<a href="#/login">Sudah punya akun? Masuk di sini</a>':'<a href="#/register">Belum punya akun? Daftar gratis</a>'}
      </div>
    </section>
  </div>`;
}
function demoOverview(){const counts={};for(const l of demo.leads)counts[l.country_origin_code]=(counts[l.country_origin_code]||0)+1;return {total:demo.leads.length,new_week:demo.leads.filter(l=>l.first_seen_at>='2026-11-05T15:00:00Z').length,confirmed:demo.leads.filter(l=>l.evidence.some(e=>e.kind==='country'&&e.status==='confirmed')).length,running:demo.jobs.filter(j=>['queued','running','ingesting'].includes(j.status)).length,review:demo.leads.reduce((s,l)=>s+l.evidence.filter(e=>e.status==='suspected').length,0),countries:Object.entries(counts).map(([code,count])=>({code,count})).sort((a,b)=>b.count-a.count),contacts:Object.fromEntries(['phone','whatsapp','email'].map(k=>[k,demo.leads.filter(l=>l['has_'+k]).length])),jobs:demo.jobs.filter(j=>!j.archived).slice(0,3),recent:demo.leads.slice(0,4),pipeline:PIPE.map(status=>({status,count:demo.leads.filter(l=>l.pipeline_status===status).length}))};}
function overviewScreen(data){state.reviewCount=data.review;const ratio=n=>data.total?Math.round(n/data.total*100):0;const pending=DEMO?demo.leads.filter(l=>l.evidence.some(e=>e.status==='suspected')).slice(0,3):data.recent.filter(l=>l.evidence.some(e=>e.status==='suspected')).slice(0,3);const kpis=[['Total lead',data.total,'Tersimpan di workspace','leads'],['Lead baru',data.new_week,'Dalam 7 hari terakhir','clock'],['Ekspor terkonfirmasi',data.confirmed,'Memiliki bukti yang direview','globe'],['Job berjalan',data.running,'Antrean, scraping & ingestion','jobs']];return head('Ringkasan Workspace','Pantau pencarian, kualitas kontak, dan peluang bisnis Anda.',canOperate()?link('Buat Job Scraping','jobs/new','plus','button primary'):'')+`<section class="kpis" aria-label="Statistik workspace">${kpis.map(([label,value,sub,ico])=>`<div class="kpi"><div class="kpi-label">${e(label)}${icon(ico)}</div><div class="kpi-value">${fmt(value)}</div><div class="kpi-sub">${e(sub)}</div></div>`).join('')}</section><div class="overview-grid"><section class="panel contact-panel"><div class="panel-head"><div><h2>Kelengkapan kontak</h2><p>Tiga output utama dari hasil discovery Anda</p></div><span class="tag">${fmt(data.total)} lead</span></div><div class="contact-summary"><div><strong>${fmt(data.contacts.phone)}<small>lead dengan telepon</small></strong><p>Kontak yang tersedia, tanpa mengisi tebakan.</p></div><div>${ratio(data.contacts.phone)}% dari seluruh lead</div></div>${[['phone','Telepon','phone'],['whatsapp','WhatsApp','chat'],['email','Email','mail']].map(([key,name,ico])=>`<div class="contact-bar"><span>${icon(ico)}${name}</span><div class="track" role="meter" aria-label="${name}" aria-valuemin="0" aria-valuemax="${data.total||1}" aria-valuenow="${data.contacts[key]}"><div class="fill" style="width:${ratio(data.contacts[key])}%"></div></div><b>${fmt(data.contacts[key])}<span class="subline">${ratio(data.contacts[key])}%</span></b></div>`).join('')}<div class="contact-note">${icon('info')}<span>WhatsApp diturunkan dari nomor seluler. Statusnya belum terverifikasi dan belum menjadi izin kirim.</span></div></section><section class="panel"><div class="panel-head"><div><h2>Sebaran negara asal</h2><p>Lokasi bisnis dari alamat Google Maps</p></div>${icon('globe')}</div><div class="country-list">${data.countries.length?data.countries.map(c=>`<div class="country-row"><span><i class="country-code">${e(c.code||'—')}</i>${e(country(c.code))}</span><div class="track"><div class="fill" style="width:${data.total?c.count/data.total*100:0}%"></div></div><b>${fmt(c.count)}</b></div>`).join(''):'<div class="chart-empty">Belum ada negara asal tercatat.</div>'}</div><div class="country-foot"><span>${data.countries.length} negara terdeteksi</span><a href="#/leads" class="text-button">Lihat database ${icon('arrow')}</a></div></section></div><section class="panel workflow"><div class="workflow-title">${icon('shield')}<div><h3>Alur consent terjaga</h3><p>Discovery adalah langkah pertama.</p></div></div><div class="workflow-stages">${['Discover','Invite','Gate','Send'].map((s,i)=>`${i?icon('chevron'):''}<div class="stage ${i===0?'current':''}"><span class="stage-index">${i===0?icon('check'):i+1}</span>${s}</div>`).join('')}</div></section><div class="bottom-grid"><section class="panel"><div class="panel-head"><div><h2>Job scraping terbaru</h2><p>Pencarian bisnis di workspace Anda</p></div>${link('Lihat semua','jobs','arrow','text-button')}</div>${data.jobs.length?`<div class="table-wrap"><table><thead><tr><th>Nama pencarian</th><th>Status</th><th class="num">Lead baru</th><th></th></tr></thead><tbody>${data.jobs.slice(0,3).map(j=>`<tr><td><a class="job-title" href="#/jobs/${e(j.id)}"><span class="job-mark">${icon('pin')}</span><div><span class="name">${e(j.name)}</span><span class="subline">${date(j.created_at)} · ${e(j.geo_mode==='grid'?'Mode grid':'Titik & radius')}</span></div></a></td><td>${tag(j.status)}</td><td class="num">${fmt(j.inserted_count)}</td><td><a href="#/jobs/${e(j.id)}" aria-label="Lihat ${e(j.name)}">${icon('chevron')}</a></td></tr>`).join('')}</tbody></table></div>`:empty('Mulai pencarian pertama','Buat job dari kata kunci dan area bisnis.',link('Buat job','jobs/new','plus','button small'))}</section><section class="panel"><div class="panel-head"><div><h2>Menunggu review</h2><p>Usulan ekspor memerlukan bukti</p></div>${tag('suspected',fmt(data.review)+' usulan')}</div>${pending.length?pending.map(l=>`<a class="mini-lead" href="#/review"><div class="initials">${e(initials(l.business_name))}</div><div><strong>${e(l.business_name)}</strong><p>${l.evidence.filter(e=>e.status==='suspected').map(v=>e(v.kind==='country'?country(v.value):v.value)).join(' · ')}</p></div>${icon('chevron')}</a>`).join(''):empty('Antrean sudah bersih','Usulan dari enrichment akan muncul di sini.')}<div style="margin-top:14px">${link('Buka antrean review','review','arrow','text-button')}</div></section></div>`;}
async function getLeads(){if(DEMO){const data=filterDemo(demo.leads,state.filters);return {total:data.length,page:state.page,page_size:state.size,data:data.slice((state.page-1)*state.size,state.page*state.size)};}return api('/leads?'+new URLSearchParams({...state.filters,page:state.page,page_size:state.size}));}
function filterPanel(){const f=state.filters;const countries=state.countries.map(c=>({value:c.code,label:c.name}));const unique=key=>DEMO?[...new Set(demo.leads.map(l=>l[key]).filter(Boolean))]:(state.facets?.[key]||[]);const fields=[['Negara asal','origin',countries],['Tujuan ekspor','destination',countries],['Produk ekspor','product',DEMO?[...new Set(demo.leads.flatMap(l=>l.evidence.filter(e=>e.kind==='product').map(e=>e.value)))]:['kopi','coffee','furnitur','furniture','rempah','spices','kelapa','coconut','rotan','rattan','kakao','cocoa','tekstil','textile','kerajinan','handicraft']],['Pipeline','pipeline_status',PIPE],['Kategori','category',unique('category')],['Kota','city',unique('city')],['Provinsi','province',unique('province')],['Consent','consent_basis',Object.entries(LABEL).filter(([k])=>['none','invited','opted_in','replied','opted_out'].includes(k)).map(([value,label])=>({value,label}))],['Telepon','has_phone',[{value:'true',label:'Punya telepon'},{value:'false',label:'Tanpa telepon'}]],['WhatsApp','has_whatsapp',[{value:'true',label:'Punya WhatsApp turunan'},{value:'false',label:'Tanpa WhatsApp'}]],['Email','has_email',[{value:'true',label:'Punya email'},{value:'false',label:'Tanpa email'}]],['Website','has_website',[{value:'true',label:'Punya website'},{value:'false',label:'Tanpa website'}]],['Status WhatsApp','whatsapp_status',['derived_unverified','active','inactive','unknown']],['Job penemu','job',(state.jobs||demo.jobs).map(j=>({value:j.id,label:j.name}))]];return `<form id="filter-form" class="filters">${fields.map(([label,name,values])=>selectField(label,name,values,f[name])).join('')}<div><label for="rating_min">Rating minimal</label><input id="rating_min" name="rating_min" type="number" min="0" max="5" step=".1" value="${e(f.rating_min||'')}"></div><div><label for="review_min">Review minimal</label><input id="review_min" name="review_min" type="number" min="0" value="${e(f.review_min||'')}"></div><div><label for="date_from">Ditemukan sejak</label><input id="date_from" name="date_from" type="date" value="${e(f.date_from||'')}"></div><div><label for="date_to">Ditemukan sampai</label><input id="date_to" name="date_to" type="date" value="${e(f.date_to||'')}"></div><div class="full inline-checks"><label class="checkline"><input type="checkbox" name="suspected" ${String(f.suspected)==='true'?'checked':''}> Sertakan yang diduga (suspected)</label><label class="checkline"><input type="checkbox" name="destination_all" ${String(f.destination_all)==='true'?'checked':''}> Wajib semua negara tujuan</label><span class="small">Beberapa negara: gunakan pilihan tambahan.</span></div><div class="full form-row"><div><label for="origin_multi">Kode negara asal tambahan</label><input id="origin_multi" name="origin_multi" placeholder="Contoh: ID,MY" value="${e((f.origin||'').includes(',')?f.origin:'')}"></div><div><label for="destination_multi">Kode negara tujuan tambahan</label><input id="destination_multi" name="destination_multi" placeholder="Contoh: JP,AU" value="${e((f.destination||'').includes(',')?f.destination:'')}"></div></div><div class="full actions"><button class="button primary" type="submit">Terapkan filter</button>${button('Reset filter','reset-filters','refresh')}</div></form>`;}
function leadsTable(data,compact=false){if(!data.length)return empty('Belum ada lead yang sesuai','Ubah filter atau jalankan pencarian Google Maps.');return `<div class="table-wrap"><table class="lead-table"><thead><tr>${!compact?'<th><input type="checkbox" id="select-all" aria-label="Pilih semua lead di halaman ini"></th>':''}<th class="identity">Nama bisnis / lokasi</th><th>Telepon</th><th>WhatsApp</th><th>Email</th><th class="num">Rating</th><th>Pipeline</th></tr></thead><tbody>${data.map(l=>`<tr>${!compact?`<td><input type="checkbox" data-select="${e(l.id)}" aria-label="Pilih ${e(l.business_name)}" ${state.selected.has(l.id)?'checked':''}></td>`:''}<td class="identity"><a class="name" href="#/leads/${e(l.id)}">${e(l.business_name)}</a><span class="subline">${e(l.city||'Lokasi belum lengkap')} · ${e(country(l.country_origin_code))}</span><span class="subline">${e(l.category)}</span></td><td class="contact">${e(l.phone_normalized||'—')}<span class="subline">${l.has_phone?'Dari Google Maps':'Belum tersedia'}</span></td><td class="contact">${e(l.whatsapp_number||'—')}<span class="subline">${l.has_whatsapp?'Turunan · belum diverifikasi':'Belum tersedia'}</span></td><td class="contact">${e(l.emails?.[0]||'—')}<span class="subline">${l.has_email?'Belum diverifikasi':'Belum tersedia'}</span></td><td class="num rating">${l.rating?icon('star')+' '+Number(l.rating).toFixed(1):'—'}<span class="subline">${l.review_count===null?'—':fmt(l.review_count)} ulasan</span></td><td>${tag(l.pipeline_status)}</td></tr>`).join('')}</tbody></table></div>`;}
function leadsScreen(result,segments){state.lastLeadResult=result;const f=state.filters;const n=Object.entries(f).filter(([k,v])=>v&&k!=='sort'&&k!=='q').length;return head('Database Lead','Temukan segmen bisnis dari tiga kontak utama.',canOperate()?button('Export CSV ('+fmt(result.total)+')','export','download','primary'):'')+`<section class="panel"><div class="toolbar"><div class="search">${icon('search')}<input id="lead-search" aria-label="Cari nama bisnis, alamat, atau produk" placeholder="Cari bisnis, alamat, atau produk…" value="${e(f.q||'')}"></div><div class="actions">${button('Filter'+(n?' ('+n+')':''),'toggle-filters','filter',state.showFilters?'green':'')}<select id="segment-select" aria-label="Segmen tersimpan">${options(segments.map(s=>({value:s.id,label:s.name})),'','Segmen tersimpan')}</select>${canOperate()?button('Simpan segmen','save-segment','plus'):''}</div></div>${state.showFilters?filterPanel():''}${String(f.suspected)==='true'?`<div class="alert">${icon('info')}Temuan suspected ikut ditampilkan. Negara dan produk belum semuanya terkonfirmasi.</div>`:''}<div class="toolbar"><span class="small"><b>${fmt(result.total)}</b> lead ditemukan${n?' dengan filter aktif':''}</span><div class="actions"><select id="lead-sort" aria-label="Urutkan lead">${options([{value:'newest',label:'Terbaru ditemukan'},{value:'rating',label:'Rating tertinggi'},{value:'reviews',label:'Review terbanyak'}],f.sort||'newest','Urutkan')}</select><select id="page-size" aria-label="Jumlah per halaman">${[25,50,100].map(n=>`<option ${state.size===n?'selected':''}>${n}</option>`).join('')}</select></div></div>${state.selected.size?`<div class="bulk"><span>${state.selected.size} lead dipilih</span><div class="actions"><select id="bulk-status" aria-label="Status pipeline massal">${PIPE.map(p=>`<option>${p}</option>`).join('')}</select>${button('Ubah pipeline','bulk-pipeline','check','primary small')}${button('Batal','clear-selection','','small')}</div></div>`:''}${leadsTable(result.data)}<div class="pagination"><span>${result.total?(state.page-1)*state.size+1:0}–${Math.min(state.page*state.size,result.total)} dari ${fmt(result.total)} lead</span><div class="actions"><button class="button small" data-action="prev-page" ${state.page===1?'disabled':''}>Sebelumnya</button><button class="button small" data-action="next-page" ${state.page*state.size>=result.total?'disabled':''}>Berikutnya</button></div></div></section>`;}
function jobsScreen(jobs){state.jobs=jobs;const shown=jobs.filter(j=>!j.archived&&(!state.jobStatus||j.status===state.jobStatus));return head('Job Scraping','Kelola pencarian Google Maps dan lihat hasilnya.',canOperate()?link('Buat Job Scraping','jobs/new','plus','button primary'):'')+`<div class="tabs">${[['','Semua job'],['draft','Draft'],['running','Berjalan'],['done','Selesai'],['failed','Gagal']].map(([s,label])=>`<button class="tab ${s===state.jobStatus?'active':''}" data-action="job-tab" data-id="${s}">${label} <span class="small">${jobs.filter(j=>!s||j.status===s).length}</span></button>`).join('')}</div><section class="panel">${shown.length?`<div class="table-wrap"><table class="job-table"><thead><tr><th>Nama job / area</th><th>Status</th><th class="num">Ditemukan</th><th class="num">Baru</th><th class="num">Duplikat</th><th>Dibuat</th><th>Aksi</th></tr></thead><tbody>${shown.map(j=>`<tr><td><a class="job-title" href="#/jobs/${e(j.id)}"><div class="job-mark">${icon('pin')}</div><div><strong class="name">${e(j.name)}</strong><span class="subline">${j.queries.length} query · ${j.geo_mode==='grid'?'Grid':'Titik & radius'} · Email ${j.email_enabled?'aktif':'nonaktif'}</span></div></a></td><td>${tag(j.status)}</td><td class="num">${fmt(j.found_count)}</td><td class="num">${fmt(j.inserted_count)}</td><td class="num">${fmt(j.duplicate_count)}</td><td><span class="small">${date(j.created_at)}</span></td><td><div class="actions"><a class="icon-button" href="#/jobs/${e(j.id)}" aria-label="Detail job ${e(j.name)}">${icon('chevron')}</a>${canOperate()?`<button class="icon-button" data-action="duplicate-job" data-id="${e(j.id)}" aria-label="Duplikasi ${e(j.name)}">${icon('copy')}</button>`:''}</div></td></tr>`).join('')}</tbody></table></div>`:empty('Belum ada job di sini','Mulai pencarian baru dari kata kunci dan area.',link('Buat job','jobs/new','plus','button small'))}</section>`;}
function newJobScreen(){return head('Buat Job Scraping','Tentukan bisnis dan area yang ingin ditemukan.',link('Kembali','jobs','','button'))+`<div class="form-layout"><form id="job-form" class="panel form-panel"><section class="form-section"><h2>Pencarian bisnis</h2><p>Satu kata kunci per baris. Query duplikat dibuang otomatis.</p><div class="field"><label for="job-name">Nama job</label><input id="job-name" name="name" placeholder="Contoh: Produsen kopi · Yogyakarta" required maxlength="120"></div><div class="field"><label for="queries">Kata kunci</label><textarea id="queries" name="queries" placeholder="produsen kopi arabika di Yogyakarta&#10;eksportir kopi di Yogyakarta" required></textarea><span class="query-count" id="query-count">0 query unik</span></div></section><section class="form-section"><h2>Area pencarian</h2><p>Gunakan grid untuk cakupan kota atau kabupaten.</p><div class="form-row"><div class="field"><label for="area-name">Nama area</label><input id="area-name" name="area_name" placeholder="Contoh: Yogyakarta" required></div><div class="field"><label for="geo-mode">Cakupan</label><select id="geo-mode" name="geo_mode"><option value="grid">Kota / kabupaten — grid</option><option value="point">Lokasi — titik & radius</option></select></div></div><div id="grid-fields" class="field"><label for="grid-bbox">Batas kotak area</label><input id="grid-bbox" name="grid_bbox" placeholder="-7.85,110.30,-7.73,110.43"><small>Latitude minimum, longitude minimum, latitude maksimum, longitude maksimum.</small></div><div id="point-fields" class="form-row three" hidden><div class="field"><label for="latitude">Latitude</label><input id="latitude" name="latitude" type="number" step="any" min="-90" max="90" placeholder="-7.7829"></div><div class="field"><label for="longitude">Longitude</label><input id="longitude" name="longitude" type="number" step="any" min="-180" max="180" placeholder="110.3671"></div><div class="field"><label for="radius">Radius (meter)</label><input id="radius" name="radius_m" type="number" min="100" max="50000" value="5000"></div></div></section><section class="form-section"><h2>Pengambilan data</h2><div class="form-row"><div class="field"><label for="lang">Bahasa hasil</label><select id="lang" name="lang"><option value="id">Bahasa Indonesia</option><option value="en">English</option><option value="ms">Bahasa Melayu</option><option value="ja">Japanese</option></select></div><div class="field"><label for="max-leads">Batas kredit untuk job ini</label><input id="max-leads" name="max_credits" type="number" min="1" max="${state.credits.balance||30}" value="${Math.min(state.credits.balance||30,30)}" required><small>Dicadangkan di awal; sisa dikembalikan setelah job.</small></div></div><label class="checkline"><input type="checkbox" name="email_enabled" checked>Ambil email dari website bisnis</label><p class="small" style="margin-top:7px">Email aktif secara bawaan. Website tanpa email tetap menghasilkan data kosong.</p></section><div id="job-errors" role="alert"></div><div class="form-actions">${button('Simpan draft','save-job-draft','file')}<button class="button primary" type="submit">${icon('search')}${DEMO?'Simpan job demo':'Jalankan Scraping'}</button></div></form><aside class="stack"><section class="panel"><div class="panel-head"><h2>Sebelum mulai</h2>${icon('info')}</div><div class="tip-list"><div class="tip">${icon('pin')}<div><strong>Mulai dari area kecil</strong><p>Kata kunci yang spesifik membantu menjaga hasil tetap relevan.</p></div></div><div class="tip">${icon('globe')}<div><strong>Negara asal dari alamat</strong><p>Tujuan ekspor diisi terpisah, dengan bukti dan review.</p></div></div><div class="tip">${icon('shield')}<div><strong>Discovery, lalu consent</strong><p>Kontak ditemukan bukan berarti sudah memberi izin kirim.</p></div></div></div><div class="info-well"><strong>gosom · Google Maps</strong><p>Konkurensi konservatif. Lama pencarian bergantung cakupan dan website.</p></div></section>${DEMO?'<div class="demo-note">Pratinjau menyimpan draft. Scraping nyata tersedia pada aplikasi self-host.</div>':''}</aside></div>`;}
function jobDetailScreen(job,result){state.currentJob=job;const statuses=['queued','running','ingesting'];const contacts=job.completeness||Object.fromEntries(['phone','whatsapp','email'].map(k=>[k,{count:result.data.filter(l=>l['has_'+k]).length,total:result.total}]));return head(job.name,'Dibuat '+date(job.created_at)+' · '+job.queries.length+' query · '+(job.email_enabled?'Email aktif':'Email nonaktif'),`<a class="button" href="#/jobs">Kembali</a>${canOperate()?button('Duplikasi','duplicate-job','copy','',job.id)+(job.status==='draft'?button('Edit draft','edit-job','settings','',job.id):''):''}`)+`<div class="toolbar">${tag(job.status)}<div class="actions">${canOperate()?(statuses.includes(job.status)?button('Hentikan job','stop-job','stop','danger',job.id):['draft','failed','stopped'].includes(job.status)?button(DEMO?'Job demo tidak dijalankan':'Jalankan job','start-job','refresh','primary',job.id):'')+button('Arsipkan','archive-job','archive','',job.id):''}${isAdmin()&&!DEMO?`<a class="button" href="/api/jobs/${e(job.id)}/raw">${icon('download')}File mentah</a>`:''}</div></div>${job.error?`<div class="alert error">${icon('info')}${e(job.error)}</div>`:''}${job.hit_result_cap?`<div class="alert">${icon('info')}Batas hasil terdeteksi. Cakupan mungkin belum lengkap.</div>`:''}${DEMO?'<div class="demo-note">Detail ini menggunakan data contoh. Tidak ada proses gosom yang berjalan.</div>':''}<section class="kpis">${[['Ditemukan',job.found_count],['Lead baru',job.inserted_count],['Duplikat',job.duplicate_count],['Galat baris',job.error_count]].map(([label,n])=>`<div class="kpi"><div class="kpi-label">${label}</div><div class="kpi-value">${fmt(n)}</div></div>`).join('')}</section><div class="detail-grid"><div class="stack"><section class="panel"><div class="panel-head"><h2>Kelengkapan tiga kontak</h2><span class="small">${fmt(result.total)} lead</span></div>${Object.entries(contacts).map(([k,v])=>`<div class="contact-bar"><span>${icon(k==='phone'?'phone':k==='whatsapp'?'chat':'mail')}${{phone:'Telepon',whatsapp:'WhatsApp',email:'Email'}[k]}</span><div class="track"><div class="fill" style="width:${v.total?v.count/v.total*100:0}%"></div></div><b>${v.count}<span class="subline">${v.total?Math.round(v.count/v.total*100):0}%</span></b></div>`).join('')}</section>${isAdmin()?`<section class="panel"><div class="panel-head"><h2>Log engine</h2><span class="small">${date(job.started_at)}</span></div><pre class="log">${e(job.log_text||'Belum ada log. Job belum dijalankan.')}</pre>${job.header_missing?.length?`<div class="alert error section-gap">Header belum lengkap: ${e(job.header_missing.join(', '))}</div>`:''}</section>`:''}</div><section class="panel"><div class="panel-head"><h2>Konfigurasi job</h2>${icon('jobs')}</div>${[['Area',job.area_name||job.grid_bbox||`${job.latitude}, ${job.longitude}`],['Cakupan',job.geo_mode==='grid'?'Grid':'Titik & radius'],['Bahasa',job.lang],['Ambil email',job.email_enabled?'Aktif':'Nonaktif'],['Mulai',date(job.started_at)],['Selesai',date(job.finished_at)]].map(([k,v])=>`<div class="kv"><span>${k}</span><strong>${e(v)}</strong></div>`).join('')}<div class="info-well"><strong>Kata kunci</strong><p>${job.queries.map(e).join('<br>')}</p></div>${job.coverage_note?`<p class="small section-gap">${e(job.coverage_note)}</p>`:''}</section></div>${job.row_errors?.length?`<section class="panel section-gap"><h2>Galat baris</h2><ul class="error-list">${job.row_errors.map(r=>`<li>Baris ${r.row}: ${e(r.error)}</li>`).join('')}</ul></section>`:''}<section class="panel section-gap"><div class="panel-head"><h2>Lead dari job ini</h2><button class="text-button" data-action="leads-from-job" data-id="${e(job.id)}">Lihat semua ${icon('arrow')}</button></div>${leadsTable(result.data,true)}</section>`;}
function evidenceBlock(ev){return `<div class="evidence"><div class="evidence-header"><strong>${e(ev.kind==='country'?country(ev.value):ev.value)}</strong>${tag(ev.status)}<span class="small">${ev.kind==='country'?'Negara tujuan':'Produk ekspor'}</span></div><blockquote>${e(ev.evidence_snippet)}</blockquote><a href="${e(safeUrl(ev.evidence_url))}" target="_blank" rel="noopener noreferrer">${e(ev.evidence_url)} ${icon('external')}</a>${ev.reviewed_by?`<span class="subline">Direview ${e(ev.reviewed_by)} · ${date(ev.reviewed_at)}</span>`:''}</div>`;}
function leadDetailScreen(l){state.currentLead=l;return head(l.business_name,l.category+' · '+(l.city||l.country_origin_name||'Lokasi belum lengkap'),`<a class="button" href="#/leads">Kembali</a>${canOperate()?button('Enrichment ulang','enrich','refresh','primary',l.id):''}`)+`<div class="detail-contact">${[['Telepon','phone',l.phone_normalized,'Dari Google Maps'],['WhatsApp','chat',l.whatsapp_number,l.whatsapp_status==='derived_unverified'?'Turunan · belum diverifikasi':l.whatsapp_status],['Email','mail',(l.emails||[]).join(', '),'Belum diverifikasi']].map(([name,ico,value,status])=>`<section class="panel contact-card"><div class="label">${icon(ico)}${name}</div><div class="contact-value">${e(value||'Belum tersedia')}</div><span class="subline">${value?e(status):'Data kosong, tanpa tebakan'}</span></section>`).join('')}</div><div class="detail-grid"><div class="stack"><section class="panel"><div class="panel-head"><h2>Profil bisnis</h2>${canOperate()?button('Koreksi data','edit-lead','settings','small',l.id):''}</div>${[['Alamat',l.address],['Kota / provinsi',[l.city,l.province].filter(Boolean).join(' / ')],['Negara asal',l.country_origin_name],['Metode penurunan',l.country_origin_method+' · '+l.country_origin_confidence],['Website',l.website_url?`<a target="_blank" rel="noopener noreferrer" href="${e(safeUrl(l.website_url))}">${e(l.website_domain||l.website_url)} ${icon('external')}</a>`:'—',true],['Rating',l.rating?Number(l.rating).toFixed(1)+' / 5 · '+fmt(l.review_count)+' ulasan':'—'],['Place ID',l.place_id||'—'],['Ditemukan',date(l.first_seen_at)],['Ditemukan kembali',fmt(l.seen_count)+' kali'],['Query penemu',l.first_query],['Koordinat',`${l.latitude??'—'}, ${l.longitude??'—'}`],['Sumber',l.source]].map(([key,value,raw])=>`<div class="kv"><span>${key}</span><strong>${raw?value:e(value||'—')}</strong></div>`).join('')}<a class="button small section-gap" target="_blank" rel="noopener noreferrer" href="${e(safeUrl(l.maps_url||'https://www.google.com/maps/search/?api=1&query='+l.latitude+','+l.longitude))}">${icon('pin')}Lihat lokasi di Google Maps ${icon('external')}</a></section><section class="panel"><div class="panel-head"><div><h2>Negara & produk ekspor</h2><p>Bukti terpisah dari lokasi asal bisnis</p></div>${canOperate()?button('Tambah bukti','add-evidence','plus','small',l.id):''}</div>${l.evidence.length?l.evidence.map(evidenceBlock).join(''):empty('Belum ada bukti ekspor','Jalankan enrichment website atau tambahkan sumber manual.')}</section></div><div class="stack"><section class="panel"><div class="panel-head"><h2>Pipeline bisnis</h2>${tag(l.pipeline_status)}</div><p class="small">Tahapan tindak lanjut. Terpisah dari consent.</p>${canOperate()?`<div class="pipeline-select"><select id="lead-pipeline" aria-label="Pipeline lead">${PIPE.map(v=>`<option ${v===l.pipeline_status?'selected':''}>${v}</option>`).join('')}</select>${button('Simpan','save-pipeline','check','small',l.id)}</div>`:''}</section><section class="panel"><div class="panel-head"><h2>Consent & izin kontak</h2>${icon('shield')}</div>${tag(l.consent_basis)}<div class="consent-box"><p>${l.eligible_to_send?'Lead telah melewati Gate berdasarkan catatan consent.':'Belum eligible untuk daftar kirim. Nomor yang tersedia bukan izin mengirim pesan.'}</p></div>${l.consent_source?`<p class="small section-gap">Sumber: ${e(l.consent_source)}<br>${date(l.consent_at)}</p>`:''}${canOperate()?`<div class="section-gap actions">${button('Catat consent','consent','shield','small',l.id)}${l.whatsapp_number?button('Pemeriksaan WA','whatsapp-check','check','small',l.id):''}</div>`:''}</section><section class="panel"><div class="panel-head"><h2>Riwayat aktivitas</h2>${icon('clock')}</div>${canOperate()?`<form id="note-form"><label class="small" for="note">Catatan baru</label><textarea id="note" name="note" placeholder="Tulis catatan tim…" required style="min-height:70px"></textarea><button class="button small section-gap" type="submit">Simpan catatan</button></form>`:''}<div class="section-gap">${(l.activities||[]).slice(0,12).map(a=>`<div class="timeline-row"><span class="timeline-dot"></span><div><strong>${e(a.actor)}</strong><p>${e(a.payload?.note||a.payload?.changes?.note||a.type.replaceAll('_',' '))}</p><small>${date(a.created_at)}</small></div></div>`).join('')}</div></section>${l.enrichment_tasks?.some(t=>t.status==='failed')?`<section class="panel"><h2>Enrichment gagal</h2>${l.enrichment_tasks.filter(t=>t.status==='failed').map(t=>`<p class="small section-gap">${e(t.payload.error)}</p>`).join('')}</section>`:''}</div></div>`;}
function reviewScreen(items){const groups=Object.groupBy(items,i=>i.lead_id);return head('Review Enrichment','Periksa sumber, lalu setujui atau tolak setiap usulan.',button('Muat ulang','refresh','refresh'))+`<p class="notice-count">${fmt(items.length)} usulan dari ${Object.keys(groups).length} bisnis menunggu review.</p>${items.length?`<div class="review-grid">${Object.entries(groups).map(([id,proposals])=>`<section class="panel review-card"><a href="#/leads/${e(id)}" class="review-name">${e(proposals[0].business_name)}</a><p>Usulan dari website atau direktori bisnis</p>${proposals.map(ev=>`<div class="evidence"><div class="evidence-header"><strong>${e(ev.kind==='country'?country(ev.value):ev.value)}</strong>${tag('suspected')}<span class="small">${ev.kind==='country'?'Negara tujuan':'Produk'}</span></div><blockquote>${highlight(ev.evidence_snippet,ev.kind==='country'?country(ev.value):ev.value)}</blockquote><a class="source-link" href="${e(safeUrl(ev.evidence_url))}" target="_blank" rel="noopener noreferrer">Buka sumber bukti ${icon('external')}</a>${canReview()?`<label class="small" for="review-${e(ev.id)}">Catatan reviewer (opsional)</label><textarea id="review-${e(ev.id)}" placeholder="Alasan atau catatan keputusan…"></textarea><div class="actions">${button('Tolak','reject-evidence','close','',ev.id)}${button('Setujui','approve-evidence','check','primary',ev.id)}</div>`:'<p class="small">Menunggu keputusan Reviewer.</p>'}</div>`).join('')}</section>`).join('')}</div>`:empty('Seluruh usulan sudah ditinjau','Temuan baru dari enrichment akan muncul di sini.',link('Buka database lead','leads','arrow','button small'))}`;}
function highlight(text,term){const aliases={'Amerika Serikat':'United States','Jepang':'Japan','Belanda':'Netherlands','Singapura':'Singapore'};const escaped=e(text);const target=e(escaped.includes(e(term))?term:(aliases[term]||term));return escaped.replace(new RegExp(target.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'),'gi'),match=>`<mark>${match}</mark>`);}

function apiMcpScreen(apiKeys) {
  state.apiKeys = apiKeys;
  const activeTab = state.apiMcpTab || 'api';
  return head(
    'API Key & MCP Server',
    'Sambungkan PokoScrap dengan aplikasi lain, Claude Desktop, Cursor, Antigravity, n8n, atau custom workflow.',
    button('+ Buat API Key Baru', 'new-api-key', 'plus', 'primary')
  ) + `
  <div class="tabs">
    <button class="tab ${activeTab === 'api' ? 'active' : ''}" data-action="mcp-tab" data-id="api">
      ${icon('key')} API Keys (${apiKeys.length})
    </button>
    <button class="tab ${activeTab === 'mcp' ? 'active' : ''}" data-action="mcp-tab" data-id="mcp">
      ${icon('refresh')} MCP Server (Claude / Cursor / Antigravity)
    </button>
  </div>

  ${activeTab === 'api' ? `
    <section class="panel" style="margin-bottom: 20px;">
      <div class="panel-head">
        <div>
          <h2>API Keys Aktif</h2>
          <p>Key dibatasi ke data organisasi Anda dengan rate limit 600 permintaan per jam.</p>
        </div>
        ${button('+ Buat Key', 'new-api-key', 'plus', 'small primary')}
      </div>

      ${apiKeys.length ? `
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Nama Key</th>
                <th>Prefix Key</th>
                <th>Waktu Dibuat</th>
                <th>Rate Limit</th>
                <th>Status</th>
                <th style="text-align: right;">Aksi</th>
              </tr>
            </thead>
            <tbody>
              ${apiKeys.map(k => `
                <tr>
                  <td><strong>${e(k.name)}</strong></td>
                  <td><code style="background: #f3f4f6; padding: 2px 6px; border-radius: 6px; font-size: 11px;">${e(k.prefix)}••••••••</code></td>
                  <td>${date(k.created_at)}</td>
                  <td>600 req/jam</td>
                  <td>${tag('confirmed', 'Aktif')}</td>
                  <td style="text-align: right;">
                    ${button('Cabut Akses', 'revoke-api-key', 'close', 'small danger', k.prefix)}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      ` : empty(
        'Belum Ada API Key',
        'Buat API Key pertama Anda untuk menghubungkan PokoScrap dengan webhook, CRM, atau script eksternal.',
        button('+ Buat API Key Baru', 'new-api-key', 'plus', 'primary')
      )}
    </section>

    <div class="settings-grid">
      <div>
        <h2>Panduan Integrasi REST API</h2>
        <p>Format otentikasi standar menggunakan HTTP header Authorization Bearer.</p>
      </div>
      <section class="panel">
        <h3 style="margin-bottom: 8px;">Contoh Pemanggilan cURL</h3>
        <div class="code-block">
          <button class="copy-btn" data-action="copy-code" data-code="curl -X GET &quot;${location.origin}/api/leads?origin=ID&quot; -H &quot;Authorization: Bearer psk_YOUR_API_KEY&quot;">Salin</button>
<pre>curl -X GET "${location.origin}/api/leads?origin=ID" \
  -H "Authorization: Bearer psk_YOUR_API_KEY"</pre>
        </div>

        <h3 style="margin: 16px 0 8px;">Contoh Pemanggilan Python (requests)</h3>
        <div class="code-block">
          <button class="copy-btn" data-action="copy-code" data-code="import requests&#10;&#10;res = requests.get(&#10;    &quot;${location.origin}/api/leads&quot;,&#10;    headers={&quot;Authorization&quot;: &quot;Bearer psk_YOUR_API_KEY&quot;},&#10;    params={&quot;origin&quot;: &quot;ID&quot;, &quot;has_phone&quot;: True}&#10;)&#10;print(res.json())">Salin</button>
<pre>import requests

res = requests.get(
    "${location.origin}/api/leads",
    headers={"Authorization": "Bearer psk_YOUR_API_KEY"},
    params={"origin": "ID", "has_phone": True}
)
print(res.json())</pre>
        </div>

        <h3 style="margin: 16px 0 8px;">Contoh Pemanggilan JavaScript / Node.js</h3>
        <div class="code-block">
          <button class="copy-btn" data-action="copy-code" data-code="const res = await fetch(&quot;${location.origin}/api/leads?origin=ID&quot;, {&#10;  headers: { &quot;Authorization&quot;: &quot;Bearer psk_YOUR_API_KEY&quot; }&#10;});&#10;const data = await res.json();&#10;console.log(data);">Salin</button>
<pre>const res = await fetch("${location.origin}/api/leads?origin=ID", {
  headers: { "Authorization": "Bearer psk_YOUR_API_KEY" }
});
const data = await res.json();
console.log(data);</pre>
        </div>
      </section>
    </div>
  ` : `
    <section class="panel" style="margin-bottom: 20px;">
      <div class="panel-head">
        <div>
          <h2>Model Context Protocol (MCP) Server</h2>
          <p>Standar terbuka dari Anthropic untuk menghubungkan LLM ke tools & database PokoScrap secara native.</p>
        </div>
        <div class="actions">
          <span class="mcp-header-badge">${icon('check')} MCP Server Aktif</span>
          ${button('Test Ping MCP', 'test-mcp-ping', 'refresh', 'small')}
        </div>
      </div>
      <p style="font-size: 12px; line-height: 1.6; color: #4b5563;">
        Dengan MCP, Anda dapat menggunakan AI di <strong>Claude Desktop</strong>, <strong>Cursor</strong>, <strong>Antigravity</strong>, atau <strong>Windsurf</strong> untuk mencari lead bisnis, mengecek kontak telepon/WhatsApp/email, memperbarui status pipeline, serta memulai scraping Google Maps langsung dari percakapan AI Anda.
      </p>
    </section>

    <div class="settings-grid">
      <div>
        <h2>Konfigurasi Claude Desktop & Cursor</h2>
        <p>Tambahkan block JSON ini ke file konfigurasi MCP Anda.</p>
        <p class="small" style="margin-top: 8px;">Path Claude Desktop:<br><code>~/Library/Application Support/Claude/claude_desktop_config.json</code></p>
      </div>
      <section class="panel">
        <h3 style="margin-bottom: 8px;">1. Stdio Command (Claude Desktop / Cursor)</h3>
        <div class="code-block">
          <button class="copy-btn" data-action="copy-mcp-config">Salin Konfigurasi</button>
<pre>{
  "mcpServers": {
    "pokoscrap": {
      "command": "python3",
      "args": [
        "${location.hostname === 'localhost' || location.hostname === '127.0.0.1' ? '/Users/ibobatsuga/Documents/Codex/2026-11-12/buat-dashboard-ini-mengikuti-tampilan-dashboard/outputs/pokoscrap/server/mcp_server.py' : 'server/mcp_server.py'}"
      ],
      "env": {
        "POKOSCRAP_API_URL": "${location.origin}",
        "POKOSCRAP_API_KEY": "${apiKeys[0]?.prefix ? apiKeys[0].prefix + '...' : 'psk_MASUKKAN_KEY_DARI_TAB_API'}"
      }
    }
  }
}</pre>
        </div>

        <h3 style="margin: 20px 0 8px;">2. HTTP JSON-RPC Endpoint (Antigravity / Web MCP)</h3>
        <div class="code-block">
          <button class="copy-btn" data-action="copy-code" data-code="{&quot;mcpServers&quot;:{&quot;pokoscrap&quot;:{&quot;url&quot;:&quot;${location.origin}/api/mcp&quot;,&quot;headers&quot;:{&quot;Authorization&quot;:&quot;Bearer psk_YOUR_API_KEY&quot;}}}}">Salin</button>
<pre>{
  "mcpServers": {
    "pokoscrap": {
      "url": "${location.origin}/api/mcp",
      "headers": {
        "Authorization": "Bearer ${apiKeys[0]?.prefix ? apiKeys[0].prefix + '...' : 'psk_YOUR_API_KEY'}"
      }
    }
  }
}</pre>
        </div>
      </section>
    </div>

    <section class="panel" style="margin-top: 20px;">
      <div class="panel-head">
        <div>
          <h2>Katalog 7 Tool MCP PokoScrap</h2>
          <p>Tool yang dapat dipanggil secara otomatis oleh AI Assistant saat terhubung.</p>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px;">
        <div class="mcp-tool-card">
          <h4>pokoscrap_search_leads</h4>
          <p>Cari lead bisnis berdasarkan query nama/kategori, negara asal (origin), destinasi ekspor, status pipeline, dan filter telepon/WA/email.</p>
          <span class="tag">query, origin, pipeline_status, limit</span>
        </div>
        <div class="mcp-tool-card">
          <h4>pokoscrap_get_lead</h4>
          <p>Ambil rincian lengkap 1 lead bisnis dari ID-nya, termasuk telepon, WhatsApp, email, rating Maps, website, dan bukti ekspor.</p>
          <span class="tag">lead_id (required)</span>
        </div>
        <div class="mcp-tool-card">
          <h4>pokoscrap_update_lead_pipeline</h4>
          <p>Perbarui status pipeline CRM lead bisnis (Baru, Dihubungi, Follow-up, Deal, Tolak) dan simpan catatan aktivitas.</p>
          <span class="tag">lead_id, pipeline_status, note</span>
        </div>
        <div class="mcp-tool-card">
          <h4>pokoscrap_create_scrape_job</h4>
          <p>Mulai job scraping Google Maps baru dengan kata kunci pencarian, koordinat pusat, dan radius pencarian.</p>
          <span class="tag">name, queries, lat, lng, radius_m</span>
        </div>
        <div class="mcp-tool-card">
          <h4>pokoscrap_get_job_status</h4>
          <p>Pantau status progres scraping (queued, running, done), log pencarian, dan total kontak yang ditemukan.</p>
          <span class="tag">job_id (required)</span>
        </div>
        <div class="mcp-tool-card">
          <h4>pokoscrap_get_stats</h4>
          <p>Dapatkan ringkasan statistik workspace: total lead, lead bertelepon, lead ber-WhatsApp, lead ber-email, dan sisa saldo kredit.</p>
          <span class="tag">no parameters</span>
        </div>
        <div class="mcp-tool-card">
          <h4>pokoscrap_export_leads</h4>
          <p>Ekspor ringkasan daftar lead bisnis siap hubungi ke format CSV ringkas.</p>
          <span class="tag">pipeline_status, origin, has_whatsapp</span>
        </div>
      </div>
    </section>
  `}
  `;
}

function settingsScreen(data){state.settings=data;const cfg=data.config;return head('Pengaturan Workspace','Kelola tim, konfigurasi engine, dan audit data.')+`<div class="settings-grid"><div><h2>Anggota & akses</h2><p>Peran berlaku untuk organisasi aktif. Akses anggota dapat dicabut kapan saja.</p></div><section class="panel">${data.users.map(u=>`<div class="user-row"><div class="avatar">${e(initials(u.name))}</div><div><strong>${e(u.name)}</strong><small>${e(u.email)} · ${e(u.roles.join(' / '))}</small></div><div class="actions">${tag(u.active?'confirmed':'rejected',u.active?'Aktif':'Nonaktif')}${button('Ubah','edit-user','settings','small',u.id)}</div></div>`).join('')}<div class="section-gap">${button('Undang anggota','invite','plus','small')}</div></section></div><div class="settings-grid"><div><h2>Engine & pengambilan</h2><p>gosom adalah satu-satunya jalur scraping ke Google Maps.</p><div class="info-well"><p>Mode cepat tersedia. Mode manager belum diaktifkan pada build ini.</p></div></div><form id="settings-form" class="panel"><div class="form-row"><div class="field"><label for="concurrency">Konkurensi (1–4)</label><input id="concurrency" name="concurrency" type="number" min="1" max="4" value="${cfg.concurrency}"></div><div class="field"><label for="depth">Kedalaman (1–20)</label><input id="depth" name="depth" type="number" min="1" max="20" value="${cfg.depth}"></div></div><div class="form-row"><div class="field"><label for="enrichment_pages">Halaman enrichment</label><input id="enrichment_pages" name="enrichment_pages" type="number" min="1" max="10" value="${cfg.enrichment_pages}"></div><div class="field"><label for="session_idle_minutes">Sesi tidak aktif (menit)</label><input id="session_idle_minutes" name="session_idle_minutes" type="number" min="5" max="480" value="${cfg.session_idle_minutes}"></div></div><button class="button primary" type="submit">Simpan konfigurasi</button></form></div><div class="settings-grid"><div><h2>Impor direktori</h2><p>Negara dan produk dari direktori masuk sebagai suspected, untuk direview.</p></div><form id="directory-form" class="panel"><div class="field"><label for="directory-file">File CSV direktori</label><input id="directory-file" type="file" accept=".csv,text/csv" required><small>Header: business_name, domain, country_code, product, evidence_url, evidence_snippet.</small></div><button class="button" type="submit">${icon('file')}Impor sebagai usulan</button></form></div><div class="settings-grid"><div><h2>API tenant Pro</h2><p>Key dibatasi ke data organisasi dan 600 permintaan per jam.</p></div><section class="panel"><div class="actions">${button('Buat API key','new-api-key','key','small')}${button('Kelola API key','list-api-keys','settings','small')}</div><p class="small section-gap">Key hanya tampil sekali. Akses dicabut saat keanggotaan nonaktif atau paket bukan Pro.</p></section></div><div class="settings-grid"><div><h2>Riwayat export</h2><p>Setiap unduhan dicatat bersama filter dan pengguna.</p></div><section class="panel">${data.exports.length?`<div class="table-wrap"><table><thead><tr><th>Waktu</th><th>Pengguna</th><th>Tipe</th><th class="num">Lead</th></tr></thead><tbody>${data.exports.map(x=>`<tr><td>${date(x.created_at)}</td><td>${e(x.actor)}</td><td>${x.type==='analysis'?'Analisis':'Daftar kirim'}</td><td class="num">${fmt(x.count)}</td></tr>`).join('')}</tbody></table></div>`:empty('Belum ada export','Log akan tercatat setelah Anda mengekspor lead.')}</section></div>${DEMO?`<div class="settings-grid"><div><h2>Data pratinjau</h2><p>Reset seluruh perubahan pada browser ini.</p></div><section class="panel">${button('Reset data demo','reset-demo','refresh','danger')}</section></div>`:''}`;}
function billingScreen(b){state.billing=b;const plans=[{code:'free',name:'Free',price:'Rp0',quota:30,features:['1 pengguna','Filter dasar','Export CSV terbatas']},{code:'starter',name:'Starter',price:'Rp99.000',quota:1000,features:['Filter negara asal & tujuan','Pipeline bisnis','Export CSV penuh']},{code:'pro',name:'Pro',price:'Rp249.000',quota:5000,features:['Semua fitur Starter','Enrichment ekspor','Tim & API tenant']}];return head('Billing & Paket','Kelola langganan dan pembayaran organisasi Anda.')+`<div class="alert">${icon('info')}Harga Starter dan Pro adalah usulan validasi. Pembayaran memakai Tripay Sandbox, bukan transaksi produksi.</div><section class="panel"><div class="panel-head"><div><h2>Paket ${e(b.plan_code||'Free')}</h2><p>${e(b.status||'trial')} · ${b.period_end?'Periode sampai '+date(b.period_end):'Paket awal workspace'}</p></div>${tag('confirmed',fmt(state.credits.balance)+' kredit tersisa')}</div><p class="small">${b.next_plan?'Paket berikutnya: '+e(b.next_plan):'Tidak ada perubahan paket terjadwal.'}</p></section><div class="plans section-gap">${plans.map(p=>`<section class="panel plan"><div class="panel-head"><h2>${p.name}</h2>${p.code===(b.plan_code||'free').toLowerCase()?tag('confirmed','Paket aktif'):tag('draft',p.code==='free'?'Gratis':'Usulan')}</div><div class="plan-price">${p.price}<small>${p.code==='free'?'':' / bulan'}</small></div><p>${fmt(p.quota)} lead / kredit${p.code==='free'?'':' per bulan'}</p><ul>${p.features.map(f=>`<li>${icon('check')}${f}</li>`).join('')}</ul>${p.code!==(b.plan_code||'free').toLowerCase()?button(p.code==='free'?'Jadwalkan downgrade':'Pilih paket sandbox','plan','arrow','',p.code):'<span class="small">Paket sedang digunakan</span>'}</section>`).join('')}</div><section class="panel section-gap"><div class="panel-head"><h2>Invoice & pembayaran</h2><span class="small">Tripay Sandbox</span></div>${b.payments?.length?`<div class="table-wrap"><table><thead><tr><th>Invoice</th><th>Paket</th><th>Status</th><th class="num">Jumlah</th><th></th></tr></thead><tbody>${b.payments.map(p=>`<tr><td>${e(p.id.slice(0,10))}<span class="subline">${date(p.created_at)}</span></td><td>${e(p.plan_code)}</td><td>${tag(p.status)}</td><td class="num">Rp${fmt(p.amount)}</td><td>${p.checkout_url?`<a class="text-button" href="${e(safeUrl(p.checkout_url))}" target="_blank" rel="noopener noreferrer">Lihat invoice ${icon('external')}</a>`:'—'}</td></tr>`).join('')}</tbody></table></div>`:empty('Belum ada pembayaran','Invoice akan muncul setelah checkout sandbox dibuat.')}</section>`;}
function creditsScreen(data){return head('Pemakaian Kredit','Saldo dan setiap mutasi tercatat dalam ledger.')+`<section class="kpis"><div class="kpi"><div class="kpi-label">Sisa kredit</div><div class="kpi-value">${fmt(data.balance)}</div><div class="kpi-sub">Saldo dihitung dari ledger</div></div><div class="kpi"><div class="kpi-label">Kredit diberikan</div><div class="kpi-value">${fmt(data.ledger.filter(x=>x.amount>0).reduce((s,x)=>s+x.amount,0))}</div></div><div class="kpi"><div class="kpi-label">Kredit terpakai</div><div class="kpi-value">${fmt(-data.ledger.filter(x=>x.amount<0).reduce((s,x)=>s+x.amount,0))}</div></div><div class="kpi"><div class="kpi-label">Paket aktif</div><div class="kpi-value">${e(state.credits.plan||'Free')}</div></div></section>${data.balance<10?`<div class="alert">${icon('info')}Kredit tersisa ${data.balance}. Periksa kebutuhan job sebelum menjalankan pencarian.</div>`:''}<section class="panel"><div class="panel-head"><h2>Mutasi kredit</h2><span class="small">Append-only ledger</span></div><div class="table-wrap"><table><thead><tr><th>Waktu</th><th>Jenis / referensi</th><th>Pelaku</th><th class="num">Mutasi</th><th class="num">Saldo</th></tr></thead><tbody>${data.ledger.map(x=>`<tr><td>${date(x.created_at)}</td><td>${e(x.type)}<span class="subline">${e(x.reference||'Aktivasi Free')}</span></td><td>${e(x.actor)}</td><td class="num">${x.amount>0?'+':''}${fmt(x.amount)}</td><td class="num">${fmt(x.balance_after)}</td></tr>`).join('')}</tbody></table></div><div class="info-well"><p>Aturan contoh beta: 1 lead baru bertelepon = 1 kredit, email ditemukan +1 kredit. Aturan final belum diputuskan. Reservasi job dikembalikan setelah penyelesaian.</p></div></section>`;}
function adminScreen(data){state.tenants=data.data||data;return head('Admin SaaS','Pantau tenant, kredit, dan audit platform.')+`<section class="panel"><div class="toolbar"><h2>Organisasi pelanggan</h2><div class="search">${icon('search')}<input id="tenant-search" placeholder="Cari organisasi…" aria-label="Cari organisasi"></div></div><div class="table-wrap"><table><thead><tr><th>Tenant</th><th>Paket</th><th>Status</th><th class="num">Kredit</th><th>Aksi</th></tr></thead><tbody>${state.tenants.map(t=>`<tr data-tenant-name="${e(t.name.toLowerCase())}"><td><strong>${e(t.name)}</strong><span class="subline">${e(t.id.slice(0,8))}</span></td><td>${e(t.plan_code||'Free')}</td><td>${tag(t.status)}</td><td class="num">${fmt(t.balance)}</td><td><div class="actions">${button('Kredit','adjust-credit','credit','small',t.id)}${button(t.status==='suspended'?'Aktifkan':'Tangguhkan','tenant-status','settings','small',t.id)}</div></td></tr>`).join('')}</tbody></table></div></section><section class="panel section-gap"><h2>Batas akses platform</h2><p class="small section-gap">Admin SaaS tidak mengubah consent, pipeline, atau isi lead tenant. Penyesuaian kredit dan status wajib memiliki alasan.</p></section>`;}
async function render(){const renderId=++render.sequence;state.route=(location.hash.replace(/^#\/?/,'')||'overview').split('?')[0];if(!state.user){$('#app').innerHTML=loginScreen(state.route==='register');return;}const [route,id]=state.route.split('/');let content,title;try{if(route==='overview'||!route){title='Ringkasan';content=overviewScreen(DEMO?demoOverview():await api('/stats/overview'));}else if(route==='leads'&&id){title='Detail Lead';content=leadDetailScreen(DEMO?structuredClone(demo.leads.find(l=>l.id===id)):await api('/leads/'+id));}else if(route==='leads'){title='Database Lead';if(!DEMO){state.jobs=(await api('/jobs')).data;state.facets=await api('/facets');}content=leadsScreen(await getLeads(),DEMO?demo.segments:await api('/segments'));}else if(route==='jobs'&&id==='new'){title='Buat Job';content=newJobScreen();}else if(route==='jobs'&&id){title='Detail Job';const job=DEMO?demo.jobs.find(j=>j.id===id):await api('/jobs/'+id);const result=DEMO?{total:demo.leads.filter(l=>l.first_job_id===id).length,data:demo.leads.filter(l=>l.first_job_id===id)}:await api('/leads?job='+id+'&page_size=25');content=jobDetailScreen(job,result);}else if(route==='jobs'){title='Job Scraping';content=jobsScreen(DEMO?demo.jobs:(await api('/jobs')).data);}else if(route==='review'){title='Review Enrichment';const items=DEMO?demo.leads.flatMap(l=>l.evidence.filter(e=>e.status==='suspected').map(ev=>({...ev,business_name:l.business_name}))):(await api('/enrichment/queue')).data;content=reviewScreen(items);}else if(route==='settings'){title='Pengaturan';if(!isAdmin())throw {detail:'Akses pengaturan hanya untuk Owner atau Admin.'};content=settingsScreen(DEMO?{...demo,users:demo.users}:await api('/settings'));}else if(route==='billing'){title='Billing & Paket';content=billingScreen(DEMO?{plan_code:'free',status:'trial',payments:[]}:await api('/billing/subscription'));}else if(route==='credits'){title='Pemakaian Kredit';content=creditsScreen(DEMO?{balance:30,ledger:[{id:'grant',type:'grant',amount:30,balance_after:30,actor:'Sistem',created_at:'2026-11-12T00:00:00Z',reference:'Free — data contoh'}]}:await api('/credits/ledger'));}else if(route==='api-mcp'){
      title='API Key & MCP';
      const apiKeys=DEMO?[]:await api('/api-keys');
      content=apiMcpScreen(apiKeys);
    }else if(route==='admin'){title='Admin SaaS';if(!state.user.platform_admin)throw {detail:'Akses khusus Platform Admin.'};content=adminScreen(DEMO?{data:[{id:'demo',name:'Workspace Demo',plan_code:'free',status:'trial',balance:30}]}:await api('/admin/tenants'));}else if(route==='onboarding'){title='Buat Organisasi';content=head('Buat Organisasi','Pisahkan data bisnis dan anggota tim Anda.')+`<form class="panel" id="org-form"><div class="field"><label for="org-name">Nama organisasi</label><input id="org-name" name="name" required></div><button class="button primary">Buat workspace · Free 30 kredit</button></form>`;}else{title='Halaman tidak ditemukan';content=empty(title,'Pilih halaman dari navigasi.',link('Buka ringkasan','overview'));}if(renderId!==render.sequence)return;$('#app').innerHTML=shell(content,title);document.title=title+' · PokoScrap';}catch(error){if(renderId!==render.sequence)return;$('#app').innerHTML=shell(head(title||'Workspace','')+`<div class="alert error">${icon('info')}${e(human(error))}</div>${button('Coba lagi','refresh','refresh')}`,title||'Workspace');}}
render.sequence=0;
function exportModal(){modal('Export lead',`<p>Hasil mengikuti filter dan urutan aktif.</p><div class="export-count">${fmt(state.lastLeadResult?.total)}</div><p>lead pada segmen ini</p><form id="export-form"><label class="export-choice"><input type="radio" name="type" value="analysis" checked><b>CSV analisis</b><small>Memuat status consent dan tiga kontak utama.</small></label><label class="export-choice"><input type="radio" name="type" value="send_list"><b>Daftar kirim</b><small>Ditolak bila ada lead yang belum lolos Gate.</small></label><div id="export-error" role="alert"></div><div class="form-actions"><button class="button primary">${icon('download')}Unduh CSV</button></div></form>`);}
function download(text,name){const url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function demoCsv(leads){const fields='business_name phone_normalized whatsapp_number whatsapp_status emails category address city province country_origin_code country_origin_name export_countries export_products website_url rating review_count pipeline_status consent_basis eligible_to_send source first_query first_seen_at maps_url'.split(' ');const cell=v=>{v=Array.isArray(v)?v.join(';'):String(v??'');if(/^[=+\-@\t\r]/.test(v))v="'"+v;return '"'+v.replaceAll('"','""')+'"';};return '\ufeff'+[fields.map(cell).join(','),...leads.map(l=>fields.map(k=>cell(l[k])).join(','))].join('\r\n');}
const route=path=>location.hash='/'+path;
document.addEventListener('click',async event=>{const el=event.target.closest('[data-action]');if(!el)return;const action=el.dataset.action,id=el.dataset.id;try{if(action==='close-modal'){$('#modal').close();return;}if(action==='menu-open'){$('.sidebar').classList.add('open');$('.mobile-overlay').classList.add('open');return;}if(action==='menu-close'){$('.sidebar').classList.remove('open');$('.mobile-overlay').classList.remove('open');return;}if(action==='refresh'){await render();return;}if(action==='google-login'){
      try{
        const gConf=await api('/auth/google/url');
        if(gConf.configured&&gConf.auth_url){location.href=gConf.auth_url;return;}
      }catch(err){}
      modal('Konfigurasi Google OAuth', `
        <div style="text-align: center; margin-bottom: 16px;">
          ${googleIcon}
          <h3 style="margin-top: 10px; font-size: 15px;">Google OAuth Memerlukan Client ID</h3>
          <p class="small" style="line-height: 1.5; margin-top: 8px;">
            Untuk login otomatis menggunakan akun Google resmi Anda, masukkan <b>GOOGLE_CLIENT_ID</b> dan <b>GOOGLE_CLIENT_SECRET</b> dari Google Cloud Console ke Environment Variables Vercel.
          </p>
        </div>
        <div style="background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-bottom: 14px;">
          <small style="color: #6b7280; display: block; margin-bottom: 4px; font-weight: 600;">Authorized Redirect URI untuk Google Console:</small>
          <code style="word-break: break-all; font-size: 12px; color: #111827;">${location.origin}/api/auth/google/callback</code>
        </div>
        <button class="button primary" style="width: 100%; min-height: 40px;" data-action="close-modal" type="button">Mengerti</button>
      `);
      return;
    }
    if(action==='mcp-tab'){state.apiMcpTab=id;await render();return;}
    if(action==='copy-mcp-config'||action==='copy-code'){
      const textToCopy=el.dataset.code||el.parentElement.querySelector('pre')?.innerText||'';
      if(navigator.clipboard&&textToCopy){await navigator.clipboard.writeText(textToCopy);toast('Konfigurasi berhasil disalin ke clipboard.');}
      return;
    }
    if(action==='test-mcp-ping'){
      try{
        const pingRes=await api('/mcp','POST',{jsonrpc:'2.0',id:Date.now(),method:'ping',params:{}});
        const info=await api('/mcp');
        modal('Status MCP Server Berhasil', `
          <div style="text-align: center; margin-bottom: 14px;">
            <span class="mcp-header-badge">${icon('check')} MCP Server Aktif & Merespons</span>
          </div>
          <div class="kv"><span>Protokol:</span><strong>JSON-RPC 2.0 (MCP 2024-11-05)</strong></div>
          <div class="kv"><span>Server Name:</span><strong>${e(info.server)} v${e(info.version)}</strong></div>
          <div class="kv"><span>Tools Siap Pakai:</span><strong>${e(info.tools_count)} tools</strong></div>
          <div class="kv"><span>Status Autentikasi:</span><strong>Terverifikasi (Sesi Aktif)</strong></div>
          <div class="code-block" style="margin-top: 14px;">
<pre>${e(JSON.stringify(pingRes, null, 2))}</pre>
          </div>
        `);
      }catch(err){toast('Gagal menghubungi MCP: '+human(err));}
      return;
    }
    if(action==='sandbox-upgrade-pro'){
      await api('/billing/sandbox-upgrade','POST',{plan:'pro'});
      $('#modal').close();
      toast('Paket Pro Sandbox diaktifkan! Silakan buat API Key.');
      await render();
      return;
    }
    if(action==='demo-login'){state.user={...demo.users[0],roles:['Owner','Admin'],platform_admin:true,organization_name:'Workspace Demo'};route('overview');await render();return;}if(action==='logout'){if(!DEMO)await api('/logout','POST',{});state.user=null;route('login');await render();return;}if(action==='forgot'){modal('Pulihkan kata sandi',`<form id="forgot-form"><p>Masukkan email akun. Tautan hanya dikirim bila akun tersedia.</p><div class="field section-gap"><label for="forgot-email">Email</label><input id="forgot-email" name="email" type="email" required></div><button class="button primary">Kirim tautan pemulihan</button></form>`);return;}if(action==='toggle-filters'){state.showFilters=!state.showFilters;await render();return;}if(action==='reset-filters'){state.filters={};state.page=1;state.selected.clear();await render();return;}if(action==='save-segment'){modal('Simpan segmen',`<form id="segment-form"><div class="field"><label for="segment-name">Nama segmen</label><input id="segment-name" name="name" placeholder="Contoh: Kopi Indonesia ke Jepang" required></div><button class="button primary">Simpan filter aktif</button></form>`);return;}if(action==='prev-page'||action==='next-page'){state.page+=action==='prev-page'?-1:1;state.selected.clear();await render();return;}if(action==='clear-selection'){state.selected.clear();await render();return;}if(action==='bulk-pipeline'){const status=$('#bulk-status').value;if(DEMO){for(const l of demo.leads.filter(l=>state.selected.has(l.id))){const from=l.pipeline_status;l.pipeline_status=status;activity(l,'pipeline_changed',{from,to:status});}}else await api('/leads/bulk-pipeline','POST',{ids:[...state.selected],status});toast(state.selected.size+' pipeline diperbarui.');state.selected.clear();await render();return;}if(action==='export'){exportModal();return;}if(action==='job-tab'){state.jobStatus=id;await render();return;}if(action==='edit-job'){const j=state.currentJob;modal('Edit draft job',`<form id="edit-job-form"><div class="field"><label for="edit-job-name">Nama job</label><input id="edit-job-name" name="name" value="${e(j.name)}" required></div><div class="field"><label for="edit-queries">Kata kunci</label><textarea id="edit-queries" name="queries" required>${e(j.queries.join('\n'))}</textarea></div><div class="field"><label for="edit-area">Nama area</label><input id="edit-area" name="area_name" value="${e(j.area_name||'')}"></div>${j.geo_mode==='grid'?`<div class="field"><label for="edit-bbox">Kotak grid</label><input id="edit-bbox" name="grid_bbox" value="${e(j.grid_bbox)}" required></div>`:`<div class="form-row"><div class="field"><label for="edit-lat">Latitude</label><input id="edit-lat" name="latitude" type="number" step="any" value="${e(j.latitude)}" required></div><div class="field"><label for="edit-lon">Longitude</label><input id="edit-lon" name="longitude" type="number" step="any" value="${e(j.longitude)}" required></div></div><div class="field"><label for="edit-radius">Radius meter</label><input id="edit-radius" name="radius_m" type="number" value="${e(j.radius_m)}" required></div>`}<div class="field"><label for="edit-max">Batas kredit</label><input id="edit-max" name="max_credits" type="number" min="1" value="${j.max_credits||30}" required></div><button class="button primary">Simpan draft</button></form>`);return;}if(action==='save-job-draft'){event.preventDefault();await submitJob(false);return;}if(action==='duplicate-job'){if(DEMO){const old=demo.jobs.find(j=>j.id===id);const copy={...structuredClone(old),id:crypto.randomUUID(),name:old.name+' (salinan)',status:'draft',found_count:0,inserted_count:0,duplicate_count:0,error_count:0,created_at:new Date().toISOString()};demo.jobs.unshift(copy);persist();route('jobs/'+copy.id);}else{const copy=await api('/jobs/'+id+'/duplicate','POST',{});route('jobs/'+copy.id);}toast('Job disalin sebagai draft.');return;}if(action==='start-job'){if(DEMO){toast('Pratinjau menyimpan draft; engine nyata tersedia pada self-host.');return;}await api('/jobs/'+id+'/start','POST',{});toast('Job masuk antrean.');await render();return;}if(action==='stop-job'){await api('/jobs/'+id+'/stop','POST',{});toast('Job dihentikan. Hasil parsial tetap tersimpan.');await render();return;}if(action==='archive-job'){if(DEMO){demo.jobs.find(j=>j.id===id).archived=true;persist();}else await api('/jobs/'+id+'/archive','POST',{});route('jobs');return;}if(action==='leads-from-job'){state.filters={job:id};state.page=1;route('leads');return;}if(action==='enrich'){if(DEMO){toast('Contoh usulan tersedia di antrean review.');}else{await api('/leads/'+id+'/enrich','POST',{});toast('Enrichment masuk antrean.');}return;}if(action==='save-pipeline'){const status=$('#lead-pipeline').value;if(DEMO){const l=demo.leads.find(l=>l.id===id);l.pipeline_status=status;activity(l,'pipeline_changed',{to:status});}else await api('/leads/'+id,'PATCH',{pipeline_status:status});toast('Pipeline tersimpan.');await render();return;}if(action==='whatsapp-check'){modal('Catat pemeriksaan WhatsApp',`<form id="whatsapp-check-form">${selectField('Status hasil pemeriksaan','status',['active','inactive','unknown'],'unknown','Pilih')}<div class="field"><label for="wa-method">Metode / sumber pemeriksaan</label><textarea id="wa-method" name="method" required placeholder="Metode sah dan berizin yang digunakan."></textarea></div><div class="field"><label for="wa-date">Tanggal pemeriksaan</label><input id="wa-date" name="date" type="datetime-local" required></div><p>Status aktif tidak mengubah consent.</p><button class="button primary section-gap">Catat hasil</button></form>`);return;}if(action==='consent'){const l=state.currentLead;modal('Catat consent',`<p>Dasar, tanggal, dan sumber wajib diisi. Pipeline tidak mengubah izin kontak.</p><form id="consent-form" class="section-gap">${selectField('Dasar consent','basis',[{value:'none',label:'Belum ada'},{value:'invited',label:'Undangan melalui kanal publik'},{value:'opted_in',label:'Opt-in sukarela'},{value:'replied',label:'Membalas'},{value:'opted_out',label:'Opt-out'}],l.consent_basis,'Pilih dasar')}<div class="field"><label for="consent-date">Tanggal consent</label><input id="consent-date" name="date" type="datetime-local" required max="${new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,16)}"></div><div class="field"><label for="consent-source">Sumber / bukti consent</label><textarea id="consent-source" name="source" required placeholder="Tautan formulir atau catatan sumber yang dapat diperiksa."></textarea></div><button class="button primary">Simpan consent</button></form>`);return;}if(action==='edit-lead'){const l=state.currentLead;modal('Koreksi data bisnis',`<form id="edit-lead-form">${selectField('Negara asal','country_origin_code',state.countries.map(c=>({value:c.code,label:c.name})),l.country_origin_code,'Pilih negara')}<div class="field"><label for="phone-raw">Telepon</label><input id="phone-raw" name="phone_raw" value="${e(l.phone_raw)}"></div><p>WhatsApp dihitung ulang dari telepon. Perubahan tercatat di riwayat.</p><button class="button primary section-gap">Simpan koreksi</button></form>`);return;}if(action==='add-evidence'){modal('Tambah bukti ekspor',`<form id="evidence-form">${selectField('Jenis bukti','kind',[{value:'country',label:'Negara tujuan ekspor'},{value:'product',label:'Produk ekspor'}],'country','Pilih')}<div class="field"><label for="evidence-value">Kode negara ISO / nama produk</label><input id="evidence-value" name="value" required placeholder="Contoh: JP atau kopi"></div><div class="field"><label for="evidence-url">URL sumber</label><input id="evidence-url" name="evidence_url" type="url" required placeholder="https://…"></div><div class="field"><label for="evidence-snippet">Kutipan bukti / catatan sumber</label><textarea id="evidence-snippet" name="evidence_snippet" required></textarea></div><button class="button primary">Simpan sebagai confirmed</button></form>`);return;}if(action==='approve-evidence'||action==='reject-evidence'){const decision=action==='approve-evidence'?'approved':'rejected',note=$('#review-'+CSS.escape(id)).value;if(DEMO){const l=demo.leads.find(l=>l.evidence.some(x=>x.id===id)),ev=l.evidence.find(x=>x.id===id);if(decision==='approved'&&(!ev.evidence_url||!ev.evidence_snippet))throw {detail:'URL dan kutipan bukti wajib tersedia.'};ev.status=decision==='approved'?'confirmed':'rejected';ev.reviewed_by=state.user.name;ev.reviewed_at=new Date().toISOString();ev.review_note=note;l.export_countries=l.evidence.filter(e=>e.kind==='country'&&e.status==='confirmed').map(e=>e.value);l.export_products=l.evidence.filter(e=>e.kind==='product'&&e.status==='confirmed').map(e=>e.value);activity(l,'evidence_reviewed',{note,decision});}else await api('/enrichment/'+id+'/review','POST',{decision,note});toast(decision==='approved'?'Usulan disetujui.':'Usulan ditolak.');await render();return;}if(action==='reset-demo'){modal('Reset data demo',`<p>Seluruh perubahan pratinjau pada browser ini akan kembali ke data contoh awal.</p><div class="form-actions">${button('Batal','close-modal')}${button('Reset data','confirm-reset','','danger')}</div>`);return;}if(action==='confirm-reset'){demo=initialDemo();persist();$('#modal').close();toast('Data contoh dipulihkan.');await render();return;}if(action==='invite'){modal('Undang anggota',`<form id="invite-form"><div class="field"><label for="invite-email">Email anggota</label><input id="invite-email" name="email" type="email" required></div>${selectField('Peran','role',['Admin','Operator','Reviewer'],'Operator','Pilih')}<p>Multi-pengguna tersedia pada paket Pro.</p><button class="button primary section-gap">Buat undangan</button></form>`);return;}if(action==='new-api-key'){modal('Buat API key',`<form id="api-key-form"><div class="field"><label for="key-name">Nama integrasi</label><input id="key-name" name="name" required></div><button class="button primary" ${DEMO?'disabled':''}>Buat key satu kali</button>${DEMO?'<p class="section-gap">Key nyata tersedia pada aplikasi self-host.</p>':''}</form>`);return;}if(action==='list-api-keys'){const keys=DEMO?[]:await api('/api-keys');modal('API key tenant',keys.length?keys.map(k=>`<div class="user-row"><div><strong>${e(k.name)}</strong><small>${e(k.prefix)}…</small></div>${button('Cabut akses','revoke-api-key','close','small',k.prefix)}</div>`).join(''):'<p>Belum ada API key dibuat.</p>');return;}if(action==='revoke-api-key'){await api('/api-keys/revoke','POST',{prefix:id});$('#modal').close();toast('API key dicabut.');await render();return;}if(action==='edit-user'){const u=state.settings.users.find(u=>u.id===id);modal('Akses anggota',`<form id="user-form" data-id="${e(id)}">${selectField('Peran','role',['Owner','Admin','Operator','Reviewer'],u.roles[0],'Pilih')}<label class="checkline"><input type="checkbox" name="active" ${u.active?'checked':''}>Anggota aktif</label><button class="button primary section-gap">Simpan akses</button></form>`);return;}if(action==='accept-invite'){const result=await api('/orgs/invite/accept','POST',{token:state.pendingInvite});await api('/orgs/'+result.tenant_id+'/select','POST',{});sessionStorage.removeItem('pokoscrap-invite');state.pendingInvite=null;state.user=await api('/me');await loadContext();history.replaceState(null,'',location.pathname+'#/overview');await render();toast('Undangan diterima. Organisasi aktif diperbarui.');return;}if(action==='switch-org'){if(DEMO){modal('Organisasi',`<p>Workspace Demo · Free 30 kredit</p><p class="section-gap">Buat dan beralih organisasi tersedia pada aplikasi self-host.</p>`);return;}const orgs=await api('/orgs');modal('Beralih organisasi',`${orgs.map(o=>`<button class="button" style="width:100%;margin-bottom:10px" data-action="select-org" data-id="${e(o.id)}">${icon('building')}${e(o.name)}</button>`).join('')}${link('Buat organisasi baru','onboarding','plus','button')}`);return;}if(action==='select-org'){await api('/orgs/'+id+'/select','POST',{});state.user=await api('/me');state.credits=await api('/credits/balance');$('#modal').close();route('overview');await render();return;}if(action==='plan'){modal('Paket '+id,`<p>Harga dan aturan kredit masih usulan validasi. Checkout hanya menggunakan Tripay Sandbox.</p><form id="checkout-form" data-plan="${e(id)}"><div class="field section-gap"><label for="payment-channel">Channel aktif sandbox</label><select id="payment-channel" name="method"><option value="">Muat channel dari merchant</option></select></div><div id="checkout-message" class="demo-note">${DEMO?'Pembayaran tidak dijalankan di pratinjau.':'Menyiapkan konfigurasi merchant…'}</div><button class="button primary" ${DEMO?'disabled':''}>${id==='free'?'Jadwalkan downgrade':'Buat invoice sandbox'}</button></form>`);if(!DEMO&&id==='free'){$('#payment-channel').closest('.field').hidden=true;$('#checkout-message').textContent='Downgrade berlaku setelah periode aktif berakhir.';}if(!DEMO&&id!=='free'){try{const channels=await api('/billing/channels');$('#payment-channel').innerHTML=options(channels.map(c=>({value:c.code,label:c.name})),'','Pilih channel');$('#checkout-message').textContent='Hanya channel aktif dari Tripay merchant Anda.';}catch(error){$('#checkout-message').textContent=human(error);$('#checkout-form button').disabled=true;}}return;}if(action==='adjust-credit'||action==='tenant-status'){modal(action==='adjust-credit'?'Penyesuaian kredit':'Status tenant',`<form id="admin-form" data-action-type="${action}" data-id="${e(id)}">${action==='adjust-credit'?'<div class="field"><label for="adjust-amount">Jumlah kredit (+ / −)</label><input id="adjust-amount" name="amount" type="number" required></div>':selectField('Status','status',['active','suspended'],'suspended','Pilih')}<div class="field"><label for="admin-reason">Alasan wajib</label><textarea id="admin-reason" name="reason" required></textarea></div><button class="button primary">Simpan dan catat audit</button></form>`);return;}}catch(error){toast(human(error));}});
let searchTimer;
document.addEventListener('input',event=>{const target=event.target;if(target.id==='queries'){$('#query-count').textContent=new Set(target.value.split('\n').map(s=>s.trim()).filter(Boolean)).size+' query unik';}if(target.id==='lead-search'){clearTimeout(searchTimer);const value=target.value,position=target.selectionStart;searchTimer=setTimeout(async()=>{state.filters.q=value;state.page=1;await render();const field=$('#lead-search');if(field){field.focus();field.setSelectionRange(position,position);}},350);}if(target.id==='tenant-search'){for(const row of document.querySelectorAll('[data-tenant-name]'))row.hidden=!row.dataset.tenantName.includes(target.value.toLowerCase());}});
document.addEventListener('change',async event=>{const target=event.target;try{if(target.id==='geo-mode'){$('#grid-fields').hidden=target.value!=='grid';$('#point-fields').hidden=target.value!=='point';}if(target.id==='lead-sort'){state.filters.sort=target.value;state.page=1;await render();}if(target.id==='page-size'){state.size=Number(target.value);state.page=1;await render();}if(target.id==='segment-select'&&target.value){const segments=DEMO?demo.segments:await api('/segments');state.filters={...segments.find(s=>s.id===target.value).filters};state.page=1;await render();}if(target.dataset.select){target.checked?state.selected.add(target.dataset.select):state.selected.delete(target.dataset.select);await render();}if(target.id==='select-all'){for(const l of state.lastLeadResult.data)target.checked?state.selected.add(l.id):state.selected.delete(l.id);await render();}}catch(error){toast(human(error));}});
async function submitJob(start=true){const form=$('#job-form');if(!form.reportValidity())return;const data=Object.fromEntries(new FormData(form));data.email_enabled=form.email_enabled.checked;data.max_credits=Number(data.max_credits);data.start=start;try{if(DEMO){const queries=[...new Set(data.queries.split('\n').map(s=>s.trim()).filter(Boolean))];const j={...data,id:crypto.randomUUID(),queries,status:'draft',created_at:new Date().toISOString(),created_by:state.user.name,found_count:0,inserted_count:0,duplicate_count:0,error_count:0,row_errors:[]};demo.jobs.unshift(j);persist();route('jobs/'+j.id);toast('Draft demo disimpan. Tidak ada scraping dijalankan.');}else{const job=await api('/jobs','POST',data);route('jobs/'+job.id);toast(start?'Job masuk antrean.':'Draft disimpan.');}}catch(error){$('#job-errors').innerHTML=`<div class="alert error">${e(human(error))}</div>`;}}
document.addEventListener('submit',async event=>{event.preventDefault();const form=event.target,data=Object.fromEntries(new FormData(form)),submit=form.querySelector('button[type="submit"],button:not([type])');if(submit)submit.disabled=true;try{if(form.id==='google-quick-form'){
      state.user=await api('/auth/google','POST',data);
      await loadContext();
      $('#modal').close();
      toast('Berhasil masuk dengan akun Google.');
      route(state.user.tenant_id?'overview':'onboarding');
      await render();
      return;
    }
    if(form.id==='auth-form'){if(DEMO){toast('Gunakan tombol Buka workspace demo.');return;}if(form.dataset.register==='true'){await api('/register','POST',data);modal('Verifikasi email',`<p>Jika alamat dapat digunakan, instruksi verifikasi akan tersedia melalui email. Pada mode pengembangan, lihat outbox lokal.</p><a class="button section-gap" href="#/login">Kembali masuk</a>`);}else{state.user=await api('/login','POST',data);await loadContext();route(state.user.tenant_id?'overview':'onboarding');await render();}return;}if(form.id==='job-form'){await submitJob(true);return;}if(form.id==='edit-job-form'){data.max_credits=Number(data.max_credits);if(DEMO){Object.assign(demo.jobs.find(j=>j.id===state.currentJob.id),data,{queries:[...new Set(data.queries.split('\n').map(x=>x.trim()).filter(Boolean))]});persist();}else await api('/jobs/'+state.currentJob.id,'PATCH',data);$('#modal').close();toast('Draft diperbarui.');await render();return;}if(form.id==='filter-form'){const next={...state.filters};for(const [k,v]of Object.entries(data))if(!k.endsWith('_multi')){if(v)next[k]=v;else delete next[k];}if(data.origin_multi)next.origin=data.origin_multi.replaceAll(' ','').toUpperCase();if(data.destination_multi)next.destination=data.destination_multi.replaceAll(' ','').toUpperCase();next.suspected=form.suspected.checked?'true':'';next.destination_all=form.destination_all.checked?'true':'';state.filters=next;state.page=1;state.selected.clear();await render();return;}if(form.id==='segment-form'){if(DEMO){demo.segments.push({id:crypto.randomUUID(),name:data.name,filters:{...state.filters}});persist();}else await api('/segments','POST',{name:data.name,filters:state.filters});$('#modal').close();toast('Segmen tersimpan.');await render();return;}if(form.id==='export-form'){let text;if(DEMO){const leads=filterDemo(demo.leads,state.filters),blocked=leads.filter(l=>!['opted_in','replied'].includes(l.consent_basis)||!l.eligible_to_send).length;if(data.type==='send_list'&&blocked){$('#export-error').innerHTML=`<div class="alert error">${blocked} lead belum lolos gerbang consent. Gunakan CSV analisis.</div>`;return;}text=demoCsv(leads);demo.exports.unshift({actor:state.user.name,created_at:new Date().toISOString(),count:leads.length,type:data.type});persist();}else text=await api('/exports','POST',{type:data.type,filters:state.filters});download(text,'pokoscrap-'+data.type+'.csv');$('#modal').close();toast('CSV dibuat sesuai filter aktif.');return;}if(form.id==='whatsapp-check-form'){if(DEMO){const l=demo.leads.find(l=>l.id===state.currentLead.id);Object.assign(l,{whatsapp_status:data.status,whatsapp_check_method:data.method,whatsapp_checked_at:data.date});activity(l,'whatsapp_checked',data);}else await api('/leads/'+state.currentLead.id+'/whatsapp-check','POST',data);$('#modal').close();toast('Hasil pemeriksaan tercatat. Consent tidak berubah.');await render();return;}if(form.id==='consent-form'){const id=state.currentLead.id;if(DEMO){const l=demo.leads.find(l=>l.id===id);Object.assign(l,{consent_basis:data.basis,consent_at:data.date,consent_source:data.source,eligible_to_send:['opted_in','replied'].includes(data.basis)});activity(l,'consent_changed',data);}else await api('/leads/'+id+'/consent','POST',data);$('#modal').close();toast('Consent tercatat.');await render();return;}if(form.id==='edit-lead-form'){if(DEMO){const l=demo.leads.find(l=>l.id===state.currentLead.id);Object.assign(l,data,{country_origin_name:country(data.country_origin_code),country_origin_method:'manual'});activity(l,'lead_updated',{changes:data});}else await api('/leads/'+state.currentLead.id,'PATCH',data);$('#modal').close();toast('Koreksi tersimpan.');await render();return;}if(form.id==='note-form'){if(DEMO)activity(demo.leads.find(l=>l.id===state.currentLead.id),'note_added',data);else await api('/leads/'+state.currentLead.id,'PATCH',data);toast('Catatan tersimpan.');await render();return;}if(form.id==='evidence-form'){if(DEMO){if(!safeUrl(data.evidence_url)||!data.evidence_snippet)throw {detail:'Bukti wajib lengkap.'};const l=demo.leads.find(l=>l.id===state.currentLead.id);l.evidence.push({...data,id:crypto.randomUUID(),lead_id:l.id,status:'confirmed',reviewed_by:state.user.name,reviewed_at:new Date().toISOString()});activity(l,'evidence_added',data);}else await api('/leads/'+state.currentLead.id+'/evidence','POST',data);$('#modal').close();toast('Bukti tersimpan.');await render();return;}if(form.id==='settings-form'){const config=Object.fromEntries(Object.entries(data).map(([k,v])=>[k,Number(v)]));if(DEMO){demo.config={...demo.config,...config};persist();}else await api('/settings','PATCH',config);toast('Konfigurasi tersimpan.');return;}if(form.id==='directory-form'){const file=$('#directory-file').files[0];if(!file||file.size>2000000)throw {detail:'Pilih CSV maksimal 2 MB.'};if(DEMO){toast('Impor aktual tersedia pada aplikasi self-host.');return;}const result=await api('/directory/import','POST',{csv:await file.text()});modal('Hasil impor',`<p>${result.matched} baris cocok. ${result.errors.length} galat.</p>${result.errors.slice(0,10).map(x=>`<p class="small">Baris ${x.row}: ${e(x.error)}</p>`).join('')}`);return;}if(form.id==='api-key-form'){
      try{
        const key=await api('/api-keys','POST',data);
        modal('Simpan API Key Baru',`
          <p>Key hanya ditampilkan sekali ini. Simpan di pengelola rahasia atau file konfigurasi MCP Anda.</p>
          <div class="code-block" style="margin: 12px 0;">
            <pre>${e(key.key)}</pre>
          </div>
          <div style="display: flex; gap: 8px; justify-content: flex-end;">
            <button class="button primary" data-action="copy-code" data-code="${e(key.key)}">${icon('copy')} Salin Key</button>
          </div>
          <p class="small section-gap">Header: <code>Authorization: Bearer &lt;key&gt;</code>. Rate limit: ${key.requests_per_hour} req/jam.</p>
        `);
        if(state.route==='api-mcp') await render();
      }catch(err){
        if(String(err.detail||'').includes('Pro')){
          modal('Akses Paket Pro Diperlukan', `
            <p>Pembuatan API Key dan MCP Server memerlukan paket Pro.</p>
            <p class="small section-gap">Anda dapat mengaktifkan paket Pro Sandbox dengan satu klik untuk pengujian:</p>
            <div style="margin-top: 14px;">
              <button class="button primary" data-action="sandbox-upgrade-pro">${icon('check')} Aktifkan Paket Pro Sandbox</button>
            </div>
          `);
        }else{
          throw err;
        }
      }
      return;
    }if(form.id==='invite-form'){if(DEMO){toast('Undangan email tidak dikirim pada pratinjau.');$('#modal').close();return;}await api('/orgs/invite','POST',data);$('#modal').close();toast('Undangan dibuat.');return;}if(form.id==='user-form'){if(DEMO){const u=demo.users.find(u=>u.id===form.dataset.id);u.roles=[data.role];u.active=form.active.checked;persist();}else await api('/users/'+form.dataset.id,'PATCH',{roles:[data.role],active:form.active.checked});$('#modal').close();await render();return;}if(form.id==='org-form'){await api('/orgs','POST',data);state.user=await api('/me');await loadContext();route('overview');return;}if(form.id==='forgot-form'){if(!DEMO)await api('/forgot','POST',data);$('#modal').close();toast('Jika akun tersedia, instruksi pemulihan dikirim.');return;}if(form.id==='checkout-form'){if(DEMO)return;if(form.dataset.plan==='free'){await api('/billing/downgrade','POST',{plan:'free'});$('#modal').close();toast('Downgrade dijadwalkan pada akhir periode.');await render();return;}const result=await api('/billing/checkout','POST',{plan:form.dataset.plan,method:data.method});const url=safeUrl(result.checkout_url);modal('Invoice sandbox dibuat',`<p>Aktivasi paket menunggu webhook pembayaran terverifikasi.</p><a class="button primary section-gap" href="${e(url)}" target="_blank" rel="noopener noreferrer">Buka Tripay Sandbox ${icon('external')}</a>`);return;}if(form.id==='admin-form'){if(DEMO){toast('Perubahan platform hanya contoh; tidak disimpan.');$('#modal').close();return;}const endpoint=form.dataset.actionType==='adjust-credit'?'credits':'status';await api('/admin/tenants/'+form.dataset.id+'/'+endpoint,'POST',{...data,amount:Number(data.amount)});$('#modal').close();toast('Perubahan tercatat dalam audit.');await render();return;}}catch(error){const message=human(error);if(form.id==='auth-form')$('#auth-error').innerHTML=`<div class="alert error">${e(message)}</div>`;else if(form.id==='export-form')$('#export-error').innerHTML=`<div class="alert error">${e(message)}</div>`;else toast(message);}finally{if(submit)submit.disabled=false;}});
async function loadContext(){if(DEMO)return;state.countries=await api('/countries');if(!state.user.tenant_id){route('onboarding');return;}state.credits=await api('/credits/balance');}
window.addEventListener('hashchange',()=>{$('#modal').close();state.selected.clear();render();});
async function init(){if(DEMO){state.user={...demo.users[0],roles:['Owner','Admin'],platform_admin:true,organization_name:'Workspace Demo'};state.credits={balance:30,plan:'Free'};}else{const params=new URLSearchParams(location.search);if(params.get('verify')){try{await api('/verify','POST',{token:params.get('verify')});history.replaceState(null,'',location.pathname);toast('Email terverifikasi. Silakan masuk.');}catch(error){toast(human(error));}}if(params.get('reset')){modal('Atur kata sandi baru',`<form id="reset-password-form"><div class="field"><label for="new-password">Kata sandi baru</label><input id="new-password" name="password" type="password" minlength="12" required></div><button class="button primary">Simpan kata sandi</button></form>`);$('#reset-password-form').addEventListener('submit',async event=>{event.preventDefault();try{await api('/reset','POST',{token:params.get('reset'),password:$('#new-password').value});$('#modal').close();history.replaceState(null,'',location.pathname);toast('Kata sandi diperbarui.');}catch(error){toast(human(error));}});}try{state.user=await api('/me');await loadContext();}catch{state.user=null;}}await render();}
init();
setInterval(()=>{if(!DEMO&&state.user&&state.route.startsWith('jobs/')&&['queued','running','ingesting'].includes(state.currentJob?.status)&&!$('#modal').open)render();},5000);
