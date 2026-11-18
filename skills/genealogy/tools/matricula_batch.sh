#!/bin/bash
# matricula_batch.sh URLFILE PREFIX  (URLFILE: lines "<image> <image URL>" taken from the browser) -> downloads PREFIX_<pg>.jpg (+ a 1900 px _s.jpg reduction)
if [ "$1" = -h ] || [ "$1" = --help ] || [ $# -lt 2 ]; then sed -n '2,2p' "$0" | sed 's/^# \{0,1\}//'; exit 2; fi   # help
M=magick   # ImageMagick 6 has no magick, only convert (on Windows convert.exe is a different program, not there)
command -v magick >/dev/null || { [ "$OS" != Windows_NT ] && command -v convert >/dev/null && M=convert; }
tr -d '"' < "$1" | sed 's/\\n/\n/g' | grep -E '^[0-9]+ https' | while read p u; do
  out="${2}_$p.jpg"
  [ -s "$out" ] || bash "$(dirname "$0")/matricula_dl.sh" "$u" "$out" || { echo "Stopping the batch at image $p." >&2; exit 1; }
  "$M" "$out" -resize 1900x "${2}_${p}_s.jpg"; done
