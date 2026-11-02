# Jak bude fungovat přihlášení a správa webu

Web má dvě podoby:

- `nahled.html` je přenosný náhled do prohlížeče. Kalkulačka funguje, ale tento soubor neumí ukládat změny ani posílat formuláře. Nemá vlastní přihlášení.
- Kompletní projekt v ZIPu obsahuje Python server a databázi. Po jeho správném spuštění na hostingu funguje správa i trvalé ukládání.

## Co bude potřeba na hostingu

Pouhé nahrání HTML přes FTP nestačí. Zvolený hosting musí umět spouštět Python 3.12+, mít trvalé soukromé úložiště a HTTPS. Běžný hosting pouze pro PHP tuto aplikaci bez podpory Pythonu nespustí. Podrobný návod a příklady konfigurace jsou v README.md a deploy/.

Při prvním nasazení správce nahraje celý projekt, nastaví doménu, HTTPS, trvalou databázi a poštovní službu. Následně na serveru spustí `python3 app.py --set-password` a majitel zadá vlastní heslo skrytě v terminálu. Není vytvořené žádné veřejné ani výchozí heslo a přihlášení není navázané na účet ChatGPT.

## Jak se pak přihlásíš

1. Otevřeš svoji doménu a za ni přidáš `/admin`. Případně použiješ odkaz Administrace v patičce serverového webu.
2. Zadáš vlastní nastavené heslo. Aktuální verze má jednoho správce a přihlašuje se heslem; uživatelské jméno se nezadává.
3. Vybereš Texty webu, Ceník, Kontaktní údaje, Právní stránky nebo jinou záložku.
4. Vyhledáš konkrétní text, přepíšeš ho a klikneš na Uložit změny. U ceníku upravíš jednotlivé částky ve formulářových polích.
5. Veřejnou stránku obnovíš. Změny jsou uložené v databázi a zůstanou i po restartu serveru.

Lze upravovat texty všech veřejných stránek, popisky formulářů a kalkulačky, kontaktní údaje, SEO, právní texty, základní ceny PENB, kraje, barvy mapy i expresní příplatek. Před uložením vzniká záloha obsahu. Změna vzhledu, funkce nebo obrázků se v této verzi dělá úpravou projektu, nikoli editorem textů.

Právní texty zapisuj jako prostý text: nadpis na samostatný řádek, další řádek obsah odstavce a prázdný řádek mezi částmi. Nadpisy se na webu zobrazí zvýrazněné. Nepíše se HTML.

## Jak se změny zálohují

Ve správě je Exportovat včetně rozepsaných změn a obnova z exportu. Export pravidelně stáhni k sobě. Zároveň má hosting zálohovat databázi pomocí tools/backup.py mimo veřejnou složku. Zdrojový ZIP sám neobsahuje pozdější úpravy uložené v provozní databázi.

Přihlášení po hodině vyprší a restart aplikace relaci ukončí. Heslo lze obnovit stejným příkazem na serveru; po změně se server restartuje. Heslo a přístupy do schránky nepatří do chatu ani do Gitu.

## E-mail a faktury

Po nastavení SMTP se poptávky posílají na penb.lahodny@seznam.cz. Před ostrým spuštěním je nutné zkontrolovat skutečné doručení. Bez konfigurace se formuláře nebudou tvářit jako odeslané. Web automaticky nevystavuje faktury; v častých dotazech a podmínkách uvádí splatnost faktury 14 dnů od vystavení. Okamžik vystavení se potvrdí při zakázce.
