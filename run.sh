#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
P4_FILE="$SCRIPT_DIR/basic_ml.p4"
JSON_FILE="$BUILD_DIR/basic_ml.json"
P4C_BIN="${P4C_BIN:-$(command -v p4c)}"
SWITCH_BIN="${SWITCH_BIN:-$(command -v simple_switch)}"
if [[ -z "${PYTHON_BIN:-}" ]]; then
  if [[ -x /usr/bin/python3 ]]; then
    PYTHON_BIN="/usr/bin/python3"
  else
    PYTHON_BIN="$(command -v python3)"
  fi
fi
BMV2_LIB_DIRS="/usr/local/lib:/home/mehtabsingh/behavioral-model/targets/simple_switch/.libs"

if [[ -z "${P4C_BIN}" || -z "${SWITCH_BIN}" || -z "${PYTHON_BIN}" ]]; then
  echo "Missing one of: p4c, simple_switch, python3" >&2
  exit 1
fi

MODE="${1:-cli}"
TOPO_ARGS=()
if [[ "${MODE}" == "test" ]]; then
  TOPO_ARGS+=(--test --no-cli)
elif [[ "${MODE}" == "nocli" ]]; then
  TOPO_ARGS+=(--no-cli)
fi

mkdir -p "$BUILD_DIR"
if [[ -n "${LD_LIBRARY_PATH:-}" ]]; then
  export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:${BMV2_LIB_DIRS}"
else
  export LD_LIBRARY_PATH="${BMV2_LIB_DIRS}"
fi

echo "[1/2] Compiling $P4_FILE"
"$P4C_BIN" --target bmv2 --arch v1model "$P4_FILE" -o "$BUILD_DIR"

echo "[2/2] Launching Mininet + BMv2"
if [[ "${EUID}" -ne 0 ]]; then
  echo "Re-running with sudo for Mininet privileges..."
  exec sudo /usr/bin/env \
    "LD_LIBRARY_PATH=$LD_LIBRARY_PATH" \
    "PATH=$PATH" \
    "$PYTHON_BIN" "$SCRIPT_DIR/topology.py" \
    --behavioral-exe "$SWITCH_BIN" \
    --json "$JSON_FILE" \
    --thrift-port 9090 \
    "${TOPO_ARGS[@]}"
fi

"$PYTHON_BIN" "$SCRIPT_DIR/topology.py" \
  --behavioral-exe "$SWITCH_BIN" \
  --json "$JSON_FILE" \
  --thrift-port 9090 \
  "${TOPO_ARGS[@]}"
