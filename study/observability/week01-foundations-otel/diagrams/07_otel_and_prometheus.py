"""OTel과 Prometheus의 관계: 생성·전송 표준 vs 저장·조회 백엔드, metric이 들어오는 3가지 경로.

실행: python3 07_otel_and_prometheus.py  →  07_otel_and_prometheus.png
"""
from diagrams import Cluster, Diagram, Edge
from diagrams.custom import Custom
from diagrams.k8s.compute import Pod
from diagrams.onprem.monitoring import Grafana, Prometheus

from _style import COLLECT, GEN, METRIC, OTEL_ICON, STORE, VIEW, WHITE, diagram_kwargs

with Diagram("OTel과 Prometheus: metric이 Prometheus에 들어오는 경로",
             **diagram_kwargs("07_otel_and_prometheus", direction="LR", ranksep="1.4")):

    with Cluster("생성 (OTel 영역)", graph_attr=GEN):
        otel_app = Pod("앱 + OTel SDK\nhttp.server.request.duration")
    with Cluster("생성 (Prometheus 영역)", graph_attr=GEN):
        prom_app = Pod("앱 + Prometheus client\n/metrics")
        exporter = Prometheus("node-exporter\nkube-state-metrics")

    with Cluster("수집 · 전송", graph_attr=COLLECT):
        col = Custom("OTel Collector\n(prometheus receiver로\nscrape도 가능)", OTEL_ICON)

    with Cluster("저장 · 쿼리 (Prometheus 3.x)", graph_attr=STORE):
        prom = Prometheus("Prometheus\n/api/v1/otlp 수신\n+ 자체 scrape\n\n→ http_server_request_\nduration_seconds")

    with Cluster("조회", graph_attr=VIEW):
        graf = Grafana("Grafana")

    otel_app >> Edge(color=METRIC, label="① OTLP push") >> col
    col >> Edge(color=METRIC, label="OTLP push\n(이름 · 단위 자동 변환)", penwidth="2.5") >> prom
    prom_app >> Edge(color=METRIC, style="dashed", label="② scrape (pull)") >> prom
    exporter >> Edge(color=METRIC, style="dashed", label="② scrape (pull)") >> prom
    prom_app >> Edge(color=METRIC, style="dotted", label="③ Collector가 scrape\n→ remote_write") >> col
    prom >> Edge(color=METRIC, label="PromQL") >> graf
