#!/usr/bin/env python3
"""Parish registers of AHMP (Prague City Archives) – downloads an image by stitching Zoomify tiles.
Usage: ahmp_scan.py XID SCAN OUT.jpg [down] [x0,y0,x1,y1]   (down=0 full resolution, 1 = half…; region in fractions)
The XID of a volume is printed by ahmp_search.sh. Permalink: https://katalog.ahmp.cz/pragapublica/permalink?xid=<XID>&scan=<N>
"""
import glob,shutil,sys,re,math,subprocess,urllib.request,os,tempfile
if len(sys.argv) < 4 or sys.argv[1] in ("-h", "--help"):   # help instead of a crash
    sys.exit(__doc__.strip())
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import polite  # noqa: E402 – brake against being blocked by the archive (shared request limit, tools/polite.py)
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
def magick():  # when ImageMagick is missing, exit right away (before downloading) with a clear message
    m=shutil.which("magick") or next(iter(sorted(glob.glob(r"C:\Program Files\ImageMagick*\magick.exe"))),None) or (os.name!="nt" and shutil.which("convert"))  # IM6 has no magick; on Windows convert.exe is a different program
    if not m: sys.exit("ImageMagick is missing (command magick). Install it (macOS: brew install imagemagick, Windows: winget install ImageMagick.ImageMagick and restart Claude Code) and run the tool again.")
    return m
MAGICK=magick()
xid,scan,out=sys.argv[1],int(sys.argv[2]),sys.argv[3]
down=int(sys.argv[4]) if len(sys.argv)>4 else 0
reg=[float(v) for v in sys.argv[5].split(',')] if len(sys.argv)>5 else [0,0,1,1]  # x0,y0,x1,y1 fractions
UA={'User-Agent':'Mozilla/5.0 genealogy-research'}
def get(u):
    return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60).read()
pl=get(f'https://katalog.ahmp.cz/pragapublica/permalink?xid={xid}&scan={scan}').decode('utf-8','replace')
path=re.search(r'zoomifyImgPath = "([^"]+)"',pl).group(1)
props=get(path+'/ImageProperties.xml').decode()
W=int(re.search(r'WIDTH="(\d+)"',props).group(1)); H=int(re.search(r'HEIGHT="(\d+)"',props).group(1)); T=int(re.search(r'TILESIZE="(\d+)"',props).group(1))
tiers=[(W,H)]
while tiers[-1][0]>T or tiers[-1][1]>T:
    w,h=tiers[-1]; tiers.append(((w+1)//2,(h+1)//2))
tiers.reverse()
ntiles=[(math.ceil(w/T),math.ceil(h/T)) for w,h in tiers]
z=len(tiers)-1-down
off=sum(a*b for a,b in ntiles[:z])
cols,rows=ntiles[z]
d=tempfile.mkdtemp()
files=[]
tw,th=tiers[z]
xs=range(int(reg[0]*tw)//T, min(cols,math.ceil(reg[2]*tw/T))); ys=range(int(reg[1]*th)//T, min(rows,math.ceil(reg[3]*th/T)))
for y in ys:
    for x in xs:
        idx=off+y*cols+x; g=idx//256
        f=f'{d}/{y:03d}_{x:03d}.jpg'
        open(f,'wb').write(get(f'{path}/TileGroup{g}/{z}-{x}-{y}.jpg')); files.append(f)
rowsf=[]
nc=len(xs)
for i,y in enumerate(ys):
    rf=f'{d}/row{y:03d}.png'; subprocess.run([MAGICK,*files[i*nc:(i+1)*nc],'+append',rf],check=True); rowsf.append(rf)
subprocess.run([MAGICK,*rowsf,'-append','-quality','90',out],check=True)
print(out,tiers[z],'src',path,'permalink',f'https://katalog.ahmp.cz/pragapublica/permalink?xid={xid}&scan={scan}')
