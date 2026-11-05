# Enepru formuláře → Lahodný CRM

Kompatibilní CRM: Stano1988/Enepru---CRM-Faktury s migracemi 0022/0023. Živý hosting ani skutečná schránka nebyly při vývoji připojené; testy nahrazují přenos a SMTP.

## Lokální CRM na Windows

Ponechte současné SMTP, nasaďte také nový crm_bridge.py vedle app.py. Všechny tři formuláře posílají zákaznická data v příloze enepru-poptavka.json, samostatně od podkladů. CRM tak použije skutečný zákaznický e-mail místo technického SMTP_FROM. Kontakt bez adresy lze přijmout a doplnit později.

V bezpečném nastavení hostingu vytvořte náhodný CRM_SHARED_SECRET (nejméně 32 znaků) a CRM_SOURCE_SLUG=enepru. Na Windows spusťte v CRM Pripojit-web.bat a stejný klíč vložte skrytým vstupem. Pro příjem nastavte Pripojit-postu.bat, vyberte vhodnou složku a případně automatický převod poptávek. CRM na PC nemusí mít veřejný port. Bez společného klíče zůstává původ e-mailu neověřený; špatný podpis se odmítá.

## Přímé veřejné HTTPS CRM

Nastavte CRM_ENDPOINT na skutečnou HTTPS adresu s cestou /api/inquiries/enepru/, CRM_SHARED_SECRET a CRM_SOURCE_SLUG=enepru. Klíč je pouze na serverech, nikdy v prohlížeči. TLS se ověřuje a přesměrování se nesledují.

Přímé API má přednost. Při chybě se zkusí SMTP; při nedostupnosti obou transportů se požadavek i soubory trvale uloží do crm_pending a server vrátí 202 s pravdivým oznámením. Pracovní vlákno opakuje přenos, rozestup se při chybách prodlužuje nejvýše na hodinu. Po restartu pokračuje. Zálohovat je nutné také databázi webu v APP_DATA_DIR, přístup k ní omezit na server. Po úspěchu se položka fronty odstraní. Administrace ve Statistikách ukazuje počet čekajících a nejistě doručených e-mailů.

Poptávka používá původní UUID formuláře. Duplicitní API retry ani pozdější e-mail nevytvoří nový záznam; jiné údaje pod stejným UUID vedou ke konfliktu. Kalkulace se uloží jako orientační podklad. Zejména PENB + pasport se nesmí automaticky potvrdit jen podle číselného součtu kalkulačky.

## Kontrola

- python -m unittest discover -s tests -v
- S testovacím prostředím CRM: ENEPRU_CRM_ROOT=/cesta/crm /cesta/crm/.venv/bin/python tests/crm_roundtrip.py
- S Playwright a Chromium: python tests/delivery_browser.py (pouze lokální server a simulované SMTP).

Po nasazení proveďte jednu vlastní testovací poptávku, zkontrolujte zákazníka, přílohy, cenu a duplicitu v cílovém CRM. Tato poslední živá kontrola vyžaduje skutečné nastavení hostingu a schránky.
