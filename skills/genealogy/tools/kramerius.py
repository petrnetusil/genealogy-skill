#!/usr/bin/env python3
"""Kramerius full-text search (API v5) – digital libraries running Kramerius, by default the Czech National Library.
Usage: kramerius.py 'SOLR_QUERY' [rows] [--server https://<library>]
e.g. kramerius.py 'text_ocr:"Jan Novák" AND datum_begin:[1860 TO 1920]'
--server: another library with a Kramerius v5 interface (e.g. https://kramerius.army.cz); default https://kramerius5.nkp.cz.
The --server option follows https://github.com/hnizdiljan/rodokmen-skill/blob/d172316bc190d0f44894fa67115505729d587c6a/skills/rodokmen/tools/kramerius.py (MIT).
Access column: public = free; private+DNNT = readable after logging in at ndk.cz (reference/countries/czech-republic.md → DNNT);
private = only inside the library. The datum_begin filter drops some periodical issues – with few hits search without it too.
Taken over from zbysekvoda/rodokmen-plus@096315a (Zbyšek Voda, MIT), adapted (replaces an older version: adds
--server, the DNNT column and the page number; -h prints the help with exit code 0)."""
import os,re,sys,json,urllib.request,urllib.parse
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I does not add the script folder by itself
import polite; polite.install()   # shared rate limit for archive websites (polite.py)
a=sys.argv[1:]; server='https://kramerius5.nkp.cz'
if '--server' in a:
    i=a.index('--server')
    if i+1>=len(a): sys.exit('--server needs the library address (https://…).')
    server=a[i+1].rstrip('/'); del a[i:i+2]
s=urllib.parse.urlsplit(server)
if (s.scheme!='https' or s.username or s.password or s.port not in (None,443) or s.query or s.fragment or s.path
        or not re.fullmatch(r'[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+',s.hostname or '') or re.fullmatch(r'[0-9.]+',s.hostname or '')):
    sys.exit('--server must be https:// and the domain name of the library (e.g. https://kramerius.army.cz).')
if not a or a[0] in ('-h','--help'):
    print(__doc__); sys.exit(0 if a else 2)
q=a[0]; rows=a[1] if len(a)>1 else '30'
p={'q':q+' AND fedora.model:page','fl':'PID,root_title,root_pid,datum_str,details,dostupnost,dnnt,dnnt-labels','rows':rows,'wt':'json','hl':'true','hl.fl':'text_ocr','hl.fragsize':'250'}
u=server+'/search/api/v5.0/search?'+urllib.parse.urlencode(p)
try:
    d=json.load(urllib.request.urlopen(u,timeout=90))
except ValueError:
    sys.exit(f'{server} did not return JSON – it probably has no Kramerius v5 interface (search/api/v5.0), only the newer v7.')
except OSError as e:
    sys.exit(f'{server} did not answer ({type(e).__name__}: {str(getattr(e, "reason", e))[:150]}).')
print('found',d['response']['numFound'])
hl=d.get('highlighting',{})
for x in d['response']['docs']:
    h=' | '.join(hl.get(x['PID'],{}).get('text_ocr',[]))[:400].replace('\n',' ')
    access=x.get('dostupnost') or '?'   # Kramerius field names are Czech (dostupnost = availability)
    if access=='private' and (x.get('dnnt') or 'dnnto' in (x.get('dnnt-labels') or [])): access='private+DNNT'
    det=str(x['details'][0]).split()[0] if x.get('details') else ''
    print('-',x.get('datum_str'),'|',str(x.get('root_title'))[:60],'| p.',det,'|',x['PID'],'|',access)
    if h: print('   ',h)
