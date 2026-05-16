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
| 발표 슬라이드 (Marp / PDF / 다이어그램)    | `presentation/<topic>/`          | `slides.md`, `diagrams/`, `*.pdf`              |
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
  - `slides.md` (Marp), `diagrams/`, `*.pdf`, `reference/`.
  - 다이어그램은 `marp-diagram-generation` skill 가이드라인을 따른다 (16:9, 큰 폰트).
- **새 학습 주제**: `study/<new-topic>/` 폴더를 만들고, 챕터/섹션 단위로 하위 폴더를 둔다.
- **Inbox 정리**: `inbox/`에 쌓인 노트는 주기적으로 분류해 `study/` 또는 `presentation/`로 옮긴다.

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
