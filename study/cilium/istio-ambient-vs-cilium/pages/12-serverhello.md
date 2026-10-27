# ServerHello — 서버가 고른 결과

```text
ServerHello
  supported_versions  TLS 1.3                 # 고른 버전
  cipher_suite        TLS_AES_128_GCM_SHA256  # 후보 중 하나만
  key_share           x25519 + 공개값 32B     # 서버 쪽 공개값
──────────────── 여기까지 평문 ────────────────
  {EncryptedExtensions} {Certificate} {Finished}
```

서버 공개값이 오면 양쪽 열쇠가 완성된다. 그래서 **그 다음 줄부터 암호화된다.**

<!--
ServerHello는 목록이 아니라 하나씩만 옵니다. 후보를 여러 개 받았으면 그중 하나만 골라 답해요.

key_share에 서버 쪽 공개값이 들어옵니다. 양쪽 공개값이 다 있으면 같은 열쇠를 계산할 수 있어요.

가운데 구분선을 봐주세요. ServerHello까지는 평문이고 그 다음부터 암호화됩니다. ServerHello 자체는 아직 평문이에요. 그림 그릴 때 자물쇠 안에 넣으면 틀립니다.

아래 중괄호로 묶인 게 암호화된 메시지입니다. 서버 인증서가 여기 들어갑니다. 그래서 지나가며 보는 사람은 어느 서비스 인증서인지 알 수 없습니다.
-->
