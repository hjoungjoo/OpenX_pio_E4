# 업스트림 동기화 기록

이 문서는 원본 저장소(hjd1964/OnStepX)와의 동기화 상태를 기록하고,
추후 업스트림 비교/반영 작업 시 참고하는 기준 문서다.

최종 갱신일: 2026-10-10

## 저장소 구조

- 원본(업스트림): https://github.com/hjd1964/OnStepX — 리모트 이름 `upstream`
- 로컬(오리진): https://github.com/hjoungjoo/OpenX_pio_E4 — 리모트 이름 `origin`
- 로컬 저장소는 업스트림 스냅샷에서 새로 시작한 **독립 히스토리**다.
  업스트림과 공통 조상이 없으므로 일반적인 공통 조상 기반 merge/rebase 대신,
  업스트림 변경은 **체리픽 또는 수동 반영** 방식으로 따라간다.

## 현재 동기화 상태 (2026-10-10)

| 항목 | 값 |
| --- | --- |
| 로컬 펌웨어 버전 | 10.28y |
| 마지막 동기화 당시 업스트림 펌웨어 버전 | 10.28x |
| 마지막 반영 업스트림 커밋 | `65a7518` "Upped patch level" (2026-09-08) |
| 반영 방식 | 추적 정밀도·부저 기본 상태 수정을 수동 반영 + 버전 동기화 |

2026-10-10 로컬 수정 (`10.28y`, 추가 업스트림 동기화 없음):

- 경위대/Alt-Alt 펄스 시작·종료 때 가이드 성분을 포함한 추적 속도를
  즉시 재계산한다. 기존에는 1초 주기의 계산 결과를 재사용해 짧은
  펄스가 누락되거나 종료 후에도 보정 속도가 남았다.
- 즉시 계산에서는 yield와 작은 속도 변화의 평활화를 사용하지 않는다.
  주기 계산은 기존 yield를 유지하되, 도중에 가이드 입력이 바뀌면
  오래된 좌표 스냅샷으로 새 속도를 덮어쓰지 않는다.
- 적도의의 기존 가이드 속도 직접 가산 경로는 유지한다.
- 호스트 시험: 실제 소스 함수를 추출해 240개 타이밍 조합과 양축 중첩,
  계산 도중 시작/종료, 방향 반전, abort를 검증했다. ASan/UBSan 및 기존
  명령 검증 시험 통과. 실행 방법은 [PlatformIO 문서](platformio.md)를 참조한다.
- ESP32 `MF_OOZOO_E4` 빌드·USB 업로드·플래시 해시 검증 성공.
  장치 `:GVN#` 응답으로 `10.28y`를 확인했다.
- 고도 약 74.5도에서 1× 가이드와 `:GXF3#`/`:GXF4#` 모터 출력 조회로
  수정 전후를 비교했다. 기존 `10.28x`의 200ms 시험 12회 중 11회는
  보정 출력이 관측되지 않았고, 1회는 약 996ms 동안 지속됐다.
  1500ms 시험은 약 952ms 늦게 시작해 약 1014ms 동안 적용됐다.
- 수정 후 100ms 2회, 200ms 5회(N/S/E/W 포함), 1500ms 1회 모두 응답했다.
  조회 시각으로 계산한 적용 시간 구간은 모두 요청 시간을 포함했고,
  첫 보정 출력은 전송 후 18.2ms 이내에 확인됐다. 약 20ms 주기의 USB
  조회이므로 서브밀리초 타이머 정밀도를 실측한 결과는 아니다.
- 시험은 IMU로 설정한 임시 좌표와 모터 출력에 대한 검증이다. 별 영상의
  추적 정확도, 슬립·백래시 해소, MFNavis 응답 프로필 재교정을 검증한
  것으로 해석하지 않는다. 시험 후 모터 출력 0 및 추적 정지를 확인하고
  INDI/MFNavis 연결을 복원했다.

2026-09-10 반영 내역:

- 기존 작업 변경은 `055d04c`로 커밋해 `origin/main`에 푸시한 후 적용했다.
- `21c3834` — `Mount::poll()`의 중앙 차분 좌표 4개를 `float`에서 `double`로
  변경해 차분 이전의 정밀도 손실을 줄였다. 로컬 좌표 스냅샷과 속도 제한은 유지했다.
- `95eca32` — `Sound.h`, `Status.h`, `Status.cpp`의 부저 기본 상태와
  저장 설정 적용 순서를 업스트림과 맞췄다.
- `d487428` — 홈 오프셋 범위 조건의 `||` → `&&` 수정은 로컬에 이미 존재한다.
  로컬의 `strtol` 입력 전체 검증과 오류 시 NV 저장 방지는 계속 유지한다.
- `65a7518` — 펌웨어 패치 버전을 `w`에서 `x`로 갱신했다.

검증 (2026-09-10): `pio run -e onstepx_esp32_mf_oozoo_e4` 빌드 성공.
RAM 63,316 / 327,680 bytes (19.3%), Flash 1,230,889 / 3,145,728 bytes (39.1%).
`git diff --check` 통과. 실제 장치 업로드 및 추적·부저 동작 검증은 수행하지 않았다.

## 10.28w 반영 내역 (2026-08-07)

업스트림 `9d755d4` "Fix for sense offset range bug" 반영 내역:

- `src/lib/Macros.h` — `degToArcsecF(x) ((x)/3600.0F)` → `degToArcsecL(x) ((x)*3600L)` 교체.
  도→각초 변환은 ×3600이 맞으며, 기존 매크로는 ÷3600으로 잘못되어 있었다.
- `src/telescope/mount/home/Home.cpp` — 부팅 시 `senseOffset` constrain 범위를
  ±0.05 arcsec → ±648,000 arcsec(±180°)로 수정. NV에 저장된 홈 센서 오프셋이
  부팅 때마다 0으로 뭉개지던 버그 해결.
- `src/telescope/mount/home/Home.command.cpp` — **업스트림 버전을 따르지 않음.**
  로컬은 `strtol` + 완전한 범위 검증(`&&`)을 쓰는 반면, 당시 업스트림 수정본은
  `l >= -degToArcsecL(180L) || l <= degToArcsecL(180L)` 식이라 항상 참이 되는
  논리 버그가 남아 있었다. 업스트림도 이후 `d487428`에서 `&&`로 수정했다.
  현재 남은 차이는 `strtol` 입력 검증과 오류 시 저장 방지이며 의도된 차이다.

빌드 검증: `onstepx_esp32_mf_oozoo_e4` 환경 컴파일 통과 (RAM 19.3%, Flash 39.1%).

## 업스트림 비교 절차

```powershell
git fetch upstream
git log --oneline 65a7518..upstream/main   # 마지막 확인 기준 이후의 신규 커밋
git diff upstream/main --stat             # 미커밋 변경을 포함한 파일 단위 차이
git show <hash>                            # 개별 커밋 내용 확인
```

주의사항:

- 공통 조상이 없으므로 `git merge-base`는 실패한다(정상).
- `git log HEAD..upstream/main`에 나오는 커밋 중 상당수는 이미 체리픽으로
  반영된 것이다. 커밋 제목이 로컬 히스토리에 있는지 먼저 대조할 것.
- 파일 diff가 크게 나오는 것은 대부분 아래 "의도된 로컬 차이" 때문이다.
  실제 검토 대상은 그 외 파일로 좁혀서 본다.

## 의도된 로컬 차이 (업스트림에 없는 것)

추후 `git diff upstream/main HEAD` 결과에서 아래 항목은 **반영 대상이 아니라
로컬 고유 기능**이므로 diff 노이즈로 간주한다.

### 대규모 추가

- `src/plugins/website/` — 내장 웹 UI 플러그인 전체(약 1만 줄, 4개 언어 로케일).
  업스트림의 `src/plugins/sample/`은 제거함.
- `src/pinmaps/Pins.MF_OOZOO_E4.h`, `Pins.MF_AVX_E4.h` — 커스텀 핀맵
  (+ `Models.h` 등록).
- `platformio.ini`, `platformio_deps.cpp`, `tools/`, `.vscode/` — PlatformIO 및
  VSCode 빌드 환경(업스트림은 Arduino IDE 전용).
- `docs/` — 한국어 문서, 아키텍처/프로토콜 문서, 변경 이력 등.
- `Config.h`, `Extended.config.h` — OOZOO E4 하드웨어에 맞춘 설정.

### 펌웨어 동작 수정

- WiFi: `src/lib/wifi/WifiManager.*` 대폭 수정 — 스테이션 연결 비블로킹화,
  재연결/폴백 복구, 성능 모드 튜닝. `src/lib/serial/Serial_IP_Wifi.cpp`
  연결 딜레이 복원.
- 모터/추적: AXIS2 드라이브 리튠, TMC UART read-back 활성화,
  추적 안정성 좌표 스냅샷(`src/telescope/mount/Mount.cpp`),
  `src/lib/axis/Axis.cpp`, `src/lib/axis/motor/stepDir/StepDir.cpp`.
- 가이드: 노이즈성 SHC 가이드 명령 거부(`Guide.cpp`), 가이드 백래시 억제,
  가이드 시간 제한/limit sense 스위치 비활성화, `St4.cpp` 수정.
- 명령/안정성: `BufferCmds.cpp`, `Convert.cpp`, `Serial_Local.*`,
  `ProcessCmds.cpp`, NV flush/limit 복구(`NvVolume.cpp`, `Park.cpp` 등).
  상세 내역은 `CHANGE_HISTORY.md` 참조.
- 파일명 정규화: `Nv.h`→`NV.h`, `Tls.h`→`TLS.h`.

## 업스트림 제출 이력

| 날짜 | PR | 내용 | 상태 |
| --- | --- | --- | --- |
| 2026-08-07 | [hjd1964/OnStepX#124](https://github.com/hjd1964/OnStepX/pull/124) | `:hC1,n#`/`:hC2,n#` 홈 오프셋 명령 파싱 수정 — 항상 참인 `\|\|` 범위 검사, `atol` 비숫자 입력 무검증, 실패 시에도 NV 저장되는 문제. 로컬 `Home.command.cpp`의 `strtol` 검증을 업스트림 코드 스타일(`degToArcsecL` 매크로)로 이식. 포크 hjoungjoo/mf_OnStepX의 `fix/home-offset-command-parsing` 브랜치 | 리뷰 대기 |

위 PR 상태는 2026-08-07 당시 기록이며 이번 작업에서는 PR 상태를 조회하지 않았다.
2026-09-10 소스 비교 결과 업스트림에는 `d487428`의 조건 수정만 확인되며,
`strtol` 입력 검증과 오류 시 NV 저장 방지는 여전히 로컬에만 존재한다.
다음 동기화에서도 PR 상태와 별도로 `Home.command.cpp`의 실제 diff를 확인할 것.

## 동기화 이력

| 날짜 | 업스트림 버전 | 반영 내용 |
| --- | --- | --- |
| 2026-09-10 | 10.28x (`65a7518`) | 중앙 차분 좌표 double 유지(`21c3834`), 부저 기본 상태 처리(`95eca32`), 홈 입력 검증은 로컬 유지, 패치 레벨 w→x |
| 2026-08-07 | 10.28w (`8500ed5`) | sense offset constrain 버그 수정 반영(`Home.cpp`, `Macros.h`), `Home.command.cpp`는 로컬 버전 유지, 패치 레벨 v→w |
| 2026-08-06 이전 | 10.28v | 커밋 `11959bf`까지 체리픽으로 동기화 (bissc 절대 엔코더, meridian flip homing, GUIDE_TIME_NO_LIMITS, cos() 선형화 수정, AltAzm overhead limit 복구, modem sleep 비활성화 등) |
