#!/bin/bash
# matricula_dl.sh URL OUT  -- downloads one image from img.data.matricula-online.eu (URL with csrf+ctrl taken from the browser)
if [ "$1" = -h ] || [ "$1" = --help ] || [ $# -lt 2 ]; then sed -n '2,2p' "$0" | sed 's/^# \{0,1\}//'; exit 2; fi   # help
PY=python3; $PY -c "" 2>/dev/null || PY=python; $PY -c "" 2>/dev/null || PY="py -3"
curl() { $PY -I "$(dirname "$0")/polite.py" curl "$@"; }   # brake against being blocked by the archive
tok=$(echo "$1" | sed -E 's/.*csrf=([^&]+).*/\1/')
# -f: on error (403 = expired link) save nothing; then check that it really is a JPEG, not an error page
if ! curl -sf -A "Mozilla/5.0" -e "https://data.matricula-online.eu/" -b "shared_csrftoken=$tok" "$1" -o "$2" \
   || [ "$(head -c 3 "$2" 2>/dev/null | od -An -tx1 | tr -d ' \n')" != "ffd8ff" ]; then
  rm -f "$2"
  echo "Matricula refused the image or returned no image (expired link?) – take fresh URLs from the browser: $2" >&2
  exit 1
fi
file "$2" | cut -d, -f1,8
