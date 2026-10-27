# ① 실제로 뜨는 리소스 - Istio Ambient

| 오브젝트 | 종류 | 개수 |
|---|---|---|
| `istiod` | **Deployment** | 1 (HPA 1~5) |
| `istio-cni-node` | **DaemonSet** | 노드 수 |
| `ztunnel` | **DaemonSet** | 노드 수 |
| `waypoint` | **Deployment** | **`Gateway` 리소스마다 1** (아래 참조) |

**waypoint는 DaemonSet이 아니다.** `Gateway` 하나당 Deployment 하나 + Service·HPA·PDB. istiod가 `Gateway`를 보고 자동으로 만든다.

붙이는 **단위는 선택**이다 — 네임스페이스에 공용 하나로 둘 수도, 서비스·서비스어카운트마다 따로 둘 수도 있다.

<div class="src">여기서 <b>Gateway</b>는 <b>쿠버네티스 Gateway API</b>의 표준 리소스(<code>gateway.networking.k8s.io/v1</code>)다. <code>gatewayClassName: istio-waypoint</code>로 하나 만들면 istiod가 그것을 보고 Deployment를 찍어낸다(<code>istioctl waypoint apply</code>가 대신 만들어 준다).<br><b>이름이 겹친다</b> — Istio 고유 API인 <code>networking.istio.io/v1 Gateway</code>(ingress·egress 게이트웨이 설정, <b>지금도 지원되는 안정 API</b>)와는 <b>별개 리소스</b>다. 그쪽은 메시 경계에 놓이고 waypoint는 <b>메시 안쪽</b>에 놓인다.</div>

<!--
실제로 클러스터에 뭐가 뜨는지 봅니다. 종류 칸을 봐 주세요. DaemonSet이냐 Deployment냐가 개수와 직결됩니다.

istiod는 Deployment 하나입니다. 오토스케일이 기본으로 켜져 있어서 부하에 따라 다섯 개까지 늘어납니다.

istio-cni-node와 ztunnel은 DaemonSet입니다. 노드마다 하나씩이니까 노드가 백 대면 각각 백 개예요.

마지막 줄이 오해가 많은 부분이라 굵게 적었습니다. waypoint는 DaemonSet이 아닙니다. Deployment입니다. Gateway 리소스를 하나 만들면 istiod가 그걸 보고 Deployment를 하나 만들어 줍니다. Service랑 오토스케일러랑 PDB까지 세트로 딸려 옵니다.

그러니까 개수가 노드 수에 비례하지 않습니다. Gateway 리소스를 몇 개 만드느냐에 달렸어요.

여기서 Gateway가 뭔지 짚고 가겠습니다. 회색 글씨 보시면 됩니다. 쿠버네티스 Gateway API의 표준 리소스입니다. Ingress를 대체하려고 나온 그거예요. gatewayClassName을 istio-waypoint로 줘서 하나 만들면 istiod가 그걸 보고 Deployment를 찍어냅니다. 보통은 손으로 안 쓰고 istioctl waypoint apply 명령이 대신 만들어 줍니다.

주의하실 게 이름이 겹칩니다. Istio에는 자체 Gateway API가 따로 있어요. networking.istio.io 쪽이고 ingress와 egress 게이트웨이를 설정합니다. 이건 폐기된 게 아니라 지금도 지원되는 안정 API예요. 쿠버네티스 Gateway API와 별개로 존재하는 겁니다.

둘은 이름만 같고 다른 리소스입니다. Istio 쪽 Gateway는 메시 경계에 놓이고, waypoint는 메시 안쪽에 놓여서 서비스 사이 트래픽을 처리합니다.

그리고 붙이는 단위를 고를 수 있습니다. 네임스페이스에 공용으로 하나만 둘 수도 있고 서비스마다 따로 둘 수도 있어요. 격리를 원하면 잘게, 파드 수를 아끼려면 굵게 갑니다. 다음 장 숫자는 서비스마다 따로 둔 경우를 가정한 겁니다.
-->
