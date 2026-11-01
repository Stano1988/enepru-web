Web ENEPRU

# Ing. Stanislav Lahodný — PENB a pasporty staveb

Obnovený web ze zachráněného HTML náhledu. Osobní prezentace, kalkulačka PENB,
mapa krajů, tři formuláře, serverové doručování a administrace. Původní backend
v archivu nebyl; tento backend je nová implementace v Pythonu se SQLite.

## Rychlé spuštění

Vyžaduje Python 3.12 nebo novější. Aplikace nemá externí Python ani Node závislosti.
Z kořene repozitáře spusťte:

```sh
python3 app.py --port 8000
```

Server naslouchá pouze na loopbacku. Pro lokální kontrolu použijte HTTP požadavek
na port 8000. Lokální HTTP náhled dovoluje kalkulačku a správu, ale odmítá odesílání
poptávek. Veřejná adresa náhledu není tímto příkazem vytvořena.

Nastavení hesla majitele (zadává se skrytě v terminálu, nikdy do příkazu či Gitu):

```sh
python3 app.py --set-password
```

Potom otevřete cestu `/admin`. Žádné výchozí heslo neexistuje. Heslo má nejméně
14 znaků; použijte jedinečné dlouhé heslo. Příkaz lze zopakovat pro obnovu přístupu;
po změně restartujte server, čímž zrušíte staré relace. Administrace obsahuje editory
textů, popisků, kontaktních údajů, SEO, právních stránek a ceníku. Vyhledávejte podle
současného textu. Změny uložte a veřejnou stránku obnovte. Při souběžné editaci
server odmítne přepsat novější verzi; exportujte své změny před novým načtením.

## Produkční konfigurace

Přehled názvů obsahuje `.env.example`. Aplikace tento soubor automaticky nenačítá.
Nastavte proměnné v zabezpečených nastaveních hostingu, případně pomocí
`EnvironmentFile` správce služeb mimo veřejnou složku s přístupem pouze pro správce.
Nikdy neukládejte skutečný `.env`, heslo SMTP ani databázi do repozitáře.

- `APP_ENV=production` — zakáže lokální HTTP výjimku pro administraci.
- `APP_DATA_DIR` — neveřejná trvalá složka vlastněná uživatelem služby. Výchozí
  `.local` v projektu je vhodná pro vývoj. Musí přežít restart a nové nasazení.
- `PUBLIC_ORIGIN` — skutečná HTTPS adresa bez cesty. Aktivuje canonical a sitemap;
  dokud není nastavená, robots blokuje indexaci a sitemap vrací 404.
- `TRUSTED_PROXIES` — pouze přesné adresy skutečných připojujících se reverzních
  proxy, oddělené čárkou. Bez nastavení se hlavičce `X-Forwarded-Proto` nevěří.
  Nepovolujte libovolné adresy ani přímý veřejný přístup na port aplikace.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` — údaje
  smluvené poštovní služby. `SMTP_FROM` musí být službou povolený odesílatel.
- `SMTP_MODE=starttls` (obvykle 587) nebo `ssl` (obvykle 465). TLS kontroluje
  certifikát a hostname; žádný přechod na nešifrovanou poštu není povolen.

Hostitel musí povolit odchozí SMTP spojení. Cloudová HTTP proxy nenahrazuje SMTP
server. Nepoužívejte proxy placeholder místo skutečného SMTP hesla na hostingu.
Příjemcem poptávek je výslovně `penb.lahodny@seznam.cz`. Zákaznický e-mail je
Reply-To. Změna veřejného kontaktního e-mailu v administraci příjemce potají nemění;
změna cílové schránky patří do samostatné změny serverové konfigurace/kódu.

Před ostrým použitím ověřte skutečný příchod všech tří zpráv do schránky včetně
příloh, Reply-To a případných složek se spamem. Lokální testy používají simulované
SMTP a nic neposílají. Úspěch znamená potvrzené přijetí SMTP serverem, nikoli záruku
konečného doručení do složky Doručené. HTTPS a SMTP TLS nejsou koncové šifrování
zpráv ani šifrování uložené schránky.

## HTTPS a provoz služby

Použijte hosting pro Python proces s trvalým diskem a reverzní HTTPS proxy.
Příklady jsou v `deploy/`; nahraďte všechny `__PLACEHOLDER__` skutečnými hodnotami.
Certifikáty zajistěte obvyklým ověřeným postupem hostingu. Aplikace má běžet jako
neprivilegovaný uživatel za proxy, v jednom procesu (relace a rate limiting jsou
v paměti). SQLite, šablony a přílohy nesmějí být zveřejněné statickým serverem.
Nevystavujte Python `http.server` pro adresář projektu; spouštějte výhradně `app.py`.
Implementovaný HTTP handler nezpřístupňuje jiné soubory než schválené statické assety.
Pro vysokou návštěvnost je vhodné doplnit produkční procesní správu a limity na proxy;
nejde o víceuzlovou aplikaci.

Proxy má vynucovat HTTPS, přepsat `X-Forwarded-Proto` vlastním údajem, omezit tělo
na 17 MB a zavést limity počtu spojení. Bezpečný příklad předpokládá proxy na stejném
stroji, aplikaci na 127.0.0.1:8000. Neukládejte citlivé URL parametry či obsah požadavků
v access logu. Zhodnoťte i logy hostingu, které aplikace sama neřídí.

Readiness: veřejné stránky vracejí 200, `/api/status` přes HTTPS vrací `canSend: true`
až po nastavení všech SMTP údajů. Tento stav ověřuje konfiguraci, nikoli funkční
přihlášení k SMTP; přenos ověřte skutečnou testovací poptávkou. HTTP POST musí vracet
403 i při podvržené hlavičce z nedůvěryhodného peeru. Po restartu se znovu přihlaste.

## Podklady, soukromí a zálohy

Povoleno nejvýše 10 souborů, 10 MB na soubor a 15 MB dohromady, PDF/JPEG/PNG/ZIP.
Server kontroluje příponu a základní signaturu, není to antivirová kontrola ani důkaz
bezpečného obsahu. ZIP nerozbaluje. Přílohy zpracovává jen v paměti, předává SMTP a
nezapisuje do veřejných složek. Nepřidávejte do Gitu zákaznické soubory.

`.local/site.sqlite3` (nebo `APP_DATA_DIR/site.sqlite3`) obsahuje editovaný obsah,
hash hesla, souhrnné počty stránek a krátkodobé otisky/stavy odeslání. Zálohujte ji
mimo veřejný web se správnými přístupovými právy pomocí SQLite backup API:

```sh
python3 tools/backup.py /bezpecna/neverejna/cesta
```

V příkazu nahraďte poslední argument skutečnou neveřejnou cestou. Export administrace obsahuje jen obsah webu a ceník, nikoli
heslo, statistiky ani otisky poptávek. Automatické zálohy před editací jsou v
`APP_DATA_DIR/backups`. Majitel určí jejich uchování a samostatnou zálohu mimo server.
Pro obnovu celého stavu zastavte proces, obnovte databázi, nastavte vlastnictví a
znovu spusťte. Export JSON lze obnovit přímo editorem administrace a uložit.

Ve veřejné části nejsou reklamní cookies ani GA. Počítadlo eviduje serverová
zobrazení stránek, ne unikátní osoby. DNT/GPC se nezapočítávají. Veřejné API
statistik neexistuje. Relace správy je nezbytná cookie na hodinu, HttpOnly a přes
HTTPS Secure. Restart relace zruší. Při nejistém SMTP výsledku se stejná poptávka
znovu automaticky neposílá; zákazník má kontaktovat provozovatele přímo.

## Ověření

```sh
python3 -m unittest discover -s tests -v
```

Patnáct testů pokrývá ceny, kraje, validace, formuláře s přílohami, SMTP TLS,
Reply-To, chyby, deduplikaci, nedůvěryhodné proxy, soukromé soubory, správu,
CSRF, souběžné úpravy, export a soukromé statistiky.

Volitelné vývojové kontroly v reálném prohlížeči vyžadují Playwright a Chromium
(testovací prostředí zde používalo `/usr/bin/chromium`; nejde o runtime závislosti):

```sh
python3 tests/browser_check.py
python3 tests/delivery_browser.py
```

Používají dočasnou databázi a náhodné heslo, nezasahují do provozního obsahu.
Druhý test simuluje důvěryhodnou proxy a SMTP; neprokazuje produkční TLS ani doručení.

## Náhled bez hostingu

```sh
python3 tools/build_preview.py nahled.html
```

Vznikne jediný HTML soubor s vloženými obrázky, styly, kalkulačkou a mapou. Lze jej
poslat přílohou a otevřít v běžném prohlížeči. Obsahuje výchozí veřejný obsah, ne
privátní provozní data. Formuláře jsou záměrně neaktivní a administrace v něm není.
Pro změněný obsah použijte serverovou verzi. Samostatný HTML náhled nenahrazuje backend.

Stav předání a nevyřešené provozní kroky: `PREDANI.md`.
