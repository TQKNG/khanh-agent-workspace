#!/usr/bin/env bash
# usage: export_png.sh <in.drawio> <out.png>   (needs the draw.io desktop CLI)
set -euo pipefail
in="$1"; out="$2"
bin=""
for c in drawio draw.io "/Applications/draw.io.app/Contents/MacOS/draw.io" "/opt/drawio/drawio"; do
  if command -v "$c" >/dev/null 2>&1 || [ -x "$c" ]; then bin="$c"; break; fi
done
if [ -z "$bin" ]; then echo "draw.io CLI not found. Install draw.io desktop, or export PNG manually (File > Export as > PNG, 2x, crop)." >&2; exit 2; fi
mkdir -p "$(dirname "$out")"
xvfb=""; command -v xvfb-run >/dev/null 2>&1 && [ -z "${DISPLAY:-}" ] && xvfb="xvfb-run -a"
$xvfb "$bin" -x -f png -s 2 -b 20 --crop -o "$out" "$in"
echo "$out"
