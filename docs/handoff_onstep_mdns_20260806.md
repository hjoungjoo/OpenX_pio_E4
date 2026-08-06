# Handoff: OnStep mDNS 멀티캐스트 무응답 (mfoozoo.local 검색 불가)

작성: 2026-08-06, PiFinder(mfpi4) 쪽 진단 세션에서 인계.
대상: OnStep 펌웨어를 다루는 다음 에이전트.

## 한 줄 요약

OnStep 컨트롤러(`mfoozoo`, OnStepX **10.28q**)의 mDNS 응답기는 정상 동작하지만
(이름·A 레코드 보유, 유니캐스트 질의 응답), **멀티캐스트 mDNS 질의에는 전혀
응답하지 않아** 모든 클라이언트(PC/폰/Pi)에서 `mfoozoo.local` 이름 검색이
실패한다. 유력 원인은 ESP 계열 WiFi **modem sleep(절전)이 멀티캐스트 프레임을
수신하지 못하는 것** — 펌웨어에서 WiFi 절전 해제 여부를 확인·수정해야 한다.

## 실측 근거 (2026-08-06, PiFinder Pi에서 측정)

| 검사 | 결과 |
|---|---|
| `getent hosts mfoozoo.local` (avahi/NSS 표준 경로) | 실패 (exit 2) |
| 멀티캐스트 mDNS A 질의 → `224.0.0.251:5353`, 5회 반복 | **0/5 무응답** |
| **유니캐스트** mDNS A 질의 → `192.168.7.100:5353` 직접 | **응답** — `mfoozoo.local → 192.168.7.100` A 레코드(47바이트) 반환 |
| TCP 9999 (OnStep 명령 포트) | 열림 |
| TCP 9998 (진단용 포트) LX200 `:GVP#`/`:GVN#` | `On-Step` / `10.28q` |

장치 정보: IP `192.168.7.100` (홈 WiFi STA, DHCP), MAC `68:fe:71:a9:fe:90`.

### 네트워크(공유기) 혐의 배제 근거

같은 AP에 붙은 PC와 Pi(mfpi4) 사이의 mDNS는 정상 동작한다(PC가
`mfpi4.local`을 풀어 접속함). 즉 AP는 STA 간 멀티캐스트를 전달하고 있고,
OnStep만 멀티캐스트 질의를 받지 못하거나 무시한다. IGMP 스누핑 등 공유기
문제였다면 유니캐스트 응답기가 살아있는 지금 패턴과 들어맞지 않는다.

## 펌웨어에서 확인할 것 (우선순위순)

1. **WiFi 절전(modem sleep) 해제 여부** — 핵심 용의자.
   - WiFi를 제공하는 주체부터 특정: OnStepX 내장 ESP32 WiFi인지, 별도
     SWS(Smart Web Server) 애드온(ESP8266/ESP32)인지.
   - 해당 코드에서 `WiFi.setSleep(false)` (Arduino) 또는
     `esp_wifi_set_ps(WIFI_PS_NONE)` (ESP-IDF) 호출 여부 확인.
     절전이 켜져 있으면 DTIM 이후 멀티캐스트 프레임이 유실되어, 응답기는
     살아 있어도 질의 자체를 못 받는다 — 지금 증상과 정확히 일치.
2. mDNS 라이브러리의 멀티캐스트 그룹 가입(IGMP join) 여부 — 절전이 이미
   꺼져 있다면 이쪽. 유니캐스트에 답하는 걸 보면 responder 자체는 살아 있음.
3. **확인 불필요한 것**: `MDNS_SERVER` on/off, 호스트네임 설정 — 이름
   `mfoozoo`와 A 레코드가 이미 정확히 서빙되고 있으므로 설정 자체는 정상.

참고: 같은 메커니즘(WiFi 절전 → 멀티캐스트 유실)을 PiFinder Pi 쪽에서도
전날 확인·수정했다(brcmfmac power save; MF_PiFinder 커밋 `633488e7`).
그 건과 이 건은 별개 장치의 동일 계열 문제다.

## 수정 후 검증 절차 (PiFinder Pi에서 실행)

```bash
# 1) 표준 경로 해석 — 성공하면 IP가 출력됨
getent hosts mfoozoo.local

# 2) 멀티캐스트 응답률 반복 측정 (5회)
python3 - <<'EOF'
import socket, struct, time
def build(name):
    q = b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\x00"
    return struct.pack(">HHHHHH", 0, 0, 1, 0, 0, 0) + q + struct.pack(">HH", 1, 1)
hits = 0
for i in range(5):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(2)
    s.sendto(build("mfoozoo.local"), ("224.0.0.251", 5353))
    try:
        d, a = s.recvfrom(1024); hits += 1; print(f"try {i+1}: {a[0]}")
    except socket.timeout:
        print(f"try {i+1}: no answer")
    s.close(); time.sleep(0.5)
print(f"multicast: {hits}/5")
EOF
```

기준: `getent` 성공 + 멀티캐스트 5/5(최소 4/5) 응답이면 해결로 판정.
절전 해제 트레이드오프: ESP 소비 전류가 수십 mA 증가할 수 있음 — 배터리
운용이면 사용자에게 고지.

## 현재 운용 상태 (수정 전 워크어라운드)

- PiFinder INDI 마운트 주소는 IP `192.168.7.100` 사용 중 — 이름 해석과
  무관하게 동작하므로 펌웨어 수정과 독립적으로 유지해도 됨.
- 공유기에서 MAC `68:fe:71:a9:fe:90`에 DHCP 예약 권장(미적용 상태로 인계).
- INDI 주소 전달 경로는 호스트네임도 지원함이 확인됨(형식 제한 없음):
  `sys_utils.apply_indi_onstep_connection` → INDI `DEVICE_ADDRESS.ADDRESS` →
  드라이버 `gethostbyname()`. 펌웨어가 고쳐지면 `mfoozoo.local` 입력도 가능.

## 주의사항

- 진단 시 LX200 질의는 **9998 포트**를 사용할 것(9999는 드라이버 명령
  포트 — 운용 중 간섭 방지). 근거: 기존 세션 실측 관행.
- OnStep 웨지/GoTo 관련 별개 이슈 이력이 있음 — 이 인계 범위 아님.
  필요 시 `PiFinder_data/logs/handoff_goto_20260803.md` 참조.

## Suggested skills

- 이 인계는 **OnStep 펌웨어 저장소** 작업이라 PiFinder 저장소 스킬
  (`pifinder-remote`, `docs`, `i18n` 등)은 해당 없음.
- 다음 에이전트가 PiFinder 환경에서 검증까지 수행한다면: 위 "수정 후 검증
  절차"의 셸 명령만으로 충분하며 별도 스킬 불필요.
- 작업을 다시 다른 에이전트로 넘길 땐 PiFinder 저장소의 `handoff` 스킬 사용.
