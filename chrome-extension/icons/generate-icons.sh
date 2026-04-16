#!/usr/bin/env bash
# Generates icon-16.png, icon-48.png, icon-128.png from the SVG source.
# Requires: rsvg-convert (librsvg) or Inkscape or ImageMagick + librsvg.
#
# Install on Ubuntu/Debian: sudo apt-get install librsvg2-bin
# Install on macOS:         brew install librsvg
#
# Run from inside the icons/ directory:
#   bash generate-icons.sh

set -euo pipefail

for SIZE in 16 48 128; do
  rsvg-convert -w $SIZE -h $SIZE icon.svg -o "icon-${SIZE}.png"
  echo "Generated icon-${SIZE}.png"
done
