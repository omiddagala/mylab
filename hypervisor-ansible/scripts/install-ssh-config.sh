#!/usr/bin/env bash
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/files/ssh_config_mylab"
DST="${HOME}/.ssh/config.d/mylab.conf"
MAIN_CFG="${HOME}/.ssh/config"

mkdir -p "${HOME}/.ssh/config.d"
chmod 700 "${HOME}/.ssh"

cp "${SRC}" "${DST}"
chmod 600 "${DST}"

touch "${MAIN_CFG}"
chmod 600 "${MAIN_CFG}"

if ! grep -q 'Include ~/.ssh/config.d/\*.conf' "${MAIN_CFG}"; then
  {
    echo ""
    echo "Include ~/.ssh/config.d/*.conf"
  } >> "${MAIN_CFG}"
fi

echo "Installed mylab SSH config at ${DST}"