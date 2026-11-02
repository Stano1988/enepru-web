// One reveal per open browser document. Returning through navigation never replays it.
(() => {
 let revealed=false;
 function reveal(){
  const home=document.getElementById('uvod');
  if(!home)return;
  if(home.hidden){home.classList.remove('hero-reveal-first');return;}
  if(revealed)return;
  revealed=true;
  home.classList.add('hero-reveal-first');
  const documents=home.querySelector('.real-documents');
  const complete=()=>home.classList.remove('hero-reveal-first');
  documents?.addEventListener('animationend',complete,{once:true});
  // Also completes when the user leaves the page mid-animation or reduces motion.
  setTimeout(complete,2200);
 }
 document.addEventListener('site:routechange',reveal);
 reveal();
})();
