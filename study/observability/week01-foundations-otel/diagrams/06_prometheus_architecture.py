"""Prometheus 아키텍처: service discovery → scrape(pull) → TSDB → PromQL / rules → Alertmanager.

실행: python3 06_prometheus_architecture.py  →  06_prometheus_architecture.png
"""
from diagrams import Cluster, Diagram, Edge
from diagrams.k8s.compute import Cronjob, Pod
from diagrams.k8s.controlplane import API
from diagrams.onprem.monitoring import Grafana, Mimir, Prometheus, Thanos
from diagrams.saas.alerting import Pagerduty
from diagrams.saas.chat import Slack

from _style import (BAD, COLLECT, GEN, GRAY, METRIC, REQ, STORE, VIEW, WHITE, cluster,
                    diagram_kwargs)

with Diagram("Prometheus 아키텍처",
             **diagram_kwargs("06_prometheus_architecture", direction="LR", ranksep="1.2")):

    sd = API("Service Discovery\n(K8s API: Pod · Service ·\nEndpoints 목록)")

    with Cluster("수집 대상 (target) : GET /metrics 노출", graph_attr=GEN):
        app = Pod("앱\n(client 라이브러리)")
        node = Prometheus("node-exporter\n노드 CPU · 메모리 · 디스크")
        ksm = Pod("kube-state-metrics\nK8s 오브젝트 상태")
        kubelet = Pod("kubelet / cAdvisor\n컨테이너 자원")
        with Cluster("짧게 끝나는 작업", graph_attr=cluster("#ffffff", "#e2e8f0", dashed=True)):
            job = Cronjob("batch job")
            pgw = Prometheus("Pushgateway")
            job >> Edge(color=METRIC, label="push", style="dashed") >> pgw

    with Cluster("Prometheus server", graph_attr=COLLECT):
        scrape = Prometheus("Retrieval\n15~30초마다 scrape (pull)\n→ up=0이면 대상 다운")
        tsdb = Prometheus("TSDB (로컬 디스크)\n시계열 = 이름 + label 집합\n2시간 블록 · WAL")
        rules = Prometheus("Rule 평가\nrecording rule\nalerting rule")
        scrape >> Edge(color=METRIC) >> tsdb >> Edge(color=METRIC) >> rules

    with Cluster("알람", graph_attr=VIEW):
        am = Prometheus("Alertmanager\ngroup · inhibit · silence · route")
        slack = Slack("Slack")
        pd = Pagerduty("PagerDuty")
        am >> Edge(color=BAD) >> slack
        am >> Edge(color=BAD) >> pd

    with Cluster("조회", graph_attr=VIEW):
        graf = Grafana("Grafana\nPromQL 쿼리")

    with Cluster("장기 보관 · 수평 확장 (선택)", graph_attr=cluster("#fefce8", "#fde68a", dashed=True)):
        lt = [Mimir("Mimir"), Thanos("Thanos")]

    sd >> Edge(color=GRAY, style="dotted", label="대상 목록 자동 갱신") >> scrape
    # scrape는 Prometheus가 가져가는 pull이지만 배치를 위해 대상 → Prometheus 방향으로 그린다
    for t in (app, node, ksm, kubelet, pgw):
        t >> Edge(color=METRIC, label="pull") >> scrape
    rules >> Edge(color=BAD, label="firing alert") >> am
    tsdb >> Edge(color=METRIC, label="PromQL") >> graf
    tsdb >> Edge(color=METRIC, style="dashed", label="remote_write") >> lt
