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
            expect(page.get_by_role('heading', level=1)).to_have_count(1)
            page.locator('.home-hero').get_by_role('link', name='Spočítat cenu PENB').click()
            expect(page).to_have_url(origin + '/#quote-form')
            expect(page.locator('#quote-form')).to_be_focused()
            expect(page.locator('#size option')).to_have_text(['Do 150 m²', 'Nad 150 do 250 m²', 'Nad 250 m²'])
            page.locator('#size').select_option('area-1')
            expect(page.locator('#price')).to_have_text('6 490 Kč')
            expect(page.locator('#quote-summary-total')).to_have_text('6 490 Kč')
            expect(page.locator('#quote-overview')).to_have_css('position', 'sticky')
            if width < 881:
                page.locator('#quote-summary summary').click()
            expect(page.locator('#quote-summary-area')).to_have_text('Nad 150 do 250 m²')
            page.locator('#quote-summary-request').click()
            draft = page.locator('#quote-form input[name=name]')
            draft.fill('Rozepsaná poptávka')
            page.locator('.home-hero').get_by_role('link', name='Potřebuji pasport stavby').click()
            expect(page).to_have_url(origin + '/#pasporty')
            page.locator('#passport-link').click()
            expect(page).to_have_url(origin + '/#quote-form')
            expect(page.locator('#passport')).to_be_checked()
            expect(draft).to_have_value('Rozepsaná poptávka')
            expect(page.locator('#size')).to_have_value('area-1')

        page.goto(origin + '/pasporty')
        page.locator('#passport-link').click()
        expect(page.locator('#passport')).to_be_checked()

        page.goto(origin + '/nahled.html')
        page.locator('.home-hero').get_by_role('link', name='Spočítat cenu PENB').click()
        expect(page).to_have_url(origin + '/nahled.html#quote-form')
        page.locator('input[name=building][value=apartment]').check()
        page.locator('#size').select_option('custom')
        expect(page.locator('#price')).to_have_text('Na dotaz')
        page.locator('#size').select_option('1')
        expect(page.locator('#price')).to_have_text('9 800 Kč')
        expect(page.locator('#quote-form [data-send]')).to_be_disabled()
        page.locator('#survey').check()
        page.locator('#region').select_option('Plzeňský')
        expect(page.locator('#quote-summary-total')).to_have_text('Na dotaz')
        expect(page.locator('#quote-summary-survey')).to_contain_text('na dotaz')
        page.locator('#region').select_option('Vysočina')
        page.locator('#express').check()
        page.locator('#passport').check()
        expect(page.locator('#quote-summary-total')).to_have_text('16 800 Kč')
        expect(page.locator('#quote-summary-express')).to_have_text('3 000 Kč')
        expect(page.locator('#quote-summary-passport-row')).to_contain_text('Nacením zvlášť')

        for route in ('penb', 'pasporty'):
            page.goto(f'{origin}/{route}')
            image = page.locator(f'#{route} .topic-visual img')
            expect(image).to_be_visible()
            assert image.evaluate('img => img.complete && img.naturalWidth > 0')

        for route in ('gdpr', 'podminky'):
            page.goto(f'{origin}/{route}')
            assert page.locator(f'#{route} .legal-copy h2').count() >= 6
        expect(page.locator('#podminky')).to_contain_text('Faktura má splatnost 14 dnů')
        page.goto(origin + '/dotazy')
        expect(page.locator('#dotazy')).to_contain_text('splatností 14 dnů')
        browser.close()

    server.shutdown()
    server.server_close()

print('PASS: one-page layout, calculator links, draft retention, combined enquiries, portable preview and legal content.')
