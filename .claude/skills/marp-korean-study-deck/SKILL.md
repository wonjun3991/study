---
name: marp-korean-study-deck
description: Build or update a Korean-language Marp study/presentation deck in this vault. Use when creating or editing slides.md, script.md, or any presentation artifact under study/<topic>/ or presentation/<topic>/ — covers directory layout, the verified dark-navy theme, speaker-note conventions, the PDF/PPTX/HTML build commands, mid-deck insertion re-sync protocol, and the consistency QA checklist.
---

# Korean Marp Study Deck

발표 자료를 만들거나 수정할 때의 전체 절차. 출력 언어는 **항상 한국어**.

## 1. 어디에 만드는가 (AGENTS.md 규칙)

발표 자료가 놓일 수 있는 위치는 **두 곳뿐**이다.

| 상황 | 디렉터리 (`<root>`) | prefix |
|---|---|---|
| 책/강의 챕터 발표 | `study/<topic>/chXX-<slug>/` | **`chXX-` 필수** |
| 독립 발표 | `presentation/<topic>/` | 없음 |

- 발표 자료를 `study/` 아래 챕터 폴더가 **아닌** 곳에 두지 않는다. 챕터에 속하지 않는 발표는 `presentation/<topic>/`.
- 예외(legacy): 기존 `study/cilium/<topic-slug>/` 덱들은 이 규칙 이전에 만들어진 것. **유지보수만** 하고, 신규 발표는 위 두 경로 중 하나에 만든다.

## 2. 산출물 6종 (전부 동기화 필수)

`P` = 챕터 작업이면 `chXX-`, `presentation/` 단일 발표면 빈 문자열.

| 파일 | 역할 |
|---|---|
| `slides.md` | Marp 원본 — **single source of truth**, 슬라이드마다 speaker note. prefix 없음 |
| `README.md` | 심화 노트, 산출물 맵, 슬라이드↔대본 매핑 표, 참고 링크. prefix 없음 |
| `<P>slides.html` | 브라우저 발표용 (←/→/Space, F 전체화면), self-contained |
| `<P>slides.pdf` | `--pdf-notes`로 발표자 노트를 PDF annotation에 포함 |
| `<P>slides.pptx` | speaker notes 자동 주입 |
| `<P>script.md` | 발표 대본. 슬라이드당 `## N.` 섹션 1개, 헤더에 `~N분 / M장` |

즉 챕터 폴더는 `slides.md` / `README.md` / `ch11-slides.html` / `ch11-slides.pdf` / `ch11-slides.pptx` / `ch11-script.md` 형태가 된다.

## 3. slides.md 작성 규칙

- Front-matter는 `templates/slides-frontmatter.md`를 그대로 복사해서 시작한다 (dark navy `#1a1a2e` + cyan `#00d4ff` + gold `#ffd700`, Apple SD Gothic Neo). 검증된 스타일이므로 임의로 색/폰트 크기를 바꾸지 않는다.
- 표지 슬라이드는 `<!-- _class: lead -->`.
- **speaker note는 각 슬라이드 끝의 HTML comment `<!-- ... -->`**. Marp의 `_notes` 디렉티브 대신 이것을 쓴다(호환성 최고). 이 텍스트가 곧 PPTX speaker notes.
- 다이어그램은 **inline SVG**. HTML/PDF/PPTX에 동일하게 임베드된다. 외부 이미지 파일은 `--allow-local-files` 의존이 생기므로 지양.
- 레이아웃 헬퍼: `.columns`, `.columns3`, `.box`(`.red`/`.gold`/`.cyan`), `.small`, `.tag`, `.cap`.

## 4. 빌드

덱 디렉터리(`<root>`)에서 실행. `PFX`에 챕터 prefix를 넣고, `presentation/` 단일 발표면 `PFX=` 로 비운다.

```bash
PFX=ch11-    # presentation/<topic>/ 이면: PFX=
marp slides.md --html              --allow-local-files -o "${PFX}slides.html"
marp slides.md --pdf --pdf-notes   --allow-local-files -o "${PFX}slides.pdf"
marp slides.md --pptx              --allow-local-files -o "${PFX}slides.pptx"
```

`slides.md`를 건드렸으면 **세 개 전부** 다시 빌드한다. 대본 파일명도 `${PFX}script.md`.

## 5. 슬라이드 추가/삭제 시 재동기화 프로토콜

중간에 슬라이드 하나만 끼워 넣어도 5가지가 깨진다. 전부 처리:

1. `<P>slides.html` / `<P>slides.pdf` / `<P>slides.pptx` 재빌드
2. `<P>script.md` 전 섹션 번호 재정렬
3. `<P>script.md` 헤더의 소요 시간 / 슬라이드 수 갱신
4. `README.md` 본문과 슬라이드↔대본 매핑 표 갱신
5. QA 체크리스트 재실행

## 6. QA

```bash
.claude/skills/marp-korean-study-deck/scripts/verify-deck.sh <deck-dir>
```

디렉터리 이름에서 `chXX-` prefix를 자동 인식해 산출물 존재 여부·mtime·PPTX 노트 수·대본 섹션 수·`↔` 사용을 검사한다. 슬라이드 수는 `slides.md`의 `---` 줄 수 - 1 (front-matter 보정).

수동 확인 항목:
- 대표 슬라이드 PNG 렌더링 → 텍스트 오버플로우, 한글 폰트 확인

## 7. 함정 (실제로 당한 것들)

- **plain Marp HTML export에는 speaker notes가 렌더되지 않는다.** PDF/PPTX에만 들어간다. 브라우저에서 노트를 보려면 presenter-mode 빌드를 따로 해야 한다.
- Chromium이 `↔`를 이모지 글리프로 렌더한다. `→` 또는 말로 풀어 쓴다.
- 편집 도구 섹션 헤더에 맨 `README.md`를 쓰면 **리포지토리 루트 README**로 해석된다. 항상 전체 경로.
- `--allow-local-files` 누락 → 로컬 이미지 누락.
- 스킬 `marp-study-slides-style` / `marp-diagram-generation`은 이 환경에 **존재하지 않는다**. 읽으려 하지 말 것.

## 8. 먹혔던 콘텐츠 구조

기준 메커니즘 → 개선된 메커니즘 → 그 개선의 숨은 비용 → 새 기술이 트레이드오프를 어떻게 바꾸는가 → 청중이 회사에서 그대로 써먹을 수 있는 도발적 마무리 질문.

`script.md`는 PPTX 노트의 **확장판**이다. 노트가 짧은 메모라면 script는 실제 입에서 나올 문장.
