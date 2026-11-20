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
   o zahájení služby ve lhůtě pro odstoupení. Splatnost je podle korekce majitele 14 dnů od vystavení. Okamžik vystavení
   a fakturace předem/později zůstávají na potvrzení zakázky.
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


## Korekce 2. listopadu 2026

Domeček je posazený na energetické čárky. Dokumenty se při otevření úvodu plynule objeví, stupnice u domu má výraznější průběžné zvýraznění. Omezení pohybu v zařízení se respektuje. PENB má obrázek dokumentace, pasporty a kontakty tematickou ilustraci pracovního stolu s měřicími pomůckami. Nový obrázek survey-workspace.webp vznikl pomocí AI, není stažený z cizího webu a je označen jako ilustrační. Původ starších obrázků ze zachráněného archivu před jeho vytvořením není ověřený. Právní stránky mají sémantické nadpisy; FAQ a podmínky uvádějí splatnost faktury 14 dnů od vystavení. Návod pro majitele: JAK-SPUSTIT-A-SPRAVOVAT.md.


## Další vizuální korekce 2. listopadu 2026

Domeček je zvětšený přibližně k horní hraně jména a dál stojí na energetických čárkách. Opakovaný hnědý popisek nad sloganem byl odstraněn. Kalkulačka má výraznou výzvu a tlačítko s informací, že výpočet nevyžaduje kontakt. PENB, pasporty i kontakty mají kompaktní čtvercový obrázek vpravo, na úzkém mobilu pod textem zarovnaný vpravo. Podnadpisy doplnil světlý barevný podklad s měděnou linkou.

Dokumenty se objeví jednou za otevření dokumentu/prohlížečové stránky; návrat přes navigaci animaci neopakuje. Omezení pohybu zařízení zůstává respektované.

Nové obrázky PENB a zaměření jsou vytvořené pomocí AI. PENB ukazuje dvě strany s nevyplněnými údaji a grafickým razítkem se jménem a oprávněním 2321; obrázek není skutečně vydaný či elektronicky autorizovaný průkaz. Velký nápis přes stránky byl na přání odstraněn, pod obrázkem je uvedeno „Ukázka“. Razítko je podle uživatelského vzoru červené, bez žlutého zvýraznění. Pokus o ověření veřejných materiálů MPO z tohoto prostředí skončil blokací přístupu; přesnou aktuální úřední podobu dokumentu ani razítka tímto nenárokujeme. Obrázky jsou pro prezentaci, pro skutečné zakázky se používá skutečný autorizovaný výstup.

Fotografie zaměření byla nahrazena ostřejší verzí s hlubší ostrostí a nové obrázky se ukládají do WebP bezztrátově. Originální PNG razítka lze stáhnout samostatně.


## Změna úvodu 8. listopadu 2026

H1 a H2 úvodní stránky byly nahrazeny přesným zněním dodaným majitelem; upravena je také typografie pro mobil a SEO titulek a popis. Silná reklamní tvrzení „nejnižší možná cena“, „certifikovaný ... MPO“ a garance rychlosti pocházejí od majitele, nejsou tímto nasazením nezávisle doložena. V ceníku zůstávají individuální případy na dotaz, standardní a expresní termíny mají původní podmínky.

Z úvodu byl odstraněn i opakovaný podpis energetického specialisty pod výzvou ke kalkulačce; hlavička a kontakty zůstávají.

Na přání je jednorázové objevení průkazu a pasportu zpomalené na 4 sekundy po krátké půlsekundové prodlevě; následně dokumenty zůstávají statické.


## UX, texty a barevnost — 8. listopadu 2026

Na přání majitele zapracovány nasbírané připomínky. Zvolena tmavomodrá, téměř bílá a tlumená šalvějová zelená namísto měděných akcentů; barevnost stupnice A–G zůstává zachovaná. Zelené plochy jsou světlé, důležitá tlačítka mají tmavší zelenou kvůli čitelnosti. Kalkulačka má zvýrazněný rámeček, stín, tři orientační kroky a větší ovládací prvky; na úzkém mobilu jsou typy staveb pod sebou.

Nad kalkulačkou je popis ceny PENB se zaměřením při prodeji nebo pronájmu, s výslovnou výhradou krajů na dotaz. Úvod má karty standardního a expresního PENB, pasportu a ceny s ikonami. Termíny zachovávají své podmínky. Přidán blok pro realitní kanceláře a projektanty se zvýhodněnými cenami při pravidelné spolupráci a individuální dohodou; žádná provize ani automatická sleva se nenastavuje. Tlačítko vede na kontaktní formulář. Pasportová stránka vysvětluje, že samotný prodej bez plánů nezakládá automatickou povinnost pasportu.

Texty bloků se dají měnit v administraci. Existující vlastní barvy krajů a upravené texty zůstávají zachované; aktualizuje se pouze známá výchozí barevná paleta. Cena, čtyřsekundová animace i předchozí úpravy úvodu zůstávají. Propojení s Google, nákup domény, placená reklama ani produkční nasazení se tímto neprováděly.

## Úvod a plochy rodinných domů — 20. listopadu 2026

Úvod používá typografii, přímé odkazy na kalkulaci a pasport a přehled termínů. Pracovní fotka majitele zatím není součástí webu. Cenu PENB lze zjistit bez zadání kontaktu a z téže kalkulace pokračovat nezávaznou poptávkou.

Rodinný dům má v kalkulačce tři pásma celkové podlahové plochy: do 150 m², nad 150 do 250 m² a nad 250 m². Pásma používají první tři dosavadní sazby pro každý účel PENB. Čtvrtá sazba zůstává uložená kvůli dříve otevřeným kalkulacím. U bytových domů zůstávají dosavadní pásma podle m² a u jiných staveb individuální nacenění. Kód nového pásma se přenáší společně s čitelným popisem v e-mailu a v poptávce pro CRM.

## Fialový vzhled a animace úvodu — 20. listopadu 2026

Hlavní nadpis úvodu reaguje na prodej a pronájem nemovitosti. Označení „PENB a pasporty staveb“ má menší velikost pod ním. Barevnost kombinuje švestkovou, světlou levandulovou a mosaznou. Úvodní ilustrace využívá dům a dokumenty z původního HTML archivu. Krátký nástup domu, dokumentů a stupnice A–G se přehraje při prvním zobrazení ilustrace. Při nastaveném omezení pohybu je scéna statická. Kalkulace podle podlahové plochy a doručování formulářů nadále používají stávající logiku.

## Cena a průběh poptávky na úvodu — 20. listopadu 2026

Světlý základ a inkoustový text dávají prostor fialové výzvě ke kalkulaci. Úvod ukazuje podmíněný příklad pro první plošné pásmo rodinných domů při prodeji nebo pronájmu. Popisek plochy a částka vycházejí z aktuální konfigurace. Vedle kalkulace je přímý telefon. Před vyplněním poptávky web vysvětluje, co následuje po odeslání.

Stupnice A–G se vykresluje po jednotlivých pruzích s odstupem 0,4 sekundy. Dokumenty se objeví po půlsekundě a jejich nástup trvá čtyři sekundy. Při omezení pohybu je ilustrace od začátku statická.

Úprava vychází z poznatků o důvěryhodnosti webů služeb a o zobrazení ceny před zadáním údajů. [Nielsen Norman Group](https://www.nngroup.com/articles/trustworthy-design/) · [Baymard Institute](https://baymard.com/blog/reduce-cart-abandonment)
