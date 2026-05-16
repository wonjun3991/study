# AGENTS.md — Routing Guide

이 vault는 **개인 학습 노트**와 **발표 자료**를 함께 보관한다. 작업 종류에 따라 알맞은 루트로 라우팅하라.

## Top-Level Layout

```
.
├── study/              # 학습 노트 (책/강의/기술 공부)
│   └── kubernetes-in-action/
│       ├── chXX-*/                # 챕터별 학습 노트 (README.md + manifests/)
│       ├── examples/              # 책 공식 예제 (upstream git submodule-like)
│       └── _alt-manifests/        # 간소화된 대안 manifest (참고용)
├── presentation/       # 발표 자료 (슬라이드, 다이어그램, PDF)
│   └── harness-engineering/
├── inbox/              # Obsidian 새 노트 기본 위치
├── daily/              # Daily notes
├── templates/          # 노트 템플릿
├── attachments/        # 이미지, 파일 첨부
└── .obsidian/          # Obsidian 설정
```

## Routing Rules

작업 의도를 먼저 분류하고, 표에서 해당 행의 루트로 직행하라.

| 작업 의도                                  | Root                             | 비고                                           |
|--------------------------------------------|----------------------------------|------------------------------------------------|
| 책/강의 학습 노트 작성·수정                | `study/<topic>/`                 | 신규 주제는 `study/` 아래 새 폴더 생성        |
| Kubernetes in Action 챕터 노트             | `study/kubernetes-in-action/chXX-*/` | 각 챕터 폴더 안에 `README.md`, `manifests/` |
| K8s 매니페스트 실습 파일                   | `study/kubernetes-in-action/chXX-*/manifests/` | 챕터 노트와 같은 폴더에 둔다           |
| 책 공식 예제 참조                          | `study/kubernetes-in-action/examples/` | 수정하지 않음 (업스트림 미러)              |
| 발표 슬라이드 (Marp / PDF / PPTX / 다이어그램)    | `presentation/<topic>/`          | `slides.md` + `slides.pdf` + `slides.pptx` + `script.md` (자세한 빌드 규칙은 아래 **Presentation Build Rules** 참조) |
| 일일 회고·메모                             | `daily/`                         | Obsidian Daily notes 플러그인이 관리           |
| 분류 미정 임시 노트                        | `inbox/`                         | 정리되면 `study/` 또는 `presentation/`으로 이동 |
| 노트 템플릿 추가/수정                      | `templates/`                     | Obsidian 템플릿 플러그인 참조                  |
| 첨부 이미지·바이너리                       | `attachments/`                   | 노트에서 상대 경로로 참조                      |

## Conventions

- **챕터 폴더 명명**: `chXX-kebab-case-title/` (예: `ch06-volumes`, `ch11-kubernetes-internals`).
- **챕터 폴더 구성**:
  - `README.md` — 학습 노트 본문 (Obsidian markdown).
  - `manifests/` — 직접 작성한 실습 매니페스트.
  - `slides.md`, `chXX-slides.pdf` — (옵션) 챕터 발표 자료.
- **발표 자료 폴더 구성**:
  - `slides.md` (Marp), `diagrams/`, `reference/`, 그리고 빌드 산출물(아래 참조).
  - 다이어그램은 `marp-diagram-generation` skill 가이드라인을 따른다 (16:9, 큰 폰트).
  - 슬라이드 테마/색상/폰트는 `marp-study-slides-style` skill을 적용한다 (dark navy + cyan/gold + Apple SD Gothic Neo). 신규 `slides.md`는 해당 skill의 front-matter 템플릿으로 시작.
- **새 학습 주제**: `study/<new-topic>/` 폴더를 만들고, 챕터/섹션 단위로 하위 폴더를 둔다.
- **Inbox 정리**: `inbox/`에 쌓인 노트는 주기적으로 분류해 `study/` 또는 `presentation/`로 옮긴다.

## Presentation Build Rules (MANDATORY)

발표 자료(`presentation/<topic>/` 또는 `study/<topic>/chXX-*/`에서 슬라이드 작업)를 만들거나 수정할 때는 항상 다음 3종 산출물을 함께 생성·갱신한다.

### 산출물 명세

작업 폴더: `<root>/` (예: `study/kubernetes-in-action/ch11-kubernetes-internals/` 또는 `presentation/harness-engineering/`)

| 파일 | 용도 | 비고 |
|---|---|---|
| `slides.md`           | Marp 소스. front-matter에 `marp: true`, `theme`, `paginate: true` 등 명시 | 단일 진실의 원천(Single Source of Truth) |
| `chXX-slides.pdf` 또는 `slides.pdf` | PDF 산출물 | 챕터 작업이면 `chXX-` prefix 사용 |
| `chXX-slides.pptx` 또는 `slides.pptx` | PowerPoint 산출물. 발표자 노트 자동 포함 | `--pptx` (또는 필요 시 `--pptx-editable`) |
| `chXX-script.md` 또는 `script.md` | 사람이 읽기 쉬운 발표 대본 | 슬라이드 번호별 섹션, 시간 배분, 강조 포인트 |

`<root>/`가 챕터 폴더면 `chXX-` prefix를, `presentation/<topic>/` 단일 발표면 prefix 없이 `slides.{pdf,pptx}` + `script.md`를 쓴다.

### 발표자 노트(speaker notes) 작성 규칙

`slides.md` 안에서 각 슬라이드 끝에 HTML comment로 노트를 둔다. Marp가 PPTX 변환 시 PowerPoint speaker notes 영역에 자동으로 주입한다.

```markdown
---
# 슬라이드 제목

- 핵심 포인트 A
- 핵심 포인트 B

<!--
이 슬라이드에서 말할 대본:
- A는 왜 중요한지 30초 정도로 설명
- B 예시 들기 (실제 사례 1개)
- 다음 슬라이드 연결 한 줄
-->
```

`<!-- ... -->` 안의 텍스트가 곧 PPTX speaker notes 가 된다. Marp의 `_notes` 디렉티브 대신 **단순 HTML comment**를 사용한다(가장 호환성 높음).

### 별도 `script.md` 작성 규칙

PPTX 노트와 별개로, 사람이 발표 연습용으로 보기 좋은 마크다운 대본을 함께 만든다. 구성:

```markdown
# <발표 제목> 대본

총 발표 시간: NN분 / 슬라이드 NN장

## 슬라이드 1: <제목>
**예상 시간**: 30초

(말할 내용 ─ 실제로 입에서 나올 문장 위주, bullet point 아님)

**강조**: 핵심 한 줄
**다음 슬라이드 연결**: "이제 ~를 보겠습니다"

---

## 슬라이드 2: <제목>
...
```

`script.md`는 PPTX speaker notes의 **확장판**이라고 간주한다. 노트가 짧은 메모라면 script는 실제 말투 문장.

### 빌드 명령 (Marp CLI)

`<root>/` 디렉토리에서 실행:

```bash
# PDF (presenter notes를 PDF annotation으로 포함)
marp slides.md --pdf --pdf-notes --allow-local-files \
  -o chXX-slides.pdf

# PPTX (speaker notes 자동 포함)
marp slides.md --pptx --allow-local-files \
  -o chXX-slides.pptx

# (선택) editable PPTX — PowerPoint에서 텍스트 직접 수정 가능
marp slides.md --pptx-editable --allow-local-files \
  -o chXX-slides.pptx
```

`presentation/<topic>/` 단일 발표면 출력 파일명만 `slides.pdf` / `slides.pptx`로 바꾼다.

옵션 의미:
- `--allow-local-files`: `diagrams/`, `attachments/`의 로컬 이미지 임베드 허용 (없으면 이미지 누락)
- `--pdf-notes`: PDF에 발표자 노트를 PDF annotation으로 첨부
- `--pptx`: PPTX 변환, speaker notes는 자동 포함 (별도 플래그 불필요)
- `--pptx-editable`: 텍스트 박스 기반 편집 가능 PPTX (이미지 기반 PPTX보다 유연하나 일부 스타일 손실 가능)

### 발표 자료 작업 워크플로우

발표를 만들거나 수정할 때 항상 다음 순서를 따른다.

1. `slides.md` 작성·수정 (각 슬라이드에 `<!-- ... -->` speaker note 포함).
2. `script.md` 작성·수정 (슬라이드 번호별 대본, 시간 배분 명시).
3. PDF + PPTX 둘 다 빌드 (`marp ... --pdf` 와 `marp ... --pptx`).
4. 빌드 산출물(PDF/PPTX)을 함께 커밋 (이 vault는 학습용이라 binary 산출물도 포함).

### Anti-Patterns (발표 자료)

- ❌ `slides.md` 만 갱신하고 PDF/PPTX 빌드 누락 → 항상 3종 동기화.
- ❌ 발표자 노트를 별도 파일로만 두고 `slides.md` 안 HTML comment를 비워두는 것 → PPTX speaker notes로 안 들어감.
- ❌ `script.md` 없이 PPTX 노트만 작성 → 연습·리뷰 시 가독성 떨어짐.
- ❌ 챕터 작업물에 prefix 없이 `slides.pdf` 사용 → 챕터 산출물은 반드시 `chXX-` prefix.
- ❌ `--allow-local-files` 누락 → diagrams/ 이미지가 PDF/PPTX에 누락되는 흔한 실수.

## Anti-Patterns

- 학습 노트를 루트에 직접 두지 않는다 → 반드시 `study/<topic>/`.
- 발표 자료를 `study/`에 섞지 않는다 → 반드시 `presentation/<topic>/`.
- `study/kubernetes-in-action/examples/`는 책 공식 예제 미러이므로 **수정 금지**.
- 챕터 폴더 안에 또 다른 챕터를 중첩하지 않는다 (평탄한 `chXX-*` 구조 유지).

## When Adding a New Study Topic

1. `study/<topic>/` 폴더 생성.
2. `study/<topic>/README.md`에 학습 목표·진행 상황을 기록.
3. 섹션/챕터 단위 하위 폴더 생성 (`ch01-*`, `part1-*` 등 일관된 prefix).
4. 발표를 만든다면 `presentation/<topic>/` 별도 생성, 학습 노트와 분리.
