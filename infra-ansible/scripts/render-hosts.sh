#!/usr/bin/env bash
set -euo pipefail
inventory_file="${1:-inventories/prod/hosts.yml}"
ansible-inventory -i "$inventory_file" --list
