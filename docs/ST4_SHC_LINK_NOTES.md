# ST4 SHC 링크 끊김 분석 및 완화

작성일: 2026-08-10
빌드 환경: `onstepx_esp32_mf_oozoo_e4`

## 증상

ST4 포트로 연결한 SHC(Smart Hand Controller)의 연결이 자주 끊어지고,
끊어진 뒤 재접속까지 수 초가 걸린다.

## 배경

이 시스템은 이미 SerialST4 비트뱅 링크의 EMI 문제 이력이 있다
(커밋 `df38dcd` "Reject noise-induced SHC guide commands", 2026-07-12).
고토/추적 중 노이즈 바이트가 패리티를 통과해 가이드 명령으로 오인되는
문제였고, 이번 끊김도 같은 노이즈의 다른 증상으로 판단한다.

하드웨어 취약 요인:

- ST4 입력(GPIO23 데이터 수신, GPIO5 톤)이 ESP32 내부 풀업(약 45kΩ)에만
  의존한다 (`ST4_INTERFACE_INIT` = `INPUT_PULLUP`).
- ST4 핀(GPIO 5/18/19/23)이 스테퍼 배선, 듀히터 PWM(AUX5/6 = GPIO2/4)과
  인접해 크로스토크에 노출된다.

## 끊김 메커니즘 (펌웨어 분석)

### 경로 1 — 톤 감지 실패로 마스터가 강제 해제

- SHC는 RA+ 라인(GPIO5)에 12.5Hz 사각파(톤, 반주기 40ms)를 계속 보낸다.
- OnStepX는 톤이 `ST4_SHC_TONE_LOSS_MS` 동안 사라지면 SHC 링크를 해제한다
  (`src/telescope/mount/st4/St4.cpp`).
- 톤 판정은 `Button::hasTone()`이 펄스 폭 이동평균(EMA)이 40±7ms 안에
  있는지로 결정하는데, EMA 갱신에 디바운스가 없어 raw 상태 변화가 전부
  반영됐다 (`src/lib/pushButton/PushButton.cpp`). 노이즈 글리치가 짧은
  펄스를 만들면 EMA가 40ms 밖으로 밀려나 톤 인식이 깨지고, 타임아웃 후
  링크가 해제된다.

### 경로 2 — start-bit 프레임 오류 반복으로 통신 블랙아웃

- 데이터/클럭 라인 노이즈로 start-bit 프레임 오류가 나면 마스터는
  통신을 멈추고 재동기화를 기다린다 (`src/lib/serial/Serial_ST4_Master.cpp`).
- 기존 대기 시간이 1000ms로 고정돼 있어, 노이즈가 연달아 오면 1초
  블랙아웃이 반복되고 SHC 쪽에서 링크가 죽었다고 판단해 접속을 포기한다.
- 슬레이브는 클럭 간격이 100ms(`ST4_MAX_BIT_TIME`)를 넘으면 다음 클럭
  에지에서 프레임 인덱스를 리셋하므로 (`src/lib/serial/Serial_ST4_Slave.cpp`),
  재동기화에는 100ms를 조금 넘는 대기면 충분하다.

### 재접속이 느린 이유

한 번 끊기면 재접속 시 양쪽 라인의 톤 EMA(가중치 1/50)가 다시 40ms로
수렴해야 해서 5~10초가 걸린다. 이번 변경으로 끊김 빈도 자체를 줄인다.

## 적용한 완화 3종 (2026-08-10)

| 파일 | 변경 |
| --- | --- |
| `Config.h` | `ST4_SHC_TONE_LOSS_MS`를 4000으로 오버라이드 (기본 1500) |
| `src/lib/serial/Serial_ST4_Master.cpp` | start 오류 백오프 1000ms → `ST4_START_ERROR_RESYNC_MS`(기본 250ms) 매크로화 |
| `src/lib/pushButton/PushButton.h` | `TONE_GLITCH_FILTER_MS`(25ms) 정의 추가 |
| `src/lib/pushButton/PushButton.cpp` | 25ms 미만 펄스는 EMA에서 제외 (글리치 필터) |

각 항목의 근거:

1. **톤 손실 타임아웃 4000ms**: 노이즈 버스트 동안 톤 인식이 일시적으로
   깨져도 링크를 유지한다. `St4.cpp`의 `#ifndef` 가드 덕에 Config.h에서
   바로 오버라이드된다.
2. **start 오류 백오프 250ms**: 슬레이브 비트 타임아웃(100ms)보다 충분히
   길어 재동기화가 보장되고, 기존 1000ms 대비 복구가 4배 빨라 SHC가
   링크를 포기하기 전에 통신이 재개된다.
3. **톤 글리치 필터 25ms**: 톤 반주기 40ms는 약 10ms(St4Mntr 주기)로
   샘플링되므로 정상 펄스는 30ms 이상으로 측정된다. 글리치로 쪼개진
   10~20ms 조각을 EMA에서 제외해 톤 평균 오염을 막는다. 상태 전이 자체
   (`stableStartMs` 리셋)는 유지되므로 버튼 디바운스/더블클릭 판정과
   톤 정지 감지(3초 안정 시 EMA를 2000ms로 밀어내는 경로)는 영향이 없다.
   `avgPulseDuration`은 `hasTone()`/`toneFreq()`에서만 쓰이고 `toneFreq()`는
   호출처가 없어 부작용 범위가 톤 감지에 한정된다.

## 검증

- `platformio run -e onstepx_esp32_mf_oozoo_e4` 빌드 성공
  (RAM 19.3%, Flash 39.1%, 2026-08-10).
- 실기 확인 항목:
  1. SHC 연결 유지 시간이 늘어나는지 (특히 슬루/듀히터 동작 중).
  2. 톤 4초 상실 시 정상적으로 링크 해제되는지 (SHC 케이블 분리 테스트).
  3. 가이드 버튼 및 alt 모드(버튼 2초 홀드) 동작이 기존과 같은지.

## 남은 권장 사항 (하드웨어, 근본 대책)

1. 컨트롤러 쪽 ST4 신호 라인 4개에 외부 풀업 2.2k~4.7kΩ(3.3V) 추가 —
   특히 GPIO23(데이터 수신), GPIO5(톤).
2. ST4 케이블을 짧고 차폐된 것으로 교체, 모터 케이블과 분리 배선,
   페라이트 코어 장착.
3. SHC 5V 전원 전압 강하/커넥터 접촉 확인 (브라운아웃 → SHC 리셋 → 끊김).

## 진단 방법

`Extended.config.h`의 `DEBUG`를 `ON`으로 하고 시리얼(460800)에서 끊김
순간의 메시지로 경로를 구분한다:

- `WRN: SerialST4.poll(), frame/start error` 연발 → 경로 2 (데이터 라인 노이즈)
- 오류 없이 `MSG: SerialST4, deactivated`만 출력 → 경로 1 (톤 라인 노이즈)
  또는 SHC 전원/리셋
