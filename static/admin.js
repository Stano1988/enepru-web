(async()=>{
 const $=s=>document.querySelector(s);let tab='texts',dirty=false;
 const r=await fetch('/api/admin/content');if(!r.ok){location.href='/admin';return;}
 const state=await r.json(),data=state.content;
 const names={house:'Rodinný dům',apartment:'Bytový dům',other:'Jiná stavba',new:'Novostavba',sale:'Prodej / pronájem',renovation:'Rekonstrukce',regions:'Zaměření – kraje',expressFee:'Expresní příplatek',travelOnRequestFrom:'Minimum zaměření na dotaz',title:'Titulek',description:'Popis pro vyhledávače',uvod:'Úvod',penb:'PENB',pasporty:'Pasporty',dotazy:'Časté dotazy',kontakty:'Kontakty',gdpr:'Zásady zpracování osobních údajů',podminky:'Obchodní podmínky',cookies:'Informace o cookies'};
 function field(parent,key,value,path){
  const label=document.createElement('label'),caption=document.createElement('span');caption.textContent=path.map(k=>names[k]||k).join(' / ');label.append(caption);
  const numeric=tab==='pricing',input=document.createElement(numeric?'input':'textarea');
  if(numeric){input.type='number';input.min='0';input.max='10000000';input.step='1';input.placeholder='Na dotaz';}
  input.value=value??'';if(tab==='legal')input.rows=20;
  label.dataset.search=(caption.textContent+' '+value).toLocaleLowerCase('cs');
  input.addEventListener('input',()=>{if(numeric){if(!input.checkValidity())return;parent[key]=input.value===''?null:Number(input.value);}else parent[key]=input.value;dirty=true;});
  label.append(input);$('#editor').append(label);
 }
 function walk(v,path=[]){for(const [k,val]of Object.entries(v)){if(val!==null&&typeof val==='object')walk(val,[...path,k]);else field(v,k,val,[...path,k]);}}
 async function draw(){
  $('#editor').replaceChildren();$('#search').value='';document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.tab===tab)));
  if(tab==='stats'){
   const p=document.createElement('p');p.textContent='Souhrnná zobrazení stránek při jejich načtení ze serveru. Nejde o unikátní návštěvníky; přechody uvnitř již otevřené stránky se nezapočítávají. DNT a GPC respektujeme.';$('#editor').append(p);
   const response=await fetch('/api/admin/stats');if(!response.ok){$('#status').textContent='Relace vypršela. Přihlaste se znovu.';return;}
   const table=document.createElement('table');for(const row of [['Den (UTC)','Stránka','Zobrazení'],...(await response.json()).views]){const tr=document.createElement('tr');for(const cell of row){const td=document.createElement('td');td.textContent=cell;tr.append(td);}table.append(tr);}$('#editor').append(table);
  }else walk(data[tab]);
 }
 document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;draw();});
 $('#search').oninput=()=>{const q=$('#search').value.toLocaleLowerCase('cs');$('#editor').querySelectorAll('label').forEach(l=>l.hidden=!l.dataset.search.includes(q));};
 $('#save').onclick=async()=>{
  if([...document.querySelectorAll('input')].some(i=>!i.checkValidity())){$('#status').textContent='Opravte neplatnou cenu.';return;}
  $('#save').disabled=true;try{const response=await fetch('/api/admin/content',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf},body:JSON.stringify({revision:state.revision,content:data})});const result=await response.json();if(!response.ok)throw Error(result.error);state.revision=result.revision;dirty=false;$('#status').textContent='Uloženo. Verze '+state.revision+'. Změny uvidíte po obnovení webu.';}catch(e){$('#status').textContent=e.message;}finally{$('#save').disabled=false;}
 };
 $('#export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({revision:state.revision,content:data},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='obsah-zaloha.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
 $('#import').onchange=async e=>{try{const f=e.target.files[0];if(!f||f.size>2000000)throw Error('Příliš velký soubor.');const v=JSON.parse(await f.text());if(!v.content||Object.keys(data).sort().join()!==Object.keys(v.content).sort().join())throw Error('Neplatná záloha.');for(const k of Object.keys(data))data[k]=v.content[k];dirty=true;draw();$('#status').textContent='Záloha načtena do editoru. Zkontrolujte obsah a uložte změny.';}catch(err){$('#status').textContent=err.message;}};
 $('#logout').onclick=async()=>{if(dirty&&!confirm('Opustit neuložené změny?'))return;await fetch('/api/admin/logout',{method:'POST',headers:{'X-CSRF-Token':state.csrf}});dirty=false;location.href='/admin';};
 addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});draw();
})();
