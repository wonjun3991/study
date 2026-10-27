# ② 같은 L4·L7, 다른 뜻

<div class="cmp"
     data-left-title="Cilium (ztunnel 없이)"
     data-left="정책 판정 = 숫자 CiliumIdentity (라벨에서 파생)|커널 eBPF 에서 판정|cilium-envoy 도 숫자 ID 로 매칭|인증서는 k8s Secret 에서 SDS 로"
     data-right-title="Istio Ambient"
     data-right="정책 판정 = SPIFFE 신원 (ns/sa)|유저스페이스 ztunnel 에서 판정|IP 기반 (ipBlocks) 도 쓸 수 있다|L7 은 waypoint - 붙인 범위만큼"></div>

**L7** - 차이는 성능이 아니라 **격리 범위**다. 노드 Envoy는 그 노드의 L7이 한곳에 모이고, waypoint는 붙인 범위만큼 나뉜다.

<div class="src">예외 하나 - <b>mutual authentication</b>은 SPIRE 기반이다. 다만 <b>1.19부터 기본 꺼짐 · 1.20 deprecated</b>(1.21 제거 예정)이고, 핸드셰이크는 Envoy가 아니라 <b>cilium-agent</b>가 노드 간 4250으로 한다. 신원도 <code>spiffe://.../identity/&lt;숫자&gt;</code> - 숫자 identity를 URI로 감싼 것이지 <code>ns/sa</code> 워크로드 신원이 아니다.</div>

<!--
둘째입니다. 양쪽 다 L4 정책, L7 정책이라는 말을 쓰는데 뜻이 다릅니다.

왼쪽은 ztunnel을 켜지 않은 기본 Cilium입니다. 정책 판정 근거가 숫자 identity예요. 파드 라벨을 모아서 숫자 하나를 부여하고, 정책은 그 숫자로 매칭합니다.

여기서 질문이 나올 수 있습니다. L7은 Envoy가 하는데 Envoy는 SPIFFE 쓰지 않느냐. 안 씁니다. cilium-envoy가 받는 정책 규칙을 열어 보면 필드 이름부터 remote_policies이고 타입이 숫자 배열이에요. 상대가 누구인지는 소스 IP로 숫자 identity를 역조회해서 정합니다. 인증서를 검증하는 게 아닙니다.

인증서를 아예 안 쓰는 건 아니에요. TLS Visibility나 Ingress에서 씁니다. 그런데 그 인증서는 쿠버네티스 Secret에 넣어둔 걸 가져다 쓰는 거지 SPIFFE가 아닙니다. 표 왼쪽 마지막 두 줄이 그 얘기입니다.

오른쪽 Ambient는 상대 인증서의 SPIFFE 신원이 그대로 정책 판정 근거가 됩니다. 물론 IP 조건도 쓸 수 있어요. AuthorizationPolicy는 ipBlocks도 지원하니까 신원만 쓴다는 뜻은 아닙니다.

L7 얘기는 격리 범위입니다. Cilium은 노드마다 Envoy 하나라 그 노드 L7이 한곳에 모입니다. 한 서비스에 몰리면 같은 노드의 다른 서비스가 영향을 받아요. Ambient의 waypoint는 붙인 범위만큼 나뉩니다.

맨 아래 회색 글씨가 예외입니다. Cilium에도 SPIFFE를 쓰는 기능이 하나 있어요. mutual authentication입니다. 그런데 세 가지 단서가 붙습니다.

하나, 1.19부터 기본으로 꺼져 있고 1.20에서 deprecated 됐습니다. 1.21에서 제거될 예정이에요. 공식 안내가 대신 ztunnel을 쓰라고 합니다.

둘, 핸드셰이크를 하는 게 Envoy가 아닙니다. cilium-agent가 상대 노드의 4250 포트로 붙어서 대역 외로 mTLS를 맺습니다. 트래픽 경로 밖에서 하는 거예요.

셋, 신원 형식이 다릅니다. spiffe 슬래시 identity 슬래시 숫자입니다. Cilium 숫자 identity를 URI로 감싼 것뿐이에요. Istio식으로 네임스페이스와 서비스어카운트가 들어가는 워크로드 신원이 아닙니다.
-->
