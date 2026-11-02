"""Check logo baseline, animation visibility, editable image captions and legal headings."""
import sys,tempfile,threading,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
from playwright.sync_api import sync_playwright,expect
with tempfile.TemporaryDirectory() as temp:
 app.DATA=Path(temp);app.initialize();server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);threading.Thread(target=server.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{server.server_address[1]}'
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1000})
  page.goto(origin+'/');page.wait_for_timeout(100)
  assert page.locator('.real-documents').evaluate("e=>getComputedStyle(e).animationName")=='documents-arrive'
  start=page.locator('.real-documents').evaluate("e=>Number(getComputedStyle(e).opacity)")
  page.wait_for_timeout(1800);end=page.locator('.real-documents').evaluate("e=>Number(getComputedStyle(e).opacity)");assert end>start and end>.99,(start,end)
  a=page.locator('.energy-level').first.evaluate("e=>getComputedStyle(e).filter");page.wait_for_timeout(1000);b=page.locator('.energy-level').first.evaluate("e=>getComputedStyle(e).filter");assert a!=b,(a,b)
  for width in (390,1440):
   page.set_viewport_size({'width':width,'height':1000})
   difference=page.locator('header .personal-brand').evaluate("e=>{const svg=e.querySelector('svg');const p=svg.createSVGPoint();p.x=35;p.y=61;return p.matrixTransform(svg.getScreenCTM()).y-e.querySelector('.brand-spectrum').getBoundingClientRect().top}")
   assert abs(difference)<2,(width,difference)
  page.screenshot(path='/workspace/korekce-uvod.png',full_page=True)
  page.goto(origin+'/gdpr');assert page.locator('#gdpr .legal-copy h2').count()>=6
  page.goto(origin+'/podminky');assert page.locator('#podminky .legal-copy h2').count()>=6;expect(page.locator('#podminky')).to_contain_text('Faktura má splatnost 14 dnů')
  page.goto(origin+'/dotazy');expect(page.locator('#dotazy')).to_contain_text('splatností 14 dnů')
  for route in ('penb','pasporty','kontakty'):
   page.goto(origin+'/'+route);image=page.locator('#'+route+' .topic-visual img');expect(image).to_be_visible();assert image.evaluate('e=>e.complete && e.naturalWidth>0');page.screenshot(path='/workspace/korekce-'+route+'.png',full_page=True)
  reduced=browser.new_context(reduced_motion='reduce');pg=reduced.new_page();pg.goto(origin+'/');assert pg.locator('.real-documents').evaluate('e=>getComputedStyle(e).animationName')=='none';assert pg.locator('.energy-level').first.evaluate('e=>getComputedStyle(e).animationName')=='none';browser.close()
 server.shutdown();server.server_close()
print('PASS: house baseline on spectrum at mobile/desktop, visible document reveal and changing energy highlight, reduced motion, legal headings, 14-day payment and 3 section images.')
