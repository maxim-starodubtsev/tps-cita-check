#!/bin/bash
# Generate com.tps.cita-check.plist from template and install into ~/Library/LaunchAgents.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$SCRIPT_DIR/com.tps.cita-check.plist.template"
PLIST="$SCRIPT_DIR/com.tps.cita-check.plist"
DEST="$HOME/Library/LaunchAgents/com.tps.cita-check.plist"

if [ ! -f "$TEMPLATE" ]; then
    echo "Error: template not found at $TEMPLATE" >&2
    exit 1
fi

# Substitute placeholder with actual project directory
sed "s|__PROJECT_DIR__|$PROJECT_DIR|g" "$TEMPLATE" > "$PLIST"
echo "Generated: $PLIST"

# Unload old version if loaded
launchctl bootout "gui/$(id -u)/com.tps.cita-check" 2>/dev/null || true

# Copy and load
cp "$PLIST" "$DEST"
launchctl load "$DEST"
echo "Installed and loaded: $DEST"
