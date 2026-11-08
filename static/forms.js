(async()=>{
 const forms=[...document.querySelectorAll('form')];
 let canSend=false;
 try{canSend=(await (await fetch('/api/status')).json()).canSend===true;}catch{}
 document.querySelector('.preview').textContent=canSend?'PENB a pasporty staveb · Ing. Stanislav Lahodný':'Pracovní náhled · formuláře neodesílají · kontaktujte nás telefonicky nebo e-mailem';
 for(const form of forms){
  const button=form.querySelector('[data-send]'),status=form.querySelector('.send-status');
  const trap=document.createElement('input');trap.name='_website';trap.tabIndex=-1;trap.autocomplete='off';trap.className='form-trap';trap.setAttribute('aria-label','Toto pole nevyplňujte');form.append(trap);
  button.disabled=!canSend;
  form.querySelector('.prototype-note').textContent=canSend?'Nezávazná poptávka. Odesláním nevzniká objednávka ani povinnost platby.':'Odesílání není aktivní. Vyplněná data ani přílohy se v náhledu neposílají.';
  let requestId,confirmed=false;
  form.addEventListener('input',()=>{if(form.dataset.sending==='true'||confirmed)return;requestId=undefined;});
  form.addEventListener('submit',async e=>{
   e.preventDefault();if(!canSend||confirmed||form.dataset.sending==='true'||!form.reportValidity())return;
   const fields=Object.fromEntries(new FormData(form));
   const kind=form.id==='quote-form'?'penb':form.id==='passport-form'?'passport':'contact';
   const payload={...fields,kind,requestId:requestId||=crypto.randomUUID()};
   if(kind==='penb')Object.assign(payload,{building:form.elements.building.value,purpose:document.getElementById('purpose').value,size:document.getElementById('size').value,survey:document.getElementById('survey').checked,region:document.getElementById('region').value,passport:document.getElementById('passport').checked,express:document.getElementById('express').checked,quoted:JSON.parse(form.dataset.quoteSnapshot),pricing:SITE.pricing});
   const body=new FormData();body.append('payload',JSON.stringify(payload));
   for(const input of form.querySelectorAll('[data-upload]'))for(const f of input.files)body.append('attachments',f,f.name);
   form.dataset.sending='true';button.disabled=true;status.textContent=SITE.ui.ui_send_working;
   // Freeze fields while a request is in flight, keeping the displayed quote stable.
   const controls=[...form.querySelectorAll('input,textarea,select')];controls.forEach(c=>c.disabled=true);
   try{
    const response=await fetch('/api/enquiries',{method:'POST',body});const result=await response.json();
    if(response.status===409&&result.pricing){
     // Never silently accept a changed price. Reload only the price configuration,
     // retaining the draft and requiring a second explicit submission.
     SITE.pricing=result.pricing;document.dispatchEvent(new CustomEvent('pricing-update'));requestId=undefined;
    }
    if(!response.ok||!result.ok)throw Error(result.error||SITE.ui.ui_send_error);
    confirmed=true;status.textContent=result.queued?'Poptávku jsme bezpečně uložili. Po obnovení spojení ji doručíme ke zpracování.':SITE.ui.ui_send_success;button.textContent=result.queued?'Poptávka přijata':SITE.ui.ui_send_sent;
   }catch(err){status.textContent=err.message||SITE.ui.ui_send_error;}
   finally{controls.forEach(c=>c.disabled=false);form.dataset.sending='false';button.disabled=confirmed;}
  });
 }
})();
