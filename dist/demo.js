// PokoScrap Production Data Definitions - No dummy data
export const demoCountries = [
  {code:'ID',name:'Indonesia'},{code:'MY',name:'Malaysia'},{code:'VN',name:'Vietnam'},
  {code:'TH',name:'Thailand'},{code:'SG',name:'Singapura'},{code:'JP',name:'Jepang'},
  {code:'AU',name:'Australia'},{code:'US',name:'Amerika Serikat'},{code:'NL',name:'Belanda'},
  {code:'DE',name:'Jerman'},{code:'GB',name:'Inggris'},{code:'AE',name:'Uni Emirat Arab'}
];

export function initialDemo() {
  return {
    leads: [],
    jobs: [],
    segments: [],
    exports: [],
    config: {
      engine_mode: 'quick',
      concurrency: 1,
      depth: 1,
      enrichment_pages: 10,
      session_idle_minutes: 60
    },
    users: [],
    audit: []
  };
}

export function filterDemo(leads, f = {}) {
  return [];
}
