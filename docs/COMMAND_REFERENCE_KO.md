# OnStepX 명령 레퍼런스

이 레퍼런스는 현재 소스 트리의 명령 핸들러에서 정리한 문서다. 주로 각 `*.command.cpp` 파일과 공통 명령 처리기인 `src/libApp/commands/ProcessCmds.cpp`를 기준으로 했다.

범위:

- 이 문서는 현재 트리에 구현된 명령군을 다룬다. 오래된 wiki 페이지의 명령까지 포함하지는 않는다.
- 많은 명령은 컴파일 타임 기능 설정에 따라 활성/비활성이 결정된다. 해당 서브시스템이 빌드에 포함되지 않으면 그 명령도 존재하지 않는다.
- 플러그인 정의 명령은 문서화하지 않는다. 플러그인 명령은 활성 플러그인 구성에 따라 달라지며 core 명령 핸들러에 속하지 않는다.
- 일부 소스 주석은 오래되었을 수 있다. 코드와 주석이 다를 때는 실제 코드 경로를 기준으로 설명한다.

## 프로토콜 기본

### 프레임

- 일반 ASCII 명령 프레임: `:CC...#`
- 체크섬 프레임: `;CC...CCS#`
  - `;`는 체크섬 명령의 시작이다.
  - 명령 처리기는 분배 전에 체크섬과 시퀀스 문자를 검증한다.
- 파서는 ASCII space, LF, CR을 무시한다.
- 내부 명령 버퍼 크기는 프레임 포함 80바이트다. 따라서 현재 구현은 오래된 40문자 LX200 관례에 제한되지 않는다.

### 명령 파싱

- `CC`는 사실상 1자 또는 2자 명령군이다. 나머지 payload는 파라미터 문자열이다.
- 응답은 다음 둘 중 하나다.
  - payload 응답. 보통 `#`으로 끝난다.
  - 숫자/boolean 응답. 성공은 `1`, 실패는 `0`으로 반환한다.
- 일부 명령은 의도적으로 끝의 `#`을 생략한다.

### 전역 응답/에러 동작

- `numericReply=true`를 유지한 채 끝나는 명령은 다음 값을 반환한다.
  - `CE_NONE` 또는 `CE_1`이면 `1`
  - 그 외 에러면 `0`
- `:GE#`는 마지막 명령 에러 코드를 2자리 payload로 반환한다.

### 명령 에러 코드

다음 값은 `:GE#`로 반환되는 코드다.

| 코드 | 심볼 | 의미 |
| --- | --- | --- |
| 00 | `CE_NONE` | 오류 없음 |
| 01 | `CE_0` | 프로토콜 에러는 아니지만 false/fail |
| 02 | `CE_CMD_UNKNOWN` | 알 수 없는 명령 |
| 03 | `CE_REPLY_UNKNOWN` | 유효하지 않은 응답 |
| 04 | `CE_PARAM_RANGE` | 파라미터 범위 오류 |
| 05 | `CE_PARAM_FORM` | 파라미터 형식 오류 |
| 06 | `CE_ALIGN_FAIL` | 정렬 실패 |
| 07 | `CE_ALIGN_NOT_ACTIVE` | 정렬이 활성 상태가 아님 |
| 08 | `CE_NOT_PARKED_OR_AT_HOME` | Park 또는 Home 상태가 아님 |
| 09 | `CE_PARKED` | 이미 Park 상태 |
| 10 | `CE_PARK_FAILED` | Park 실패 |
| 11 | `CE_NOT_PARKED` | Park 상태가 아님 |
| 12 | `CE_NO_PARK_POSITION_SET` | Park 위치가 설정되지 않음 |
| 13 | `CE_GOTO_FAIL` | Goto 실패 |
| 14 | `CE_LIBRARY_FULL` | 라이브러리 저장공간 부족 |
| 15 | `CE_SLEW_ERR_BELOW_HORIZON` | 대상이 수평선 제한 아래 |
| 16 | `CE_SLEW_ERR_ABOVE_OVERHEAD` | 대상이 overhead 제한 위 |
| 17 | `CE_SLEW_ERR_IN_STANDBY` | 컨트롤러가 standby 상태 |
| 18 | `CE_SLEW_ERR_IN_PARK` | 마운트가 Park 상태 |
| 19 | `CE_SLEW_IN_SLEW` | Goto가 이미 동작 중 |
| 20 | `CE_SLEW_ERR_OUTSIDE_LIMITS` | 설정 제한 밖 |
| 21 | `CE_SLEW_ERR_HARDWARE_FAULT` | 하드웨어 fault |
| 22 | `CE_SLEW_IN_MOTION` | 마운트가 이미 움직이는 중 |
| 23 | `CE_SLEW_ERR_UNSPECIFIED` | 기타 slew 오류 |
| 25 | `CE_1` | 명시적 true/success |

## 전역 처리기 명령

이 명령들은 개별 서브시스템 `*.command.cpp`가 아니라 `ProcessCmds.cpp`에서 처리한다.

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:SBB#` | `1` 후 460800 baud로 전환 | Serial baud rate 설정 |
| `:SBA#` | `1` 후 230400 baud로 전환 | Serial baud rate 설정 |
| `:SB0#` | `1` 후 115200 baud로 전환 | Serial baud rate 설정 |
| `:SB1#` | `1` 후 56700 baud로 전환 | Serial baud rate 설정 |
| `:SB2#` | `1` 후 38400 baud로 전환 | Serial baud rate 설정 |
| `:SB3#` | `1` 후 28800 baud로 전환 | Serial baud rate 설정 |
| `:SB4#` | `1` 후 19200 baud로 전환 | Serial baud rate 설정 |
| `:SB5#` | `1` 후 14400 baud로 전환 | Serial baud rate 설정 |
| `:SB6#` | `1` 후 9600 baud로 전환 | Serial baud rate 설정 |
| `:SB7#` | `1` 후 4800 baud로 전환 | Serial baud rate 설정 |
| `:SB8#` | `1` 후 2400 baud로 전환 | Serial baud rate 설정 |
| `:SB9#` | `1` 후 1200 baud로 전환 | Serial baud rate 설정 |
| `:GE#` | `CC#` | 마지막 명령 에러 코드 조회 |
| `<0x06>` | `A`, `P`, 또는 `CK_FAIL` 형식 응답 | buffer/processor가 처리하는 특수 LX200 상태 조회 또는 체크섬 실패 경로 |

## 분배 순서 참고

전체 telescope 빌드에서 명령 분배 순서는 다음과 같다.

1. mount
2. guide
3. GPIO/plugin status helper
4. goto
5. park
6. library
7. site
8. limits
9. home
10. PEC
11. axis 1 / axis 2
12. rotator
13. focuser
14. auxiliary features

일부 명령 이름은 여러 서브시스템에서 재사용되므로 이 순서가 중요하다. 특히 `:hP#`와 `:hR#`가 그렇다. 통합 마운트 빌드에서는 rotator/focuser 핸들러가 해당 프레임을 보기 전에 mount의 park/unpark가 먼저 처리된다. rotator/focuser의 `h*` 명령은 standalone 또는 remote-node 빌드에서는 여전히 유효하다.

## Core Telescope / Firmware / Environment

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:B+#` | 없음 | reticle 밝기 증가 |
| `:B-#` | 없음 | reticle 밝기 감소 |
| `:ECtext#` | 없음 | text를 debug 출력으로 echo. `_`는 space가 되고, 끝의 `&`는 newline이 된다. |
| `:ERESET#` | 없음 | MCU reset |
| `:ENVRESET#` | text | 다음 boot 때 NV storage를 지우도록 표시 |
| `:ESPFLASH#` | 빌드 경로에 따라 `1`/없음 | 지원되는 경우 addon/ESP 장치를 펌웨어 flashing mode로 전환 |
| `:GVD#` | `MTH DD YYYY#` | 펌웨어 빌드 날짜 |
| `:GVM#` | `name version#` | 펌웨어 이름과 버전 |
| `:GVN#` | `M.mm...#` | 펌웨어 버전 번호 |
| `:GVP#` | `name#` | 제품명 |
| `:GVT#` | `HH:MM:SS#` | 펌웨어 빌드 시간 |
| `:GVC#` | `string#` | 펌웨어 config/product 설명 |
| `:GVH#` | `string#` | 펌웨어 하드웨어/핀맵 문자열 |
| `:GX9A#` | `sn.n#` | 주변 온도, C |
| `:GX9B#` | `n.n#` | 기압, mbar |
| `:GX9C#` | `n.n#` | 상대습도, percent |
| `:GX9E#` | `sn.n#` | 이슬점, C |
| `:GX9F#` | `n#` 또는 `0` | MCU 온도, C |
| `:SX9A,sn.n#` | `0/1` | 주변 온도 설정 |
| `:SX9B,n.n#` | `0/1` | 기압 설정 |
| `:SX9C,n.n#` | `0/1` | 습도 설정 |

## Time / Date / Site

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:Ga#` | `HH:MM:SS#` | Local standard time, 12시간 형식 |
| `:GC#` | `MM/DD/YY#` | Local standard calendar date |
| `:Gc#` | `24#` | Local time format indicator |
| `:GG#` | `sHH:MM#` | Local time에 더해 UT1을 얻기 위한 UTC offset |
| `:Gg#` | `sDDD*MM#` | 현재 경도 |
| `:GgH#` | `sDDD*MM:SS.SSS#` | 경도, 최고 정밀도 |
| `:GL#` | `HH:MM:SS#` | Local standard time, 24시간 형식 |
| `:GLH#` | `HH:MM:SS.SSSS#` | Local standard time, 최고 정밀도 |
| `:GM#` | `string#` | Site 1 이름 |
| `:GN#` | `string#` | Site 2 이름 |
| `:GO#` | `string#` | Site 3 이름 |
| `:GP#` | `string#` | Site 4 이름 |
| `:GS#` | `HH:MM:SS#` | 항성시 |
| `:GSH#` | `HH:MM:SS.ss#` | 항성시, 최고 정밀도 |
| `:Gt#` | `sDD*MM#` | 현재 위도 |
| `:GtH#` | `sDD*MM:SS.SSS#` | 위도, 최고 정밀도 |
| `:Gv#` | `sn.n#` | 고도, meters |
| `:GX80#` | `HH:MM:SS.ss#` | UT1 시간 |
| `:GX81#` | `MM/DD/YY#` | UT1 날짜 |
| `:GX89#` | `0` 또는 `1` | 날짜/시간 준비 상태. `0`은 ready, `1`은 not ready. |
| `:SCMM/DD/YY#` | `0/1` | Local date 설정 |
| `:SCMM/DD/YYYY#` | `0/1` | Local date 설정 |
| `:SGsHH#` | `0/1` | UTC offset 설정 |
| `:SGsHH:MM#` | `0/1` | UTC offset 설정. 주석상 `MM`은 `00`, `30`, `45`여야 한다. |
| `:Sg(s)DDD*MM#` | `0/1` | 경도 설정 |
| `:Sg(s)DDD*MM:SS#` | `0/1` | 경도 설정 |
| `:Sg(s)DDD*MM:SS.SSS#` | `0/1` | 경도 설정 |
| `:SLHH:MM:SS#` | `0/1` | Local time 설정 |
| `:SLHH:MM:SS.SSS#` | `0/1` | Local time 설정 |
| `:SMname#` | `0/1` | Site 1 이름 설정, 최대 15자 |
| `:SNname#` | `0/1` | Site 2 이름 설정, 최대 15자 |
| `:SOname#` | `0/1` | Site 3 이름 설정, 최대 15자 |
| `:SPname#` | `0/1` | Site 4 이름 설정, 최대 15자 |
| `:StsDD*MM#` | `0/1` | 위도 설정 |
| `:StsDD*MM:SS#` | `0/1` | 위도 설정 |
| `:StsDD*MM:SS.SSS#` | `0/1` | 위도 설정 |
| `:SUs.s#` | `0/1` | DUT1 보정값 설정, seconds. 일반적으로 `-0.9`부터 `+0.9` |
| `:Svsn.n#` | `0/1` | 고도 설정, meters |
| `:W0#` .. `:W3#` | 없음 | 활성 site slot 선택 |
| `:W?#` | `n#` | 활성 site slot 조회 |

## Mount Position / Tracking / Rates

`MOUNT_PRESENT`가 활성화된 경우 사용할 수 있다.

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:GA#` | `sDD*MM#` 또는 `sDD*MM'SS#` | 현재 마운트 고도 |
| `:GAH#` | `sDD*MM'SS.SSS#` | 현재 마운트 고도, 최고 정밀도 |
| `:GD#` | `sDD*MM#` 또는 `sDD*MM:SS#` | 현재 적위 |
| `:GDH#` | `sDD*MM:SS.SSS#` | 현재 적위, 최고 정밀도 |
| `:GR#` | `HH:MM.T#` 또는 `HH:MM:SS#` | 현재 적경 |
| `:GRH#` | `HH:MM:SS.SSSS#` | 현재 적경, 최고 정밀도 |
| `:GT#` | `n.nnnnn#` 또는 `0#` | Tracking rate, Hz. tracking 중이 아니면 `0` |
| `:GZ#` | `DDD*MM#` 또는 `DDD*MM'SS#` | 현재 방위각 |
| `:GZH#` | `DDD*MM'SS.SSS#` | 현재 방위각, 최고 정밀도 |
| `:GXTD#` | `n.nnnnnnnn#` | Dec tracking rate offset, sidereal second당 arcsec |
| `:GXTR#` | `n.nnnnnnnn#` | RA tracking rate offset, sidereal second당 arcsec |
| `:GX40#` | `DDD*MM:SS#` | Axis1 instrument angle |
| `:GX41#` | `DDD*MM:SS#` | Axis2 instrument angle |
| `:GX42#` | `n.nnnnnn#` | Axis1 instrument angle, decimal degrees |
| `:GX43#` | `n.nnnnnn#` | Axis2 instrument angle, decimal degrees |
| `:GX44#` | `n#` | Axis1 encoder count |
| `:GX45#` | `n#` | Axis2 encoder count |
| `:GXE4#` | `n#` | Axis1 steps per degree |
| `:GXE5#` | `n#` | Axis2 steps per degree |
| `:GXEE#` | `0#`, `1#`, ... | Mount coordinate mode (`MOUNT_COORDS - 1`) |
| `:GXEF#` | `1` 또는 `0` | Axis2 tangent-arm 존재 flag |
| `:GXEG#` | `1` 또는 `0` | Axis1 sector-gear 존재 flag |
| `:GXEM#` | `n#` | 현재 mount type |
| `:GXF3#` | `sn.nnnnnn#` | Axis1 step frequency |
| `:GXF4#` | `sn.nnnnnn#` | Axis2 step frequency |
| `:GXFA#` | `50%#` | workload 보고용 placeholder |
| `:GXFF#` | `n.nnnnnn#` | Axis1 index position |
| `:GXFG#` | `n.nnnnnn#` | Axis2 index position |
| `:STn.n#` | `0/1` | Tracking rate 설정, Hz. `0`은 tracking 정지 |
| `:SEO#` | `0/1` | 지원되는 경우 absolute encoder origin 저장 또는 home에서 mount coordinate memory 초기화 |
| `:SX40,n#` | `0/1` | Encoder axis1 angle을 degrees로 staging |
| `:SX41,n#` | `0/1` | Encoder axis2 angle을 degrees로 staging |
| `:SX42,1#` | `0/1` | staging된 encoder axis 값으로 mount sync |
| `:SX43,0#` | `0/1` | SWS가 sync mode를 제어하도록 허용 |
| `:SX44,deg1,deg2[a]#` | `0/1` | 두 encoder axis 값을 staging하고 sync. SWS encoder 값 둘 다 absolute/trusted이면 `a`를 붙임 |
| `:GXSGn#` | `sg,trip,badMs,armed,latched#` | 지원되는 경우 axis `n`의 live StallGuard telemetry |
| `:SXEM,n#` | `0/1` | 다음 restart에 사용할 mount type 설정 |
| `:SXTD,n.n#` | `0/1` | Dec tracking rate offset 설정, sidereal second당 arcsec |
| `:SXTR,n.n#` | `0/1` | RA tracking rate offset 설정, sidereal second당 arcsec |
| `:TS#` | 없음 | Solar tracking rate |
| `:TK#` | 없음 | King tracking rate |
| `:TL#` | 없음 | Lunar tracking rate |
| `:TQ#` | 없음 | Sidereal tracking rate |
| `:T+#` | 없음 | master sidereal clock을 0.02 Hz 증가 |
| `:T-#` | 없음 | master sidereal clock을 0.02 Hz 감소 |
| `:TR#` | 없음 | master sidereal clock reset |
| `:Te#` | `0/1` | Tracking 활성 |
| `:Td#` | `0/1` | Tracking 비활성 |
| `:To#` | `0/1` | 전체 compensation model 활성 |
| `:Tr#` | `0/1` | Refraction compensation 활성 |
| `:Tn#` | `0/1` | Compensation 비활성 |
| `:T1#` | `0/1` | Single-axis tracking mode |
| `:T2#` | `0/1` | Dual-axis tracking mode |
| `:$BDn#` | `0/1` | Dec/Alt backlash 설정, arcsec |
| `:$BRn#` | `0/1` | RA/Azm backlash 설정, arcsec |
| `:%BD#` | `n#` | Dec/Alt backlash 조회, arcsec |
| `:%BR#` | `n#` | RA/Azm backlash 조회, arcsec |

### Mount Type 값

현재 core constant는 다음과 같다.

| 값 | Mount type |
| --- | --- |
| `1` | GEM |
| `2` | FORK |
| `3` | ALTAZM |
| `4` | ALTALT |
| `5` | GEM_TA |
| `6` | GEM_TAC |
| `7` | FORK_TA |
| `8` | FORK_TAC |
| `9` | ALTAZM_UNL |

## Goto / Sync / Alignment

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:AW#` | `1` | Alignment model을 NV에 저장 |
| `:A?#` | `mno#` | Alignment 상태: 최대 star 수, 현재 star, 마지막 required star |
| `:A1#` .. `:A9#` | `0/1` | 지정한 star 수로 manual alignment 시작 |
| `:A+#` | `0/1` | 현재 align point 수락 |
| `:CS#` | 없음 | 현재 target coordinate로 sync |
| `:CM#` | `N/A#` 또는 `E1#`..`E9#` | 현재 catalog/database object로 sync |
| `:D#` | 이동 중 `0x7f#`, 그 외 raw `#` | LX200 distance-bar 형식의 motion indicator |
| `:Gr#` | `HH:MM.T#` 또는 `HH:MM:SS#` | Target RA 조회 |
| `:GrH#` | `HH:MM:SS.SSSS#` | Target RA 조회, 최고 정밀도 |
| `:Gd#` | `sDD*MM#` 또는 `sDD*MM:SS#` | Target Dec 조회 |
| `:GdH#` | `sDD*MM:SS.SSS#` | Target Dec 조회, 최고 정밀도 |
| `:Gal#` | `sDD*MM#` 또는 `sDD*MM'SS#` | Target altitude 조회 |
| `:GaH#` | `sDD*MM'SS.SSS#` | Target altitude 조회, 최고 정밀도 |
| `:Gz#` | `DDD*MM#` 또는 `DDD*MM'SS#` | Target azimuth 조회 |
| `:GzH#` | `DDD*MM'SS.SSS#` | Target azimuth 조회, 최고 정밀도 |
| `:MA#` | `0`..`9` | Target Alt/Az로 goto |
| `:MD#` | `0`, `1`, 또는 `2` | 현재 target의 destination pier side |
| `:MN#` | `0`..`9` | 현재 위치를 opposite pier side로 goto |
| `:MNe#` | `0`..`9` | 같은 위치 goto를 east pier side로 강제 |
| `:MNw#` | `0`..`9` | 같은 위치 goto를 west pier side로 강제 |
| `:MP#` | `0`..`9` | Polar-align goto |
| `:MS#` | `0`..`9` | 현재 target으로 goto |
| `:SrHH:MM.T#` | `0/1` | Target RA 설정 |
| `:SrHH:MM:SS#` | `0/1` | Target RA 설정 |
| `:SrHH:MM:SS.SSSS#` | `0/1` | Target RA 설정 |
| `:SdsDD*MM#` | `0/1` | Target Dec 설정 |
| `:SdsDD*MM:SS#` | `0/1` | Target Dec 설정 |
| `:SdsDD*MM:SS.SSS#` | `0/1` | Target Dec 설정 |
| `:SasDD*MM#` | `0/1` | Target altitude 설정 |
| `:SasDD*MM'SS#` | `0/1` | Target altitude 설정 |
| `:SasDD*MM'SS.SSS#` | `0/1` | Target altitude 설정 |
| `:SzDDD*MM#` | `0/1` | Target azimuth 설정 |
| `:SzDDD*MM'SS#` | `0/1` | Target azimuth 설정 |
| `:SzDDD*MM'SS.SSS#` | `0/1` | Target azimuth 설정 |

### `:MS#` / `:MA#` / `:MN#` / `:MP#` 반환 코드

| 값 | 의미 |
| --- | --- |
| `0` | Goto 수락 |
| `1` | 수평선 제한 아래 |
| `2` | overhead 제한 위 |
| `3` | 컨트롤러가 standby 상태 |
| `4` | 마운트가 Park 상태 |
| `5` | Goto가 이미 진행 중 |
| `6` | 제한 밖 |
| `7` | 하드웨어 fault |
| `8` | 이미 움직이는 중 |
| `9` | 지정되지 않은 오류 |

### Alignment Model 확장 명령

`ALIGN_MAX_NUM_STARS > 1` 빌드에서 노출된다.

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:GX00#` | `n#` | `ax1Cor`, arcsec |
| `:GX01#` | `n#` | `ax2Cor`, arcsec |
| `:GX02#` | `n#` | `altCor`, arcsec |
| `:GX03#` | `n#` | `azmCor`, arcsec |
| `:GX04#` | `n#` | `doCor`, arcsec |
| `:GX05#` | `n#` | `pdCor`, arcsec |
| `:GX06#` | `n#` | FORK/ALTAZM의 `ffCor`, 그 외 `0` |
| `:GX07#` | `n#` | GEM 계열 mount의 `dfCor`, 그 외 `0` |
| `:GX08#` | `n#` | `tfCor`, arcsec |
| `:GX0a#` | `n#` | `hcp`, degrees |
| `:GX0b#` | `n#` | `hca`, arcsec |
| `:GX0c#` | `n#` | `dcp`, degrees |
| `:GX0d#` | `n#` | `dca`, arcsec |
| `:GX09#` | `n#` | 업로드된 star 수. 이후 내부 star index reset |
| `:GX0A#` | `HH:MM:SS#` | 업로드된 star의 actual HA |
| `:GX0B#` | `sDD*MM:SS#` | 업로드된 star의 actual Dec |
| `:GX0C#` | `HH:MM:SS#` | 업로드된 star의 mount HA |
| `:GX0D#` | `sDD*MM:SS#` | 업로드된 star의 mount Dec |
| `:GX0E#` | `n#` | 업로드된 star pier side. 이후 star index advance |
| `:SX00,n#` .. `:SX0d,n#` | `0/1` | 위에 나열된 alignment model coefficient 설정 |
| `:SX09,0#` | `0/1` | Alignment upload state reset |
| `:SX09,1#` | `0/1` | 업로드된 star로 model build |
| `:SX09,2#` | `0/1` | Model active 강제 |
| `:SX0A,HH:MM:SS#` | `0/1` | 현재 star의 actual HA upload |
| `:SX0B,sDD*MM:SS#` | `0/1` | 현재 star의 actual Dec upload |
| `:SX0C,HH:MM:SS#` | `0/1` | 현재 star의 mount HA upload |
| `:SX0D,sDD*MM:SS#` | `0/1` | 현재 star의 mount Dec upload |
| `:SX0E,n#` | `0/1` | Pier side upload 후 다음 star로 advance |

### Goto 확장 설정

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:GX92#` | `n.nnn#` | 현재 slew period, us/step |
| `:GX93#` | `n.nnn#` | 기본/default slew period, us/step |
| `:GX94#` | `n` plus optional ` N` | 현재 pier side: `0` none, `1` east, `2` west |
| `:GX95#` | `0` 또는 `1` | Auto meridian flip 활성 여부 |
| `:GX96#` | `E`, `W`, `B`, 또는 `A` | Preferred pier side |
| `:GX97#` | `n.n#` | 현재 step rate, deg/s |
| `:GX99#` | `n.nnn#` | 허용되는 가장 빠른 slew period, us/step |
| `:SX92,n.nnn#` | `0/1` | 현재 slew period 설정, us/step |
| `:SX93,[1-5]#` | 없음 | Slew preset: `5`=50%, `4`=66.7%, `3`=100%, `2`=150%, `1`=200% |
| `:SX95,0#` 또는 `:SX95,1#` | `0/1` | Automatic meridian flip 비활성/활성 |
| `:SX96,E#` | `0/1` | Preferred pier side east |
| `:SX96,W#` | `0/1` | Preferred pier side west |
| `:SX96,B#` | `0/1` | Preferred pier side best |
| `:SX96,A#` | `0/1` | Preferred pier side automatic |
| `:SX98,0#` 또는 `:SX98,1#` | `0/1` | Meridian flip 중 home pause 비활성/활성 |
| `:SX99,1#` | `0/1` | Home pause 후 계속 진행 |

## Guide / Manual Motion

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:GX90#` | `n.nn#` | Pulse guide rate |
| `:Mgdn#` | 없음 | 방향 `d`로 `n` ms pulse guide. `d`는 `w`, `e`, `n`, `s` |
| `:MGdn#` | `0/1` | `:Mgdn#`와 동일, numeric form |
| `:Mw#` | 없음 | 현재 guide rate로 west 이동 |
| `:Me#` | 없음 | 현재 guide rate로 east 이동 |
| `:Mn#` | 없음 | 현재 guide rate로 north 이동 |
| `:Ms#` | 없음 | 현재 guide rate로 south 이동 |
| `:Mp#` | 없음 | Spiral-search motion |
| `:Q#` | 없음 | 모든 slew 정지, goto abort |
| `:Qe#` / `:Qw#` | 없음 | East/west motion 정지 |
| `:Qn#` / `:Qs#` | 없음 | North/south motion 정지 |
| `:RAn.n#` | 없음 | Axis1 custom guide rate 설정, deg/s |
| `:REn.n#` | 없음 | Axis2 custom guide rate 설정, deg/s |
| `:RG#` | 없음 | Guide rate preset 1x |
| `:RC#` | 없음 | Centering rate preset 8x |
| `:RM#` | 없음 | Find rate preset 20x |
| `:RF#` | 없음 | Fast rate preset 48x |
| `:RS#` | 없음 | Slew rate preset, 현재 goto rate의 절반 |
| `:R0#` .. `:R9#` | 없음 | 숫자 guide-rate preset |

## Park / Home / Limits / Status

### Park

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:hP#` | `0/1` | 마운트 Park |
| `:hQ#` | `0/1` | 현재 위치를 Park 위치로 설정 |
| `:hR#` | `0/1` | 마운트 Unpark |

### Home

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:h?#` | `hasSense,axis1Offset,axis2Offset#` | Home 상태. 소스 주석은 auto-home을 언급하지만 현재 코드는 3개 필드만 반환한다. |
| `:hA0#` / `:hA1#` | 없음 | Boot 시 automatic home 비활성/활성 |
| `:hC#` | 없음 | Home으로 이동 |
| `:hC1,R#` | 없음 | Axis1 home-sense reversal toggle |
| `:hC1,n#` | 없음 | Axis1 home offset 설정, arcsec |
| `:hC2,R#` | 없음 | Axis2 home-sense reversal toggle |
| `:hC2,n#` | 없음 | Axis2 home offset 설정, arcsec |
| `:hF#` | 없음 | Home/cold-start 위치에서 mount reset |

### Limits

헷갈리기 쉬운 GEM east/west pier-side limit geometry의 시각적 설명은 [GOTO_NOTES.md](GOTO_NOTES.md#workflow-4-reachability-and-target-unwinding)를 참고한다.

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:Gh#` | `sDD*#` | Horizon limit |
| `:Go#` | `DD*#` | Overhead limit |
| `:GXE9#` | `n#` | East meridian limit, minutes |
| `:GXEA#` | `n#` | West meridian limit, minutes |
| `:GXEe#` | `n#` | Axis1 minimum limit, degrees |
| `:GXEw#` | `n#` | Axis1 maximum limit, degrees |
| `:GXEB#` | `n#` | Axis1 maximum limit, hours |
| `:GXEC#` | `n#` | Axis2 minimum limit, degrees |
| `:GXED#` | `n#` | Axis2 maximum limit, degrees |
| `:ShsDD#` | `0/1` | Lower altitude limit 설정 |
| `:SoDD#` | `0/1` | Overhead altitude limit 설정 |
| `:SXE9,n#` | `0/1` | East meridian limit 설정, minutes |
| `:SXEA,n#` | `0/1` | West meridian limit 설정, minutes |

### Status

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:Gm#` | `E#`, `W#`, 또는 `N#` | Meridian pier side |
| `:GU#` | status string | 사람이 읽을 수 있는 packed status |
| `:Gu#` | packed bytes | Bit-packed status |
| `:GW#` | 4-char status | Mount type, tracking, parked/home, align-done |
| `:SX97,0#` | `0/1` | Buzzer 비활성 |
| `:SX97,1#` | `0/1` | Buzzer 활성 |
| `:SX97,2#` | `0/1` | Beep |
| `:SX97,3#` | `0/1` | Alert tone |
| `:SX97,4#` | `0/1` | Click |

#### `:GU#` 상태 문자

응답은 활성 조건에서 조립된 순서 있는 문자열이다. 현재 코드에서 사용하는 문자는 다음과 같다.

| 문자 | 의미 |
| --- | --- |
| `n` | Tracking 중이 아님 |
| `N` | 활성 goto 없음 |
| `p` | Park 상태 아님 |
| `I` | Parking 진행 중 |
| `P` | Parked |
| `F` | Park 실패 |
| `e` | Sync-to-encoders-only mode |
| `H` | Home 위치 |
| `h` | Homing 중 |
| `B` | Boot 시 auto-home |
| `S` | PPS synced |
| `G` | Pulse guide 활성 |
| `g` | Guide 활성 |
| `r` | Refraction compensation 활성 |
| `s` | Single-axis compensation mode |
| `t` | Full compensation model 활성 |
| `(` | Lunar tracking rate 선택 |
| `O` | Solar tracking rate 선택 |
| `k` | King tracking rate 선택 |
| `w` | Meridian flip이 home에서 pause됨 |
| `u` | Pause-at-home 활성 |
| `z` | Buzzer 활성 |
| `a` | Automatic meridian flip 활성 |
| `R` | PEC data recorded |
| `/`, `,`, `~`, `;`, `^` | PEC state |
| `E`, `K`, `A`, `L` | GEM, FORK, ALTAZM, ALTALT |
| `o`, `T`, `W` | Pier side none, east, west |
| 마지막 digits | pulse-guide rate, guide rate, general error code |

#### `:Gu#` Packed Status Layout

`Gu`는 binary/pseudo-binary 상태 형식이다. 현재 구현은 바이트를 다음처럼 채운다.

| 바이트 | 내용 |
| --- | --- |
| `0` | tracking/goto/PPS/pulse-guide와 compensation mode |
| `1` | tracking-rate selection과 sync-to-encoders, guide-active |
| `2` | home/homing/auto-home/home-pause/buzzer/auto-flip |
| `3` | mount type과 pier side |
| `4` | PEC state와 PEC-recorded flag |
| `5` | park state |
| `6` | pulse-guide selection |
| `7` | guide-rate selection |
| `8` | general limits/error code |

## Object Library

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:LB#` | 없음 | 현재 constraint에 맞는 이전 object |
| `:LCn#` | 없음 | Record number `n` 선택 |
| `:LI#` | `name,type#` | 현재 object 이름과 type |
| `:LIG#` | 없음 | 현재 object를 goto target으로 load |
| `:LR#` | `name,type,ra,dec#` | 현재 object 정보 반환 후 다음 record로 advance |
| `:LWname,type#` | `0/1` | 현재 target RA/Dec를 다음 빈 record에 write |
| `:LN#` | 없음 | 현재 constraint에 맞는 다음 object |
| `:L$#` | `1` | Catalog name record로 이동 |
| `:LD#` | 없음 | 현재 record clear |
| `:LL#` | 없음 | 현재 catalog clear |
| `:L!#` | 없음 | 모든 catalog clear |
| `:L?#` | `n#` | 전체 catalog의 free records |
| `:Lon#` | `0/1` | Catalog `0..14` 선택 |

Library 명령이 쓰고 읽는 object type code:

`UNK`, `OC`, `GC`, `PN`, `DN`, `SG`, `EG`, `IG`, `KNT`, `SNR`, `GAL`, `CN`, `STR`, `PLA`, `CMT`, `AST`

## PEC

Axis 1에 PEC support가 활성화된 경우 사용할 수 있다.

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:GX91#` | `n#` | PEC analog value |
| `:GXE6#` | `n.nnnnnn#` | Sidereal second당 steps |
| `:GXE7#` | `n#` | NV에서 읽은 worm rotation steps |
| `:GXE8#` | `n#` | PEC buffer size, seconds |
| `:SXE7,n#` | `0/1` | Worm rotation steps 설정 |
| `:VH#` | `nnnnn#` | PEC index sense position, sidereal seconds |
| `:VR#` | `snnn,nnn#` | 현재 PEC segment correction과 segment index |
| `:VRn#` | `snnn#` | Segment `n`의 PEC correction |
| `:Vrn#` | `x0x1...x9#` | Segment `n`부터 시작하는 PEC data의 10-byte hex frame |
| `:VS#` | `n.nnnnnn#` | Worm rotation의 sidereal second당 steps |
| `:VW#` | `nnnnnn#` | Worm rotation steps |
| `:WR+#` | `0/1` | PEC table을 1초 forward rotate |
| `:WR-#` | `0/1` | PEC table을 1초 backward rotate |
| `:WRn,sn#` | 없음 | Segment `n`의 PEC correction write |
| `:$QZ+#` | 없음 | PEC playback 활성 |
| `:$QZ-#` | 없음 | PEC 비활성 |
| `:$QZ/#` | 없음 | PEC recording arm |
| `:$QZZ#` | 없음 | PEC buffer clear |
| `:$QZ!#` | 없음 | PEC data를 NV에 저장 |
| `:$QZ?#` | `I#`, `p#`, `P#`, `r#`, `R#`, optional `.#` | PEC status |

`:$QZ?#`의 PEC status 문자:

| 문자 | 의미 |
| --- | --- |
| `I` | Ignore/off |
| `p` | 재생 준비 |
| `P` | 재생 중 |
| `r` | 기록 준비 |
| `R` | 기록 중 |
| `.` | 이번 초에 index 감지 |

### `:GXUa#` Driver Status Flags

Local ASCII 응답은 comma로 구분된 flag mnemonic이다.

| Flag | 의미 |
| --- | --- |
| `ST` | Standstill |
| `OA` | Output A open load |
| `OB` | Output B open load |
| `GA` | Output A short to ground |
| `GB` | Output B short to ground |
| `OT` | Over-temperature |
| `PW` | Over-temperature warning |
| `GF` | Driver fault |

## Focuser

Focuser가 활성화된 빌드 또는 remote-focuser 빌드에서 사용할 수 있다.

Addressing rule:

- `:FA#`는 현재 선택된 focuser 번호를 반환한다.
- `:FA1#` .. `:FA6#`는 active focuser를 선택한다.
- `:F...#`는 active focuser를 사용한다.
- `:F1...#` .. `:F6...#`는 특정 focuser로 즉시 명령을 보낸다.

Local ASCII focuser 명령의 단위 rule:

- 대문자 `B`, `D`, `G`, `I`, `M`, `R`, `S`는 microns를 사용한다.
- 소문자 `b`, `d`, `g`, `i`, `m`, `r`, `s`는 raw steps를 사용한다.
- 그 외 focuser 명령은 아래에 적힌 것처럼 unitless 또는 고정 단위다.

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:FA#` | `n` | Active focuser number 조회 |
| `:FA1#` .. `:FA6#` | `0/1` | Active focuser 선택 |
| `:hP#` | `0/1` | Standalone/remote focuser 빌드에서 모든 focuser park |
| `:hR#` | `0/1` | Standalone/remote focuser 빌드에서 모든 focuser unpark |
| `:Fa#` | `1` | Primary focuser 존재/선택됨 |
| `:FT#` | `M1#`, `S3#`, etc. | Focuser status와 goto-rate digit |
| `:Fp#` | `0` 또는 `1` | Mode. 현재 구현은 DC/pseudo-absolute면 `1`, 아니면 `0` 반환 |
| `:FI#` / `:Fi#` | `n#` | Full-in/min position |
| `:FM#` / `:Fm#` | `n#` | Maximum position |
| `:Fe#` | `n.n#` | TCF baseline에서의 temperature delta |
| `:Ft#` | `n.n#` | Focuser temperature, C |
| `:Fu#` | `n.nnnnn#` | Microns per step |
| `:FB#` / `:Fb#` | `n#` | Backlash |
| `:FBn#` / `:Fbn#` | `0/1` | Backlash 설정 |
| `:FC#` | `n.nnnnn#` | TCF coefficient, microns per C |
| `:FCsn.n#` | `0/1` | TCF coefficient 설정 |
| `:Fc#` | `0` 또는 `1` | TCF enabled status |
| `:Fc0#` / `:Fc1#` | `0/1` | TCF 비활성/활성 |
| `:FD#` / `:Fd#` | `n#` | TCF deadband |
| `:FDn#` / `:Fdn#` | `0/1` | TCF deadband 설정 |
| `:FP#` | `n#` | DC motor power percent |
| `:FPn#` | `0/1` | DC motor power percent 설정 |
| `:FQ#` | 없음 | Focuser 정지 |
| `:F1#` .. `:F9#` | 없음 | Move/goto rate preset 설정 |
| `:FW#` | `n#` | Working goto rate, um/s |
| `:F+#` | 없음 | Inward 이동 |
| `:F-#` | 없음 | Outward 이동 |
| `:FG#` / `:Fg#` | `sn#` | 현재 위치 |
| `:FRsn#` / `:Frsn#` | 없음 | Relative goto |
| `:FSn#` / `:Fsn#` | `0/1` | Absolute goto |
| `:FZ#` | 없음 | 현재 위치 zero |
| `:FH#` | 없음 | 현재 위치를 home으로 설정 |
| `:Fh#` | 없음 | Home으로 이동 |
| `:GXU4#` .. `:GXU9#` | flags | `Axis.command.cpp`를 노출하는 focuser axis의 driver status |

Rate preset 의미:

| Preset | 의미 |
| --- | --- |
| `1` | 1 um/s move rate |
| `2` | 10 um/s move rate |
| `3` | 100 um/s move rate |
| `4` | 0.5x goto rate, move mode |
| `5` | 0.5x goto rate |
| `6` | 0.66x goto rate |
| `7` | 1x goto rate |
| `8` | 1.5x goto rate |
| `9` | 2x goto rate |

## Rotator

Rotator가 활성화된 빌드 또는 remote-rotator 빌드에서 사용할 수 있다.

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:rA#` | `0/1` | Rotator active |
| `:hP#` | `0/1` | Standalone/remote rotator 빌드에서 rotator park |
| `:hR#` | `0/1` | Standalone/remote rotator 빌드에서 rotator unpark |
| `:rT#` | `M1#`, `SD3#`, etc. | Status string과 rate digit |
| `:rI#` | `n#` | Minimum angle, degrees |
| `:rM#` | `n#` | Maximum angle, degrees |
| `:rD#` | `n.n#` | Degrees per step |
| `:rb#` | `n#` | Backlash, steps |
| `:rbn#` | `0/1` | Backlash 설정 |
| `:rQ#` | 없음 | Motion 정지 |
| `:r1#` .. `:r9#` | 없음 | Move/goto rate preset 설정 |
| `:rW#` | `n.n#` | Working slew rate, deg/s |
| `:rc#` | 없음 | Continuous-move no-op. 호환성을 위해 수락 |
| `:r>#` | 없음 | Clockwise 이동 |
| `:r<#` | 없음 | Counter-clockwise 이동 |
| `:rG#` | `sDDD*MM#` | 현재 angle |
| `:rrsDDD*MM#` | 없음 | Relative goto |
| `:rSsDDD*MM#` | `0/1` | Absolute goto |
| `:rZ#` | 없음 | 위치 zero |
| `:rF#` | 없음 | 현재 위치를 travel의 절반으로 설정 |
| `:rC#` | 없음 | Half-travel / home target으로 이동 |
| `:r+#` | 없음 | Derotation 활성 |
| `:r-#` | 없음 | Derotation 비활성 |
| `:rP#` | 없음 | Parallactic angle로 이동 |
| `:rR#` | 없음 | Derotator reverse direction toggle |
| `:GX98#` | `D#`, `R#`, 또는 `N#` | Rotator capability: derotate, rotate-only, none |
| `:GXU3#` | flags | Standalone/remote 빌드의 rotator axis driver status |

Rotator rate preset:

| Preset | 의미 |
| --- | --- |
| `1` | 0.01 deg/s move rate |
| `2` | 0.1 deg/s move rate |
| `3` | 1.0 deg/s move rate |
| `4` | move rate로 쓰는 0.5x goto rate |
| `5` | 0.5x goto rate |
| `6` | 0.66x goto rate |
| `7` | 1x goto rate |
| `8` | 1.5x goto rate |
| `9` | 2x goto rate |

## Auxiliary Features

Auxiliary features가 활성화된 경우 사용할 수 있다.

Feature slot 번호는 `1..8`이다.

### Discovery

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:GXY0#` | `xxxxxxxx#` | 활성 feature slot의 8문자 bitmap. `1`은 present |
| `:GXYn#` | `name,purpose#` | Slot 이름과 purpose code |

### Slot State

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:GXXn#` | purpose-specific payload | Slot `n`의 현재 state 조회 |
| `:SXXn,Vv#` | `0/1` | Generic value set |
| `:SXXn,Zf#` | `0/1` | Dew-heater zero temperature |
| `:SXXn,Sf#` | `0/1` | Dew-heater span temperature |
| `:SXXn,Ef#` | `0/1` | Intervalometer exposure seconds |
| `:SXXn,Df#` | `0/1` | Intervalometer delay seconds |
| `:SXXn,Cf#` | `0/1` | Intervalometer count |

### `:GXXn#` 응답 형식

Payload는 slot purpose에 따라 달라진다.

| Purpose | 응답 형식 |
| --- | --- |
| Switch / momentary switch / cover switch | `value`와 optional power telemetry |
| Analog output | `value`와 optional power telemetry |
| Dew heater | `enabled,zero,span,deltaT`와 optional power telemetry |
| Intervalometer | `currentCount,exposure,delay,count` |

Power monitoring이 컴파일되어 있으면 local ASCII 구현은 다음을 추가한다.

`;<volts>,<amps>,<flags>`

여기서 flags는 `P`, `C`, `U`, `V`, `T` 또는 `!`를 사용하는 5문자 문자열이다.

## Axis / Motor / Driver Service Commands

Axis service 명령은 `Axis.command.cpp`에 구현되어 있다. Main telescope/mount 빌드에서는 axis 1과 axis 2가 존재하면 접근 가능하다. Rotator는 axis3이 존재하면 노출한다. Focuser는 존재하는 axis 4부터 axis 9까지 노출한다.

| 명령 | 응답 | 설명 |
| --- | --- | --- |
| `:GXAa,p#` | `value,min,max,type,name#` | Axis `a` (`1..9`)의 axis parameter `p` 조회 |
| `:GXAa,M#` | `name#` | Axis `a`의 motor/driver name |
| `:GXAa,0#` | `n#` | Axis `a`의 parameter count |
| `:GXSa#` | `delta,velocity#` | Axis `a`의 servo-only delta와 velocity |
| `:GXUa#` | `flags#` | Axis `a`의 stepper driver status |
| `:SXAC,0#` | `0/1` | Runtime NV axis settings 사용 |
| `:SXAC,1#` | `0/1` | Compile-time `Config.h` axis settings 사용 |
| `:SXAa,R#` | `0/1` | 다음 boot 때 axis `a` settings를 default로 되돌림 |
| `:SXAa,p,value#` | `0/1` | Axis `a`의 axis parameter `p` 설정 |

### `:GXAa,p#` 응답 형식

응답은 다음 형식이다.

`value,min,max,type,name#`

각 필드:

- `value`: 현재 NV value
- `min`과 `max`: 문서화된 범위
- `type`: 펌웨어가 반환하는 axis parameter type code
- `name`: axis parameter table의 parameter name
- 일부 `name` 값은 영어 label이 아니라 `$1`, `$12` 같은 locale token이다.

Axis parameter type code:

| 코드 | 심볼 | 의미 |
| --- | --- | --- |
| `0` | `AXP_INVALID` | 유효하지 않음 / placeholder entry |
| `1` | `AXP_BOOLEAN` | NV에 저장되고 restart/reinit 때 적용되는 boolean value |
| `2` | `AXP_BOOLEAN_IMMEDIATE` | 설정 즉시 적용되는 boolean value |
| `3` | `AXP_INTEGER` | NV에 저장되고 restart/reinit 때 적용되는 integer value |
| `4` | `AXP_INTEGER_IMMEDIATE` | 설정 즉시 적용되는 integer value |
| `5` | `AXP_FLOAT` | NV에 저장되고 일반 numeric field로 보고되는 floating-point value |
| `6` | `AXP_FLOAT_IMMEDIATE` | 설정 즉시 적용되는 floating-point value |
| `7` | `AXP_FLOAT_RAD` | 내부적으로 radians로 저장되는 angular float |
| `8` | `AXP_FLOAT_RAD_INV` | radian/degree 변환을 포함해 내부 저장되는 inverse angular float |
| `9` | `AXP_POW2` | Power-of-two 제한을 받는 integer-like value |
| `10` | `AXP_DECAY` | Driver decay-mode selector |

프로토콜 참고:

- `:GXAa,p#`는 `AXP_FLOAT_RAD`와 `AXP_FLOAT_RAD_INV`를 응답 type code `5`로 normalize하고, 전송용 value/range를 degree 기반 단위로 변환한다.
- Axis parameter 값은 펌웨어 내부에서 float 기반이다. 논리 type이 boolean 또는 integer여도 값은 항상 float이므로 UI는 적절한 control을 보여줄 수 있다.
- Boolean parameter: 일부는 논리 `0`/`1`을 사용하고, 다른 일부는 펌웨어 상수 `OFF = -1`, `ON = -2`를 사용한다. 따라서 UI는 'True'/'False' 또는 'On'/'Off'를 표시할 수 있다.
- `AXP_DECAY`의 경우 UI는 숫자값에 맞는 decay-mode text를 표시한다. `1=MIXED`, `2=FAST`, `3=SLOW`, `4=SPREADCYCLE`, `5=STEALTHCHOP`.

펌웨어에서 현재 사용하는 locale-backed axis parameter name token:

| Token | 의미 |
| --- | --- |
| `$1` | Counts/degree |
| `$2` | Min limit, degs |
| `$3` | Max limit, degs |
| `$4` | Steps/um |
| `$5` | Min limit, um |
| `$6` | Max limit, um |
| `$7` | Reverse |
| `$8` | Microsteps |
| `$9` | Microsteps Goto |
| `$10` | Decay mode |
| `$11` | Decay mode Goto |
| `$12` | mA Hold |
| `$13` | mA Run |
| `$14` | mA Goto |
| `$15` | 256x Interpolate |
| `$16` | P tracking |
| `$17` | I tracking |
| `$18` | D tracking |
| `$19` | P slewing |
| `$20` | I slewing |
| `$21` | D slewing |
| `$22` | Rads/count |
| `$23` | Steps/count ratio |
| `$24` | Max accel, %/s/s |
| `$25` | Min power, % |
| `$26` | Max power, % |

## CAN Remote-Node Variants

아키텍처, 설정, 현재 범위는 [CAN_NOTES.md](CAN_NOTES.md)를 참고한다.

다음 파일은 ASCII LX200-style transport가 아니라 packed CAN message로 동일한 논리 명령군을 구현한다.

- `src/telescope/focuser/local/Focuser.can.command.cpp`
- `src/telescope/rotator/local/Rotator.can.command.cpp`
- `src/telescope/auxiliary/local/Features.can.command.cpp`

이들은 별도의 end-user command name이 아니다. 위에서 설명한 focuser, rotator, auxiliary-feature 명령 집합의 binary transport 구현이다.

주요 transport 차이:

- CAN 응답은 ASCII text가 아니라 binary-packed 형식이다.
- CAN features의 `:GXY0#`는 8문자 ASCII bitmap이 아니라 단일 bitmask byte를 반환한다.
- CAN focuser/rotator driver-status 응답은 comma-separated text flag가 아니라 packed bitfield다.

## Source Coverage

이 문서는 현재 handler에서 작성했다.

- `src/telescope/Telescope.command.cpp`
- `src/telescope/mount/Mount.command.cpp`
- `src/telescope/mount/goto/Goto.command.cpp`
- `src/telescope/mount/guide/Guide.command.cpp`
- `src/telescope/mount/home/Home.command.cpp`
- `src/telescope/mount/library/Library.command.cpp`
- `src/telescope/mount/limits/Limits.command.cpp`
- `src/telescope/mount/park/Park.command.cpp`
- `src/telescope/mount/pec/Pec.command.cpp`
- `src/telescope/mount/site/Site.command.cpp`
- `src/telescope/mount/status/Status.command.cpp`
- `src/lib/axis/Axis.command.cpp`
- `src/telescope/focuser/local/Focuser.command.cpp`
- `src/telescope/rotator/local/Rotator.command.cpp`
- `src/telescope/auxiliary/local/Features.command.cpp`
- 대응되는 CAN transport handler
- `src/libApp/commands/ProcessCmds.cpp`

