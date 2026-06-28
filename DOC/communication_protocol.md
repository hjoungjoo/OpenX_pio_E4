# OnStepX 통신 프로토콜 문서

작성 기준: 현재 작업트리의 OnStepX 소스와 `Config.h` 설정.

이 문서는 OnStepX가 외부 프로그램, WiFi 클라이언트, Bluetooth SPP, ST4/SHC, 내부 명령 큐와 통신하는 방법을 정리한다. 개별 명령의 전체 목록은 기존 `docs/COMMAND_REFERENCE.md`를 기준 문서로 사용한다.

## 현재 빌드 기준

현재 설정에서 중요한 통신 관련 값은 다음과 같다.

| 항목 | 현재 값 | 의미 |
| --- | --- | --- |
| `PINMAP` | `MF_OOZOO_E4` | 사용자 보드 핀맵 |
| `SERIAL_RADIO` | `WIFI_ACCESS_POINT` | ESP32 WiFi AP 명령 채널 활성 |
| `ST4_INTERFACE` | `ON` | ST4 물리 입력 활성 |
| `ST4_HAND_CONTROL` | `ON` | ST4 포트의 SHC/핸드컨트롤 기능 활성 |
| `SERIAL_BT_MODE` | 기본 `OFF` | Bluetooth SPP는 현재 기본 설정에서 꺼짐 |
| `MOUNT_TYPE` | `ALTAZM_UNL` | Alt-Az unlimited mount |
| Axis1/Axis2 driver | `TMC2209` | 마운트 축 활성 |

`SERIAL_RADIO WIFI_ACCESS_POINT`는 `Config.defaults.h`에서 `SERIAL_IP_MODE WIFI_ACCESS_POINT`, `WEB_SERVER ON`, `OPERATIONAL_MODE WIFI`, `AP_ENABLED true`로 확장된다.

## 프로토콜 계층

OnStepX 명령 통신은 물리 채널과 명령 파서가 분리되어 있다.

```mermaid
flowchart LR
  Client["외부 클라이언트"]
  Transport["물리/가상 채널"]
  Wrapper["SerialWrapper"]
  Buffer["Buffer"]
  Processor["CommandProcessor"]
  Telescope["Telescope::command()"]
  Subsystem["Mount / Guide / Goto / Park / Site / Focuser / Features"]

  Client --> Transport --> Wrapper --> Buffer --> Processor --> Telescope --> Subsystem
```

주요 구현 파일:

| 역할 | 파일 |
| --- | --- |
| 명령 채널 태스크 생성/폴링 | `src/libApp/commands/ProcessCmds.cpp` |
| 명령 프레임 버퍼/파서 | `src/lib/commands/BufferCmds.cpp` |
| 채널 추상화 | `src/lib/commands/SerialWrapper.cpp` |
| 명령 분배 | `src/telescope/Telescope.command.cpp` |
| WiFi TCP serial stream | `src/lib/serial/Serial_IP_Wifi.cpp` |
| WiFi AP/STA 관리 | `src/lib/wifi/WifiManager.cpp` |
| ST4/SHC 감지 및 가이드 처리 | `src/telescope/mount/st4/St4.cpp` |
| ST4 직렬 링크 | `src/lib/serial/Serial_ST4_Master.cpp` |
| 내부 명령 큐 | `src/lib/serial/Serial_Local.cpp`, `src/libApp/commands/CommandBroker.cpp` |

## 명령 프레임

기본 명령은 LX200 계열 ASCII 프레임을 사용한다.

| 형식 | 설명 |
| --- | --- |
| `:CC...#` | 일반 명령 프레임 |
| `;CC...CCS#` | 체크섬 및 시퀀스 문자가 있는 프레임 |
| `0x06` | LX200 특수 상태 요청 |

파서는 공백, LF, CR을 무시한다. 내부 명령 버퍼는 80바이트이며, `#`을 만나면 명령 하나가 준비된 것으로 본다.

### 명령과 파라미터 분리

`Buffer::getCmd()`는 `:` 또는 `;` 다음의 1~2자를 명령 코드로 취급한다. 이후 내용은 파라미터 문자열로 전달된다.

예:

| 원본 프레임 | 명령 | 파라미터 |
| --- | --- | --- |
| `:GVP#` | `GV` | `P` |
| `:Mn#` | `M` | `n` |
| `:SX9A,12.3#` | `SX` | `9A,12.3` |

## 체크섬 프레임

체크섬 프레임은 `;`로 시작한다. `Buffer::add()`는 프레임 끝의 체크섬 2문자와 시퀀스 1문자를 검증한 뒤 명령만 남겨 처리한다.

오류가 나면 내부적으로 `:0x06 0#` 형태의 체크섬 실패 응답 경로로 들어가며, `CommandProcessor`는 `CK_FAIL`을 응답한다.

응답에도 체크섬이 필요한 경우 `CommandProcessor::appendChecksum()`이 응답 문자열의 바이트 합을 2자리 16진수로 붙이고, 이어서 시퀀스 문자를 붙인 뒤 `#`으로 닫는다.

## 응답 형식

명령 핸들러는 기본적으로 두 가지 응답 모드를 가진다.

| 모드 | 동작 |
| --- | --- |
| 숫자 응답 | 성공 시 `1`, 실패 시 `0`. 일반적으로 `#` 없이 반환 |
| 문자열 응답 | 응답 payload 뒤에 `#`을 붙여 반환 |

`numericReply`가 `true`인 상태로 명령 처리가 끝나면, `CE_NONE` 또는 `CE_1`은 `1`, 그 외 에러는 `0`으로 변환된다. 문자열 응답이 있는 명령은 보통 `numericReply=false`를 설정한다.

마지막 명령 에러는 `:GE#`로 조회할 수 있으며, 2자리 숫자 문자열로 반환된다.

## 에러 코드 요약

에러 코드는 `src/lib/commands/CommandErrors.h`에 정의되어 있다.

| 코드 | 심볼 | 의미 |
| --- | --- | --- |
| 00 | `CE_NONE` | 오류 없음 |
| 01 | `CE_0` | 명령은 처리했지만 false/fail |
| 02 | `CE_CMD_UNKNOWN` | 알 수 없는 명령 |
| 03 | `CE_REPLY_UNKNOWN` | 유효하지 않은 응답 |
| 04 | `CE_PARAM_RANGE` | 파라미터 범위 오류 |
| 05 | `CE_PARAM_FORM` | 파라미터 형식 오류 |
| 06 | `CE_ALIGN_FAIL` | 정렬 실패 |
| 07 | `CE_ALIGN_NOT_ACTIVE` | 정렬 비활성 |
| 08 | `CE_NOT_PARKED_OR_AT_HOME` | Park 또는 Home 상태가 아님 |
| 09 | `CE_PARKED` | 이미 Park 상태 |
| 10 | `CE_PARK_FAILED` | Park 실패 |
| 11 | `CE_NOT_PARKED` | Park 상태가 아님 |
| 12 | `CE_NO_PARK_POSITION_SET` | Park 위치 없음 |
| 13 | `CE_GOTO_FAIL` | Goto 실패 |
| 14 | `CE_LIBRARY_FULL` | 라이브러리 저장공간 부족 |
| 15 | `CE_SLEW_ERR_BELOW_HORIZON` | 수평선 아래 대상 |
| 16 | `CE_SLEW_ERR_ABOVE_OVERHEAD` | 오버헤드 제한 초과 |
| 17 | `CE_SLEW_ERR_IN_STANDBY` | Standby 상태에서 slew 시도 |
| 18 | `CE_SLEW_ERR_IN_PARK` | Park 상태에서 slew 시도 |
| 19 | `CE_SLEW_IN_SLEW` | 이미 goto/slew 중 |
| 20 | `CE_SLEW_ERR_OUTSIDE_LIMITS` | 설정 제한 밖 |
| 21 | `CE_SLEW_ERR_HARDWARE_FAULT` | 하드웨어 fault |
| 22 | `CE_SLEW_IN_MOTION` | 이미 움직이는 중 |
| 23 | `CE_SLEW_ERR_UNSPECIFIED` | 기타 slew 오류 |
| 24 | `CE_NULL` | 내부용, 마지막 에러 갱신 억제 |
| 25 | `CE_1` | 명시적 true/success |

## WiFi 명령 채널

현재 설정은 ESP32 WiFi Access Point 모드다. 실제 SSID, 비밀번호, IP 값은 `Config.h`, `Config.defaults.h`, NV 저장값을 따른다.

### 포트

`SERIAL_SERVER` 기본값은 `BOTH`이다. 따라서 WiFi 명령 채널은 다음 TCP 포트를 사용한다.

| 채널 | 포트 | 성격 |
| --- | --- | --- |
| `SERIAL_SIP` | `9999` | 표준 명령 포트 |
| `SERIAL_PIP1` | `9996` | persistent 명령 포트 |
| `SERIAL_PIP2` | `9997` | persistent 명령 포트 |
| `SERIAL_PIP3` | `9998` | persistent 명령 포트 |

`SerialWrapper::begin()`에서 표준 포트는 `9999`, persistent 포트는 `9996`~`9998`로 열린다. 각 포트는 `WiFiServer` 기반이며, `IPSerial::available()`이 클라이언트를 accept하고 명령 바이트를 읽는다.

### 클라이언트 동작

클라이언트는 TCP 연결 후 `:GVP#`, `:GVD#`, `:Mn#` 같은 ASCII 명령을 그대로 전송하면 된다. 응답은 같은 TCP 연결로 돌아온다.

권장 동작:

- 명령은 반드시 `#`으로 종료한다.
- 한 명령의 응답을 받은 뒤 다음 명령을 보내는 방식을 기본으로 한다.
- persistent 포트는 연결 유지에 유리하지만, 장시간 무응답/무데이터 연결은 timeout으로 닫힐 수 있다.
- mount motion 관련 명령은 `:GE#`로 실패 원인을 확인한다.

## Bluetooth SPP 채널

현재 기본 설정에서는 `SERIAL_BT_MODE`가 `OFF`다. `SERIAL_RADIO BLUETOOTH` 또는 별도 `SERIAL_BT_MODE SLAVE`를 지정하면 ESP32 `BluetoothSerial` 기반 SPP 명령 채널이 활성화된다.

SPP 채널은 게임패드 HID가 아니다. Bluetooth 터미널 또는 SPP 리모컨이 OnStep 명령 문자열을 보내는 구조다.

WiFi AP를 유지하면서 SPP를 추가하는 임시 빌드는 성공했다. 다만 실제 운용에서는 ESP32의 WiFi와 Bluetooth가 같은 2.4GHz RF를 공유하므로 지연이나 끊김 가능성을 현장 테스트해야 한다.

## ST4와 SHC

현재 `ST4_INTERFACE ON`, `ST4_HAND_CONTROL ON`이다.

ST4는 두 가지 방식으로 동작한다.

1. 일반 ST4 입력: RA/DEC 네 방향 핀 상태를 읽어 `guide.startAxis1/2()`와 `guide.stopAxis1/2()`를 호출한다.
2. Smart Hand Controller: RA+ 핀의 12.5Hz tone과 RA- tone을 감지하면 DEC 핀을 clock/data 출력으로 바꾸고 `SerialST4Master` 링크를 시작한다.

SHC 활성 상태에서는 `St4Comm` 태스크가 약 100us 주기로 `serialST4.poll()`을 호출한다. 한 바이트 교환은 24회의 poll을 필요로 하며, 주석 기준 약 4200bps 수준이다.

SHC에서 들어오는 단일 바이트 가이드 명령은 다음처럼 직접 처리된다.

| 코드 | 동작 |
| --- | --- |
| `14` | East 방향 guide |
| `15` | West 방향 guide |
| `16` | North 방향 guide |
| `17` | South 방향 guide |
| `18`, `19` | Axis1 guide stop |
| `20`, `21` | Axis2 guide stop |

현재 작업트리에는 SHC tone이 잠깐 끊겨도 즉시 해제되지 않도록 `ST4_SHC_TONE_LOSS_MS` 기본 1500ms 지연이 들어가 있다. 이 값은 필요하면 `Config.h`에서 override할 수 있다.

## 내부 명령 채널

`SERIAL_LOCAL`은 외부 포트가 아니라 펌웨어 내부에서 자기 자신에게 명령을 넣기 위한 Stream이다. 예를 들어 ST4 핸드컨트롤의 조합 버튼은 `SERIAL_LOCAL.transmit(":B+#")`처럼 기존 LX200 명령을 재사용한다.

`CommandBroker`는 내부 명령 request/reply 충돌을 줄이기 위한 큐다.

| 항목 | 기본값 |
| --- | --- |
| 큐 슬롯 | `8` |
| 명령 길이 | `40` |
| 응답 길이 | `80` |
| 기본 timeout | `100ms` |
| 태스크 주기 | `3ms` |

내부 기능에서 응답을 기다려야 하면 직접 `SERIAL_LOCAL.receive()`를 섞지 말고 `commandBroker.request()`를 사용하는 것이 안전하다.

## 명령 분배 순서

`Telescope::command()`는 명령을 다음 순서로 각 하위 시스템에 전달한다.

1. 명령 처리 플러그인
2. Mount
3. Guide
4. GPIO 확장
5. Mount status
6. Goto
7. Park
8. Library
9. Site
10. Limits
11. Home
12. PEC
13. Axis1
14. Axis2
15. Rotator
16. Focuser
17. Auxiliary features
18. Telescope 공통 명령

먼저 `true`를 반환한 핸들러가 해당 명령을 처리한 것으로 본다.

## 대표 명령 예

자세한 명령표는 `docs/COMMAND_REFERENCE.md`를 본다. 개발/테스트 때 자주 쓰는 기본 명령은 다음과 같다.

| 명령 | 의미 |
| --- | --- |
| `:GVP#` | 제품명 조회 |
| `:GVN#` | 펌웨어 버전 조회 |
| `:GVH#` | 하드웨어/핀맵 문자열 조회 |
| `:GE#` | 마지막 명령 에러 코드 조회 |
| `:Mn#`, `:Ms#`, `:Me#`, `:Mw#` | 현재 guide rate로 수동 이동 |
| `:Qn#`, `:Qs#`, `:Qe#`, `:Qw#` | 해당 방향 guide/slew 정지 |
| `:Q#` | 전체 slew/goto 정지 |
| `:RG#`, `:RC#`, `:RM#`, `:RF#` | guide rate preset |

## 게임패드/리모컨 확장 관점

현재 소스의 Bluetooth는 SPP 명령 채널이며 HID 게임패드 입력은 없다. 게임패드를 직접 붙이려면 별도의 HID host 계층을 추가하고, 버튼/스틱 이벤트를 다음 중 하나로 변환해야 한다.

- 직접 `guide.startAxis1/2()`와 `guide.stopAxis1/2()` 호출
- `SERIAL_LOCAL` 또는 `CommandBroker`를 통해 기존 `:Mn#`, `:Qn#` 계열 명령 호출

안전 설계에서는 입력 끊김 timeout, 버튼 release 시 정지, goto 중 입력 처리 정책, 최대 guide rate 제한을 반드시 포함해야 한다.

