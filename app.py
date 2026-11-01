"""PENB website. Python 3.12+, standard library only. Run behind a TLS reverse proxy."""
import argparse, base64, collections, hashlib, hmac, html, http.cookies, io, ipaddress, json, os, re, secrets, smtplib, sqlite3, ssl, threading, time, zipfile
from email.message import EmailMessage
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('APP_DATA_DIR', str(ROOT / '.local')))
ROUTES = ['uvod','penb','pasporty','dotazy','kontakty','gdpr','podminky','cookies']
LOCK = threading.RLock()
LIMITS = collections.defaultdict(collections.deque)
SESSIONS = {}
LOGIN_TOKENS = {}

class Invalid(ValueError): pass

def db():
    c = sqlite3.connect(DATA / 'site.sqlite3', timeout=15)
    c.execute('PRAGMA journal_mode=WAL')
    return c

def initialize():
    DATA.mkdir(parents=True,exist_ok=True,mode=0o700)
    with db() as c:
        c.executescript('CREATE TABLE IF NOT EXISTS content(id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, body TEXT NOT NULL); CREATE TABLE IF NOT EXISTS auth(id INTEGER PRIMARY KEY CHECK(id=1),salt TEXT,hash TEXT); CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, state TEXT NOT NULL, created INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS views(day TEXT,page TEXT,count INTEGER, PRIMARY KEY(day,page));')
        c.execute('INSERT OR IGNORE INTO content VALUES(1,1,?)',(ROOT.joinpath('content.default.json').read_text(),))
        saved_rev,saved_body=c.execute('SELECT revision,body FROM content WHERE id=1').fetchone()
        saved=json.loads(saved_body);defaults=json.loads(ROOT.joinpath('content.default.json').read_text());missing={k:v for k,v in defaults.items() if k not in saved}
        if missing:
            saved.update(missing);c.execute('UPDATE content SET revision=revision+1,body=? WHERE id=1',(json.dumps(saved,ensure_ascii=False),))
        # An interrupted send is deliberately uncertain, never automatically replayed.
        c.execute("UPDATE requests SET state='uncertain' WHERE state='sending'")

def content():
    with db() as c: rev,body=c.execute('SELECT revision,body FROM content WHERE id=1').fetchone()
    return rev,json.loads(body)

def password_hash(password,salt):
    return hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()

def check_password(password):
    with db() as c: row=c.execute('SELECT salt,hash FROM auth WHERE id=1').fetchone()
    return bool(row and hmac.compare_digest(password_hash(password,row[0]),row[1]))

def throttle(key, count, seconds):
    with LOCK:
        now=time.monotonic(); q=LIMITS[key]
        while q and q[0]<now-seconds:q.popleft()
        if len(q)>=count: return False
        q.append(now)
        if len(LIMITS)>10000:
            for k in list(LIMITS):
                if not LIMITS[k] or LIMITS[k][-1]<now-3600: LIMITS.pop(k,None)
        return True

def quote(p, data):
    building=data.get('building');purpose=data.get('purpose');size=str(data.get('size',''))
    if building not in ('house','apartment','other') or purpose not in ('new','sale','renovation') or size not in ('0','1','2','3','custom'): raise Invalid('Neplatná kategorie nebo rozsah stavby.')
    for k in ('survey','express','passport'):
        if type(data.get(k)) is not bool:raise Invalid('Neplatná volba '+k)
    if data['survey'] and purpose!='sale': raise Invalid('Zaměření je dostupné pouze pro prodej či pronájem.')
    if data.get('region') not in p['regions']:raise Invalid('Vyberte platný kraj.')
    base=p['other'][purpose] if building=='other' else None if size=='custom' else p[building][purpose][int(size)]
    travel=p['regions'][data['region']] if data['survey'] else 0
    fee=p['expressFee'] if data['express'] else 0
    request=base is None or travel is None
    return dict(base=base,travel=travel,expressFee=fee,total=None if request else base+travel+fee,onRequest=request,passport=data['passport'],express=data['express'])

def validate_content(data, original):
    if set(data)!=set(original):raise Invalid('Neplatná struktura obsahu.')
    for section in ('texts','ui','seo','legal','contacts','mapBands'):
        if set(data[section])!=set(original[section]):raise Invalid('Změněná struktura textů.')
    def strings(v):
        if isinstance(v,dict):
            for a in v.values():strings(a)
        elif not isinstance(v,str) or len(v)>40000:raise Invalid('Neplatný text.')
    for s in ('texts','ui','seo','legal','contacts','mapBands'):strings(data[s])
    if any(not re.fullmatch(r'#[0-9a-fA-F]{6}',v) for v in data['mapBands'].values()):raise Invalid('Barvy pásem musí mít formát #RRGGBB.')
    if any(len(data['ui'][k].split('|'))!=5 for k in ('ui_house_sizes','ui_apartment_sizes')):raise Invalid('Popisky rozsahu musí obsahovat pět možností oddělených znakem |.')
    if not re.fullmatch(r'[^\s@<>\r\n]+@[^\s@<>\r\n]+\.[^\s@<>\r\n]+',data['contacts']['email']):raise Invalid('Neplatný kontaktní e-mail.')
    if not re.fullmatch(r'[+0-9 ()-]{5,30}',data['contacts']['phone']):raise Invalid('Neplatný telefon.')
    def numbers(a,b):
        if isinstance(b,dict):
            if not isinstance(a,dict) or set(a)!=set(b):raise Invalid('Neplatná struktura ceníku.')
            for k in b:numbers(a[k],b[k])
        elif isinstance(b,list):
            if not isinstance(a,list) or len(a)!=len(b):raise Invalid('Neplatný rozsah ceníku.')
            for x,y in zip(a,b):numbers(x,y)
        elif a is not None and (type(a)!=int or not 0<=a<=10000000):raise Invalid('Ceny musí být celé nezáporné částky, případně na dotaz.')
    numbers(data['pricing'],original['pricing'])
    p=data['pricing']
    if p['expressFee'] is None or p['travelOnRequestFrom'] is None:raise Invalid('Příplatek a minimum vyžadují částku.')
    if any(x is None for b in ('house','apartment') for arr in p[b].values() for x in arr):raise Invalid('Základní ceny PENB vyžadují částku.')

def smtp_ready():
    return all(os.environ.get(k) for k in ('SMTP_HOST','SMTP_PORT','SMTP_USER','SMTP_PASSWORD','SMTP_FROM')) and os.environ.get('SMTP_MODE','starttls') in ('starttls','ssl')

def send_mail(payload, attachments, result, site):
    msg=EmailMessage(); msg['Subject']='Nezávazná poptávka – '+{'penb':'PENB','passport':'pasport stavby','contact':'dotaz'}[payload['kind']]
    msg['From']=os.environ['SMTP_FROM'];msg['To']='penb.lahodny@seznam.cz';msg['Reply-To']=payload['email']
    labels={'name':'Jméno','email':'E-mail','phone':'Telefon','address':'Adresa','municipality':'Obec','propertyNumber':'Číslo popisné / parcelní','cadastralArea':'Katastrální území','description':'Popis stavby','notes':'Poznámky','building':'Typ stavby','purpose':'Účel','size':'Rozsah (index 0–3, custom = na dotaz)','region':'Kraj','survey':'Zaměření','passport':'Také pasport','express':'Expres'}
    lines=[f'{label}: {payload[k]}' for k,label in labels.items() if k in payload]
    if result:
        lines+=['','Cenový rozpis (Kč, neplátce DPH):']+[f'{k}: {v if v is not None else "Na dotaz"}' for k,v in result.items()]
        lines+=['Rozsah: '+(('1 podlaží','2 podlaží','3 podlaží','4 podlaží')[int(payload['size'])] if payload['building']=='house' and payload['size']!='custom' else ('Do 500 m²','Nad 500 do 1 000 m²','Nad 1 000 do 2 000 m²','Nad 2 000 do 3 000 m²')[int(payload['size'])] if payload['building']=='apartment' and payload['size']!='custom' else 'Individuální nabídka')]
        if result['travel'] is None:lines+=['Zaměření na dotaz, od '+str(site['pricing']['travelOnRequestFrom'])+' Kč; konečný součet není potvrzen.']
        lines+=['PENB do '+('5' if payload['express'] else '10')+' pracovních dnů od potvrzení zakázky a kompletních podkladů.','Pasport samostatně na dotaz, do 30 dnů od zaměření.','Platba na fakturu; podmínky se potvrdí při objednávce.']
    msg.set_content('\n'.join(lines))
    for name,mime,body in attachments:
        main,sub=mime.split('/');msg.add_attachment(body,maintype=main,subtype=sub,filename=name)
    context=ssl.create_default_context();mode=os.environ.get('SMTP_MODE','starttls')
    host=os.environ['SMTP_HOST'];port=int(os.environ['SMTP_PORT'])
    if mode=='ssl': client=smtplib.SMTP_SSL(host,port,context=context,timeout=25)
    else:
        client=smtplib.SMTP(host,port,timeout=25);client.ehlo();client.starttls(context=context);client.ehlo()
    with client:
        client.login(os.environ['SMTP_USER'],os.environ['SMTP_PASSWORD'])
        if client.send_message(msg):raise RuntimeError('Recipient refused')

def attachment(name, body):
    name=Path(name.replace('\\','/')).name
    name=re.sub(r'[\x00-\x1f\x7f]','',name)[:180]
    ext=Path(name).suffix.lower()
    mime={'.pdf':'application/pdf','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.zip':'application/zip'}.get(ext)
    if not mime or len(body)>10*1024*1024 or not body:raise Invalid('Příloha musí být PDF, JPG, PNG nebo ZIP, nejvýše 10 MB.')
    valid=body.startswith(b'%PDF-') if ext=='.pdf' else body.startswith(b'\x89PNG\r\n\x1a\n') if ext=='.png' else body.startswith(b'\xff\xd8\xff') if ext in ('.jpg','.jpeg') else zipfile.is_zipfile(io.BytesIO(body))
    if not valid:raise Invalid('Typ přílohy neodpovídá jejímu obsahu.')
    return name,mime,body

def render(route,site,rev):
    source=ROOT.joinpath('templates/site.html').read_text()
    source=re.sub(r'\{\{(\w+)\}\}',lambda m:html.escape(site['texts'].get(m[1],''),quote=True),source)
    if route not in ROUTES:route='uvod'
    source=re.sub(r'<section class="page wrap" id="(uvod|penb|pasporty|dotazy|kontakty)"([^>]*)>',lambda m:'<section class="page wrap" id="'+m[1]+'"'+re.sub(r'\s+hidden','',m[2])+(' hidden' if route!=m[1] else '')+'>',source)
    legal=''
    for k,text in site['legal'].items():
        legal+=f'<section class="page wrap" id="{k}"'+(' hidden' if route!=k else '')+'><div class="page-heading"><h1>'+html.escape(site['seo'][k]['title'].split(' | ')[0])+'</h1></div><article class="legal-copy">'+''.join('<p>'+html.escape(p).replace('\n','<br>')+'</p>' for p in text.split('\n\n'))+'</article></section>'
    source=source.replace('@@LEGAL@@',legal)
    defaults=json.loads(ROOT.joinpath('content.default.json').read_text())['contacts']
    for key,value in site['contacts'].items():
        source=source.replace(html.escape(defaults[key],quote=True),html.escape(value,quote=True))
    name=site['contacts']['name'].rsplit(' ',1)
    brand=html.escape(name[0])+(' <strong>'+html.escape(name[1])+'</strong>' if len(name)>1 else '')
    source=re.sub(r'(<span class="person-name">).*?(</span>)',lambda m:m[1]+brand+m[2],source)
    source=source.replace('tel:+420604572042','tel:'+re.sub(r'[^+0-9]','',site['contacts']['phone']))
    source=source.replace('mailto:penb.lahodny@seznam.cz','mailto:'+html.escape(site['contacts']['email'],quote=True))
    seo=site['seo'][route]
    source=re.sub(r'<title>.*?</title>','<title>'+html.escape(seo['title'])+'</title>',source)
    source=re.sub(r'<meta name="description"[^>]*>','<meta name="description" content="'+html.escape(seo['description'],quote=True)+'">',source)
    domain=os.environ.get('PUBLIC_ORIGIN','').rstrip('/')
    if domain:
        source=source.replace('</head>','<link rel="canonical" href="'+html.escape(domain+('/' if route=='uvod' else '/'+route),quote=True)+'"></head>')
    source=source.replace('</body>','<script src="/site-data.js"></script><script src="/static/navigation.js"></script><script src="/static/calculator.js"></script><script src="/static/forms.js"></script></body>')
    return source

class Handler(BaseHTTPRequestHandler):
    server_version='Lahodny'
    def log_message(self, *_):pass # Do not log query strings, submitted data or IP addresses.
    def secure(self):
        if isinstance(self.connection,ssl.SSLSocket):return True
        trusted=os.environ.get('TRUSTED_PROXIES','').split(',')
        return self.client_address[0] in trusted and self.headers.get('X-Forwarded-Proto')=='https'
    def local_dev(self):return os.environ.get('APP_ENV','development')=='development' and ipaddress.ip_address(self.client_address[0]).is_loopback
    def origin_ok(self):
        origin=self.headers.get('Origin','')
        expected=os.environ.get('PUBLIC_ORIGIN','').rstrip('/') or ('https' if self.secure() else 'http')+'://'+self.headers.get('Host','')
        return origin==expected and self.headers.get('Sec-Fetch-Site','same-origin') in ('same-origin','none')
    def reply(self,status,body,ctype='text/html; charset=utf-8',headers=None):
        body=body.encode() if isinstance(body,str) else body
        self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin');self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        if self.secure():self.send_header('Strict-Transport-Security','max-age=31536000')
        for k,v in (headers or {}).items():self.send_header(k,v)
        self.end_headers();self.wfile.write(body)
    def json(self,status,value,headers=None):self.reply(status,json.dumps(value,ensure_ascii=False),'application/json; charset=utf-8',headers)
    def read_body(self,max_size):
        try:n=int(self.headers.get('Content-Length','0'))
        except ValueError:raise Invalid('Chybí délka požadavku.')
        if n<=0 or n>max_size:raise Invalid('Příliš velký nebo prázdný požadavek.')
        self.connection.settimeout(30)
        return self.rfile.read(n)
    def session(self):
        try:
            cookies=http.cookies.SimpleCookie(self.headers.get('Cookie',''));token=cookies.get('sl_session');token=token.value if token else ''
        except http.cookies.CookieError:return None
        with LOCK:
            for key in list(SESSIONS):
                if SESSIONS[key]['expires']<time.time():SESSIONS.pop(key,None)
            return SESSIONS.get(token)
    def admin_allowed(self):return self.secure() or self.local_dev()
    def do_GET(self):
        path=urlsplit(self.path).path
        if path.startswith('/static/'):
            name=path.removeprefix('/static/')
            if '/' in name or name.startswith('.') or not re.fullmatch(r'[\w.-]+',name):return self.reply(404,'Nenalezeno')
            p=ROOT/'static'/name
            if not p.is_file():return self.reply(404,'Nenalezeno')
            mime={'.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.webp':'image/webp'}.get(p.suffix,'application/octet-stream')
            return self.reply(200,p.read_bytes(),mime)
        if path=='/api/status':return self.json(200,{'canSend':smtp_ready() and self.secure()})
        if path=='/site-data.js':
            rev,site=content();public={k:site[k] for k in ('pricing','ui','seo','mapBands')};public['revision']=rev
            return self.reply(200,'window.SITE='+json.dumps(public,ensure_ascii=True).replace('<','\\u003c')+';','text/javascript; charset=utf-8')
        if path.startswith('/admin') or path.startswith('/api/admin'):
            if not self.admin_allowed():return self.reply(403,'Administrace vyžaduje HTTPS.')
            session=self.session()
            if path=='/admin':
                if not session:
                    token=secrets.token_urlsafe(32)
                    with LOCK:
                        for k in list(LOGIN_TOKENS):
                            if LOGIN_TOKENS[k]<time.time():LOGIN_TOKENS.pop(k,None)
                        LOGIN_TOKENS[token]=time.time()+600
                    return self.reply(200,'<!doctype html><html lang="cs"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><link rel="stylesheet" href="/static/admin.css"><title>Přihlášení</title><main><h1>Správa webu</h1><p>Přihlášení majitele. Heslo se nastavuje příkazem na serveru; žádné výchozí heslo neexistuje.</p><form action="/api/admin/login" method="post"><input type="hidden" name="csrf" value="'+token+'"><label>Heslo <input type="password" name="password" required autocomplete="current-password" maxlength="256"></label><button>Přihlásit</button></form><a href="/">Zpět na web</a></main></html>')
                return self.reply(200,ROOT.joinpath('templates/admin.html').read_text())
            if not session:return self.json(401,{'error':'Přihlaste se.'})
            if path=='/api/admin/content':
                rev,site=content();return self.json(200,{'revision':rev,'content':site,'csrf':session['csrf']})
            if path=='/api/admin/stats':
                with db() as c:rows=c.execute('SELECT day,page,count FROM views ORDER BY day DESC,page LIMIT 500').fetchall()
                return self.json(200,{'views':rows})
            if path=='/api/admin/export':
                rev,site=content();return self.json(200,{'revision':rev,'content':site}, {'Content-Disposition':'attachment; filename="obsah-zaloha.json"'})
            return self.json(404,{'error':'Nenalezeno'})
        if path=='/robots.txt':
            origin=os.environ.get('PUBLIC_ORIGIN','').rstrip('/')
            return self.reply(200,'User-agent: *\n'+('Disallow: /admin\nDisallow: /api/\nSitemap: '+origin+'/sitemap.xml\n' if origin else 'Disallow: /\n'),'text/plain')
        if path=='/sitemap.xml':
            origin=os.environ.get('PUBLIC_ORIGIN','').rstrip('/')
            if not origin:return self.reply(404,'Produkční doména zatím není nastavená.')
            return self.reply(200,'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+html.escape(origin+('/' if r=='uvod' else '/'+r))+'</loc></url>' for r in ROUTES)+'</urlset>','application/xml')
        route='uvod' if path=='/' else path.strip('/')
        if path!='/' and path!='/'+route or route not in ROUTES:return self.reply(404,'Stránka nenalezena. <a href="/">Úvod</a>')
        if self.headers.get('DNT')!='1' and self.headers.get('Sec-GPC')!='1':
            with db() as c:c.execute('INSERT INTO views VALUES(?,?,1) ON CONFLICT(day,page) DO UPDATE SET count=count+1',(time.strftime('%Y-%m-%d',time.gmtime()),route))
        rev,site=content();return self.reply(200,render(route,site,rev))
    def do_POST(self):
        try:self.post()
        except Invalid as e:self.json(400,{'error':str(e)})
        except (json.JSONDecodeError,UnicodeError,KeyError,TypeError,AttributeError):self.json(400,{'error':'Neplatný požadavek.'})
        except Exception:self.json(500,{'error':'Požadavek se nepodařilo dokončit. Kontaktujte nás přímo.'})
    def post(self):
        path=urlsplit(self.path).path
        if path=='/api/enquiries':
            if not self.secure():return self.json(403,{'error':'Poptávky přijímáme pouze přes HTTPS.'})
            if not self.origin_ok():return self.json(403,{'error':'Nepovolený původ požadavku.'})
            if not throttle(('enquiry',self.client_address[0]),8,600):return self.json(429,{'error':'Příliš mnoho požadavků. Zkuste to později.'})
            if not smtp_ready():return self.json(503,{'error':'Odesílání není nakonfigurované. Zavolejte nebo napište přímo e-mailem.'})
            ct=self.headers.get('Content-Type','')
            if not ct.startswith('multipart/form-data;'):raise Invalid('Použijte formulář s přílohami.')
            raw=self.read_body(17*1024*1024)
            msg=BytesParser(policy=policy.default).parsebytes(('Content-Type: '+ct+'\r\nMIME-Version: 1.0\r\n\r\n').encode()+raw)
            if not msg.is_multipart() or msg.defects:raise Invalid('Poškozený formulář.')
            payload=None;files=[]
            for part in msg.iter_parts():
                name=part.get_param('name',header='content-disposition');body=part.get_payload(decode=True)
                if name=='payload' and payload is None:
                    if len(body)>64000:raise Invalid('Příliš dlouhý formulář.')
                    payload=json.loads(body)
                elif name=='attachments':files.append(attachment(part.get_filename() or '',body))
                else:raise Invalid('Neznámá nebo opakovaná část formuláře.')
            if len(files)>10 or sum(len(f[2]) for f in files)>15*1024*1024:raise Invalid('Nejvýše 10 souborů a 15 MB celkem.')
            if not isinstance(payload,dict):raise Invalid('Chybí formulář.')
            kind=payload.get('kind')
            if kind not in ('penb','passport','contact'):raise Invalid('Neplatný formulář.')
            if payload.get('_website'):raise Invalid('Poptávku nelze přijmout.')
            fields=('name','email','phone','address','municipality','propertyNumber','cadastralArea','description','notes')
            for k in fields:
                v=payload.get(k,'')
                if not isinstance(v,str) or len(v)> (10000 if k in ('notes','description') else 500) or '\x00' in v:raise Invalid('Neplatné nebo příliš dlouhé pole.')
                payload[k]=v.strip()
            if not payload['name'] or not re.fullmatch(r'[^\s@<>\r\n]+@[^\s@<>\r\n]+\.[^\s@<>\r\n]+',payload['email']) or len(payload['email'])>254:raise Invalid('Vyplňte jméno a platný e-mail.')
            if kind=='passport' and (not payload['municipality'] or not payload['propertyNumber']):raise Invalid('Vyplňte obec a číslo nemovitosti.')
            if kind=='contact' and (not payload['notes'] or files):raise Invalid('Vyplňte dotaz bez příloh.')
            request_id=payload.get('requestId','')
            if not isinstance(request_id,str) or not re.fullmatch(r'[a-fA-F0-9-]{36}',request_id):raise Invalid('Neplatný identifikátor odeslání.')
            rev,site=content();result=None
            if kind=='penb':
                result=quote(site['pricing'],payload)
                if payload.get('pricing')!=site['pricing'] or payload.get('quoted')!=result:
                    return self.json(409,{'error':'Ceník nebo kalkulace se změnily. Zkontrolujte novou cenu a odešlete znovu.','pricing':site['pricing']})
            fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()+b''.join(hashlib.sha256(f[2]).digest()+f[0].encode() for f in files)).hexdigest()
            with LOCK, db() as c:
                c.execute('DELETE FROM requests WHERE created<?',(int(time.time())-7*86400,))
                row=c.execute('SELECT fingerprint,state FROM requests WHERE id=?',(request_id,)).fetchone()
                if row:
                    if row[0]!=fingerprint:raise Invalid('Identifikátor byl použit pro jiný obsah.')
                    if row[1]=='sent':return self.json(200,{'ok':True})
                    return self.json(409,{'error':'Tato poptávka se již odesílá nebo je její doručení nejisté. Neodesílejte ji opakovaně; kontaktujte nás přímo.'})
                c.execute('INSERT INTO requests VALUES(?,?,?,?)',(request_id,fingerprint,'sending',int(time.time())))
            try:send_mail(payload,files,result,site)
            except Exception:
                with db() as c:c.execute("UPDATE requests SET state='uncertain' WHERE id=?",(request_id,))
                return self.json(502,{'error':'Poštovní služba nepotvrdila přijetí. Doručení je nejisté, neopakujte odeslání; kontaktujte nás přímo.'})
            with db() as c:c.execute("UPDATE requests SET state='sent' WHERE id=?",(request_id,))
            return self.json(200,{'ok':True})
        if path.startswith('/api/admin/'):
            if not self.admin_allowed() or not self.origin_ok():return self.json(403,{'error':'Vyžadováno HTTPS a stejný původ.'})
            if path=='/api/admin/login':
                if not throttle(('login',self.client_address[0]),5,900):return self.json(429,{'error':'Příliš mnoho pokusů. Zkuste za 15 minut.'})
                fields=parse_qs(self.read_body(4096).decode());token=fields.get('csrf',[''])[0]
                with LOCK:expiry=LOGIN_TOKENS.pop(token,0)
                if expiry<time.time() or not check_password(fields.get('password',[''])[0]):return self.reply(403,'Přihlášení se nezdařilo. <a href="/admin">Zkusit znovu</a>')
                token=secrets.token_urlsafe(32)
                with LOCK:SESSIONS[token]={'csrf':secrets.token_urlsafe(32),'expires':time.time()+3600}
                cookie='sl_session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600'+('; Secure' if self.secure() else '')
                return self.reply(303,'',headers={'Location':'/admin','Set-Cookie':cookie})
            session=self.session()
            if not session or not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),session['csrf']):return self.json(403,{'error':'Neplatná relace nebo CSRF token.'})
            if path=='/api/admin/logout':
                with LOCK:
                    for token,s in list(SESSIONS.items()):
                        if s is session:SESSIONS.pop(token,None)
                return self.json(200,{'ok':True},{'Set-Cookie':'sl_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0'})
            if path=='/api/admin/content':
                update=json.loads(self.read_body(2000000));rev,original=content();validate_content(update['content'],original)
                with LOCK,db() as c:
                    current=c.execute('SELECT revision,body FROM content WHERE id=1').fetchone()
                    if update['revision']!=current[0]:return self.json(409,{'error':'Obsah mezitím upravil někdo jiný. Exportujte své změny a načtěte aktuální obsah.'})
                    backup=DATA/'backups';backup.mkdir(exist_ok=True,mode=0o700)
                    (backup/f'content-{current[0]}.json').write_text(current[1]);
                    c.execute('UPDATE content SET revision=revision+1,body=? WHERE id=1',(json.dumps(update['content'],ensure_ascii=False),))
                return self.json(200,{'ok':True,'revision':rev+1})
        self.json(404,{'error':'Nenalezeno'})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8000);parser.add_argument('--bind',default='127.0.0.1');parser.add_argument('--set-password',action='store_true');args=parser.parse_args();initialize()
    if args.set_password:
        import getpass
        p=getpass.getpass('Nové heslo (min. 14 znaků): ')
        if len(p)<14 or p!=getpass.getpass('Znovu: '):raise SystemExit('Hesla se neshodují nebo je heslo příliš krátké.')
        salt=secrets.token_hex(16)
        with db() as c:c.execute('INSERT OR REPLACE INTO auth VALUES(1,?,?)',(salt,password_hash(p,salt)))
        print('Heslo bezpečně nastaveno.');return
    origin=os.environ.get('PUBLIC_ORIGIN','')
    if origin and (not origin.startswith('https://') or urlsplit(origin).path not in ('','/') or urlsplit(origin).username):raise SystemExit('PUBLIC_ORIGIN musí být HTTPS origin bez cesty.')
    server=ThreadingHTTPServer((args.bind,args.port),Handler)
    print(f'Server běží na portu {args.port}. Produkční odesílání vyžaduje HTTPS a SMTP.',flush=True)
    server.serve_forever()
if __name__=='__main__':main()
