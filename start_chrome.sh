#!/bin/bash

# Script zum Start von Chrome mit Remote-Debugging und speziellem Profil

CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE_DIR="$HOME/.chrome-ignorecert-profile"
PORT=9222

echo "📂 Verwende Profilordner: $PROFILE_DIR"
echo "🚀 Starte Chrome mit Remote-Debugging auf Port $PORT ..."

"$CHROME_PATH" \
  --remote-debugging-port=$PORT \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  --start-maximized
