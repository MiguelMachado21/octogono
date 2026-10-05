// Abre uma página no Chromium headless (passa o desafio de JS do ufcstats.com) e imprime o HTML.
const {chromium}=require(require('child_process').execSync('npm root -g').toString().trim()+'/playwright');
(async()=>{const u=process.argv[2], px=u.startsWith("https:")?process.env.HTTPS_PROXY:process.env.HTTP_PROXY;
const b=await chromium.launch(px?{proxy:{server:px}}:{});
const p=await b.newPage({ignoreHTTPSErrors:true});
await p.goto(process.argv[2],{timeout:60000});
for(let i=0;i<30&&/Checking your browser/.test(await p.content());i++)await p.waitForTimeout(1000);
process.stdout.write(await p.content());await b.close();})().catch(e=>{console.error(e);process.exit(1)});
