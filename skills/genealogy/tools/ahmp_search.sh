#!/bin/bash
# Registers of AHMP (Prague City Archives): ahmp_search.sh "query" -> lists volumes of the register collection (description | parish | XID, number of images).
# Uses the old catalogue katalog.ahmp.cz/pragapublica (the new digi.ahmp.cz has bot protection – do not use it).
if [ "$1" = -h ] || [ "$1" = --help ] || [ $# -lt 1 ]; then sed -n '2,3p' "$0" | sed 's/^# \{0,1\}//'; exit 2; fi   # help
D=$(mktemp -d); B=https://katalog.ahmp.cz; C=$D/cj
# Python 3: on Windows "python3" is often just a broken Microsoft Store alias → try python, py -3
PY=python3; $PY -c "" 2>/dev/null || PY=python; $PY -c "" 2>/dev/null || PY="py -3"
curl() { $PY -I "$(dirname "$0")/polite.py" curl "$@"; }   # brake against being blocked by the archive
q=$($PY -I -c "import urllib.parse,sys;print(urllib.parse.quote_plus(sys.argv[1]))" "$1")
curl -s -b $C -c $C -L "$B/pragapublica/searchlink?xid=7EF18906B65E11DF820F00166F1163D4&fcDb=&onlyDigi=&modeView=LIST&searchAsPhrase=&patternTxt=$q" -o $D/a.html
f=$(grep -A6 'name="pageRows"' $D/a.html | grep -oE 'name="(_sourcePage|__fp)" value="[^"]*"' | head -2)
sp=$(echo "$f" | grep _sourcePage | cut -d'"' -f4); fp=$(echo "$f" | grep __fp | cut -d'"' -f4)
curl -s -b $C -c $C -L "$B/pragapublica/ViewControlImpl.action" --data-urlencode "pageRows=51" --data-urlencode "myPageRows=" --data-urlencode "_sourcePage=$sp" --data-urlencode "__fp=$fp" -o $D/p0.html
$PY -I -X utf8 "$(dirname "$0")/ahmp_parse.py" $D/p0.html; cur=$D/p0.html
for k in $(seq 1 30); do u=$(grep -oE '/pragapublica/PaginatorResult.action[^"]*row=[0-9]+' $cur | sed 's/&amp;/\&/g' | grep -E "row=$((k*51))$" | head -1); [ -z "$u" ] && break; curl -s -b $C -c $C "$B$u" -o $D/p$k.html; $PY -I -X utf8 "$(dirname "$0")/ahmp_parse.py" $D/p$k.html; cur=$D/p$k.html; done
