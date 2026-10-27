"""week01 다이어그램 공용 스타일 (lab/diagrams와 같은 색·폰트)."""
from pathlib import Path

import diagrams

HERE = Path(__file__).parent
OTEL_ICON = str(HERE.parent.parent / "lab" / "diagrams" / "icons" / "opentelemetry.png")
K8S_RES = Path(diagrams.__file__).parent.parent / "resources" / "k8s"

FONT = "Apple SD Gothic Neo"
METRIC, LOG, TRACE, PROFILE = "#0891b2", "#d97706", "#7c3aed", "#db2777"
REQ, GRAY, BAD = "#64748b", "#94a3b8", "#dc2626"
ALL = f"{METRIC}:{LOG}:{TRACE}"

GRAPH = {"fontname": FONT, "fontsize": "26", "labelloc": "t", "pad": "0.5", "nodesep": "0.6",
         "ranksep": "1.1", "dpi": "150", "splines": "spline"}
NODE = {"fontname": FONT, "fontsize": "13"}
EDGE = {"fontname": FONT, "fontsize": "12", "penwidth": "1.8"}


def cluster(fill: str, border: str, dashed: bool = False) -> dict:
    return {"bgcolor": fill, "pencolor": border, "fontname": FONT, "fontsize": "16",
            "style": "rounded,dashed" if dashed else "rounded", "margin": "18"}


# 레이어별 배경색 (telemetry_pipeline.py와 동일 계열)
GEN = cluster("#f1f5f9", "#cbd5e1")
COLLECT = cluster("#ecfeff", "#a5f3fc")
STORE = cluster("#fefce8", "#fde68a")
VIEW = cluster("#f5f3ff", "#ddd6fe")
WARN = cluster("#fef2f2", "#fecaca")
WHITE = cluster("#ffffff", "#e2e8f0")


def diagram_kwargs(name: str, direction: str = "LR", **graph) -> dict:
    return {"filename": str(HERE / name), "outformat": "png", "show": False, "direction": direction,
            "graph_attr": {**GRAPH, **graph}, "node_attr": NODE, "edge_attr": EDGE}
