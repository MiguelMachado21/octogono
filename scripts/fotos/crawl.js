const {chromium}=require(require('child_process').execSync('npm root -g').toString().trim()+'/playwright');
const fs=require('fs');const list=JSON.parse(fs.readFileSync('list.json'));
const resF='res.json';const res=fs.existsSync(resF)?JSON.parse(fs.readFileSync(resF)):{};
const norm=s=>s.normalize('NFKD').replace(/[^\x00-\x7f]/g,'').toLowerCase().replace(/[^a-z]/g,'');
const W=+process.argv[2]||4;
(async()=>{const b=await chromium.launch(process.env.HTTPS_PROXY?{proxy:{server:process.env.HTTPS_PROXY}}:{});
const ctx=await b.newContext({ignoreHTTPSErrors:true});
await ctx.route('**/*',r=>{const q=r.request();return (q.isNavigationRequest()&&q.frame()===q.frame().page().mainFrame())?r.continue():r.abort();});
let i=0,done=0;const todo=list.filter(x=>!(res[x.id]&&res[x.id].st));
async function worker(){let p=await ctx.newPage();while(i<todo.length){const f=todo[i++];
 for(let a=0;a<4;a++){try{const r=await p.goto('https://www.ufc.com/athlete/'+f.slug,{timeout:40000,waitUntil:'domcontentloaded'});
  if(r.status()!==200){res[f.id]={st:r.status()};break;}
  const info=await p.evaluate(()=>{const h=document.querySelector('.hero-profile__name');const hero=document.querySelector('img.hero-profile__image');
    return {pname:h?h.textContent.trim():'',hero:hero?hero.getAttribute('src'):null,heads:[...document.querySelectorAll('img.image-style-event-results-athlete-headshot')].map(x=>[x.alt,x.getAttribute('src')])}});
  const pn=norm(info.pname||f.name);const hd=info.heads.find(h=>norm(h[0])===pn);
  res[f.id]={st:200,pname:info.pname,head:hd?hd[1]:null,hero:info.hero};break;
 }catch(e){res[f.id]={err:String(e).slice(0,100)};try{await p.close()}catch(_){};p=await ctx.newPage();await new Promise(z=>setTimeout(z,2000*(a+1)));}}
 if(++done%50===0){fs.writeFileSync(resF,JSON.stringify(res));console.log(new Date().toISOString(),done,'/',todo.length,Object.values(res).filter(v=>v.err).length,'err');}}}
await Promise.all(Array.from({length:W},worker));fs.writeFileSync(resF,JSON.stringify(res));console.log('DONE');await b.close();})();
