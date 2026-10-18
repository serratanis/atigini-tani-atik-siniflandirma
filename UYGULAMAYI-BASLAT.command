#!/bin/zsh

set -e
cd "$(dirname "$0")"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "İlk kullanım için çalışma ortamı hazırlanıyor..."
  python3 -m venv .venv
fi

if ! .venv/bin/python -c "import streamlit, torch, transformers" >/dev/null 2>&1; then
  echo "Gerekli paketler kuruluyor. İlk kurulum birkaç dakika sürebilir..."
  .venv/bin/python -m pip install -r requirements.txt
fi

echo "Atığını Tanı açılıyor. Bu pencereyi uygulamayı kullanırken kapatmayın."
.venv/bin/python -m streamlit run app.py --server.fileWatcherType none

