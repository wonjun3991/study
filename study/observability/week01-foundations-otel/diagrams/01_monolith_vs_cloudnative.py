"""배경: 모놀리식 → 클라우드 네이티브로 오면서 관측이 어려워진 이유.

실행: python3 01_monolith_vs_cloudnative.py  →  01_monolith_vs_cloudnative.png
"""
from diagrams import Cluster, Diagram, Edge
from diagrams.k8s.compute import Pod
from diagrams.onprem.client import User
from diagrams.onprem.compute import Server
from diagrams.onprem.database import Postgresql
from diagrams.onprem.queue import Kafka

from _style import BAD, GEN, REQ, WARN, WHITE, diagram_kwargs

with Diagram("왜 관측이 어려워졌나: 모놀리식 vs 클라우드 네이티브",
             **diagram_kwargs("01_monolith_vs_cloudnative", direction="LR")):

    with Cluster("예전: 모놀리식 + 고정 서버", graph_attr=GEN):
        u1 = User("사용자")
        mono = Server("app-01\n(오래 떠 있는 서버)\nssh 접속 → 로그 파일 확인")
        db1 = Postgresql("DB")
        u1 >> Edge(color=REQ, label="요청 1개 = 프로세스 1개") >> mono >> Edge(color=REQ) >> db1

    with Cluster("지금: 마이크로서비스 + Kubernetes", graph_attr=WARN):
        u2 = User("사용자")
        with Cluster("수시로 생성 · 삭제되는 Pod (오토스케일 · 재배포)", graph_attr=WHITE):
            gw = Pod("gateway\n×3")
            order = Pod("order\n×5")
            pay = Pod("payment\n×2 → 4")
            stock = Pod("inventory\n×2")
        q = Kafka("이벤트 큐")
        db2 = Postgresql("DB ×N")
        ext = Server("외부 PG API")

        u2 >> Edge(color=REQ) >> gw
        gw >> Edge(color=REQ) >> order
        order >> Edge(color=REQ) >> pay
        order >> Edge(color=REQ) >> stock
        order >> Edge(color=REQ, style="dashed") >> q
        pay >> Edge(color=BAD, label="어디서 느려졌지?") >> ext
        stock >> Edge(color=REQ) >> db2

    db1 >> Edge(style="invis") >> u2  # 예전 → 지금 순서로 왼쪽부터 배치
