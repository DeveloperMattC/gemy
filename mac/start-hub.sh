#!/usr/bin/env bash
# Start Gemy Control Center on macOS (monitor / control; no board push by default).
#   ./mac/start-hub.sh
#   ./mac/start-hub.sh --allow-push   # dangerous: overwrites board with this repo
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/mac/hub/hub_server.py" "$@"
