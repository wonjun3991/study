# ① 규모를 넣어 보면 - 노드 50

| | Istio Ambient | Cilium |
|---|---|---|
| 노드 단위 | cni 50 + ztunnel 50 = **100** | agent 50 + envoy 50 = **100** |
| 그 외 | istiod 1~5 | operator 2 |
| **기본 합계** | **약 101~105** | **약 102** |
| 선택 추가 | waypoint - `Gateway`마다 1 | ztunnel-cilium 50 (**Beta**) |

**기본은 거의 같다.** 갈리는 건 아래 줄이다 - Ambient는 **L7을 켤 때** `Gateway` 수만큼, Cilium은 **워크로드 mTLS를 켤 때** 노드 수만큼 늘어난다.

<div class="src">Ambient 쪽 숫자에는 <b>주 CNI가 빠져 있다</b> - Cilium이든 Calico든 무언가는 깔아야 하고 그것도 DaemonSet이다. 지연·처리량은 여기서 말하지 않는다: 공개된 head-to-head 수치가 없고, Istio 2025 벤치마크의 Cilium은 <code>v1.16.6</code>으로 ztunnel 도입(1.19) 이전이다.</div>

<!--
숫자를 넣어 보겠습니다. 노드 50대 클러스터입니다.

첫 줄, 노드 단위. 양쪽 다 백 개입니다. Ambient는 cni와 ztunnel, Cilium은 에이전트와 envoy예요. 우연히 같습니다.

둘째 줄도 비슷합니다. istiod 몇 개 대 오퍼레이터 둘.

그래서 세 번째 줄, 기본 합계가 거의 같습니다. 백 개 남짓씩이에요. 여기까지는 차이가 없습니다.

갈리는 건 네 번째 줄입니다. 그런데 방향이 다릅니다.

Ambient는 L7을 켤 때 늘어납니다. Gateway를 몇 개 만드느냐에 달렸어요. 서비스마다 따로 두면 서비스 수만큼, 네임스페이스 공용으로 묶으면 네임스페이스 수만큼입니다.

Cilium은 워크로드 단위 mTLS를 켤 때 늘어납니다. 이건 DaemonSet이라 노드 수만큼, 즉 오십 개가 붙습니다. 그리고 Beta예요.

정리하면 Ambient는 L7 기능에 비용을 내고 Cilium은 워크로드 신원에 비용을 냅니다. 둘 다 켜면 둘 다 냅니다.

회색 글씨 두 가지. 하나, Ambient 쪽 숫자에는 주 CNI가 아직 안 들어 있습니다. 그걸 넣으면 Ambient가 더 많아집니다. 둘, 성능 수치는 말하지 않겠습니다. 공개된 맞대결 자료가 없고, 이스티오 벤치마크가 쓴 Cilium은 ztunnel 들어오기 전 버전입니다.
-->
