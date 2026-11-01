import copy, http.client, importlib.util, io, json, os, re, tempfile, threading, unittest, uuid, zipfile
from email.message import EmailMessage
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app

class Prices(unittest.TestCase):
 def setUp(self):self.site=json.loads((app.ROOT/'content.default.json').read_text());self.p=self.site['pricing']
 def data(self,**kwargs):return dict(building='house',purpose='sale',size='0',survey=False,region='Vysočina',passport=False,express=False,**kwargs)
 def test_all_24_base_prices(self):
  count=0
  for building in ('house','apartment'):
   for purpose in ('new','sale','renovation'):
    for i,expected in enumerate(self.p[building][purpose]):
     d=self.data();d.update(building=building,purpose=purpose,size=str(i));self.assertEqual(app.quote(self.p,d)['total'],expected);count+=1
  self.assertEqual(count,24)
 def test_all_regions_and_express(self):
  for region,travel in self.p['regions'].items():
   for express in (False,True):
    d=self.data();d.update(region=region,survey=True,express=express)
    q=app.quote(self.p,d);self.assertEqual(q['travel'],travel);self.assertEqual(q['expressFee'],3000 if express else 0);self.assertEqual(q['total'],None if travel is None else 4900+travel+(3000 if express else 0))
 def test_custom_and_other(self):
  for b in ('house','apartment','other'):
   d=self.data();d.update(building=b,size='custom');self.assertIsNone(app.quote(self.p,d)['total'])
  d=self.data();d['building']='other';self.p['other']['sale']=10000;self.assertEqual(app.quote(self.p,d)['total'],10000)
 def test_basement(self):
  d=self.data();d['size']='2';self.assertEqual(app.quote(self.p,d)['total'],7490)
 def test_invalid(self):
  for changes in ({'purpose':'new','survey':True},{'purpose':'renovation','survey':True},{'size':'-1'},{'size':'4'},{'building':'bad'},{'region':'bad'},{'express':'false'}):
   d=self.data();d.update(changes)
   with self.assertRaises(app.Invalid):app.quote(self.p,d)
 def test_content_validation(self):
  for bad in (-1,1.5,True,'500'):
   c=copy.deepcopy(self.site);c['pricing']['expressFee']=bad
   with self.assertRaises(app.Invalid):app.validate_content(c,self.site)
 def test_attachments(self):
  self.assertEqual(app.attachment('../../plan.pdf',b'%PDF-1.7\n')[0],'plan.pdf')
  for n,b in [('x.pdf',b'evil'),('x.exe',b'%PDF-1'),('x.jpg',b'%PDF-1'),('x.zip',b'PK')]:
   with self.assertRaises(app.Invalid):app.attachment(n,b)
  buff=io.BytesIO()
  with zipfile.ZipFile(buff,'w') as z:z.writestr('plan.txt','document')
  self.assertEqual(app.attachment('plan.zip',buff.getvalue())[1],'application/zip')

class HTTP(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();app.DATA=Path(cls.tmp.name);app.initialize()
  cls.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);cls.port=cls.server.server_address[1]
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.tmp.cleanup()
 def setUp(self):
  app.LIMITS.clear();self.origin=f'http://127.0.0.1:{self.port}'
  self.env=patch.dict(os.environ,{'APP_ENV':'development','TRUSTED_PROXIES':'127.0.0.1','SMTP_HOST':'smtp.test','SMTP_PORT':'587','SMTP_MODE':'starttls','SMTP_USER':'test','SMTP_PASSWORD':'test','SMTP_FROM':'sender@example.test'},clear=True);self.env.start();self.addCleanup(self.env.stop)
 def request(self,path,method='GET',body=None,headers=None):
  c=http.client.HTTPConnection('127.0.0.1',self.port);c.request(method,path,body,headers or {});r=c.getresponse();v=(r.status,dict(r.getheaders()),r.read());c.close();return v
 def payload(self,kind='penb'):
  rev,s=app.content();d=dict(kind=kind,requestId=str(uuid.uuid4()),name='Test osoba',email='test@example.test',notes='Poznámka',phone='+420000000000',municipality='Obec',propertyNumber='—',description='Popis stavby',address='—',cadastralArea='—',_website='')
  if kind=='penb':
   d.update(building='house',purpose='sale',size='2',survey=True,region='Vysočina',passport=True,express=True,pricing=s['pricing']);d['quoted']=app.quote(s['pricing'],d)
  return d
 def multipart(self,payload,files=None):
  boundary='----TestBoundary';b=b''
  for name,filename,data in [('payload',None,json.dumps(payload).encode())]+[('attachments',n,d) for n,d in (files or [])]:
   b+=f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'.encode()
   if filename:b+=f'; filename="{filename}"'.encode()
   b+=b'\r\n\r\n'+data+b'\r\n'
  return b+f'--{boundary}--\r\n'.encode(),{'Content-Type':f'multipart/form-data; boundary={boundary}','Origin':f'https://127.0.0.1:{self.port}','X-Forwarded-Proto':'https'}
 def submit(self,payload,files=None,headers=None):
  body,h=self.multipart(payload,files);h.update(headers or {});return self.request('/api/enquiries','POST',body,h)
 def test_routes_and_private_files(self):
  for path in ('/','/penb','/pasporty','/dotazy','/kontakty','/gdpr','/podminky','/cookies'):
   status,h,b=self.request(path);self.assertEqual(status,200,path);self.assertIn(b'<title>',b);self.assertIn('Content-Security-Policy',h)
  for path in ('/.local/site.sqlite3','/app.py','/static/../app.py','/.env','/api/admin/stats','/api/admin/export'):
   self.assertIn(self.request(path)[0],(401,404))
 def test_unsecured_and_untrusted_rejected(self):
  p=self.payload();self.assertEqual(self.submit(p,headers={'X-Forwarded-Proto':''})[0],403)
  with patch.dict(os.environ,{'TRUSTED_PROXIES':''}):self.assertEqual(self.submit(p)[0],403)
  self.assertEqual(self.submit(p,headers={'Origin':'https://evil.test'})[0],403)
 def test_no_smtp(self):
  with patch.dict(os.environ,{'SMTP_PASSWORD':''}):self.assertEqual(self.submit(self.payload())[0],503)
 def test_all_forms_mail_content_tls_and_duplicate(self):
  for kind in ('penb','passport','contact'):
   p=self.payload(kind);files=[] if kind=='contact' else [('plan.pdf',b'%PDF-1.7\n')]
   with patch('app.smtplib.SMTP') as smtp:
    smtp.return_value.__enter__.return_value=smtp.return_value;smtp.return_value.send_message.return_value={}
    self.assertEqual(self.submit(p,files)[0],200)
    smtp.return_value.starttls.assert_called_once();ctx=smtp.return_value.starttls.call_args.kwargs['context'];self.assertTrue(ctx.check_hostname)
    mail=smtp.return_value.send_message.call_args.args[0];self.assertEqual(mail['Reply-To'],p['email']);self.assertEqual(mail['To'],'penb.lahodny@seznam.cz');text=mail.get_body(preferencelist=('plain',)).get_content();self.assertIn('Poznámka',text)
    self.assertEqual(len(list(mail.iter_attachments())),len(files))
    if kind=='penb':
     self.assertIn('14490',text);self.assertIn('3000',text);self.assertIn('Vysočina',text);self.assertIn('5 pracovních dnů',text)
    self.assertEqual(self.submit(p,files)[0],200);self.assertEqual(smtp.return_value.send_message.call_count,1)
 def test_changed_price_invalid_fields_and_files(self):
  p=self.payload();p['quoted']['total']=1;self.assertEqual(self.submit(p)[0],409)
  p=self.payload();p['pricing']['expressFee']=1;self.assertEqual(self.submit(p)[0],409)
  p=self.payload();p['email']='x\r\nBcc: victim@example.test';self.assertEqual(self.submit(p)[0],400)
  p=self.payload();self.assertEqual(self.submit(p,[('evil.pdf',b'not pdf')])[0],400)
  p=self.payload();p['_website']='spam';self.assertEqual(self.submit(p)[0],400)
 def test_smtp_failure_not_success(self):
  p=self.payload()
  with patch('app.smtplib.SMTP',side_effect=OSError('failure')):
   self.assertEqual(self.submit(p)[0],502);self.assertEqual(self.submit(p)[0],409)
 def login(self):
  salt='ab'*16
  with app.db() as c:c.execute('INSERT OR REPLACE INTO auth VALUES(1,?,?)',(salt,app.password_hash('Long-test-password-123',salt)))
  page=self.request('/admin')[2].decode();token=re.search('name="csrf" value="([^"]+)"',page)[1]
  s,h,b=self.request('/api/admin/login','POST','csrf='+token+'&password=Long-test-password-123',{'Origin':self.origin,'Content-Type':'application/x-www-form-urlencoded'});self.assertEqual(s,303)
  return h['Set-Cookie'].split(';')[0]
 def test_admin_csrf_persistence_conflict_export_stats(self):
  cookie=self.login();headers={'Cookie':cookie,'Origin':self.origin,'Content-Type':'application/json'}
  state=json.loads(self.request('/api/admin/content',headers=headers)[2]);state['content']['legal']['gdpr']='Upravené GDPR <script>bad</script>'
  state['content']['texts'][next(iter(state['content']['texts']))]='Nový text <script>bad</script>'
  self.assertEqual(self.request('/api/admin/content','POST',json.dumps(state),headers)[0],403)
  headers['X-CSRF-Token']=state['csrf'];self.assertEqual(self.request('/api/admin/content','POST',json.dumps(state),headers)[0],200)
  self.assertEqual(self.request('/api/admin/content','POST',json.dumps(state),headers)[0],409)
  self.assertIn(b'&lt;script&gt;bad&lt;/script&gt;',self.request('/gdpr')[2]);self.assertTrue(list((app.DATA/'backups').glob('*.json')))
  self.assertEqual(self.request('/api/admin/export',headers=headers)[0],200);self.assertEqual(self.request('/api/admin/stats',headers=headers)[0],200)
  self.assertEqual(app.content()[1]['legal']['gdpr'],state['content']['legal']['gdpr'])
  self.assertEqual(self.request('/api/admin/logout','POST','{}',headers)[0],200);self.assertEqual(self.request('/api/admin/content',headers=headers)[0],401)
 def test_dnt_and_gpc(self):
  with app.db() as c:c.execute('DELETE FROM views')
  self.request('/penb',headers={'DNT':'1'});self.request('/penb',headers={'Sec-GPC':'1'})
  with app.db() as c:self.assertEqual(c.execute('SELECT count(*) FROM views').fetchone()[0],0)
  self.request('/penb')
  with app.db() as c:self.assertEqual(c.execute('SELECT count FROM views').fetchone()[0],1)

if __name__=='__main__':unittest.main()
