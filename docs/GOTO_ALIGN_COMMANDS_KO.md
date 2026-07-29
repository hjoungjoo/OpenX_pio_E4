# Goto / Sync / Multi-Point Align 명령 요약

이 문서는 현재 OnStepX_pio 설정 기준으로 일반 goto, sync, multi-point alignment에 자주 쓰는 명령을 간단히 정리한 것이다.

현재 주요 설정:

- `MOUNT_TYPE ALTAZM_UNL`
- `GOTO_FEATURE ON`
- `ALIGN_MAX_STARS AUTO`
- PlatformIO 기본 env는 ESP32 계열이므로 `AUTO` align 최대값은 보통 9점이다.

## 1. 일반 Goto

RA/Dec target을 지정한 뒤 `:MS#`로 이동한다.

| 명령 | 의미 |
| --- | --- |
| `:SrHH:MM:SS#` | target RA 설정 |
| `:SdsDD*MM:SS#` | target Dec 설정 |
| `:MS#` | 현재 RA/Dec target으로 goto |
| `:Gr#` | target RA 조회 |
| `:Gd#` | target Dec 조회 |

Alt/Az target을 직접 지정하려면 다음 명령을 쓴다.

| 명령 | 의미 |
| --- | --- |
| `:SasDD*MM'SS#` | target altitude 설정 |
| `:SzDDD*MM'SS#` | target azimuth 설정 |
| `:MA#` | 현재 Alt/Az target으로 goto |
| `:Gal#` | target altitude 조회 |
| `:Gz#` | target azimuth 조회 |

동작 확인과 중지는 다음 명령을 쓴다.

| 명령 | 의미 |
| --- | --- |
| `:D#` | goto/motion 중이면 `0x7f#`, 아니면 `#` |
| `:Q#` | 전체 slew/goto 중지 |

### Goto 반환 코드

`:MS#`, `:MA#`, `:MN#`, `:MP#`는 `0`..`9`를 반환한다.

| 값 | 의미 |
| --- | --- |
| `0` | goto 수락 |
| `1` | horizon limit 아래 |
| `2` | overhead limit 위 |
| `3` | controller standby |
| `4` | mount parked |
| `5` | goto 이미 진행 중 |
| `6` | limit 밖 |
| `7` | hardware fault |
| `8` | 이미 motion 중 |
| `9` | 기타 오류 |

## 2. Sync

Sync는 현재 물리 위치를 target 좌표에 맞추어 좌표계를 보정한다. 일반 goto처럼 이동하지 않는다.

| 명령 | 의미 |
| --- | --- |
| `:CS#` | 현재 target coordinate로 sync |
| `:CM#` | 현재 catalog/database object로 sync |

주의: alignment가 진행 중일 때 `:CS#`와 `:CM#`는 일반 sync가 아니라 align point accept처럼 처리된다.

## 3. Multi-Point Alignment

기본 흐름은 다음과 같다.

```text
:A3#                 3-star alignment 시작
:SrHH:MM:SS#         첫 번째 별 RA 설정
:SdsDD*MM:SS#        첫 번째 별 Dec 설정
:MS#                 해당 별로 goto
수동 이동             별을 시야 중앙에 맞춤
:A+#                 현재 align point 수락
반복
:AW#                 alignment model을 NV에 저장
```

주요 alignment 명령:

| 명령 | 의미 |
| --- | --- |
| `:A?#` | align 상태 조회. `mno#` 형식 |
| `:A1#` .. `:A9#` | n-star manual alignment 시작 |
| `:A+#` | 현재 align point 수락 |
| `:AW#` | alignment model을 NV에 저장 |

`:A?#` 응답 `mno#`의 의미:

| 문자 | 의미 |
| --- | --- |
| `m` | 최대 align star 수 |
| `n` | 현재 align star 번호 |
| `o` | 이번 alignment에서 필요한 마지막 star 번호 |

별을 중앙에 맞출 때는 guide/manual motion 명령을 쓴다.

| 명령 | 의미 |
| --- | --- |
| `:Mn#` | north 방향 이동 |
| `:Ms#` | south 방향 이동 |
| `:Me#` | east 방향 이동 |
| `:Mw#` | west 방향 이동 |
| `:Qn#`, `:Qs#` | north/south 이동 정지 |
| `:Qe#`, `:Qw#` | east/west 이동 정지 |
| `:R0#` .. `:R9#` | guide/move rate preset |
| `:RG#`, `:RC#`, `:RM#`, `:RF#`, `:RS#` | guide, centering, find, fast, slew rate preset |

## 4. Alignment Model 확장 명령

외부 앱이나 컨트롤러가 alignment model과 star 데이터를 직접 업로드/조회할 때 사용한다.

| 명령 | 의미 |
| --- | --- |
| `:GX00#` .. `:GX0d#` | model coefficient 조회 |
| `:SX00,n#` .. `:SX0d,n#` | model coefficient 설정 |
| `:SX09,0#` | star upload 상태 reset |
| `:SX0A,HH:MM:SS#` | 현재 star의 actual HA upload |
| `:SX0B,sDD*MM:SS#` | 현재 star의 actual Dec upload |
| `:SX0C,HH:MM:SS#` | 현재 star의 mount HA upload |
| `:SX0D,sDD*MM:SS#` | 현재 star의 mount Dec upload |
| `:SX0E,n#` | pier side upload 후 다음 star로 advance |
| `:SX09,1#` | 업로드된 star로 model build |
| `:SX09,2#` | model active 강제 |

## 5. Tracking Compensation

Alignment model은 goto 좌표 변환에 사용된다. 추적 보정에도 model을 쓰려면 별도 tracking compensation 명령을 사용한다.

| 명령 | 의미 |
| --- | --- |
| `:To#` | full compensation model tracking 활성 |
| `:Tr#` | refraction compensation 활성 |
| `:Tn#` | compensation 비활성 |
| `:T1#` | single-axis compensation |
| `:T2#` | dual-axis compensation |

현재 `Config.h`는 `TRACK_COMPENSATION_DEFAULT OFF`이므로 부팅 직후 tracking compensation은 꺼진 상태다.

## 6. 참고 구현 위치

- `src/telescope/mount/goto/Goto.command.cpp`: goto, sync, alignment 명령 처리
- `src/telescope/mount/goto/Goto.cpp`: goto/sync 실행과 align point 추가
- `src/telescope/mount/coordinates/Align.ref.cpp`: alignment model 계산
- `src/telescope/mount/coordinates/Transform.cpp`: pointing model/refraction 좌표 변환
- `docs/COMMAND_REFERENCE_KO.md`: 전체 명령 레퍼런스
