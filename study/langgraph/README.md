# LangGraph Study

> **학습 목표**: LangGraph를 "LLM 호출 래퍼"가 아니라 **상태를 가진 장기 실행 에이전트의 오케스트레이션 런타임**으로 이해한다.
> Graph API로 직접 에이전트를 조립하고, persistence · interrupt · streaming · memory를 붙여 실제 운영 가능한 형태까지 만들어 본다.
>
> **1차 출처**: [LangGraph 공식 문서 (Python)](https://docs.langchain.com/oss/python/langgraph/overview)
> **기준 버전**: `langgraph 1.2.12` (PyPI, 2026-09-30 확인) / Python 3.12 (uv로 관리)
> **시작일**: 2026-09-30

---

## 0. LangGraph 한 줄 정의

> *"a low-level orchestration framework and runtime for building, managing, and deploying long-running, stateful agents."*

- **low-level**: 프롬프트·아키텍처를 추상화하지 않는다. 노드/엣지/상태를 직접 설계한다.
- **stateful + long-running**: 체크포인트 기반 persistence → 실패 후 재개, 사람 개입(HITL), time travel.
- **결정적 로직 + 에이전트 로직 혼합**: 한 그래프 안에 하드코딩 분기와 LLM 판단을 같이 둔다.
- 설계 영감: Google **Pregel**, Apache Beam, NetworkX.

생태계 위치:

| 레이어 | 역할 |
|---|---|
| **Deep Agents** | 계획·서브에이전트가 내장된 상위 harness |
| **LangChain** | 모델/툴 통합, `create_agent` 등 고수준 추상화 (내부적으로 LangGraph 위에서 동작) |
| **LangGraph** | 이 스터디의 대상. 그래프 런타임 |
| **LangSmith** | Observability · Studio · Deployment |

---

## 1. 환경 구성

이 폴더 자체가 uv 프로젝트다 (`pyproject.toml`, `.python-version`, `uv.lock`). 시스템 Python이 3.9라 LangGraph 요구사항(`>=3.10`)을 못 맞추므로 uv가 3.12를 관리한다.

```bash
cd study/langgraph
uv sync                                   # .venv 생성 + 의존성 설치
uv run python ch01-overview-quickstart/hello_world.py
uv add langchain-anthropic                # LLM이 필요한 챕터부터 추가
```

API 키는 `study/langgraph/.env`에 두고 커밋하지 않는다 (`.gitignore` 등록됨).

---

## 2. 커리큘럼

공식 문서 사이드바 순서를 기준으로 개념 의존성에 맞게 재배열했다. 챕터 폴더는 해당 챕터를 시작할 때 만든다.

| # | 챕터 폴더 | 주제 | 공식 문서 | 상태 |
|---|---|---|---|---|
| 01 | `ch01-overview-quickstart/` | 개요, 설치, Quickstart, "Thinking in LangGraph" | [overview](https://docs.langchain.com/oss/python/langgraph/overview) · [install](https://docs.langchain.com/oss/python/langgraph/install) · [quickstart](https://docs.langchain.com/oss/python/langgraph/quickstart) · [thinking-in-langgraph](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph) | 🟡 진행 중 |
| 02 | `ch02-graph-api/` | State · Reducer · Node · Edge · 조건부 엣지 · `Send` · `Command` | [graph-api](https://docs.langchain.com/oss/python/langgraph/graph-api) · [use-graph-api](https://docs.langchain.com/oss/python/langgraph/use-graph-api) | ⬜ |
| 03 | `ch03-workflows-agents/` | 워크플로 패턴 (chaining, routing, parallelization, orchestrator-worker, evaluator-optimizer) vs 에이전트 | [workflows-agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) | ⬜ |
| 04 | `ch04-persistence/` | Checkpointer · Thread · Store · Durable execution / fault tolerance | [persistence](https://docs.langchain.com/oss/python/langgraph/persistence) · [checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers) · [stores](https://docs.langchain.com/oss/python/langgraph/stores) · [fault-tolerance](https://docs.langchain.com/oss/python/langgraph/fault-tolerance) | ⬜ |
| 05 | `ch05-streaming/` | stream modes (values / updates / messages / custom), 이벤트 스트리밍 | [streaming](https://docs.langchain.com/oss/python/langgraph/streaming) · [event-streaming](https://docs.langchain.com/oss/python/langgraph/event-streaming) | ⬜ |
| 06 | `ch06-human-in-the-loop/` | `interrupt()` · `Command(resume=...)` · time travel (replay / fork) | [interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) · [use-time-travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel) | ⬜ |
| 07 | `ch07-memory/` | 단기 메모리(thread) vs 장기 메모리(store), 메시지 트리밍·요약 | [add-memory](https://docs.langchain.com/oss/python/langgraph/add-memory) | ⬜ |
| 08 | `ch08-subgraphs/` | 서브그래프 · 멀티 에이전트 구성 · 애플리케이션 구조 | [use-subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs) · [application-structure](https://docs.langchain.com/oss/python/langgraph/application-structure) | ⬜ |
| 09 | `ch09-functional-api/` | `@entrypoint` · `@task`, Graph API와의 선택 기준 | [choosing-apis](https://docs.langchain.com/oss/python/langgraph/choosing-apis) · [functional-api](https://docs.langchain.com/oss/python/langgraph/functional-api) · [use-functional-api](https://docs.langchain.com/oss/python/langgraph/use-functional-api) | ⬜ |
| 10 | `ch10-runtime-pregel/` | 런타임 내부: Pregel 슈퍼스텝, 채널, 실행 모델 | [pregel](https://docs.langchain.com/oss/python/langgraph/pregel) | ⬜ |
| 11 | `ch11-test-observe-deploy/` | 테스트, LangSmith Studio/Observability, 로컬 서버, 배포, Agent Chat UI | [test](https://docs.langchain.com/oss/python/langgraph/test) · [studio](https://docs.langchain.com/oss/python/langgraph/studio) · [observability](https://docs.langchain.com/oss/python/langgraph/observability) · [local-server](https://docs.langchain.com/oss/python/langgraph/local-server) · [deploy](https://docs.langchain.com/oss/python/langgraph/deploy) | ⬜ |
| 12 | `ch12-projects/` | 실전: Agentic RAG, SQL agent | [agentic-rag](https://docs.langchain.com/oss/python/langgraph/agentic-rag) · [sql-agent](https://docs.langchain.com/oss/python/langgraph/sql-agent) | ⬜ |

상태 범례: ⬜ 시작 전 · 🟡 진행 중 · ✅ 완료

---

## 3. 챕터 폴더 규칙

```
study/langgraph/
├── README.md                 # 이 파일 (목표·커리큘럼·진행 상황)
├── pyproject.toml / uv.lock  # 공용 실습 환경
└── chXX-kebab-title/
    ├── README.md             # 학습 노트
    └── *.py                  # 실습 코드 (uv run python chXX-*/foo.py)
```

- 실습 코드는 **모두 `uv run`으로 실행 가능한 상태**로 커밋한다.
- 노트에는 공식 문서 인용 + 직접 돌려본 결과를 함께 적는다.
- 발표 자료를 만들게 되면 `presentation/langgraph/`로 분리한다.

---

## 4. 참고 링크

- 공식 문서: https://docs.langchain.com/oss/python/langgraph/overview
- Changelog: https://docs.langchain.com/oss/python/langgraph/changelog-py
- 문서 인덱스 (LLM용): https://docs.langchain.com/llms.txt
- 소스: https://github.com/langchain-ai/langgraph
