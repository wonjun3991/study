"""OTel 구성 요소: API → SDK → Exporter → OTLP → Collector(receiver → processor → exporter) → 백엔드.

실행: python3 03_otel_components.py  →  03_otel_components.png
"""
from diagrams import Cluster, Diagram, Edge
from diagrams.custom import Custom
from diagrams.onprem.logging import Loki
from diagrams.onprem.monitoring import Prometheus
from diagrams.onprem.tracing import Tempo
from diagrams.programming.language import Python

from _style import (ALL, COLLECT, GEN, GRAY, LOG, METRIC, OTEL_ICON, REQ, STORE, TRACE, WHITE,
                    diagram_kwargs)

with Diagram("OpenTelemetry 구성 요소와 데이터 흐름",
             **diagram_kwargs("03_otel_components", direction="LR", ranksep="0.9")):

    with Cluster("애플리케이션 프로세스", graph_attr=GEN):
        code = Python("비즈니스 코드\n+ 라이브러리 (FastAPI, requests…)")
        with Cluster("자동 계측 (코드 수정 없음)", graph_attr=WHITE):
            auto = Custom("instrumentation\n라이브러리 호출을 가로채\nspan · metric 생성", OTEL_ICON)
        with Cluster("OTel SDK", graph_attr=WHITE):
            api = Custom("API\nTracer · Meter · Logger\n(구현 없으면 no-op)", OTEL_ICON)
            sdk = Custom("SDK\nProvider · Sampler\nBatch · Aggregation\n+ Resource(service.name…)", OTEL_ICON)
            exp = Custom("Exporter\nOTLP exporter", OTEL_ICON)
        code >> Edge(color=REQ, label="수동 계측") >> api
        code >> Edge(color=REQ, style="dashed") >> auto >> Edge(color=REQ) >> api
        api >> Edge(color=ALL) >> sdk >> Edge(color=ALL) >> exp

    with Cluster("OpenTelemetry Collector", graph_attr=COLLECT):
        rcv = Custom("receivers\notlp · file_log\nprometheus", OTEL_ICON)
        prc = Custom("processors\nk8s_attributes · batch\nfilter · tail_sampling", OTEL_ICON)
        cex = Custom("exporters\notlp_grpc · otlp_http\nprometheusremotewrite", OTEL_ICON)
        rcv >> Edge(color=ALL) >> prc >> Edge(color=ALL) >> cex

    with Cluster("백엔드 (OTel 범위 밖)", graph_attr=STORE):
        prom = Prometheus("Metric")
        loki = Loki("Log")
        tempo = Tempo("Trace")

    exp >> Edge(color=ALL, label="OTLP\ngRPC 4317 / HTTP 4318", penwidth="2.5") >> rcv
    cex >> Edge(color=METRIC) >> prom
    cex >> Edge(color=LOG) >> loki
    cex >> Edge(color=TRACE) >> tempo
