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
            expect(page.get_by_role('heading', name='Energetický průkaz pro vaši stavbu', level=1)).to_be_visible()
            expect(page.locator('.home-services')).to_have_text('PENB a pasporty staveb')
            expect(page.locator('.home-house')).to_be_visible()
            page.locator('.home-hero').get_by_role('link', name='Spočítat cenu PENB').click()
            expect(page).to_have_url(origin + '/#cena')
            expect(page.locator('#cena')).to_be_focused()
            expect(page.locator('#home-example-price')).to_have_text('4 900 Kč')
            expect(page.locator('#home-size option')).to_have_text(['Do 150 m²', 'Nad 150 do 250 m²', 'Nad 250 m²'])
            page.locator('#home-size').select_option('area-1')
            expect(page.locator('#home-example-price')).to_have_text('6 490 Kč')
            page.locator('.home-stage').scroll_into_view_if_needed()
            expect(page.locator('.home-phone')).to_have_attribute('href', 'tel:+420604572042')
            expect(page.locator('.home-papers')).to_have_css('animation-name', 'papers-arrive')
            expect(page.locator('.home-papers')).to_have_css('animation-duration', '4s')
            expect(page.locator('.home-scale span').last).to_have_css('animation-delay', '2.4s')
            assert page.locator('.home-house').evaluate('image => image.complete && image.naturalWidth > 0')
            page.get_by_role('link', name='Upřesnit cenu a poptat PENB').click()
            expect(page).to_have_url(origin + '/penb#quote-form')
            expect(page.locator('#quote-form')).to_be_focused()
            expect(page.locator('#size option')).to_have_text(['Do 150 m²', 'Nad 150 do 250 m²', 'Nad 250 m²'])
            expect(page.locator('#size')).to_have_value('area-1')
            expect(page.locator('#price')).to_have_text('6 490 Kč')
            page.locator('#size').select_option('area-2')
            expect(page.locator('#price')).to_have_text('7 490 Kč')
            page.get_by_text('Pokračovat k poptávce', exact=True).click()
            expect(page.locator('#quote-form input[name=name]')).to_be_visible()
            expect(page.locator('.request-next-step')).to_contain_text('potvrzením ceny a termínu')

            page.goto(origin + '/')
            page.locator('.home-hero').get_by_role('link', name='Potřebuji pasport').click()
            expect(page).to_have_url(origin + '/pasporty')
            page.locator('#passport-link').click()
            expect(page).to_have_url(origin + '/penb#quote-form')
            expect(page.locator('#passport')).to_be_checked()

        page.set_viewport_size({'width': 360, 'height': 550})
        page.goto(origin + '/')
        expect(page.locator('.home-papers')).to_have_css('animation-name', 'none')
        page.locator('.home-stage').scroll_into_view_if_needed()
        expect(page.locator('.home-papers')).to_have_css('animation-name', 'papers-arrive')

        page.emulate_media(reduced_motion='reduce')
        page.goto(origin + '/')
        expect(page.locator('.home-papers')).to_have_css('animation-name', 'none')
        expect(page.locator('.home-papers')).to_have_css('opacity', '1')
        expect(page.locator('.motion-replay')).to_be_hidden()

        page.emulate_media(reduced_motion='no-preference')
        page.set_viewport_size({'width': 1440, 'height': 900})
        page.goto(origin + '/nahled.html')
        page.locator('.home-hero').get_by_role('link', name='Spočítat cenu PENB').click()
        expect(page).to_have_url(origin + '/nahled.html#cena')
        expect(page.locator('#cena')).to_be_focused()
        page.locator('.home-stage').scroll_into_view_if_needed()
        expect(page.locator('.home-papers')).to_have_css('animation-name', 'papers-arrive')
        page.locator('#home-size').select_option('area-2')
        page.get_by_role('link', name='Upřesnit cenu a poptat PENB').click()
        expect(page.locator('#quote-form')).to_be_focused()
        expect(page.locator('#size')).to_have_value('area-2')
        expect(page.locator('#price')).to_have_text('7 490 Kč')
        expect(page.locator('#size option')).to_have_count(3)
        expect(page.locator('#quote-form [data-send]')).to_be_disabled()
        page.go_back()
        expect(page.locator('#uvod')).to_be_visible()
        expect(page.locator('.home-papers')).to_have_css('animation-name', 'none')
        page.get_by_role('button', name='Přehrát animaci znovu').click()
        expect(page.locator('.home-papers')).to_have_css('animation-name', 'papers-arrive')

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

print('PASS: responsive home, replay and reduced motion, home estimate handoff, calculator anchors, three house area bands, passport enquiry, portable preview and legal content.')
