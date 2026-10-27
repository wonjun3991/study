# Observability Study

> **학습 목표**: Metric · Log · Trace를 각각의 도구가 아니라 **하나의 질문 흐름**("무엇이 → 어디서 → 왜")으로 엮어 장애를 추적할 수 있게 된다.
> OpenTelemetry를 공통 기반으로 LGTM 스택(Loki · Grafana · Tempo · Mimir/Prometheus)을 직접 구성하고, 마지막 2주는 같은 원리를 **LLM 애플리케이션/에이전트**에 적용한다.
>
> **1차 출처**: [OpenTelemetry 공식 문서](https://opentelemetry.io/docs/) · [Prometheus 공식 문서](https://prometheus.io/docs/) · [Grafana Loki](https://grafana.com/docs/loki/latest/) · [Grafana Tempo](https://grafana.com/docs/tempo/latest/)
> **보조 자료**: *Observability Engineering* (Majors, Fong-Jones, Miranda) · *Prometheus: Up & Running* · [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
> **기간**: 8주 (주 1회 정리)
> **시작일**: 2026-10-10

---

## 0. Observability 한 줄 정의

> **시스템 내부를 미리 예상하지 못한 질문으로도 바깥에서 나오는 신호(telemetry)만으로 설명할 수 있는 능력.**

| 신호 | 답하는 질문 | 데이터 형태 | 대표 도구 |
|---|---|---|---|
| **Metric** | **무엇이** 이상한가? | 시간 단위로 집계된 숫자 | Prometheus, Mimir |
| **Trace** | **어디서** 느려지거나 실패하는가? | span 트리 (trace_id / span_id / parent) | Tempo, Jaeger |
| **Log** | **왜** 그런가? | 개별 이벤트 레코드 | Loki, Elasticsearch |
| (Profile) | 코드의 **어느 함수가** 자원을 쓰는가? | 스택 샘플 | Pyroscope |

신호를 잇는 열쇠:
- **trace_id**: log ↔ trace 연결
- **exemplar**: metric → trace 연결
- **공통 resource attribute** (`service.name`, `k8s.pod.name` …): 세 신호 모두를 같은 대상으로 필터

```
[Metric] checkout p99 급증 ──exemplar──▶ [Trace] Payment span 720ms ──trace_id──▶ [Log] "gateway timeout"
```

---

## 1. 실습 환경

| 단계 | 환경 | 용도 |
|---|---|---|
| 1~2주 | Docker Compose + [`grafana/otel-lgtm`](https://github.com/grafana/docker-otel-lgtm) | 단일 컨테이너로 OTel Collector + Prometheus + Loki + Tempo + Grafana. 개념 실습 |
| 3~6주 | kind 클러스터 + Helm (`kube-prometheus-stack`, Loki, Tempo, OTel Collector) → [`lab/`](lab/README.md) | K8s 환경 수집 구조 (kubernetes-in-action ch14·15 연계) |
| 7~8주 | 위 스택 + **Langfuse v3 self-host** (`lab/llm/`, Docker Compose) + 직접 만든 LangGraph 에이전트 (`lab/llm/agent/`) | LLM 트레이싱·평가. OTel Collector가 trace를 Tempo와 Langfuse로 동시에 보낸다 |

샘플 앱: 서비스 2~3개짜리 간단한 HTTP 앱(예: `gateway → order → payment`)을 직접 만들어 주차마다 계측을 덧붙인다. 규모가 큰 레퍼런스가 필요하면 [OpenTelemetry Demo](https://opentelemetry.io/docs/demo/)를 참고한다.

---

## 2. 커리큘럼

| 주 | 폴더 | 주제 | 상태 |
|---|---|---|---|
| 1 | [`week01-foundations-otel/`](week01-foundations-otel/README.md) | Observability 기초 · OpenTelemetry 아키텍처 | 🟡 |
| 2 | `week02-metrics-prometheus/` | Metric 데이터 모델 · Prometheus · PromQL | ⬜ |
| 3 | `week03-metrics-slo-alerting/` | Golden Signals · SLI/SLO · 알람 · K8s 메트릭 | ⬜ |
| 4 | `week04-logs/` | 구조화 로그 · K8s 로그 수집 · Loki/LogQL | ⬜ |
| 5 | `week05-traces/` | Span · Context Propagation · Sampling · Tempo | ⬜ |
| 6 | `week06-correlation/` | 신호 연결 · Profiling · eBPF 계측 · 장애 훈련 | ⬜ |
| 7 | `week07-llm-tracing/` | LLM Observability I: Langfuse self-host · GenAI 시맨틱 컨벤션 · 에이전트 트레이싱 직접 구현 | ⬜ |
| 8 | `week08-llm-eval-ops/` | LLM Observability II: Langfuse 평가(Score · Dataset · LLM-as-judge) · 프롬프트 버전 · 비용 · 캡스톤 | ⬜ |

상태 범례: ⬜ 시작 전 · 🟡 진행 중 · ✅ 완료

---

### 1주차: Observability 기초와 OpenTelemetry

**목표**: Monitoring과 Observability의 차이를 이해하고, OTel이 왜 공통 기반이 되었는지 설명할 수 있다.

**핵심 질문**
- Monitoring(알려진 문제 감시)과 Observability(모르는 문제 탐색)는 무엇이 다른가?
- 세 신호는 각각 어떤 비용·정보량 trade-off를 가지는가?
- OTel의 API / SDK / Collector / OTLP는 각각 어떤 역할인가?
- 왜 벤더 SDK 대신 OTel로 계측해야 하는가?

**학습 내용**
- Three pillars 개념과 그 한계 ("pillar가 아니라 연결된 데이터")
- Cardinality / Dimensionality
- OTel 구성: Instrumentation(auto/manual), SDK, Exporter, Collector(receiver → processor → exporter 파이프라인)
- OTLP 프로토콜 (gRPC 4317 / HTTP 4318)
- Resource attributes와 Semantic Conventions

**실습**
- `otel-lgtm` 컨테이너 띄우기, 샘플 앱에 OTel SDK 자동 계측 적용
- Grafana에서 metric / log / trace가 들어오는 것 확인

---

### 2주차: Metric과 Prometheus

**목표**: Prometheus 데이터 모델과 PromQL로 원하는 지표를 직접 뽑을 수 있다.

**핵심 질문**
- Counter, Gauge, Histogram, Summary는 언제 무엇을 쓰는가?
- Prometheus는 왜 pull 모델인가? push가 필요할 때는?
- `rate()`를 counter에 왜 써야 하는가?
- label을 잘못 붙이면 왜 Prometheus가 터지는가? (cardinality 폭발)

**학습 내용**
- 시계열 = metric name + label set, TSDB 구조 개요
- Scrape, target, exporter (node-exporter 등), service discovery
- PromQL: instant/range vector, `rate`, `sum by`, `histogram_quantile`
- Histogram bucket 설계, Native histogram 개념
- OTel metric ↔ Prometheus metric 변환 (이름·단위 규칙)

**실습**
- 샘플 앱에 커스텀 metric(요청 수, 지연 histogram) 추가
- PromQL로 에러율 · p50/p95/p99 지연 쿼리 작성

---

### 3주차: Golden Signals, SLO, 알람

**목표**: "무엇을 측정하고 언제 사람을 깨울지"를 설계할 수 있다.

**핵심 질문**
- RED · USE · 4 Golden Signals는 각각 어떤 대상에 쓰는가?
- SLI / SLO / SLA / Error budget은 어떻게 연결되는가?
- 임계값 알람 대신 burn-rate 알람을 쓰는 이유는?
- K8s 클러스터 메트릭은 어디서 오는가? (cAdvisor, kubelet, kube-state-metrics, node-exporter)

**학습 내용**
- RED(Rate/Errors/Duration) vs USE(Utilization/Saturation/Errors)
- SLO 설계, multi-window multi-burn-rate 알람
- Recording rule, Alerting rule, Alertmanager(routing, grouping, inhibition, silence)
- Grafana 대시보드 설계 원칙
- 장기 저장·확장: Mimir / Thanos 개념
- (연계) ch15 HPA의 Metrics Server · Prometheus Adapter 경로 복습

**실습**
- kind + `kube-prometheus-stack` 설치
- 샘플 앱의 가용성 SLO 정의 → burn-rate 알람 → 장애 주입으로 알람 발생 확인

---

### 4주차: Log

**목표**: 검색 가능하고 trace와 연결되는 로그를 설계하고 K8s에서 수집할 수 있다.

**핵심 질문**
- 비구조화 로그와 구조화(JSON) 로그는 운영에서 어떤 차이를 만드는가?
- K8s에서 컨테이너 로그는 물리적으로 어디에 쌓이고, 누가 수집하는가?
- Loki는 왜 본문을 인덱싱하지 않는가? Elasticsearch와 무엇이 다른가?
- 로그 비용은 어떻게 통제하는가?

**학습 내용**
- 로그 레벨 · 구조화 로그 · 로그에 trace_id/span_id 주입
- K8s 로그 경로: stdout → container runtime → `/var/log/pods` → DaemonSet 에이전트
- 수집기: OTel Collector `filelog` receiver, Fluent Bit, Promtail(→ Alloy) 비교
- Loki: label(인덱스) vs content, stream, chunk, LogQL (필터, parser, metric 쿼리)
- 보존 기간 · 샘플링 · 민감정보 마스킹

**실습**
- 샘플 앱을 JSON 로그 + trace_id 출력으로 변경
- Loki 설치, LogQL로 에러 로그 → 로그 기반 metric(`count_over_time`) 만들기

---

### 5주차: Trace

**목표**: 분산 요청이 서비스 경계를 넘어 하나의 trace로 이어지는 원리를 설명하고 직접 계측할 수 있다.

**핵심 질문**
- span에는 어떤 정보가 들어 있고, 부모-자식 관계는 어떻게 만들어지는가?
- 서비스 A에서 B로 trace context는 어떻게 넘어가는가?
- 모든 요청을 trace하면 왜 안 되는가? head vs tail sampling의 차이는?
- 비동기(메시지 큐) 구간은 어떻게 이어 붙이는가?

**학습 내용**
- Span 구조: name, kind, attributes, events, status, links
- W3C Trace Context (`traceparent`, `tracestate`), Baggage
- Auto instrumentation vs manual span
- Sampling: head-based(ratio), tail-based(Collector `tail_sampling` processor)
- Tempo / Jaeger 구조, TraceQL
- Span metrics, Service graph

**실습**
- `gateway → order → payment` 3개 서비스에 trace 전파 확인
- payment에 지연을 주입하고 Tempo에서 병목 span 찾기
- tail sampling으로 "에러·느린 trace만 보존" 설정

---

### 6주차: 신호 연결과 운영

**목표**: Metric 알람에서 시작해 trace, log로 내려가 근본 원인까지 도달하는 흐름을 실제로 수행할 수 있다.

**핵심 질문**
- Exemplar는 어떻게 metric에 trace_id를 붙이는가?
- Grafana에서 trace ↔ log ↔ metric 이동은 어떤 설정으로 가능한가?
- 코드 수정 없이 계측하는 방법은? (eBPF 기반)
- 네 번째 신호인 Profile은 언제 필요한가?

**학습 내용**
- Exemplar (OpenMetrics), Grafana data source correlation (trace-to-logs, trace-to-metrics, logs-to-trace)
- Continuous profiling: Pyroscope, trace-to-profile
- eBPF 기반 zero-code 계측: Grafana Beyla / OTel eBPF 계측
- Observability 비용 구조와 telemetry 파이프라인 설계 (Collector agent vs gateway 배포)

**실습**
- 장애 시나리오 훈련: 알람 → exemplar → trace → log → 원인 기록
- 결과를 포스트모템 형식으로 정리

---

### 7주차: LLM Observability I: Langfuse로 에이전트 트레이싱 직접 구현

**목표**: 직접 만든 LLM 에이전트를 OTel로 계측해, 같은 trace를 **Tempo(인프라 관점)** 와 **Langfuse(LLM 관점)** 에서 동시에 보여줄 수 있다.

**핵심 질문**
- LLM 애플리케이션은 기존 서비스와 무엇이 다르게 관측되어야 하는가? (비결정성, 토큰·비용, TTFT, 품질)
- 에이전트 한 번의 실행(LLM 호출 → tool 호출 → 재호출)은 어떤 span 트리가 되는가?
- Langfuse의 trace / observation(span · generation · event)은 OTel span과 어떻게 대응되는가?
- 프롬프트·응답 본문을 trace에 남겨도 되는가? (용량 · PII → Tempo에는 빼고 Langfuse에만?)
- LLM 전용 도구(Langfuse)와 OTel 기반 스택은 어떻게 공존하는가? (Langfuse v3 SDK 자체가 OTel 기반)

**학습 내용**
- [OTel GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/): `gen_ai.*` attribute, inference / tool execution / agent span, 토큰 사용량 metric
- [Langfuse](https://langfuse.com/docs) 데이터 모델: Trace · Observation · Session · User, Langfuse가 `gen_ai.*` attribute를 generation/usage/cost로 매핑하는 방식
- Langfuse v3 아키텍처: Web · Worker · Postgres · ClickHouse · Redis · S3(MinIO), self-host 구성
- 계측 경로 비교: Langfuse Python SDK(`@observe`, LangChain `CallbackHandler`) vs 순수 OTel(OpenLLMetry/OpenInference) → Langfuse OTLP endpoint(`/api/public/otel`)
- LLM 핵심 지표: 입력·출력 토큰, 비용, 지연(TTFT, 전체), 에러/rate limit, 캐시 적중률

**실습 (직접 구현)**
1. `lab/llm/`에 Langfuse v3 self-host (Docker Compose) → 프로젝트 생성, public/secret key 발급
2. `lab/llm/agent/`: LangGraph로 tool-calling 에이전트 작성 (`study/langgraph` uv 환경 재사용, ch02~03 개념만 필요)
   - tool은 데모 앱 API를 호출한다 (예: "주문 상태 조회" → gateway `/checkout`, "결제 재시도" → payment)
   - → 에이전트 span 아래로 `gateway → order → payment` HTTP span이 **같은 trace_id**로 이어진다
3. 계측 2단계로 비교
   - A. Langfuse SDK 직접 연결 (`CallbackHandler`) → Langfuse UI에서 generation · 토큰 · 비용 확인
   - B. OTel SDK → **otel-gateway에 `otlphttp/langfuse` exporter 추가** → 같은 trace를 Tempo와 Langfuse로 fan-out
4. 결과물: 에이전트 1회 실행의 span 트리 다이어그램 + Tempo / Langfuse 화면 비교표 (무엇이 어느 쪽에서 더 잘 보이는가)

---

### 8주차: LLM Observability II: Langfuse 평가와 운영 + 캡스톤

**목표**: "응답이 빨리 왔는가"를 넘어 "응답이 좋았는가"를 Langfuse Score로 지속 측정하고, 전체 스택을 하나의 장애 시나리오로 엮는다.

**핵심 질문**
- LLM 품질은 어떻게 숫자로 만들 수 있는가? (offline eval, online eval, LLM-as-judge, 사용자 피드백)
- 프롬프트·모델 버전 변경이 품질/비용에 준 영향을 어떻게 추적하는가?
- LLM 서비스의 SLO는 무엇으로 정의하는가? (지연 · 에러율 + 품질 점수)
- 비용 폭증, 무한 루프 에이전트는 어떻게 감지하는가?

**학습 내용**
- Langfuse Score: 수치/범주/불리언, API·SDK로 사람 피드백 기록, 관리형 LLM-as-judge evaluator
- Langfuse Dataset · Experiment: 데이터셋 기반 회귀 평가, 실행 간 비교, LLM-as-judge 한계
- Langfuse Prompt Management: 프롬프트 버전 · label(production/staging)과 trace 연결
- Session · User 단위 분석, 비용 대시보드
- 알람: Langfuse는 분석, 알람은 Prometheus/Alertmanager로 (토큰/비용 예산, 에러율, 에이전트 step 수 상한)
- 가드레일 · PII 마스킹 (SDK mask 함수 / Collector `transform`·`redaction` processor) · 데이터 보존 정책

**실습 (직접 구현)**
- 에이전트용 평가 데이터셋 10~20개 작성 → Langfuse Dataset 등록 → 프롬프트 v1 / v2 Experiment 비교 (점수 · 토큰 · 지연)
- online eval: production trace에 LLM-as-judge evaluator 연결, 사용자 피드백(👍/👎)을 Score로 기록
- 에이전트 step 수 · 토큰을 OTel metric으로도 내보내 Prometheus 알람 규칙 작성

**캡스톤**
- 데모 앱 + LLM 에이전트를 하나의 시스템으로 구성
- Grafana 대시보드 1장: 서비스 RED + LLM 토큰/비용/지연 / Langfuse: 품질 점수 · 프롬프트 버전별 비교
- 장애 주입 2종
  - 인프라: payment 지연 → 알람 → Tempo에서 에이전트 tool span 아래 병목 확인
  - 품질: 프롬프트 v3(일부러 나쁘게) 배포 → 지연은 정상인데 Langfuse 점수 하락 → 버전 롤백
- "지연은 Tempo가, 품질은 Langfuse가 잡는다"를 포스트모템으로 정리

---

## 3. 주차 폴더 규칙

주차 폴더는 해당 주를 시작할 때 만든다.

```
study/observability/
├── README.md                    # 이 파일 (목표·커리큘럼·진행 상황)
├── diagrams/                    # 개념 다이어그램 (Python graphviz 소스 + PNG)
├── lab/                         # 공용 kind 실습 환경 (./up.sh) — lab/README.md 참고
└── weekXX-kebab-title/
    ├── README.md                # 학습 노트
    ├── manifests/               # Helm values, K8s 매니페스트, Collector 설정
    └── app/                     # 샘플 앱 · 계측 코드 (필요 시)
```
