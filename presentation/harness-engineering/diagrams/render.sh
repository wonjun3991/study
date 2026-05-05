#!/usr/bin/env bash
# Mermaid 다이어그램 → PNG 렌더 스크립트
# 사용법: ./render.sh               # 모든 .mmd 파일 렌더
#         ./render.sh sisyphus-flow # 특정 파일만 (확장자 제외)

set -euo pipefail
cd "$(dirname "$0")"

if ! command -v mmdc >/dev/null 2>&1; then
  echo "❌ mermaid-cli(mmdc)가 없습니다. 설치: npm i -g @mermaid-js/mermaid-cli"
  exit 1
fi

render_one() {
  local base="$1"
  local src="${base}.mmd"
  local out="${base}.png"
  if [[ ! -f "$src" ]]; then
    echo "⚠️  $src 없음, 건너뜀"
    return
  fi
  echo "🖼  렌더링: $src → $out"
  mmdc \
    -i "$src" \
    -o "$out" \
    -C mermaid.css \
    -p puppeteer-config.json \
    -b transparent \
    -w 2400 \
    -H 1400 \
    --scale 2
}

if [[ $# -gt 0 ]]; then
  for arg in "$@"; do
    render_one "${arg%.mmd}"
  done
else
  for f in *.mmd; do
    render_one "${f%.mmd}"
  done
fi

echo "✅ 완료"
