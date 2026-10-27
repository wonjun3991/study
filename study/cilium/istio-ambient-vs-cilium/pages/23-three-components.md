# 구성요소는 세 개

<div class="seq" data-seq="istio-cni-node\nDaemonSet\n파드를 메시에 등록|ztunnel\nDaemonSet\nL4 mTLS 전담|waypoint\nDeployment\nL7 — 선택" data-accent="gold|green|dim"></div>

**`istio-cni-node`는 이름과 달리 파드에 IP를 주지 않는다.** 하는 일이 두 개다.

① 기존 CNI 체인 **끝에 자기 바이너리를 얹는다** — 파드가 생길 때 호출되도록

② 상주 에이전트로 남아 파드 netns에 **리디렉션 규칙**을 넣고, ztunnel에 등록을 알린다

<!--
istio-cni-node는 이름 때문에 오해를 많이 삽니다. CNI가 들어가 있으니 Calico나 Cilium을 대체하는 것처럼 들리는데 아닙니다. 파드에 IP를 주지 않아요.

첫 번째 일. 노드에 뜨면 기존 CNI 설정 파일을 열어서 플러그인 목록 맨 끝에 자기 바이너리를 추가합니다. 그러면 앞으로 파드가 생길 때마다 자기가 호출됩니다. 왜 맨 끝이냐면, 주 CNI가 파드 IP를 먼저 만들어야 그 IP를 대상으로 규칙을 넣을 수 있으니까요.

두 번째 일. 프로세스가 죽지 않고 노드에 계속 남습니다. 파드가 생기면 그 파드의 네트워크 네임스페이스에 들어가 트래픽을 ztunnel로 돌리는 규칙을 넣고, ztunnel에게 이 파드가 등록됐다고 알립니다. 이 두 번째 역할이 본체입니다.

ztunnel은 Rust로 쓰인 L4 전용 프록시고 Envoy가 아닙니다. waypoint만 Envoy인데 안 붙여도 메시가 돌아갑니다. istio-cni-node는 사이드카 모드에서는 선택이지만 ambient에서는 없으면 아예 동작하지 않습니다.
-->
