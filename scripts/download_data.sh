#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="$project_dir/data/raw/realwaste-main/RealWaste"

mkdir -p "$project_dir/data/raw"
python3 "$project_dir/scripts/download_data.py" --target "$target"
