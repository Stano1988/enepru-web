"""Local browser/server integration with a simulated trusted TLS proxy and SMTP.
No actual TLS connection or e-mail delivery is claimed by this test.
"""
import json, os, sys, tempfile, threading
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
from playwright.sync_api import sync_playwright,expect
with tempfile.TemporaryDirectory() as tmp:
 app.DATA=Path(tmp);app.initialize();server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);threading.Thread(target=server.serve_forever,daemon=True).start();origin=f'http://127.0.0.1:{server.server_address[1]}'
 with patch.dict(os.environ,{'PUBLIC_ORIGIN':origin,'TRUSTED_PROXIES':'127.0.0.1','SMTP_HOST':'smtp.test','SMTP_PORT':'587','SMTP_USER':'test','SMTP_PASSWORD':'test','SMTP_FROM':'sender@example.test'}),patch('app.smtplib.SMTP') as smtp,sync_playwright() as p:
  smtp.return_value.__enter__.return_value=smtp.return_value;smtp.return_value.send_message.return_value={}
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);context=browser.new_context(extra_http_headers={'X-Forwarded-Proto':'https'});page=context.new_page();page.goto(origin+'/penb');page.locator('#request-details summary').click();page.locator('#quote-form input[name=name]').fill('Test poptávka');page.locator('#quote-form input[name=email]').fill('test@example.test');page.locator('#quote-form textarea[name=notes]').fill('Poznámka z prohlížeče');page.locator('#files').set_input_files({'name':'plan.pdf','mimeType':'application/pdf','buffer':b'%PDF-1.7\n'});page.locator('#express').check();page.locator('#quote-form [data-send]').click();expect(page.locator('#quote-form .send-status')).to_contain_text('předána poštovní službě');assert smtp.return_value.send_message.call_count==1
  mail=smtp.return_value.send_message.call_args.args[0];assert mail['Reply-To']=='test@example.test';assert len([part for part in mail.iter_attachments() if part.get_content_type()!=app.crm_bridge.MIME])==1;assert any(part.get_content_type()==app.crm_bridge.MIME for part in mail.iter_attachments());assert 'Poznámka z prohlížeče' in mail.get_body(preferencelist=('plain',)).get_content()
  page.goto(origin+'/pasporty');page.locator('#passport-form input[name=name]').fill('Test pasport');page.locator('#passport-form input[name=email]').fill('test@example.test');page.locator('#passport-form input[name=municipality]').fill('Obec');page.locator('#passport-form input[name=propertyNumber]').fill('—');page.locator('#passport-form textarea[name=notes]').fill('Poznámka pasport');page.locator('#passport-files').set_input_files({'name':'plan.pdf','mimeType':'application/pdf','buffer':b'%PDF-1.7\n'});page.locator('#passport-form [data-send]').click();expect(page.locator('#passport-form .send-status')).to_contain_text('předána poštovní službě');assert smtp.return_value.send_message.call_count==2
  page.goto(origin+'/kontakty');page.locator('#contact-form input[name=name]').fill('Test dotaz');page.locator('#contact-form input[name=email]').fill('test@example.test');page.locator('#contact-form textarea').fill('Dotaz z prohlížeče');page.locator('#contact-form [data-send]').click();expect(page.locator('#contact-form .send-status')).to_contain_text('předána poštovní službě');assert smtp.return_value.send_message.call_count==3
  # A stale tariff must not send and must require a second explicit click.
  page.goto(origin+'/penb');page.locator('#request-details summary').click();page.locator('#quote-form input[name=name]').fill('Test nové ceny');page.locator('#quote-form input[name=email]').fill('test@example.test')
  with app.db() as c:
   rev,site=app.content();site['pricing']['house']['sale'][0]=5000;c.execute('UPDATE content SET revision=revision+1,body=? WHERE id=1',(json.dumps(site),))
  page.locator('#quote-form [data-send]').click();expect(page.locator('#quote-form .send-status')).to_contain_text('změnily');expect(page.locator('#price')).to_contain_text('5');assert smtp.return_value.send_message.call_count==3;page.locator('#quote-form [data-send]').click();expect(page.locator('#quote-form .send-status')).to_contain_text('předána poštovní službě');assert smtp.return_value.send_message.call_count==4
  browser.close()
 server.shutdown();server.server_close()
print('PASS: all 3 real browser forms reached the local server and simulated SMTP, with notes, PDF, Reply-To, express and explicit tariff reconfirmation. No actual e-mail sent.')
