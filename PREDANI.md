# Stav předání — 1. listopadu 2026

Obnovený podklad: uživatelský archiv `Stanislav-Lahodny-nahled.rar`, jeden HTML
soubor s vloženými styly, skripty a dvěma WebP obrázky. Ceník v archivu odpovídal
konečnému zadání. Použity původní fotografie/ilustrace, teplý světlý vzhled,
obsah PENB/pasportů, mapové cesty a kalkulačka. Nově vznikl server, trvalá správa
obsahu a cen, právní stránky, skutečné adresy a zabezpečení formulářů.
Nejde o obnovu původního nedochovaného backendu či verze 9 bit po bitu.

## Ověřeno

- 15 serverových testů: 24 základních cen, všechny kraje, expres, sklep,
  na dotaz, neplatné kombinace, přílohy, Reply-To, poštovní chyby, CSRF,
  admin, konflikty editace, export, soukromé soubory a statistiky.
- Prohlížeč: 24 základních cen a 28 kombinací kraj/expres, mapa myší a klávesnicí,
  přímé adresy a historie; 8 stránek na 4 šířkách 360/390/768/1440 bez přetékání;
  zachování formuláře při otevření právních informací; editace textů/cen/GDPR.
- Všechny tři formuláře prošly z prohlížeče do skutečného lokálního aplikačního
  serveru a simulovaného SMTP. Ověřeny poznámky, PDF přílohy, Reply-To, expres
  a změna ceníku vyžadující další potvrzení zákazníka.
- Samostatný HTML náhled: navigace, kalkulačka a neaktivní odesílání.
  Ověřen jako jediný dokument bez externích souborů v lokálním prohlížečovém
  testu; cloudová politika prohlížeče blokuje přímé otevření file://.

Žádný test neposílal skutečnou poštu. Nejsou nakonfigurované SMTP údaje ani
produkční hosting/doména. Úspěch testů není ověřením produkčního doručování.
Veřejná hostovaná URL v tomto prostředí není k dispozici; předává se samostatný
HTML soubor, který lze poslat dál. Lokální server není veřejný náhled.

## Majitel před ostrým spuštěním

1. Zvolit Python hosting s trvalým diskem, HTTPS proxy a odchozím TLS SMTP.
2. Bezpečně nastavit proměnné podle `.env.example`; tajemství nepsat do chatu ani Gitu.
3. Nastavit soukromé heslo správce příkazem `python3 app.py --set-password`.
4. Doplnit skutečnou doménu a přesnou adresu důvěryhodné proxy. Ověřit HTTPS,
   nepřístupnost aplikačního portu zvenku a správné odmítnutí HTTP formulářů.
5. Otestovat všechny formuláře proti skutečné schránce včetně příloh a odpovědi.
6. Doplnit právní provozní údaje: hosting, pošta, retenční lhůty a mazání schránky
   a záloh. Zavést skutečný proces mazání. Registrační údaje pocházejí od majitele.
   Podmínky zkontrolovat pro konkrétní uzavírání smluv, zejména samostatnou žádost
   o zahájení služby ve lhůtě pro odstoupení. Splatnost a fakturace předem/později
   zůstávají na potvrzení zakázky, nejsou bez dohody vymyšlené.
7. Zajistit pravidelné neveřejné zálohy mimo tento server a vyzkoušet obnovu.

## Správa a limity

Obsah se mění ve formulářovém editoru, ne ruční editací JSONu. Vyhledávání pomůže
najít konkrétní nadpis nebo popisek. Export a import obsahu jsou dostupné majiteli.
Před změnou vzniká záloha; souběžné přepsání je blokováno verzí obsahu.

Veřejná kontaktní adresa v administraci je oddělená od explicitně určené doručovací
schránky. Statistiky jsou zobrazení ze serveru, ne unikátní osoby. Jeden proces
s relacemi a ochranou frekvence v paměti; není připravena víceuzlová infrastruktura.

Přílohy nejsou ukládány na web, neprobíhá antivirová kontrola. Přenosové TLS není
koncové šifrování e-mailu. Záruku doručení do schránky nelze odvodit z přijetí SMTP.
Při nejistém přenosu se stejný požadavek automaticky neopakuje.

GitHub je nezávislou zálohou pouze pro skutečně odeslané a následně ověřené commity.
Provozní databáze, hesla a klientské podklady v repozitáři nejsou a být nemají.
