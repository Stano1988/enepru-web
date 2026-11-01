(async()=>{
function quote(pricing, {building, purpose, size, survey, region, passport, express = false}) {
  const base = building === 'other' ? pricing.other?.[purpose] ?? null : size === 'custom' ? null : pricing[building]?.[purpose]?.[Number(size)] ?? null;
  const needsSurvey = purpose === 'sale' && survey;
  const travel = needsSurvey ? pricing.regions[region] : 0;
  const onRequest = base === null || (needsSurvey && travel == null);
  const expressFee = express ? pricing.expressFee : 0;
  return {base, travel: travel ?? null, expressFee, total: onRequest ? null : base + travel + expressFee, onRequest, passport: Boolean(passport), express: Boolean(express)};
}

const $ = id => document.getElementById(id);
const copy = window.SITE.ui;
const t = (key, fallback, values = {}) => {
  let value = copy[key] ?? fallback;
  for (const [name, replacement] of Object.entries(values)) value = value.replaceAll('{' + name + '}', replacement);
  return value;
};
window.enepruText = t;
const money = value => new Intl.NumberFormat('cs-CZ').format(value) + ' Kč';
const form = $('quote-form');
form.addEventListener('submit', event => event.preventDefault());
$('year').textContent = new Date().getFullYear();

$('passport-form').addEventListener('submit', event => event.preventDefault());
try {
  const pricing = window.SITE.pricing;
  for (const [name, price] of Object.entries(pricing.regions)) {
    const option = document.createElement('option');
    option.value = name;
    option.textContent = name + ' · ' + (price === null ? t('ui_region_request','na dotaz, od {price}',{price:money(pricing.travelOnRequestFrom)}) : '+' + money(price));
    $('region').append(option);
  }
  function regionPrice(name) {
    const price = pricing.regions[name];
    return price === null ? t('ui_region_request','na dotaz, od {price}',{price:money(pricing.travelOnRequestFrom)}) : '+' + money(price);
  }
  const regionControls = [...document.querySelectorAll('[data-region]')];
  regionControls.forEach(control => {
    const name = control.dataset.region;
    control.setAttribute('aria-label', name + ', ' + t('ui_travel','výjezd se zaměřením') + ' ' + regionPrice(name));
    control.dataset.band = pricing.regions[name] === null ? 'request' : String(pricing.regions[name]);
    if(control.tagName.toLowerCase()==='path' && window.SITE.mapBands?.[name])control.style.fill=window.SITE.mapBands[name];
    if (control.querySelector('title')) control.querySelector('title').textContent = name + ': ' + regionPrice(name);
    control.addEventListener('click', () => {
      $('region').value = name;
      update();
    });
    if (control.tagName.toLowerCase() === 'path') control.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        $('region').value = name;
        update();
      }
    });
  });
  let previousBuilding = null;
  function update() {
    const building = form.elements.building.value;
    if (building !== previousBuilding) {
      const labels = building === 'house' ? t('ui_house_sizes','1 podlaží|2 podlaží|3 podlaží|4 podlaží|5 a více — na dotaz').split('|') : t('ui_apartment_sizes','Do 500 m²|Nad 500 do 1 000 m²|Nad 1 000 do 2 000 m²|Nad 2 000 do 3 000 m²|Nad 3 000 m² — na dotaz').split('|');
      $('size').replaceChildren(...labels.map((label,i) => new Option(label,i === 4 ? 'custom' : String(i))));
      $('size-title').textContent = building === 'house' ? t('ui_size_house','Počet podlaží včetně sklepa') : t('ui_size_apartment','Podlahová plocha');
      $('size-note').textContent = building === 'house' ? t('ui_basement','Máte sklep? Připočítejte k nadzemním podlažím ještě jedno podlaží. Například přízemí + patro + sklep = 3 podlaží.') : t('ui_area_note','Vyberte podlahovou plochu celé budovy.');
      previousBuilding = building;
    }
    const sale = $('purpose').value === 'sale';
    $('size-label').hidden = building === 'other';
    $('size-note').hidden = building === 'other';
    $('survey-option').hidden = !sale;
    $('documentation-note').hidden = sale;
    if (!sale) $('survey').checked = false;
    $('region-panel').hidden = !$('survey').checked;
    regionControls.forEach(control => control.setAttribute('aria-pressed',String(control.dataset.region === $('region').value)));
    $('map-selection').textContent = $('region').value + ' · ' + t('ui_travel','výjezd se zaměřením') + ' ' + regionPrice($('region').value);
    const express = $('express').checked;
    $('express-fee').textContent = '+' + money(pricing.expressFee);
    const result = quote(pricing, {building,purpose:$('purpose').value,size:$('size').value,survey:$('survey').checked,region:$('region').value,passport:$('passport').checked,express});
    form.dataset.quoteSnapshot = JSON.stringify(result);
    $('price-label').textContent = result.onRequest ? t('ui_price_request','Cena vyžaduje potvrzení') : $('survey').checked ? t('ui_price_survey','PENB včetně zaměření') : t('ui_price_penb','Cena PENB');
    $('price').textContent = result.total === null ? t('ui_on_request','Na dotaz') : money(result.total);
    const parts = [t('ui_tax','Nejsme plátci DPH.')];
    if (building === 'other' && result.base === null) parts.unshift(t('ui_other','U jiné stavby cenu stanovíme podle typu, velikosti a dostupných podkladů.'));
    if ($('survey').checked && result.base !== null) parts.unshift(t('ui_quote_breakdown','PENB {base} + zaměření {travel}.',{base:money(result.base),travel:result.travel === null ? t('ui_price_from','od {price} (na dotaz)',{price:money(pricing.travelOnRequestFrom)}) : money(result.travel)}));
    if (express) parts.push(t('ui_express_breakdown','Expresní PENB do 5 pracovních dnů: +{price}.',{price:money(result.expressFee)}));
    if (result.passport) parts.push(t('ui_passport_price','Pasport: individuální nabídka, není zahrnut v součtu.'));
    $('price-detail').textContent = parts.join(' ');
  }
  form.addEventListener('change', update);
  $('passport-link').addEventListener('click', () => {$('passport').checked = true; update();});
  document.addEventListener('pricing-update',()=>{Object.assign(pricing,window.SITE.pricing);for(const opt of $('region').options)opt.textContent=opt.value+' · '+regionPrice(opt.value);regionControls.forEach(c=>c.dataset.band=pricing.regions[c.dataset.region]===null?'request':String(pricing.regions[c.dataset.region]));update();});
  update();
} catch (error) {
  $('price').textContent = t('ui_unavailable','Nedostupná');
  $('price-detail').textContent = t('ui_pricing_error','Ceník se nepodařilo načíst. Obnovte stránku a zkuste to znovu.');
}
document.querySelectorAll('[data-upload]').forEach(input => input.addEventListener('change', () => {
  const files = [...input.files];
  const invalid = files.length > 10 || files.reduce((sum,file) => sum + file.size,0) > 15 * 1024 * 1024 || files.some(file => file.size > 10 * 1024 * 1024 || !/\.(pdf|jpe?g|png|zip)$/i.test(file.name));
  const output = $(input.dataset.message);
  output.replaceChildren();
  if (invalid) {
    output.textContent = t('ui_upload_invalid','Výběr byl zrušen. Použijte PDF, JPG, PNG nebo ZIP do 10 MB na soubor, nejvýše 10 souborů a 15 MB celkem.');
    input.value = '';
    return;
  }
  if (!files.length) return;
  const list = document.createElement('ul');
  files.forEach(file => {
    const item = document.createElement('li');
    item.textContent = file.name + ' · ' + (file.size / 1024 / 1024).toLocaleString('cs-CZ',{maximumFractionDigits:1}) + ' MB';
    list.append(item);
  });
  const note = document.createElement('p');
  note.textContent = t('ui_upload_preview','Soubory jsou zatím pouze vybrané ve vašem prohlížeči.');
  const clear = document.createElement('button');
  clear.type = 'button'; clear.className = 'inline-button'; clear.textContent = t('ui_upload_clear','Zrušit výběr příloh');
  clear.addEventListener('click', () => {input.value = '';output.replaceChildren();});
  output.append(list,note,clear);
}));

})();