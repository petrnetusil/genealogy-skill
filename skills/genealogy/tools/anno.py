#!/usr/bin/env python3
"""ANNO (Austrian National Library) – full text of newspapers 1700–1950. REST API only, no browser.
Optionally ANNO_TITLE=<paper code>[,<another>] limits the search to these papers (code = letters in the docId:
ANNO_ptb… = ptb).
--losses = only the casualty lists 1914–1919: vll (Verlustliste), vlv (alphabetical index), nvv (Nachrichten über
Verwundete = news about the wounded).
Usage: anno.py "TEXT QUERY" [yearFrom] [yearTo] [maxpages] [--snip] [--losses]
API: GET https://anno.onb.ac.at/anno-suche/rest/search/complex?text=..&dateFrom=YYYY&dateTo=YYYY&from=1&facets=true
     GET https://anno.onb.ac.at/anno-suche/rest/search/snippet?documentId=<docId>&query=<textQuery>
"""
import html, os, re, sys, json, time, urllib.parse, urllib.request
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):   # help instead of a crash
    sys.exit(__doc__.strip())
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); import polite  # noqa: E402 – brake against being blocked by the archive (shared request limit, tools/polite.py)
for _s in (sys.stdout, sys.stderr):   # UTF-8 output on Windows too without -X utf8 (cp1250 cannot print e.g. "→")
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")
B='https://anno.onb.ac.at/anno-suche/rest/search/'
def get(path, params):
    u=B+path+'?'+urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'genealogy-research'}),timeout=90) as r:
        return json.load(r)
LOSSES=['vll','vlv','nvv']   # Verlustliste (casualty lists 1914–1919), their alphabetical index, Nachrichten über Verwundete


def search(q, yf, yt, maxp, snip, title=None):
    for p in range(maxp):
        prm={'text':q,'from':1+p*10,'facets':'false'}
        if yf: prm['dateFrom']=yf
        if yt: prm['dateTo']=yt
        if title: prm['selectedFilters']='title:'+title   # ANNO does not know a title= parameter (returns 0)
        d=get('complex',prm)
        if p==0: print('TOTAL',d.get('totalHits'),'|',d.get('textQuery'),'|',title or 'all papers')
        for doc in d.get('documents',[]):
            print('-',doc['docId'],'|',doc['displayTitle'],'| hits',doc.get('totalHitsInDoc'),'|',doc['openUrl'])
            if snip:
                try:
                    s=get('snippet',{'documentId':doc['docId'],'query':d.get('textQuery',q)})
                    for sp in s.get('snippetPages',[])[:3]:
                        for sn in sp.get('snippets',[])[:2]:
                            t=html.unescape(re.sub(r'<[^>]+>',' ',sn['text']))
                            print('   p.%s: %s'%(sp['pageLabel'],re.sub(r'\s+',' ',t)[:400]))
                except Exception as e: print('   snip err',e)
                time.sleep(0.5)
        if d.get('lastHit',0)>=d.get('totalHits',0): break
        time.sleep(1)


def main(argv, env):
    flags={'--snip','--losses'}
    args=[a for a in argv if a not in flags]
    if not args: sys.exit(__doc__)
    q=args[0]; yf=args[1] if len(args)>1 else ''; yt=args[2] if len(args)>2 else ''
    maxp=int(args[3]) if len(args)>3 else 1
    titles=LOSSES if '--losses' in argv else [t.strip() for t in env.get('ANNO_TITLE','').split(',') if t.strip()]
    # ANNO combines several filters in one query as "and" (0 results) – search each title separately
    for t in titles or [None]:
        search(q, yf, yt, maxp, '--snip' in argv, t)


if __name__ == '__main__':
    main(sys.argv[1:], os.environ)
