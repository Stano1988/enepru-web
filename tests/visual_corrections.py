"""Check public typography, navigation to enquiry forms and the portable preview."""
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

class PreviewHandler(app.Handler):
    def do_GET(self):
        if self.path == '/nahled.html':
            body = (app.ROOT / 'nahled.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()


with tempfile.TemporaryDirectory() as temp:
    app.DATA = Path(temp)
    app.initialize()
    server = app.ThreadingHTTPServer(('127.0.0.1', 0), PreviewHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_address[1]}'

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        page = browser.new_page()
        for width in (360, 1440):
            page.set_viewport_size({'width': width, 'height': 900})
            page.goto(origin + '/')
            expect(page.get_by_role('heading', name='PENB a pasporty staveb', level=1)).to_be_visible()
            expect(page.locator('main > .page:not([hidden]) img')).to_have_count(0)
            page.get_by_role('link', name='Zjistit cenu PENB').click()
            expect(page).to_have_url(origin + '/penb#quote-form')
            expect(page.locator('#quote-form')).to_be_focused()
            expect(page.locator('#size option')).to_have_text(['Do 150 m²', 'Nad 150 do 250 m²', 'Nad 250 m²'])
            page.locator('#size').select_option('area-2')
            expect(page.locator('#price')).to_have_text('7 490 Kč')
            page.get_by_text('Pokračovat k poptávce', exact=True).click()
            expect(page.locator('#quote-form input[name=name]')).to_be_visible()

            page.goto(origin + '/')
            page.get_by_role('link', name='Potřebuji pasport').click()
            expect(page).to_have_url(origin + '/pasporty')
            page.locator('#passport-link').click()
            expect(page).to_have_url(origin + '/penb#quote-form')
            expect(page.locator('#passport')).to_be_checked()

        page.goto(origin + '/nahled.html')
        page.get_by_role('link', name='Zjistit cenu PENB').click()
        expect(page.locator('#quote-form')).to_be_focused()
        expect(page.locator('#size option')).to_have_count(3)
        expect(page.locator('#quote-form [data-send]')).to_be_disabled()
        page.go_back()
        expect(page.locator('#uvod')).to_be_visible()

        for route in ('gdpr', 'podminky'):
            page.goto(f'{origin}/{route}')
            assert page.locator(f'#{route} .legal-copy h2').count() >= 6
        expect(page.locator('#podminky')).to_contain_text('Faktura má splatnost 14 dnů')
        page.goto(origin + '/dotazy')
        expect(page.locator('#dotazy')).to_contain_text('splatností 14 dnů')
        browser.close()

    server.shutdown()
    server.server_close()

print('PASS: responsive home, calculator anchors, three house area bands, passport enquiry, portable preview and legal content.')
