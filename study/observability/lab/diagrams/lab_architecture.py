"""kind-observability 실습 환경 아키텍처 (실제 배포 기준).

실행: python3 lab_architecture.py  →  lab_architecture.png
"""
from pathlib import Path

import graphviz

FONT = "Apple SD Gothic Neo"
METRIC, LOG, TRACE, UI = "#0891b2", "#d97706", "#7c3aed", "#475569"
ALL = f"{METRIC}:{LOG}:{TRACE}"


def box(title: str, body: str = "", sub: str = "") -> str:
    rows = [f'<TR><TD><B><FONT POINT-SIZE="14">{title}</FONT></B></TD></TR>']
    if body:
        rows.append(f'<TR><TD><FONT POINT-SIZE="11">{body}</FONT></TD></TR>')
    if sub:
        rows.append(f'<TR><TD><FONT POINT-SIZE="10" COLOR="#64748b">{sub}</FONT></TD></TR>')
    return f'<<TABLE BORDER="0" CELLPADDING="2">{"".join(rows)}</TABLE>>'


g = graphviz.Digraph("lab_architecture", format="png")
g.attr(rankdir="LR", splines="spline", nodesep="0.3", ranksep="0.9", pad="0.4", dpi="160", fontname=FONT,
       labelloc="t", label='<<B><FONT POINT-SIZE="22">kind-observability 실습 아키텍처</FONT></B><BR/>'
                           '<FONT POINT-SIZE="12" COLOR="#64748b">control-plane 1 + worker 2 · namespace: demo / observability</FONT>>')
g.attr("node", shape="box", style="rounded,filled", fillcolor="white", color="#94a3b8", fontname=FONT,
       margin="0.12,0.06")
g.attr("edge", fontname=FONT, fontsize="10", penwidth="1.6", arrowsize="0.7")

g.node("user", box("Mac (localhost)", "브라우저", "kubectl port-forward"), shape="box", fillcolor="#f8fafc")

with g.subgraph(name="cluster_kind") as k:
    k.attr(label='<<B>kind cluster: observability</B>>', style="rounded", color="#334155", penwidth="2",
           fontsize="15")

    # demo namespace -----------------------------------------------------
    with k.subgraph(name="cluster_demo") as d:
        d.attr(label='<<B>ns: demo</B>  (image demo-app:0.1, FastAPI + OTel 자동 계측)>', style="rounded,filled",
               fillcolor="#f1f5f9", color="#cbd5e1", fontsize="13")
        d.node("loadgen", box("loadgen", "curl 루프 ~2 req/s", "curlimages/curl"))
        d.node("gateway", box("gateway", "GET /checkout", ":8000"))
        d.node("order", box("order", "POST /orders", "span reserve_inventory · demo.orders"))
        d.node("payment", box("payment", "POST /pay", "10% 1~2s 지연 · 5% 500"))
        d.node("podlogs", box("/var/log/pods/*.log", "stdout JSON (trace_id 포함)", "노드 파일시스템"),
               shape="note", fillcolor="#fffbeb", color=LOG)

    # observability namespace -------------------------------------------
    with k.subgraph(name="cluster_obs") as o:
        o.attr(label='<<B>ns: observability</B>>', style="rounded,filled", fillcolor="#f8fafc",
               color="#cbd5e1", fontsize="13")

        with o.subgraph(name="cluster_collect") as c:
            c.attr(label="수집 · 가공 (OTel Collector 0.161)", style="rounded,filled", fillcolor="#ecfeff",
                   color="#a5f3fc", fontsize="12")
            c.node("agent", box("otel-agent  ×2", "DaemonSet (worker 노드마다)",
                                "OTLP 4317 · file_log · k8s_attributes<br/>transform: JSON 파싱 → trace_id 승격"))
            c.node("gw", box("otel-gateway", "Deployment ×1", "memory_limiter · batch · 신호별 라우팅"))

        with o.subgraph(name="cluster_store") as s:
            s.attr(label="저장 · 쿼리", style="rounded,filled", fillcolor="#fefce8", color="#fde68a", fontsize="12")
            s.node("prom", box("Prometheus", "kps-kube-prometheus-stack-prometheus:9090",
                               "OTLP 수신 · remote_write 수신 · exemplar · 보존 2d"), color=METRIC, penwidth="2.2")
            s.node("loki", box("Loki 3.6", "loki:3100 (SingleBinary)", "/otlp · structured metadata · 보존 48h"),
                   color=LOG, penwidth="2.2")
            s.node("tempo", box("Tempo 2.9", "tempo:3200 / 4317", "metrics-generator: span-metrics · service-graphs"),
                   color=TRACE, penwidth="2.2")

        with o.subgraph(name="cluster_scrape") as e:
            e.attr(label="scrape 대상 (pull)", style="rounded,filled", fillcolor="#f0fdfa", color="#99f6e4",
                   fontsize="12")
            e.node("nodeexp", box("node-exporter ×3", "DaemonSet (모든 노드)"))
            e.node("ksm", box("kube-state-metrics", "K8s 오브젝트 상태"))
            e.node("kubelet", box("kubelet / cAdvisor", "컨테이너 CPU·메모리"))
            e.node("otelself", box("Collector 자체 metric", ":8888 (ServiceMonitor)"))

        with o.subgraph(name="cluster_view") as v:
            v.attr(label="조회 · 알람", style="rounded,filled", fillcolor="#f5f3ff", color="#ddd6fe", fontsize="12")
            v.node("grafana", box("Grafana", "grafana:80", "datasource: prometheus · loki · tempo<br/>exemplar · trace↔log 연결"))
            v.node("am", box("Alertmanager", "kps-kube-prometheus-stack-alertmanager"))
            v.node("operator", box("Prometheus Operator", "ServiceMonitor → scrape 설정 생성"),
                   style="rounded,dashed,filled")

# 요청 흐름 ------------------------------------------------------------
g.edge("loadgen", "gateway", label="HTTP", color=UI)
g.edge("gateway", "order", label="HTTP + traceparent", color=UI)
g.edge("order", "payment", label="HTTP + traceparent", color=UI)

# 텔레메트리 -----------------------------------------------------------
for svc in ("gateway", "order", "payment"):
    g.edge(svc, "agent", color=f"{METRIC}:{TRACE}", style="solid")
    g.edge(svc, "podlogs", color=LOG, style="dashed", arrowhead="none")
g.edge("podlogs", "agent", label="file_log (tail)", color=LOG)
g.edge("agent", "gw", label="OTLP gRPC", color=ALL)
g.edge("gw", "prom", label="OTLP/HTTP /api/v1/otlp", color=METRIC)
g.edge("gw", "loki", label="OTLP/HTTP /otlp", color=LOG)
g.edge("gw", "tempo", label="OTLP gRPC", color=TRACE)
g.edge("tempo", "prom", label="remote_write\ntraces_spanmetrics_*", color=METRIC, style="dashed")

for t in ("nodeexp", "ksm", "kubelet", "otelself"):
    g.edge("prom", t, color=METRIC, style="dashed", arrowhead="none", arrowtail="normal", dir="back")
g.edge("operator", "prom", label="설정", color=UI, style="dotted")

g.edge("prom", "grafana", color=METRIC)
g.edge("loki", "grafana", color=LOG)
g.edge("tempo", "grafana", color=TRACE)
g.edge("prom", "am", label="alert rule", color=METRIC)
g.edge("user", "grafana", label="port-forward 3000:80", color=UI, constraint="false")

g.node("legend", shape="plaintext", style="", label=(
    '<<TABLE BORDER="1" COLOR="#cbd5e1" CELLBORDER="0" CELLPADDING="3" BGCOLOR="white">'
    '<TR><TD COLSPAN="2"><B>범례</B></TD></TR>'
    f'<TR><TD BGCOLOR="{METRIC}" WIDTH="30"> </TD><TD ALIGN="LEFT">Metric</TD></TR>'
    f'<TR><TD BGCOLOR="{LOG}"> </TD><TD ALIGN="LEFT">Log</TD></TR>'
    f'<TR><TD BGCOLOR="{TRACE}"> </TD><TD ALIGN="LEFT">Trace</TD></TR>'
    f'<TR><TD BGCOLOR="{UI}"> </TD><TD ALIGN="LEFT">요청 / 조회</TD></TR>'
    '<TR><TD>- - -</TD><TD ALIGN="LEFT">pull(scrape) · 파생</TD></TR>'
    "</TABLE>>"))
g.edge("legend", "loadgen", style="invis")

out = Path(__file__).with_suffix("")
g.render(out, cleanup=True)
print(f"rendered: {out}.png")
