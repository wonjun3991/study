"""Kubernetes에서 Collector 배치: 노드마다 agent(DaemonSet) + 중앙 gateway(Deployment).

실행: python3 04_collector_k8s.py  →  04_collector_k8s.png
"""
from diagrams import Cluster, Diagram, Edge
from diagrams.custom import Custom
from diagrams.generic.storage import Storage
from diagrams.k8s.compute import Pod
from diagrams.k8s.controlplane import API
from diagrams.onprem.logging import Loki
from diagrams.onprem.monitoring import Prometheus
from diagrams.onprem.tracing import Tempo

from _style import (ALL, COLLECT, GEN, GRAY, LOG, METRIC, OTEL_ICON, STORE, TRACE, WHITE,
                    diagram_kwargs)

with Diagram("Kubernetes에서 Collector 배치: agent + gateway",
             **diagram_kwargs("04_collector_k8s", direction="LR", ranksep="1.3")):

    k8s_api = API("kube-apiserver\n(Pod 메타데이터 조회)")

    agents = []
    for n, apps in (("worker-1", ("gateway", "order")), ("worker-2", ("payment", "order"))):
        with Cluster(f"node: {n}", graph_attr=GEN):
            pods = [Pod(a) for a in apps]
            logs = Storage("/var/log/pods/*.log\n(stdout 로그 파일)")
            agent = Custom("otel-agent\n(DaemonSet)\nfile_log · k8s_attributes", OTEL_ICON)
            for p in pods:
                p >> Edge(color=f"{METRIC}:{TRACE}", label="OTLP\n(같은 노드)") >> agent
                p >> Edge(color=LOG, style="dashed") >> logs
            logs >> Edge(color=LOG, label="tail") >> agent
            agents.append(agent)

    with Cluster("otel-gateway (Deployment)", graph_attr=COLLECT):
        gw = Custom("batch · tail_sampling\n신호별 라우팅\n백엔드 인증 · 재시도", OTEL_ICON)

    with Cluster("백엔드", graph_attr=STORE):
        prom = Prometheus("Prometheus")
        loki = Loki("Loki")
        tempo = Tempo("Tempo")

    for a in agents:
        k8s_api >> Edge(color=GRAY, style="dotted", label="pod → 이름·ns·label") >> a
        a >> Edge(color=ALL, label="OTLP", penwidth="2.2") >> gw
    gw >> Edge(color=METRIC, label="metric") >> prom
    gw >> Edge(color=LOG, label="log") >> loki
    gw >> Edge(color=TRACE, label="trace") >> tempo
