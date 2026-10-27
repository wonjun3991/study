# TLS → mTLS: 무엇이 추가되나

<div class="cmp"
     data-left-title="TLS — 서버만 인증"
     data-left="서버만 Certificate 제시|클라이언트는 검증만 한다|서버는 상대가 누구인지 모른다|앱 레벨 토큰·API 키로 따로 보완"
     data-right-title="mTLS — 상호 인증"
     data-right="서버가 CertificateRequest 를 추가|클라이언트도 Certificate + CertificateVerify|양쪽이 서로를 암호학적으로 확인|대신 인증서 배포·갱신 부담이 생긴다"></div>

<!--
웹 브라우징에서 쓰는 TLS는 한쪽만 인증합니다. 서버가 신분증을 보이고 브라우저가 확인합니다. 서버는 접속한 사람이 누군지 모릅니다. 그래서 로그인을 따로 합니다.
mTLS는 양쪽입니다. 서버가 CertificateRequest를 보내서 "너도 신분증 내라"고 요구하고, 클라이언트가 Certificate와 CertificateVerify를 보냅니다.
CertificateVerify가 핵심입니다. 인증서만 보내면 복사해서 쓸 수 있으니, 개인키로 지금까지의 핸드셰이크에 서명해서 "그 인증서의 개인키를 실제로 갖고 있다"를 증명합니다.
오른쪽 마지막 줄이 대가입니다. 클라이언트도 인증서를 가져야 하니, 그 인증서를 누가 만들어 어떻게 나눠주고 언제 갱신하느냐가 새 숙제로 생깁니다.
-->
