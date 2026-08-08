#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script with sudo: sudo ./scripts/setup_vcan.sh" >&2
  exit 1
fi

if ! modprobe vcan; then
  echo "Warning: modprobe could not load vcan; trying the interface directly." >&2
  echo "The driver may be built into the WSL2 kernel." >&2
fi

if ! ip link show vcan0 >/dev/null 2>&1; then
  if ! ip link add dev vcan0 type vcan; then
    echo "Unable to create vcan0. The running kernel may lack VCAN support." >&2
    echo "See the WSL2 kernel checks in README.md." >&2
    exit 1
  fi
fi

ip link set vcan0 up
ip -details link show vcan0
