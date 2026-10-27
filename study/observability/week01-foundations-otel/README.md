# 1주차: Observability 기초와 OpenTelemetry

> **함께 보기**: [다이어그램 + lab 실측으로 따라가기](otel-prometheus-walkthrough.md)
>
> **출처**: [OpenTelemetry Docs — Signals](https://opentelemetry.io/docs/concepts/signals/) · [OTel Specification Status](https://opentelemetry.io/status/) · OTEP 0239 (Profiles)

---

## 1. OTel의 다섯 가지 Signal

OpenTelemetry는 **Traces · Metrics · Logs · Baggage · Profiles** 다섯 가지 신호를 정의한다.
이 중 Baggage는 관측 데이터를 직접 만들지 않고 다른 신호에 맥락을 붙이는 역할이다.

| Signal | 한 줄 정의 | 알 수 있는 것 |
|---|---|---|
| **Traces** | 요청 하나가 분산 시스템을 지나간 경로 | 어느 구간이 느린지, 어디서 실패했는지 |
| **Metrics** | 런타임 측정값을 시간 단위로 집계한 숫자 | 추세, SLI/SLO, 알람 조건 |
| **Logs** | 타임스탬프가 붙은 텍스트 또는 구조화 레코드 | 특정 시점의 상세 상황, 에러 원인 |
| **Baggage** | 서비스 간에 전파되는 사용자 정의 key-value | 신호 전반에 비즈니스 맥락 주입 |
| **Profiles** | 스택 트레이스 단위로 샘플링한 자원 사용 분포 | 어느 함수가 CPU/메모리를 쓰는지 |

---

## 2. Traces

**하나의 요청이 분산 시스템을 지나간 전체 경로**를 기록한다.

### 구성 요소
- **Trace**: 요청 하나의 전체 여정. `trace_id`(16바이트)로 식별한다.
- **Span**: 트레이스를 이루는 작업 단위(HTTP 핸들러, DB 쿼리 등).
  - `span_id`, `parent_span_id`: 부모-자식 관계로 트리를 구성
  - `name`, `start_time`, `end_time`
  - `attributes`: key-value 메타데이터 (`http.request.method`, `db.system` 등)
  - `events`: span 안의 특정 시점 사건 (예외 발생 등)
  - `links`: 다른 트레이스의 span과 인과관계 연결 (배치 처리, 메시지 큐)
  - `status`: `Unset` / `Ok` / `Error`
- **SpanKind**: `SERVER`, `CLIENT`, `PRODUCER`, `CONSUMER`, `INTERNAL`

### Context Propagation
서비스 경계를 넘을 때 W3C `traceparent` 헤더에 `trace_id`와 `span_id`를 담아 전달한다. 받는 쪽은 이 값으로 자식 span을 만든다.

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             버전-trace_id-parent_span_id-flags(sampled)
```

### 샘플링
모든 요청을 저장하면 비용이 너무 크기 때문에 샘플링한다.
- **Head sampling**: 요청 시작 시점에 결정 (SDK의 `TraceIdRatioBased`, `ParentBased`)
- **Tail sampling**: 트레이스가 끝난 뒤 에러·지연 여부를 보고 결정 (Collector `tail_sampling` processor)

---

## 3. Metrics

**런타임에 측정한 수치를 시간에 따라 집계한 데이터**. 작고 저렴해서 대시보드와 알람의 기반이 된다.

### Instrument 종류
| Instrument | 특성 | 예시 |
|---|---|---|
| **Counter** | 단조 증가 | 요청 수, 처리 바이트 |
| **UpDownCounter** | 증가·감소 모두 가능 | 활성 연결 수, 큐 길이 |
| **Histogram** | 값의 분포 | 요청 지연시간, 응답 크기 |
| **Gauge** | 현재 값을 그대로 기록 | 온도, CPU 사용률 |
| **Asynchronous (Observable)** Counter/UpDownCounter/Gauge | 수집 주기마다 callback으로 값을 읽음 | 메모리 사용량 |

### 데이터 모델 핵심 개념
- **Aggregation**: Sum, LastValue, Explicit Bucket Histogram, Exponential Histogram
- **Temporality**
  - *Cumulative*: 시작 시점부터 누적 (Prometheus 방식)
  - *Delta*: 직전 수집 이후 변화량 (일부 SaaS 백엔드가 선호)
- **Attributes와 cardinality**: attribute 조합마다 별도 시계열이 된다. `user_id` 같은 고유값을 넣으면 시계열 수가 폭증한다.
- **View**: SDK 단계에서 집계 방식, 버킷, 남길 attribute를 재정의
- **Exemplar**: 히스토그램 버킷 등에 실제 측정 샘플의 `trace_id`를 붙여 메트릭 → 트레이스로 이동 가능

---

## 4. Logs

**타임스탬프가 붙은 텍스트 또는 구조화 레코드**. OTel은 로그를 새로 만들지 않고, 기존 로깅 라이브러리(Log4j, SLF4J/Logback, Python logging 등)를 **Log Bridge API**로 연결하는 방식을 택했다.

### LogRecord 주요 필드
- `Timestamp`, `ObservedTimestamp`: 이벤트 발생 시각 / 수집기가 관측한 시각
- `SeverityText`, `SeverityNumber`: 1~24로 정규화 (TRACE 1~4, DEBUG 5~8, INFO 9~12, WARN 13~16, ERROR 17~20, FATAL 21~24)
- `Body`: 로그 본문 (문자열 또는 구조화 값)
- `Attributes`
- **`TraceId`, `SpanId`, `TraceFlags`**: 활성 span 안에서 찍히면 자동으로 채워짐 → 로그와 트레이스를 잇는 핵심 필드
- `Resource`, `InstrumentationScope`

### 수집 경로
1. **SDK 경로**: 앱 → 로깅 라이브러리 → OTel Log Bridge → OTLP → Collector
2. **파일 경로**: 앱 → stdout/파일 → Collector `filelog` receiver (파싱 후 변환)

### Events
별도 Event API 대신 **`event.name` 속성을 가진 LogRecord**로 Logs 신호에 통합되는 방향이다. 이름이 정해진 구조화 이벤트(브라우저 클릭, GenAI 프롬프트/응답 등)를 표현할 때 쓴다.

---

## 5. Baggage

**서비스 사이에 전파되는 사용자 정의 key-value 컨텍스트**. 그 자체로는 텔레메트리 데이터가 아니다.

```
baggage: tenant.id=acme,user.tier=premium
```

- W3C Baggage 헤더로 `traceparent`와 함께 다운스트림 전체에 전파된다.
- **자동으로 span이나 메트릭 attribute가 되지 않는다.** 필요하면 `BaggageSpanProcessor` 등으로 명시적으로 복사해야 한다.
- 활용 예: 프론트엔드에서 넣은 `tenant.id`를 깊은 백엔드 span/로그에 붙이기, A/B 실험군·요청 출처 전달

**주의**
- 외부 서비스로 나가는 요청에도 헤더가 그대로 실리므로 PII, 토큰 같은 민감정보를 넣지 않는다.
- 모든 요청에 붙기 때문에 크기가 커지면 네트워크 오버헤드가 생긴다.

---

## 6. Profiles

**코드 수준의 자원 사용 분포**(CPU, 메모리 할당, lock 경합 등)를 스택 트레이스 단위로 샘플링한 데이터. 다섯 신호 중 가장 최근에 추가됐다 (OTEP 0239, 2024년 채택).

- 데이터 모델은 **pprof** 기반 확장. 스택·위치·함수·매핑 테이블을 dictionary 형태로 중복 제거해 크기를 줄인다.
- Elastic이 기증한 **eBPF 기반 프로파일러**가 Collector에 붙는 방식으로 개발 중. 코드 수정 없이 시스템 전체 프로파일링이 가능하다.
- 샘플에 `trace_id`/`span_id`를 연결하면 "느린 span에서 실제로 CPU를 쓴 함수"까지 내려갈 수 있다.
- **상태**: Development/Alpha. 프로덕션 적용 전 SDK·Collector 버전별 지원 현황을 확인한다.

메트릭·트레이스가 "느리다"는 사실을 알려준다면, 프로파일은 "어떤 함수 때문에 느린지"를 알려준다.

---

## 7. 신호 간 상관관계 (Correlation)

OTel의 핵심 가치는 신호가 **공통 컨텍스트로 서로 연결된다는 점**이다.

```
           ┌──────────── Resource (service.name, k8s.pod.name, host...) ────────────┐
           │                                                                        │
 Metrics ──(Exemplar: trace_id)──▶ Traces ◀──(trace_id/span_id)── Logs              │
                                     ▲                                              │
                                     └──(trace_id/span_id)── Profiles               │
                                     ▲                                              │
                         Baggage ────┘ (모든 신호에 비즈니스 맥락 주입)            │
           └────────────────────────────────────────────────────────────────────────┘
```

| 연결 수단 | 역할 |
|---|---|
| **Resource** | 모든 신호에 "누가 만들었는지"(서비스, 파드, 노드)를 붙인다. 시맨틱 컨벤션 기반 |
| **Context (trace_id/span_id)** | 트레이스·로그·프로파일을 같은 요청 단위로 묶는다 |
| **Exemplar** | 메트릭 → 트레이스 연결점 |
| **Baggage** | 비즈니스 차원의 맥락을 신호 전반에 전파 |

### 장애 분석 흐름 예시
1. **Metrics**: p99 지연시간 알람 발생
2. Exemplar를 따라 느린 요청의 **Trace**로 이동 → `payment-service`의 DB span이 3초
3. 같은 `span_id`의 **Logs** 확인 → connection pool 고갈 경고
4. 해당 시간대 **Profiles** 확인 → 커넥션 획득 대기 중 lock 경합, 특정 함수 CPU 급증
5. **Baggage**의 `tenant.id` 확인 → 특정 고객사 트래픽에만 몰린 문제

---

## 8. 안정성 현황

| Signal | API/SDK | OTLP |
|---|---|---|
| Traces | Stable | Stable |
| Metrics | Stable | Stable |
| Logs | Stable (Bridge API) | Stable |
| Baggage | Stable | — (W3C 헤더로 전파) |
| Profiles | Development | Development |

언어별 SDK 성숙도는 다르다(예: 일부 언어의 Logs SDK는 Beta). 도입 시 [opentelemetry.io/status](https://opentelemetry.io/status/)에서 확인한다.
