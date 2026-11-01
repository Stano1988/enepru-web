"""Browser regression checks; requires Playwright and Chromium only for testing."""
import json, os, secrets, sys, tempfile, threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
from playwright.sync_api import sync_playwright, expect

with tempfile.TemporaryDirectory() as temp:
 app.DATA=Path(temp);app.initialize();salt=secrets.token_hex(16);password=secrets.token_urlsafe(24)
 with app.db() as c:c.execute('INSERT INTO auth VALUES(1,?,?)',(salt,app.password_hash(password,salt)))
 server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);threading.Thread(target=server.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{server.server_address[1]}'
 errors=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(origin+'/penb');expect(page.locator('#price')).to_contain_text('900')
  pricing=app.content()[1]['pricing'];count=0
  for building in ('house','apartment'):
   page.locator(f'input[name=building][value={building}]').check()
   for purpose in ('new','sale','renovation'):
    page.locator('#purpose').select_option(purpose)
    for i,expected in enumerate(pricing[building][purpose]):
     page.locator('#size').select_option(str(i));actual=int(''.join(x for x in page.locator('#price').inner_text() if x.isdigit()));assert actual==expected,(building,purpose,i,actual);count+=1
  page.locator('input[name=building][value=house]').check();page.locator('#purpose').select_option('sale');page.locator('#size').select_option('0');page.locator('#survey').check()
  for name,fee in pricing['regions'].items():
   page.locator('#region').select_option(name)
   assert page.locator('[data-region][aria-pressed=true]').count()>=1
   for express in (False,True):
    page.locator('input[name=processing][value='+('express' if express else 'standard')+']').check()
    price=page.locator('#price').inner_text()
    if fee is None:assert price=='Na dotaz'
    else:assert int(''.join(x for x in price if x.isdigit()))==4900+fee+(3000 if express else 0)
  page.locator('#region-map [data-region="Vysočina"]').click();assert page.locator('#region').input_value()=='Vysočina'
  page.locator('#region-map [data-region="Praha"]').focus();page.keyboard.press('Enter');assert page.locator('#region').input_value()=='Praha'
  page.locator('#purpose').select_option('new');assert not page.locator('#survey').is_checked();assert not page.locator('#region-panel').is_visible()
  page.locator('#size').select_option('custom');assert page.locator('#price').inner_text()=='Na dotaz'
  page.locator('input[name=building][value=other]').check();assert page.locator('#price').inner_text()=='Na dotaz'
  page.locator('#request-details summary').click();page.locator('#quote-form input[name=name]').fill('Rozepsaný formulář')
  page.locator('#quote-form .privacy-note a').click();assert page.locator('#quote-form input[name=name]').input_value()=='Rozepsaný formulář'
  assert page.locator('#quote-form [data-send]').is_disabled()
  for width in (360,390,768,1440):
   page.set_viewport_size({'width':width,'height':900})
   for path in ('/','/penb','/pasporty','/dotazy','/kontakty','/gdpr','/podminky','/cookies'):
    page.goto(origin+path);assert page.locator('main > .page:not([hidden])').count()==1
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(width,path)
   page.goto(origin+'/');page.get_by_role('link',name='PENB',exact=True).click();assert page.url.endswith('/penb');page.go_back();assert page.locator('#uvod').is_visible();page.go_forward();assert page.locator('#penb').is_visible()
  page.set_viewport_size({'width':390,'height':900});page.goto(origin+'/');page.screenshot(path='/workspace/nahled-mobil.png',full_page=True)
  page.set_viewport_size({'width':1440,'height':1000});page.screenshot(path='/workspace/nahled-desktop.png',full_page=True)
  page.goto(origin+'/admin');page.locator('input[name=password]').fill(password);page.get_by_role('button',name='Přihlásit',exact=True).click();page.wait_for_selector('#editor textarea')
  page.locator('#editor textarea').first.fill('Upravený text vlastníkem');page.locator('#save').click();expect(page.locator('#status')).to_contain_text('Uloženo')
  page.locator('[data-tab=pricing]').click();page.locator('#editor input').first.fill('4700');page.locator('#save').click();expect(page.locator('#status')).to_contain_text('Verze 3')
  page.locator('[data-tab=legal]').click();page.locator('#editor textarea').first.fill('Aktualizované zásady GDPR');page.locator('#save').click();expect(page.locator('#status')).to_contain_text('Verze 4')
  page.locator('[data-tab=stats]').click();page.wait_for_selector('#editor table');assert page.locator('#editor tr').count()>1
  page.goto(origin+'/gdpr');assert 'Aktualizované zásady GDPR' in page.locator('#gdpr').inner_text()
  assert app.content()[1]['pricing']['house']['new'][0]==4700
  browser.close()
 server.shutdown();server.server_close()
 assert not errors,errors
 print(f'PASS: {count} base prices, 28 region/express combinations, keyboard map, 32 route/viewport checks, browser history, drafts, admin text/price/GDPR editing and private statistics. No browser errors.')
