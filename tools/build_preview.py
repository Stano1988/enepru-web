"""Generate a standalone, non-sending HTML preview from public default content."""
import base64,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
site=json.loads((app.ROOT/'content.default.json').read_text());s=app.render('uvod',site,1)
s=re.sub(r'<link rel="canonical"[^>]+>','',s)
s=re.sub(r'<link rel="stylesheet" href="/static/([^"]+)">',lambda m:'<style>'+app.ROOT.joinpath('static',m[1]).read_text()+'</style>',s)
s=re.sub(r'src="/static/([^"/]+\.webp)"',lambda m:'src="data:image/webp;base64,'+base64.b64encode(app.ROOT.joinpath('static',m[1]).read_bytes()).decode()+'"',s)
s=re.sub(r'href="/(penb|pasporty|dotazy|kontakty|gdpr|podminky|cookies)(#[^"]*)?"',lambda m:'href="#'+(m[2][1:] if m[2] else m[1])+'"',s)
s=s.replace('href="/"','href="#uvod"').replace('<a href="/admin">Administrace</a>','<span>Správa textů a cen: po spuštění webu na hostingu na adrese /admin</span>')
s=s.replace('<script src="/site-data.js"></script>','<script>window.SITE='+json.dumps({k:site[k] for k in ('pricing','ui','seo','mapBands')},ensure_ascii=True).replace('<','\\u003c')+';</script>')
nav='''(() => {function show(){const id=location.hash.slice(1)||'uvod';const route=id==='pasport-form'?'pasporty':Object.keys(SITE.seo).includes(id)?id:'uvod';document.querySelectorAll('main > .page').forEach(s=>s.hidden=s.id!==route);document.querySelectorAll('.header nav a').forEach(a=>{if(a.hash==='#'+route)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});document.title=SITE.seo[route]?.title||SITE.seo.uvod.title;if(id==='pasport-form')document.getElementById(id)?.scrollIntoView();else scrollTo(0,0);}addEventListener('hashchange',show);show();})();'''
s=s.replace('<script src="/static/navigation.js"></script>','<script>'+nav+'</script>')
s=s.replace('<script src="/static/calculator.js"></script>','<script>'+app.ROOT.joinpath('static/calculator.js').read_text()+'</script>')
s=s.replace('<script src="/static/forms.js"></script>','<script>document.querySelectorAll("form").forEach(f=>{f.addEventListener("submit",e=>e.preventDefault());f.querySelector("[data-send]").disabled=true;});document.querySelector(".preview").textContent="Samostatný náhled · formuláře a přílohy se neodesílají";</script>')
out=Path(sys.argv[1]) if len(sys.argv)>1 else app.ROOT/'nahled.html';out.write_text(s);print(out)
