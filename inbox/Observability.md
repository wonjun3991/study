### 관측 가능성

시스템 외부에서 내부에 대한 이해없이 질문을 던져 시스템을 이해할 수 있도록 하는 것. 또한 새로운 문제, 즉 **‘알 수 없는 미지의 문제(unknown unknowns)’**를 쉽게 조사하고 해결할 수 있도록 돕습니다. “왜 이런 일이 발생하고 있지?”라는 질문에도 답할 수 있게 해준다.

### 신뢰성(Reliability)과 계측(Metrics)
**원격측정(Telemetry)은 시스템과 그 동작에서 발생하는 데이터를 의미합니다.** 이러한 데이터는 Trace, Metric, Log 등의 형태로 나타 날 수 있습니다.

**신뢰성은** "서비스가 사용자가 기대하는 대로 작동하는가?"라는 질문에 대한 답입니다.

**메트릭은** 인프라 또는 애플리케이션에 대한 수치 데이터를 일정 기간 동안 집계한 것입니다.

**SLI** (서비스 수준 지표)는 서비스의 동작을 측정하는 지표입니다. 좋은 SLI는 사용자 관점에서 서비스의 성능을 측정합니다.

**SLO** (서비스 수준 목표)는 조직/다른 팀에 신뢰성을 전달하는 수단입니다. 이는 하나 이상의 SLI(서비스 수준 지표)를 비즈니스 가치와 연결함으로써 달성됩니다.

### Traces(흔적)
요청이 어플리케이션을 지나간 경로

**Trace는** 애플리케이션에 요청이 발생했을 때 일어나는 전체적인 상황을 보여줍니다. 애플리케이션이 단일 데이터베이스를 사용하는 모놀리식 구조이든, 복잡하게 얽힌 서비스 네트워크이든, Trace는 애플리케이션 내에서 요청이 거치는 전체 "경로"를 이해하는 데 필수적입니다.

#### Tracer Provider(추적 제공업체)
Tracer Provider는 리소스를 생성하는 팩토리입니다. 대부분의 애플리케이션에서 Tracer Provider는 한 번 초기화되며, 그 수명 주기는 애플리케이션의 수명 주기와 일치합니다.
#### Tracer(추적)
서비스의 요청과 같은 특정 작업에 대해 발생하는 상황에 대한 자세한 정보를 담고 있는 Span을 생성합니다. Tracer는 Tracer Provider를 통해 생성됩니다.

#### Trace Exporter(추적 수출업체)

Trace Exporters 는 Trace를 Consumer(소비자)에게 보냅니다. 수신 대상은 개발 및 디버깅을 위한 표준 출력일 수도 있고, OpenTelemetry Collector나 원하는 오픈소스·상용 백엔드일 수도 있습니다.

#### Context Propagation(컨텍스트 전파)

### Distributed Tracing(분산 추적)
분산 추적을 사용하면 복잡한 분산 시스템에서 요청이 전파되는 과정을 관찰할 수 있습니다.


## OpenTelemetry
### 배경

클라우드 컴퓨팅과 마이크로서비스 아키텍처가 확산되고 비즈니스 요구사항이 점점 복잡해지면서, 소프트웨어와 인프라의 [관측 가능성](https://opentelemetry.io/docs/concepts/observability-primer/#what-is-observability)이 그 어느 때보다 중요해졌습니다.

OpenTelemetry는 두 가지 핵심 원칙을 바탕으로 관측 가능성에 대한 요구를 충족합니다.

1. 생성한 데이터는 사용자가 소유합니다. 특정 벤더에 종속되지 않습니다.
2. 하나의 API와 규칙만 익히면 됩니다.

이 두 원칙을 통해 팀과 조직은 현대의 복잡한 컴퓨팅 환경에서 필요한 유연성을 얻을 수 있습니다.

### 구성요소 
OpenTelemetry는 다음과 같은 주요 구성 요소로 이루어져 있습니다.

- 모든 구성 요소의 기준을 정의하는 [명세](https://opentelemetry.io/docs/specs/otel/)
- 텔레메트리 데이터의 형식을 정의하는 표준 [프로토콜](https://opentelemetry.io/docs/specs/otlp/)
- 일반적인 텔레메트리 데이터 유형의 표준 명명 규칙을 정하는 [시맨틱 규칙](https://opentelemetry.io/docs/specs/semconv/)
- 텔레메트리 데이터를 생성하는 방법을 정의하는 API
- 명세와 API, 텔레메트리 데이터 내보내기를 구현한 [언어별 SDK](https://opentelemetry.io/docs/languages)
- 자주 사용하는 라이브러리와 프레임워크의 계측을 구현한 [라이브러리 생태계](https://opentelemetry.io/ecosystem/registry/)
- 코드를 변경하지 않아도 텔레메트리 데이터를 생성하는 자동 계측 구성 요소
- 텔레메트리 데이터를 수신하고, 처리하고, 내보내는 프록시인 [OpenTelemetry Collector](https://opentelemetry.io/docs/collector)
- [Kubernetes용 OpenTelemetry Operator](https://opentelemetry.io/docs/platforms/kubernetes/operator/), [OpenTelemetry Helm 차트](https://opentelemetry.io/docs/platforms/kubernetes/helm/), [FaaS용 커뮤니티 리소스](https://opentelemetry.io/docs/platforms/faas/) 등 여러 도구

다양한 [라이브러리, 서비스, 애플리케이션](https://opentelemetry.io/ecosystem/integrations/)이 OpenTelemetry를 통합해 기본적으로 관측 가능성을 제공합니다.

### 명세

비전
- [원격 측정은 쉬워야 합니다.](https://opentelemetry.io/community/mission/#telemetry-should-be-easy)
- [원격 측정은 보편적이어야 합니다.](https://opentelemetry.io/community/mission/#telemetry-should-be-universal)
- [원격 측정 데이터는 벤더에 구애받지 않아야 합니다.](https://opentelemetry.io/community/mission/#telemetry-should-be-vendor-neutral)
- [원격 측정 데이터는 느슨하게 결합되어야 합니다.](https://opentelemetry.io/community/mission/#telemetry-should-be-loosely-coupled)
- [원격 측정 기능은 내장되어 있어야 합니다.](https://opentelemetry.io/community/mission/#telemetry-should-be-built-in)
공학적 가치
- [호환성](https://opentelemetry.io/community/mission/#we-value-compatibility)
	-  언어 및 신호 유형(추적, 메트릭, 로깅 등)에 관계없이 통일되어야 하며, 서로 다르거나 고립되어서는 안 됩니다.
- [안정](https://opentelemetry.io/community/mission/#we-value-stability)
	- 하위 버전에서도 문제 없이 동작해야 합니다.
- [회복력](https://opentelemetry.io/community/mission/#we-value-resilience)
	- 자원 부족이나 기타 어려움 속에서도 지속되어야 합니다.
- [성능](https://opentelemetry.io/community/mission/#we-value-performance)
	- 고품질 원격 측정 데이터와 고성능 애플리케이션 사이에서 선택을 강요받아서는 안 됩니다.



## TimeSeries DB

## Prometheus
