import json,os,re,io,sys,urllib.request,concurrent.futures as cf
from PIL import Image
PH=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','site','photos.json')
res=json.load(open('res.json'))
CDN='https://dmxg5wxfqgb4u.cloudfront.net/'
def url(s):
    s=re.sub(r'^(https?://(www\.)?ufc\.com)?/images/',CDN,s); return s
def get(fid,v):
    src=v.get('head') or v.get('hero')
    if not src or re.search(r'silhouette|no-profile|default|shadow',src,re.I): return fid,None
    kind='h' if v.get('head') else 'b'
    p=f'raw/{fid}.{kind}.png'
    if not os.path.exists(p):
        for a in range(3):
            try:
                b=urllib.request.urlopen(url(src),timeout=30).read();open(p,'wb').write(b);break
            except Exception as e: err=e
        else: return fid,'ERR '+str(err)
    return fid,p
def crop(p):
    im=Image.open(p).convert('RGBA'); a=im.getchannel('A'); bb=a.getbbox()
    if not bb: return None
    x0,y0,x1,y1=bb
    if '.h.' in p:
        side=min(x1-x0,y1-y0); cx=(x0+x1)//2; box=(cx-side//2,y0,cx+side//2,y0+side)
    else:
        H=y1-y0; side=int(im.width*0.5)
        band=a.crop((x0,y0,x1,y0+int(H*0.1))); bb2=band.getbbox()
        cx=x0+(bb2[0]+bb2[2])//2 if bb2 else (x0+x1)//2
        top=y0; box=(cx-side//2,top,cx+side//2,top+side)
    c=im.crop(box).resize((128,128),Image.LANCZOS)
    bg=Image.new('RGBA',c.size,(0,0,0,0)); bg.alpha_composite(c); return bg
os.makedirs('raw',exist_ok=True);os.makedirs('out',exist_ok=True)
OLD=json.load(open(PH)) if os.path.exists(PH) else {}
items=[(k,v) for k,v in res.items() if v.get('st')==200 and k not in OLD]
with cf.ThreadPoolExecutor(8) as ex: got=list(ex.map(lambda kv:get(*kv),items))
photos=dict(OLD)
import base64
for fid,p in got:
    if not p or p.startswith('ERR'): continue
    c=crop(p)
    if c is None: continue
    buf=io.BytesIO(); c.save(buf,'WEBP',quality=70,method=6); photos[fid]='data:image/webp;base64,'+base64.b64encode(buf.getvalue()).decode()
    c.save(f'out/{fid}.png')
json.dump(photos,open(PH,'w'),separators=(',',':'))
print(len(items),'pages',len(photos),'photos',sum(1 for _,p in got if p and p.startswith('ERR')),'dl errors',os.path.getsize(PH)//1024,'KB')
