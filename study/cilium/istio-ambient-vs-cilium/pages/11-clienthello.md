# ClientHello — 실제로 나가는 내용

```text
ClientHello                                  # 전체가 평문
  supported_versions  TLS 1.3, TLS 1.2       # 쓸 수 있는 버전
  cipher_suites       TLS_AES_128_GCM_SHA256 # 암호 방식 후보
  key_share           x25519 + 공개값 32B    # 키 만들 그룹 + 내 공개값
  server_name         api.example.com        # 접속할 도메인
  alpn                h2, http/1.1           # 그 위에서 쓸 프로토콜
```

`server_name`과 `alpn`이 **평문으로 그대로 보인다**는 걸 여기서 확인할 수 있다.

<!--
실제로 와이어에 나가는 걸 줄여 적었습니다.

key_share에 x25519라는 그룹 이름과 32바이트 공개값이 들어가 있어요. 앞 장에서 본 그 공개값입니다.

server_name을 보세요. api.example.com이 그냥 보이죠. 서버가 인증서를 고르려면 어느 도메인인지 먼저 알아야 하니 어쩔 수 없습니다.

alpn에 h2가 있는데, 뒤에서 ztunnel이 이걸 h2로 고정한다는 얘기가 나올 때 이 줄입니다.

맨 윗줄 주석이 중요합니다. 전부 평문이에요. 열쇠를 맞추려고 보내는 첫 메시지니까 아직 감쌀 열쇠가 없습니다.
-->
