# waypoint — L7이 필요할 때만

<div class="seq" data-seq="출발지\nztunnel|waypoint\n(Envoy)|목적지\nztunnel|Pod B" data-accent="green|gold|green|cyan"></div>

**누가 waypoint로 보내나** — 파드 안 방화벽 규칙이 아니라 **출발지 ztunnel**이 정한다. 목적지에 waypoint가 붙어 있다는 걸 알고 그쪽으로 먼저 보낸다. 그래서 waypoint를 붙이거나 떼도 파드 안 설정은 건드리지 않는다.

**비용 두 가지** — 프록시를 지나는 횟수가 2회에서 **3회**로 늘고, waypoint는 별도 Deployment라 **다른 노드에 떠 있을 수 있어** 그 노드까지 다녀오는 왕복이 추가된다.

<!--
waypoint는 Envoy입니다. HTTP 라우팅, 리트라이, 타임아웃, L7 인가를 여기서 합니다.

첫 문단이 헷갈리기 쉬운 부분이라 풀어서 적었습니다. waypoint로 꺾는 주체가 누구냐는 얘기예요. 파드 안에 넣어둔 방화벽 규칙이 목적지를 바꾸는 게 아닙니다. 출발지 ztunnel이 "이 목적지에는 waypoint가 붙어 있네" 하고 알고 있어서, 목적지 파드로 바로 가지 않고 waypoint로 먼저 보냅니다.

이게 왜 좋냐면, waypoint를 새로 붙이거나 떼어낼 때 파드 안 설정을 다시 안 건드려도 됩니다. 판단이 ztunnel 쪽에 있으니까요.

두 번째 문단이 비용입니다. 하나, 앞에서 프록시를 두 번 지난다고 했는데 waypoint가 끼면 세 번이 됩니다. 둘, waypoint는 DaemonSet이 아니라 별도 Deployment입니다. 출발지나 목적지와 다른 노드에 떠 있을 수 있어요. 그러면 그 노드까지 갔다 오는 네트워크 왕복이 하나 더 붙습니다.

그래서 필요한 서비스에만 붙이라고 안내합니다. 전 네임스페이스에 다 붙이면 사이드카보다 무거워질 수 있습니다.
-->
