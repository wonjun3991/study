"""Metric · Log · Trace 텔레메트리 파이프라인 전체 구조도.

실행: python3 telemetry_pipeline.py  →  telemetry_pipeline.png
필요: graphviz (brew install graphviz), python graphviz 패키지
"""
from pathlib import Path

import graphviz

FONT = "Apple SD Gothic Neo"
METRIC, LOG, TRACE = "#0891b2", "#d97706", "#7c3aed"
ALL = f"{METRIC}:{LOG}:{TRACE}"  # 평행선 3개 = 세 신호가 함께 흐름

LAYER_STYLE = {
    "gen": "#f1f5f9",
    "collect": "#ecfeff",
    "store": "#fefce8",
    "view": "#f5f3ff",
}


def box(title: str, body: str, sub: str = "", fill: str = "white") -> str:
    """제목(굵게) + 본문 + 보조설명(회색) HTML 라벨."""
    sub_row = f'<TR><TD><FONT POINT-SIZE="11" COLOR="#64748b">{sub}</FONT></TD></TR>' if sub else ""
    return (
        f'<<TABLE BORDER="0" CELLPADDING="3" BGCOLOR="{fill}">'
        f'<TR><TD><B><FONT POINT-SIZE="15">{title}</FONT></B></TD></TR>'
        f'<TR><TD><FONT POINT-SIZE="12">{body}</FONT></TD></TR>'
        f"{sub_row}</TABLE>>"
    )


g = graphviz.Digraph("telemetry_pipeline", format="png")
g.attr(rankdir="LR", splines="spline", nodesep="0.35", ranksep="1.1", pad="0.4", dpi="160",
       fontname=FONT, label='<<B><FONT POINT-SIZE="24">Metric · Log · Trace 파이프라인</FONT></B>>',
       labelloc="t")
g.attr("node", shape="box", style="rounded,filled", fillcolor="white", color="#94a3b8",
       fontname=FONT, margin="0.15,0.08")
g.attr("edge", fontname=FONT, fontsize="11", penwidth="1.8", arrowsize="0.8")

# ① 생성 ---------------------------------------------------------------
with g.subgraph(name="cluster_gen") as c:
    c.attr(label='<<B>① 생성 (Instrumentation)</B>>', style="rounded,filled",
           fillcolor=LAYER_STYLE["gen"], color="#cbd5e1", fontsize="16")
    c.node("app_otel", box("애플리케이션 + OTel SDK", "metric · log · trace 생성",
                           "Python / Java / Go … (auto + manual 계측)"))
    c.node("app_prom", box("/metrics 엔드포인트", "Prometheus client 라이브러리",
                           "앱이 현재 값을 노출만 함"))
    c.node("app_stdout", box("stdout / stderr 로그", "→ /var/log/pods/*.log",
                             "컨테이너 런타임이 파일로 기록"))
    c.node("exporters", box("인프라 Exporter", "node-exporter · kube-state-metrics",
                            "kubelet(cAdvisor) · DB/Redis exporter"))

# ② 수집 · 가공 ----------------------------------------------------------
with g.subgraph(name="cluster_collect") as c:
    c.attr(label='<<B>② 수집 · 가공 (Collection)</B>>', style="rounded,filled",
           fillcolor=LAYER_STYLE["collect"], color="#a5f3fc", fontsize="16")
    c.node("otel_agent", box("OTel Collector (agent)", "receiver → processor → exporter",
                             "DaemonSet · 노드마다 1개 · k8s 메타데이터 부착"))
    c.node("otel_gw", box("OTel Collector (gateway)", "tail sampling · 라우팅 · 배치",
                          "Deployment · 백엔드 앞단 집결지"))
    c.node("scraper", box("Pull 수집기 (scrape)", "Prometheus · vmagent · Grafana Alloy",
                          "주기적으로 /metrics를 긁어옴"))
    c.node("shipper", box("로그 수집기 (tail)", "Fluent Bit · Vector · Alloy · Filebeat",
                          "파일을 따라 읽어 전송"))
    c.node("kafka", box("(선택) Kafka 버퍼", "대규모 로그 폭주 흡수"), style="rounded,dashed,filled")

# ③ 저장 · 쿼리 ----------------------------------------------------------
with g.subgraph(name="cluster_store") as c:
    c.attr(label='<<B>③ 저장 · 쿼리 (Backend)</B>>', style="rounded,filled",
           fillcolor=LAYER_STYLE["store"], color="#fde68a", fontsize="16")
    c.node("m_store", box("Metric TSDB", "Prometheus · VictoriaMetrics · Mimir · Thanos",
                          "쿼리: PromQL / MetricsQL"), color=METRIC, penwidth="2.5")
    c.node("l_store", box("Log 저장소", "Loki · VictoriaLogs (label/stream 인덱스)<br/>"
                          "Elasticsearch · OpenSearch (전문 검색 인덱스)",
                          "쿼리: LogQL / LogsQL / Lucene·ES|QL"), color=LOG, penwidth="2.5")
    c.node("t_store", box("Trace 저장소", "Tempo · Jaeger · Elastic APM",
                          "쿼리: TraceQL / trace_id 조회"), color=TRACE, penwidth="2.5")

# ④ 조회 · 시각화 · 알람 ------------------------------------------------
with g.subgraph(name="cluster_view") as c:
    c.attr(label='<<B>④ 조회 · 시각화 · 알람</B>>', style="rounded,filled",
           fillcolor=LAYER_STYLE["view"], color="#ddd6fe", fontsize="16")
    c.node("grafana", box("Grafana", "대시보드 · Explore",
                          "metric ↔ trace ↔ log 이동 (exemplar, trace_id)"))
    c.node("kibana", box("Kibana / OpenSearch Dashboards", "Elastic 계열 전용 UI"))
    c.node("alert", box("알람 엔진", "Alertmanager · vmalert · Grafana Alerting",
                        "rule 평가 → 그룹핑 · 억제 · 라우팅"))
    c.node("notify", box("알림 채널", "Slack · PagerDuty · 이메일"))

# 엣지 ------------------------------------------------------------------
g.edge("app_otel", "otel_agent", label="OTLP push", color=ALL)
g.edge("app_stdout", "otel_agent", label="filelog receiver", color=LOG, style="dashed")
g.edge("app_prom", "scraper", label="scrape (pull)", color=METRIC)
g.edge("exporters", "scraper", label="scrape (pull)", color=METRIC)
g.edge("app_stdout", "shipper", label="tail", color=LOG)

g.edge("otel_agent", "otel_gw", label="OTLP", color=ALL)
g.edge("shipper", "kafka", color=LOG, style="dashed")

g.edge("scraper", "m_store", label="remote_write", color=METRIC)
g.edge("otel_gw", "m_store", label="OTLP / remote_write", color=METRIC)
g.edge("otel_gw", "l_store", label="OTLP / push API", color=LOG)
g.edge("otel_gw", "t_store", label="OTLP", color=TRACE)
g.edge("shipper", "l_store", label="push", color=LOG)
g.edge("kafka", "l_store", color=LOG, style="dashed")

g.edge("m_store", "grafana", color=METRIC)
g.edge("l_store", "grafana", color=LOG)
g.edge("t_store", "grafana", color=TRACE)
g.edge("l_store", "kibana", color=LOG, style="dashed")
g.edge("t_store", "kibana", color=TRACE, style="dashed")
g.edge("m_store", "alert", label="alert rule", color=METRIC)
g.edge("l_store", "alert", label="log rule", color=LOG, style="dashed")
g.edge("alert", "notify", color="#475569")

# 범례 ------------------------------------------------------------------
g.node("legend", shape="plaintext", style="", label=(
    '<<TABLE BORDER="1" COLOR="#cbd5e1" CELLBORDER="0" CELLPADDING="4" BGCOLOR="white">'
    '<TR><TD COLSPAN="2"><B>범례</B></TD></TR>'
    f'<TR><TD><FONT COLOR="{METRIC}">━━━</FONT></TD><TD ALIGN="LEFT">Metric</TD></TR>'
    f'<TR><TD><FONT COLOR="{LOG}">━━━</FONT></TD><TD ALIGN="LEFT">Log</TD></TR>'
    f'<TR><TD><FONT COLOR="{TRACE}">━━━</FONT></TD><TD ALIGN="LEFT">Trace</TD></TR>'
    '<TR><TD>┄┄┄</TD><TD ALIGN="LEFT">선택 경로</TD></TR>'
    "</TABLE>>"))
g.edge("legend", "app_otel", style="invis")

out = Path(__file__).with_suffix("")
g.render(out, cleanup=True)
print(f"rendered: {out}.png")
