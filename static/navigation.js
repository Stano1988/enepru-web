(() => {
 const routes=['uvod','penb','pasporty','dotazy','kontakty','gdpr','podminky','cookies'];
 function show(){
  const route=location.pathname==='/'?'uvod':location.pathname.slice(1);
  document.querySelectorAll('main > .page').forEach(s=>s.hidden=s.id!==route);
  document.querySelectorAll('.header nav a').forEach(a=>{if(a.pathname===location.pathname)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  if(window.SITE?.seo[route]) {document.title=SITE.seo[route].title;document.querySelector('meta[name="description"]').content=SITE.seo[route].description;}
  const canonical=document.querySelector('link[rel=canonical]');if(canonical)canonical.href=location.origin+location.pathname;
  if(location.hash)document.getElementById(location.hash.slice(1))?.scrollIntoView();else scrollTo(0,0);
 }
 document.addEventListener('click',e=>{
  const a=e.target.closest('a');if(!a||a.target||e.defaultPrevented||e.button!==0||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey||a.origin!==location.origin)return;
  const r=a.pathname==='/'?'uvod':a.pathname.slice(1);if(!routes.includes(r))return;
  e.preventDefault();history.pushState(null,'',a.pathname+a.hash);show();
  document.querySelector('main > .page:not([hidden]) h1')?.setAttribute('tabindex','-1');
  document.querySelector('main > .page:not([hidden]) h1')?.focus({preventScroll:true});
 });
 addEventListener('popstate',show);show();
})();
