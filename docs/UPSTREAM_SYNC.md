# 업스트림 동기화 기록

이 문서는 원본 저장소(hjd1964/OnStepX)와의 동기화 상태를 기록하고,
추후 업스트림 비교/반영 작업 시 참고하는 기준 문서다.

최종 갱신일: 2026-08-07

## 저장소 구조

- 원본(업스트림): https://github.com/hjd1964/OnStepX — 리모트 이름 `upstream`
- 로컬(오리진): https://github.com/hjoungjoo/OpenX_pio_E4 — 리모트 이름 `origin`
- 로컬 저장소는 업스트림 스냅샷에서 새로 시작한 **독립 히스토리**다.
  업스트림과 공통 조상이 없으므로 merge/rebase가 불가능하며,
  업스트림 변경은 **체리픽 또는 수동 반영** 방식으로 따라간다.

## 현재 동기화 상태 (2026-08-07)

| 항목 | 값 |
| --- | --- |
| 로컬 펌웨어 버전 | 10.28w |
| 업스트림 펌웨어 버전 | 10.28w |
| 마지막 반영 업스트림 커밋 | `8500ed5` "Upped patch level" (2026-08-06) |
| 반영 방식 | 실질 변경(`9d755d4` sense offset 수정)을 수동 반영 + 버전 동기화 |

업스트림 `9d755d4` "Fix for sense offset range bug" 반영 내역:

- `src/lib/Macros.h` — `degToArcsecF(x) ((x)/3600.0F)` → `degToArcsecL(x) ((x)*3600L)` 교체.
  도→각초 변환은 ×3600이 맞으며, 기존 매크로는 ÷3600으로 잘못되어 있었다.
- `src/telescope/mount/home/Home.cpp` — 부팅 시 `senseOffset` constrain 범위를
  ±0.05 arcsec → ±648,000 arcsec(±180°)로 수정. NV에 저장된 홈 센서 오프셋이
  부팅 때마다 0으로 뭉개지던 버그 해결.
- `src/telescope/mount/home/Home.command.cpp` — **업스트림 버전을 따르지 않음.**
  로컬은 `strtol` + 완전한 범위 검증(`&&`)을 쓰는 반면, 업스트림 수정본은
  `l >= -degToArcsecL(180L) || l <= degToArcsecL(180L)` 식이라 항상 참이 되는
  논리 버그가 남아 있다. 로컬 버전이 더 안전하므로 유지한다.
  추후 diff에서 이 파일이 다르게 나오는 것은 의도된 차이다.

빌드 검증: `onstepx_esp32_mf_oozoo_e4` 환경 컴파일 통과 (RAM 19.3%, Flash 39.1%).

## 업스트림 비교 절차

```powershell
git fetch upstream
git log --oneline HEAD..upstream/main      # 업스트림 신규 커밋 확인
git diff upstream/main HEAD --stat         # 파일 단위 차이 확인
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

PR이 머지되면 해당 파일의 "의도된 로컬 차이"가 해소되므로, 다음 동기화 때
`Home.command.cpp` diff가 사라졌는지 확인하고 위 "반영 내역" 항목을 갱신할 것.

## 동기화 이력

| 날짜 | 업스트림 버전 | 반영 내용 |
| --- | --- | --- |
| 2026-08-07 | 10.28w (`8500ed5`) | sense offset constrain 버그 수정 반영(`Home.cpp`, `Macros.h`), `Home.command.cpp`는 로컬 버전 유지, 패치 레벨 v→w |
| 2026-08-06 이전 | 10.28v | 커밋 `11959bf`까지 체리픽으로 동기화 (bissc 절대 엔코더, meridian flip homing, GUIDE_TIME_NO_LIMITS, cos() 선형화 수정, AltAzm overhead limit 복구, modem sleep 비활성화 등) |
