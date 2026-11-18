"""Helper for ahmp_search.sh: prints the volumes from an HTML result page of the AHMP catalogue (Prague City Archives)
(description | parish | XID, number of images).
Usage: ahmp_parse.py <page.html>"""
import re,sys,html
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):   # help instead of a crash
    sys.exit(__doc__.strip())
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
t=open(sys.argv[1],encoding='utf-8').read()
for blk in t.split('class="navigatorLine listArticle')[1:]:
    crumbs=re.findall(r'class="crumb">\s*<a[^>]*>([^<]*)</a>',blk)
    # the Czech title text "Zobrazit v plné kvalitě" (= show in full quality) is the portal's own label
    z=re.search(r'Zoomify.action\?xid=(\w+).*?%28(\d+)%29%29&amp;scanIndex=0" title="Zobrazit v plné kvalitě (\d+)',blk)
    lab=re.search(r'rowPg=\d+">(.*?)</a>',blk,re.S)
    l=re.sub(r'<[^>]+>','',lab.group(1)) if lab else '?'
    print(html.unescape(l).strip(),'|',(crumbs[-1][:40] if crumbs else ''),'|',z.groups() if z else '-')
