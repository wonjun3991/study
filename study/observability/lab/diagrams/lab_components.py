"""kind-observability 실습 환경 구성요소 (실제 배포 이미지·버전 기준, 2026-10-11).

실행: python3 lab_components.py  →  lab_components.png
필요: pip install diagrams (graphviz 필요). OTel 아이콘은 icons/opentelemetry.png (CNCF artwork).
"""
from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.custom import Custom
import diagrams
from diagrams.onprem.client import Client
from diagrams.onprem.logging import Loki
from diagrams.onprem.monitoring import Grafana, Prometheus, PrometheusOperator
from diagrams.onprem.tracing import Tempo
from diagrams.programming.framework import Fastapi

HERE = Path(__file__).parent
OTEL_ICON = str(HERE / "icons" / "opentelemetry.png")
K8S_ICON = str(Path(diagrams.__file__).parent.parent / "resources" / "k8s" / "k8s.png")
FONT = "Apple SD Gothic Neo"
METRIC, LOG, TRACE, REQ = "#0891b2", "#d97706", "#7c3aed", "#64748b"


def cluster_attr(fill: str, border: str) -> dict:
    return {"bgcolor": fill, "pencolor": border, "fontname": FONT, "fontsize": "15", "style": "rounded",
            "margin": "18"}


graph_attr = {"fontname": FONT, "fontsize": "26", "labelloc": "t", "pad": "0.5", "nodesep": "0.55",
              "ranksep": "1.2", "dpi": "150", "splines": "spline"}
node_attr = {"fontname": FONT, "fontsize": "12"}

with Diagram("kind-observability 구성요소", filename=str(HERE / "lab_components"), outformat="png", show=False,
             direction="LR", graph_attr=graph_attr, node_attr=node_attr):

    with Cluster("① 워크로드  ns: demo", graph_attr=cluster_attr("#f1f5f9", "#cbd5e1")):
        loadgen = Client("loadgen\ncurlimages/curl:8.11.1\nDeployment ×1 · ~2 req/s")
        with Cluster("demo-app:0.1  (Python 3.12 · FastAPI · OTel 자동 계측 0.66b1)",
                     graph_attr=cluster_attr("#ffffff", "#e2e8f0")):
            gateway = Fastapi("gateway\nGET /checkout")
            order = Fastapi("order\nPOST /orders")
            payment = Fastapi("payment\nPOST /pay")

    with Cluster("② 수집 · 가공  OpenTelemetry Collector\notel/opentelemetry-collector-k8s:0.161.0",
                 graph_attr=cluster_attr("#ecfeff", "#a5f3fc")):
        agent = Custom("otel-agent\nDaemonSet ×2 (worker)\nOTLP · file_log · k8s_attributes", OTEL_ICON)
        gw = Custom("otel-gateway\nDeployment ×1\n신호별 라우팅", OTEL_ICON)

    with Cluster("③ 저장 · 쿼리", graph_attr=cluster_attr("#fefce8", "#fde68a")):
        prom = Prometheus("Prometheus\nprometheus:v3.15.0\nStatefulSet ×1\nTSDB · PromQL · OTLP 수신")
        loki = Loki("Loki\ngrafana/loki:3.6.11\nStatefulSet ×1 (SingleBinary)\nLogQL · structured metadata")
        tempo = Tempo("Tempo\ngrafana/tempo:2.9.0\nStatefulSet ×1\nTraceQL · metrics-generator")

    with Cluster("Metric 수집 대상 · 운영 (kube-prometheus-stack 92.3.0)",
                 graph_attr=cluster_attr("#f0fdfa", "#99f6e4")):
        nodeexp = Prometheus("node-exporter\nv1.12.1\nDaemonSet ×3")
        ksm = Custom("kube-state-metrics\nv2.20.0\nDeployment ×1", K8S_ICON)
        operator = PrometheusOperator("Prometheus Operator\nv0.94.1\nServiceMonitor → scrape 설정")

    with Cluster("④ 조회 · 알람", graph_attr=cluster_attr("#f5f3ff", "#ddd6fe")):
        grafana = Grafana("Grafana\ngrafana:13.2.3\nDeployment ×1\nExplore · 신호 간 이동")
        am = Prometheus("Alertmanager\nv0.34.1\nStatefulSet ×1")

    # 요청 흐름
    loadgen >> Edge(color=REQ) >> gateway >> Edge(color=REQ, label="traceparent") >> order \
        >> Edge(color=REQ, label="traceparent") >> payment

    # 앱 → agent (trace·metric은 OTLP, log는 stdout 파일)
    for svc in (gateway, order, payment):
        svc >> Edge(color=f"{METRIC}:{TRACE}:{LOG}") >> agent
    agent >> Edge(color=f"{METRIC}:{LOG}:{TRACE}", label="OTLP", penwidth="2") >> gw

    gw >> Edge(color=METRIC, label="metric") >> prom
    gw >> Edge(color=LOG, label="log") >> loki
    gw >> Edge(color=TRACE, label="trace") >> tempo
    tempo >> Edge(color=METRIC, style="dashed", label="span metrics") >> prom

    # 수집 대상 3개를 가로로 나란히 배치 (보이지 않는 엣지로 rank를 나눔)
    nodeexp >> Edge(style="invis") >> ksm >> Edge(style="invis") >> operator

    # scrape는 Prometheus가 가져가는 pull이지만, 배치를 위해 대상 → Prometheus 방향으로 그린다
    nodeexp >> Edge(color=METRIC, style="dashed", label="scrape (pull)") >> prom
    ksm >> Edge(color=METRIC, style="dashed", label="scrape (pull)") >> prom
    operator >> Edge(color=REQ, style="dotted", label="scrape 설정") >> prom

    prom >> Edge(color=METRIC) >> grafana
    loki >> Edge(color=LOG) >> grafana
    tempo >> Edge(color=TRACE) >> grafana
    prom >> Edge(color=METRIC, label="alert") >> am
