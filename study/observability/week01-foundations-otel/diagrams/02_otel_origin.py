"""OpenTelemetry 이전(벤더별 계측 · 표준 분열)과 이후(계측 1번, 백엔드 자유).

실행: python3 02_otel_origin.py  →  02_otel_origin.png
"""
from diagrams import Cluster, Diagram, Edge
from diagrams.custom import Custom
from diagrams.onprem.monitoring import Datadog, Dynatrace, Grafana, Newrelic, Prometheus
from diagrams.onprem.tracing import Jaeger
from diagrams.programming.language import Go, Java, Python

from _style import BAD, GRAY, METRIC, OTEL_ICON, STORE, WARN, WHITE, COLLECT, ALL, diagram_kwargs

with Diagram("OpenTelemetry는 왜 생겼나",
             **diagram_kwargs("02_otel_origin", direction="LR", ranksep="1.4")):

    with Cluster("Before: 벤더마다 다른 SDK · 에이전트 (vendor lock-in)", graph_attr=WARN):
        with Cluster("서비스", graph_attr=WHITE):
            a1 = Java("주문 (Java)\nDatadog agent")
            a2 = Python("결제 (Python)\nNew Relic SDK")
            a3 = Go("재고 (Go)\nOpenTracing + Jaeger")
        dd = Datadog("Datadog")
        nr = Newrelic("New Relic")
        jg = Jaeger("Jaeger")
        a1 >> Edge(color=BAD, label="전용 포맷") >> dd
        a2 >> Edge(color=BAD, label="전용 포맷") >> nr
        a3 >> Edge(color=BAD, label="전용 포맷") >> jg

    merge = Custom("OpenTracing (CNCF)\n+ OpenCensus (Google)\n→ 2019 OpenTelemetry", OTEL_ICON)

    with Cluster("After: 계측은 OTel 한 번, 백엔드는 설정으로 선택", graph_attr=COLLECT):
        with Cluster("서비스 (모두 OTel SDK)", graph_attr=WHITE):
            b1 = Java("주문")
            b2 = Python("결제")
            b3 = Go("재고")
        col = Custom("OTel Collector", OTEL_ICON)
        with Cluster("아무 백엔드 (교체 가능)", graph_attr=STORE):
            back = [Prometheus("Prometheus"), Grafana("Grafana\nLoki · Tempo"), Dynatrace("상용 SaaS")]
        for b in (b1, b2, b3):
            b >> Edge(color=ALL, label="OTLP") >> col
        col >> Edge(color=METRIC, style="dashed") >> back

    jg >> Edge(color=GRAY, style="invis") >> merge
    merge >> Edge(color=GRAY, style="bold", label="표준 통합") >> b2
