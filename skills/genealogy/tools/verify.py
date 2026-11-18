#!/usr/bin/env python3
"""Verify a reading (e.g. after a helper): the record's area split into two halves of 1900 px each.
Usage: verify.py <image.jpg> x0,y0,x1,y1 <prefix> [v] [--contrast]  (v = split horizontally; --contrast = faded record)
Writes <prefix>_0.jpg and <prefix>_1.jpg (e.g. prefix work/verify/baptism_jan).
"""
import glob,os,shutil,sys,subprocess
if len(sys.argv) < 4 or sys.argv[1] in ("-h", "--help"):   # help instead of a crash
    sys.exit(__doc__.strip())
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows even without -X utf8
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
def magick():  # if ImageMagick is missing, stop right away with a clear message
    m=shutil.which("magick") or next(iter(sorted(glob.glob(r"C:\Program Files\ImageMagick*\magick.exe"))),None) or (os.name!="nt" and shutil.which("convert"))  # IM6 has no magick; on Windows convert.exe is another program
    if not m: sys.exit("ImageMagick is missing (command magick). Install it (macOS: brew install imagemagick, Windows: winget install ImageMagick.ImageMagick and restart Claude Code) and run the tool again.")
    return m
MAGICK=magick()
K='--contrast' in sys.argv; A=[a for a in sys.argv[1:] if a!='--contrast']
f,box,pre=A[0:3]; mode=A[3] if len(A)>3 else 'h'
W,H=map(int,subprocess.run([MAGICK,f+'[0]','-format','%w %h','info:'],capture_output=True,text=True).stdout.split())
x0,y0,x1,y1=map(float,box.split(','))
if not (0<=x0<x1<=1 and 0<=y0<y1<=1): sys.exit(f'Area {box} must be fractions 0..1 (x0 < x1, y0 < y1), not pixels.')
if mode=='v': ym=(y0+y1)/2; parts=[(x0,y0,x1,ym+0.02),(x0,ym-0.02,x1,y1)]
else: xm=(x0+x1)/2; parts=[(x0,y0,xm+0.02,y1),(xm-0.02,y0,x1,y1)]
os.makedirs(os.path.dirname(os.path.abspath(pre)),exist_ok=True)  # the output folder (work/verify/…) need not exist
for i,(a,b,c,d) in enumerate(parts):
    o=f'{pre}_{i}.jpg'; subprocess.run([MAGICK,f,'-crop','%dx%d+%d+%d'%((c-a)*W,(d-b)*H,a*W,b*H),'+repage',*(['-colorspace','Gray','-contrast-stretch','2%x35%'] if K else []),'-resize','1900x',o]); print(o)
