"""5개 signal이 어떻게 서로 연결되는가 + 장애 분석 순서.

실행: python3 05_signal_correlation.py  →  05_signal_correlation.png
"""
from diagrams import Cluster, Diagram, Edge
from diagrams.custom import Custom
from diagrams.onprem.client import User
from diagrams.onprem.logging import Loki
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.onprem.tracing import Tempo

from _style import (COLLECT, GEN, GRAY, LOG, METRIC, OTEL_ICON, PROFILE, REQ, STORE, TRACE, VIEW,
                    diagram_kwargs)

with Diagram("Signal 연결: 무엇이 → 어디서 → 왜 → 어느 함수가",
             **diagram_kwargs("05_signal_correlation", direction="LR", ranksep="1.4")):

    with Cluster("모든 신호에 공통으로 붙는 맥락", graph_attr=COLLECT):
        res = Custom("Resource\nservice.name · k8s.pod.name\nhost.name", OTEL_ICON)
        bag = Custom("Baggage\ntenant.id=acme\n(헤더로 전파)", OTEL_ICON)

    with Cluster("① Metric: 무엇이 이상한가", graph_attr=STORE):
        m = Prometheus("checkout p99 3s\n에러율 5%")
    with Cluster("② Trace: 어디서 느린가", graph_attr=STORE):
        t = Tempo("payment → DB span\n2.8s")
    with Cluster("③ Log: 왜 그런가", graph_attr=STORE):
        l = Loki("\"connection pool\nexhausted\"")
    with Cluster("④ Profile: 어느 함수가", graph_attr=STORE):
        p = Custom("acquire_conn()\nlock 경합 CPU 40%", OTEL_ICON)

    with Cluster("조회", graph_attr=VIEW):
        g = Grafana("Grafana\n클릭으로 신호 간 이동")
        sre = User("엔지니어")

    m >> Edge(color=METRIC, label="exemplar\n(trace_id)", penwidth="2.5") >> t
    t >> Edge(color=LOG, label="trace_id · span_id", penwidth="2.5") >> l
    t >> Edge(color=PROFILE, label="span_id", penwidth="2.5", style="dashed") >> p

    for x in (m, t, l, p):
        res >> Edge(color=GRAY, style="dotted") >> x
    bag >> Edge(color=GRAY, style="dotted", label="attribute로 복사") >> t

    sre >> Edge(color=REQ, label="알람 수신") >> g
    g >> Edge(color=REQ, style="dashed") >> m
