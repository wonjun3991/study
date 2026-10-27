# istiod → ztunnel: 전송은 xDS, 타입은 전용

<div class="seq" data-seq="istiod|:15012\nxDS over gRPC|istio.workload.Address\nistio.security.Authorization" data-accent="cyan|gold|green"></div>

공식 표현은 *"a simplified set of resources are used in the **xDS APIs**"* — xDS를 안 쓰는 것이 아니라 **Envoy 타입 대신 Istio 전용 타입 2개**를 쓴다. 인증서도 같은 연결로 받는다.

<!--
여기도 정확하게 말해야 하는 지점입니다.
"ztunnel은 표준 xDS를 안 쓴다"고 말하면 공식 문서와 충돌합니다. 문서는 "xDS API에서 단순화된 리소스 집합을 쓴다"고 씁니다. 전송 프로토콜은 xDS 그대로입니다. 다른 건 실려오는 리소스 타입입니다.
사이드카 Envoy는 LDS, CDS, RDS, EDS를 받습니다. ztunnel은 두 타입만 받습니다. istio.workload.Address가 파드와 서비스 목록입니다. IP, SPIFFE 신원, 어느 노드에 있는지, waypoint가 붙어 있는지가 들어갑니다. istio.security.Authorization이 L4 인가 정책입니다.
재밌는 게 PeerAuthentication은 그대로 안 옵니다. istiod가 네임스페이스와 워크로드 정책을 합쳐 유효 정책을 계산한 다음 Authorization으로 변환해 보냅니다. 판단은 컨트롤 플레인에서 끝납니다.
그리고 인증서도 같은 연결로 받습니다. 별도 채널이 아닙니다.
받지 않는 것도 알아두세요. VirtualService, DestinationRule, L7 정책은 안 옵니다. waypoint 몫입니다.
-->
