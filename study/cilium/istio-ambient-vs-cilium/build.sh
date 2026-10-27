#!/usr/bin/env bash
# pages/*.md 를 조립해 slides.md 를 만들고 HTML/PPTX/PDF 를 빌드한다.
#
#   ./build.sh          조립 + 3종 빌드 + 검증
#   ./build.sh --md     조립만 (slides.md 만 갱신)
#   ./build.sh --check  조립 결과가 현재 slides.md 와 같은지만 확인 (파일 안 건드림)
#
# 편집 규칙
#   - 페이지 내용은 pages/NN-slug.md 만 고친다. slides.md 는 산출물이므로 직접 고치지 말 것.
#   - 페이지 파일 안에 맨 앞 열의 `---` 를 쓰지 말 것 (슬라이드 구분자와 충돌).
#   - 테마/CSS/다이어그램 킷 CSS 는 pages/_head.md, 렌더러 <script> 는 pages/_tail.md.
#   - 페이지를 추가·삭제하면 번호를 다시 매긴다: ./build.sh 가 정렬 순서대로 이어붙인다.

set -euo pipefail
cd "$(dirname "$0")"

HEAD=pages/_head.md
TAIL=pages/_tail.md
OUT=slides.md
TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

for f in "$HEAD" "$TAIL"; do
  [[ -f $f ]] || { echo "없음: $f" >&2; exit 1; }
done

# 정렬된 페이지 목록
shopt -s nullglob
PAGES=(pages/[0-9][0-9]-*.md)
shopt -u nullglob
(( ${#PAGES[@]} > 0 )) || { echo "pages/NN-*.md 가 없다" >&2; exit 1; }

# 맨 앞 열 `---` 사용 금지 검사 (슬라이드가 조용히 쪼개지는 사고 방지)
BAD=0
for p in "${PAGES[@]}"; do
  if grep -qn '^---[[:space:]]*$' "$p"; then
    echo "오류: $p 에 맨 앞 열 '---' 가 있다 (슬라이드 구분자와 충돌)" >&2
    BAD=1
  fi
done
(( BAD == 0 )) || exit 1

# 조립: _head + 페이지들(\n\n---\n\n 로 연결) + _tail
{
  sed -e '$a\' "$HEAD" | sed -e :a -e '/^\n*$/{$d;N;ba' -e '}'
  first=1
  for p in "${PAGES[@]}"; do
    if (( first )); then first=0; else printf '\n---\n\n'; fi
    # 앞뒤 빈 줄 제거
    awk 'BEGIN{s=0} {b[NR]=$0} END{
      st=1; while (st<=NR && b[st]=="") st++;
      en=NR; while (en>=st && b[en]=="") en--;
      for(i=st;i<=en;i++) print b[i]
    }' "$p"
  done
  printf '\n'
  awk 'BEGIN{s=0} {b[NR]=$0} END{
    st=1; while (st<=NR && b[st]=="") st++;
    en=NR; while (en>=st && b[en]=="") en--;
    for(i=st;i<=en;i++) print b[i]
  }' "$TAIL"
} > "$TMP"

if [[ ${1:-} == --check ]]; then
  if diff -q "$TMP" "$OUT" >/dev/null 2>&1; then
    echo "일치: 조립 결과 == $OUT (페이지 ${#PAGES[@]}장)"
  else
    echo "차이 있음 — $OUT 가 pages/ 와 동기화되지 않았다. './build.sh' 로 갱신하라." >&2
    diff "$OUT" "$TMP" | head -40 >&2
    exit 1
  fi
  exit 0
fi

cp "$TMP" "$OUT"
echo "조립 완료: $OUT (페이지 ${#PAGES[@]}장)"

[[ ${1:-} == --md ]] && exit 0

# --html 은 세 명령 모두에 필수 (raw HTML 허용 스위치; 없으면 다이어그램 킷이 텍스트로 이스케이프된다)
marp "$OUT" --html --allow-local-files -o slides.html
marp "$OUT" --html --pptx --allow-local-files -o slides.pptx
marp "$OUT" --html --pdf --pdf-notes --allow-local-files -o slides.pdf

# 검증
N=${#PAGES[@]}
HS=$(grep -o '<section' slides.html | wc -l | tr -d ' ')
PS=$(unzip -l slides.pptx | grep -c 'slides/slide[0-9]*\.xml$')
PN=$(unzip -l slides.pptx | grep -c 'notesSlides/notesSlide[0-9]*\.xml$')
echo "검증  페이지 $N / html $HS / pptx $PS + 노트 $PN"
[[ "$HS" == "$N" && "$PS" == "$N" && "$PN" == "$N" ]] \
  && echo "OK — 산출물 3종이 페이지 수와 일치" \
  || { echo "불일치 — 위 숫자를 확인하라" >&2; exit 1; }
