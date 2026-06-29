# 전체 소스 수정 히스토리

이 문서는 현재 작업 트리에 반영된 소스 변경 전체를 파일 단위로 기록한다.

작성 기준일: 2026-06-29  
작업 목적: 동작 안정성 개선, 명령 처리 경로 안정화, 입력 검증 보강  
빌드 환경: `onstepx_esp32_mf_oozoo_e4`

## 변경 요약

이번 변경은 안정성 리뷰에서 선택한 1, 2, 3, 5, 6번 항목을 실제 코드에 반영한 것이다.

- 모터 구동, 추적 주기, 축 제어 알고리즘 자체는 변경하지 않았다.
- 별 추적과 모터 제어의 동작 정확도를 해치지 않도록 명령 파서, 통신 큐, 입력 검증 계층에만 손을 댔다.
- 웹 UI, WiFi, Ethernet 명령 경로는 내부 명령 브로커를 통해 순서와 응답 매칭을 맞추도록 정리했다.
- 잘못된 입력값이 설정 저장소에 기록되는 상황을 줄였다.
- 내부 `SerialLocal` 큐가 가득 찬 상황에서 읽지 않은 데이터를 덮어쓰지 않도록 보호했다.

## 전체 변경 파일

| 구분 | 파일 | 수정 이력 |
| --- | --- | --- |
| 명령 파서 | `src/lib/commands/BufferCmds.cpp` | 짧은 명령의 파라미터 추출 경계 보호 |
| 좌표 변환 | `src/lib/convert/Convert.cpp` | DMS 초 단위 구분자 파싱 오류 수정 |
| Ethernet 명령 서버 | `src/lib/ethernet/cmdServer/CmdServer.cpp` | 응답 버퍼 크기 전달 |
| WiFi 명령 서버 | `src/lib/wifi/cmdServer/CmdServer.cpp` | 응답 버퍼 크기 전달 |
| 내부 직렬 큐 | `src/lib/serial/Serial_Local.cpp` | 수신 큐 여유 공간 확인 후 전송 |
| 내부 직렬 큐 | `src/lib/serial/Serial_Local.h` | 송신 큐 full 상태에서 write 거부 |
| 웹 명령 처리 | `src/plugins/website/libApp/cmd/Cmd.cpp` | 직접 `SERIAL_LOCAL` 접근 제거, `CommandBroker` 경로로 통일 |
| 웹 명령 인터페이스 | `src/plugins/website/libApp/cmd/Cmd.h` | 응답 버퍼 크기 인자와 배열 템플릿 overload 추가 |
| 홈 설정 명령 | `src/telescope/mount/home/Home.command.cpp` | 홈 오프셋 숫자 변환과 범위 검증 강화 |
| 사이트 설정 명령 | `src/telescope/mount/site/Site.command.cpp` | 시간대 범위 조건 수정 |
| 날짜 파서 | `src/telescope/mount/site/Site.cpp` | `MM/DD/YYYY` 4자리 연도 파싱 수정 |
| 문서 인덱스 | `docs/README.md` | 변경 히스토리 문서 링크 추가 |

## 파일별 상세 이력

### `src/lib/commands/BufferCmds.cpp`

수정 위치:

- `Buffer::getParameter()`

기존 문제:

- `:Q#`처럼 파라미터가 없는 짧은 명령에서 `cbp - 4`가 음수 위치로 해석될 수 있었다.
- 이 경우 `pb[-1] = 0` 형태의 버퍼 앞쪽 쓰기 위험이 있었다.

변경 내용:

- 명령 문자열의 실제 길이를 `strlen(cb)`로 확인한다.
- 끝 문자가 `#`이면 파라미터 계산 전에 제외한다.
- 파라미터 길이가 0보다 클 때만 `memmove()`를 수행한다.
- 복사 길이를 `bufferSize - 1`로 제한하고 널 종료를 보장한다.

효과:

- 중지/중단 계열의 짧은 명령이 들어와도 파라미터 버퍼 앞쪽을 쓰지 않는다.
- 체크섬 명령을 포함한 기존 명령 파라미터 처리 흐름은 유지된다.

### `src/plugins/website/libApp/cmd/Cmd.cpp`

수정 위치:

- `OnStepCmd::serialRecvFlush()`
- `OnStepCmd::processCommand()`
- `OnStepCmd::command()`

기존 문제:

- 웹 명령 처리 경로가 `SERIAL_LOCAL`에 직접 접근해 송수신 순서가 다른 내부 명령 경로와 어긋날 수 있었다.
- 응답이 비어 있을 때 `response[strlen(response) - 1]`로 버퍼 앞쪽을 읽을 수 있었다.
- 오래된 응답이 다음 명령 응답처럼 섞일 가능성이 있었다.

변경 내용:

- `CommandBroker.h`를 포함하고 웹 명령도 `CommandBroker`를 통해 처리하도록 변경했다.
- 응답이 필요 없는 명령은 `commandBroker.send()`를 사용한다.
- 응답이 필요한 명령은 `commandBroker.request()`와 `commandBroker.result()`를 사용한다.
- 응답 복사는 `sstrcpyex()`로 버퍼 크기를 지키도록 했다.
- 응답 끝 확인은 `len > 0 && response[len - 1] == '#'`로 보호했다.
- `serialRecvFlush()`는 브로커가 순서를 관리한다는 주석만 남기고 직접 큐를 비우지 않도록 했다.

효과:

- 웹 UI 명령, 내부 명령 큐, 응답 매칭의 일관성이 좋아진다.
- 타임아웃 또는 빈 응답 상황에서 잘못된 메모리 읽기를 하지 않는다.
- 응답 순서가 중요한 명령에서 안정성이 올라간다.

### `src/plugins/website/libApp/cmd/Cmd.h`

수정 위치:

- `OnStepCmd::processCommand()`
- `OnStepCmd::command()`

변경 내용:

- `processCommand()`에 `responseSize` 인자를 추가했다.
- 기존 호출 호환을 위해 기본값 `80`을 유지했다.
- `command(const char*, char*, size_t)` overload를 추가했다.
- 고정 크기 배열을 넘길 때 배열 크기를 자동으로 전달하는 템플릿 overload를 추가했다.

효과:

- 호출부의 실제 응답 버퍼 크기를 명령 처리 함수가 알 수 있다.
- 작은 응답 버퍼를 사용하는 서버 코드에서도 안전하게 복사할 수 있다.

### `src/lib/wifi/cmdServer/CmdServer.cpp`

수정 위치:

- WiFi 명령 처리 중 `onStep.processCommand()` 호출부

변경 내용:

- `char result[40]`의 실제 크기인 `sizeof(result)`를 `processCommand()`에 전달하도록 수정했다.

효과:

- WiFi 명령 응답이 40바이트 버퍼 안에서 처리된다.
- 웹 명령 인터페이스의 버퍼 크기 보강과 일관된다.

### `src/lib/ethernet/cmdServer/CmdServer.cpp`

수정 위치:

- Ethernet 명령 처리 중 `onStep.processCommand()` 호출부

변경 내용:

- `char result[40]`의 실제 크기인 `sizeof(result)`를 `processCommand()`에 전달하도록 수정했다.

효과:

- Ethernet 명령 응답이 40바이트 버퍼 안에서 처리된다.
- WiFi 명령 서버와 같은 방식으로 응답 크기를 관리한다.

### `src/lib/serial/Serial_Local.cpp`

수정 위치:

- `SerialLocal::transmit()`

기존 문제:

- 내부 수신 큐의 여유 공간을 확인하지 않고 데이터를 쓰고 있었다.
- 큐가 가득 찬 상황에서 아직 읽지 않은 응답 데이터가 덮어써질 가능성이 있었다.

변경 내용:

- 전송 데이터 길이를 `size_t`로 계산한다.
- ring buffer의 현재 head/tail 기준으로 남은 공간을 계산한다.
- 명령 전체가 들어갈 공간이 없으면 아무것도 쓰지 않고 반환한다.
- 쓰기 후 tail 위치에 널 종료 문자를 유지한다.

효과:

- 큐 overflow로 인한 응답 손상을 줄인다.
- 부분 명령이 큐에 들어가 다음 처리 흐름을 깨뜨리는 위험을 줄인다.

### `src/lib/serial/Serial_Local.h`

수정 위치:

- `SerialLocal::write(uint8_t data)`

기존 문제:

- 송신 큐가 가득 찬 상태에서도 tail을 진행시켜 읽지 않은 데이터를 덮어쓸 수 있었다.

변경 내용:

- 다음 tail 위치를 먼저 계산한다.
- 다음 tail이 현재 읽기 인덱스와 같으면 큐가 full인 것으로 보고 `0`을 반환한다.
- 공간이 있을 때만 데이터를 기록하고 tail을 갱신한다.

효과:

- 송신 큐 full 상태에서 데이터 덮어쓰기를 방지한다.
- `Stream::write()`의 의미에 맞게 쓰기 실패를 `0`으로 알린다.

### `src/telescope/mount/site/Site.command.cpp`

수정 위치:

- 시간대 설정 명령 처리

기존 문제:

- 시간대 범위 조건이 `hour >= -13.75 || hour <= 12.0` 형태라 대부분의 값이 통과할 수 있었다.

변경 내용:

- 범위 조건을 `hour >= -13.75 && hour <= 12.0`으로 수정했다.

효과:

- 허용 범위를 벗어난 시간대 값이 저장되지 않는다.
- 잘못된 시간대가 추적 기준 계산에 영향을 줄 가능성을 낮춘다.

### `src/telescope/mount/site/Site.cpp`

수정 위치:

- `Site::strToDate()`

기존 문제:

- `ymd` 포인터를 이동한 뒤 `strlen(ymd) == 10`을 검사해 `MM/DD/YYYY`의 4자리 연도 판단이 실패할 수 있었다.

변경 내용:

- 입력 문자열의 원래 길이를 `size_t len`에 먼저 저장한다.
- 길이 검증과 4자리 연도 판단 모두 저장된 `len`을 사용한다.

효과:

- `MM/DD/YY`와 `MM/DD/YYYY` 형식이 의도대로 구분된다.
- 4자리 연도 입력이 잘못 해석될 가능성을 줄인다.

### `src/telescope/mount/home/Home.command.cpp`

수정 위치:

- Axis1/Axis2 홈 오프셋 설정 명령

기존 문제:

- 홈 오프셋 범위 조건이 `l >= -648000 || l <= 648000` 형태라 범위 검사가 사실상 항상 통과할 수 있었다.
- `atol()`은 잘못된 문자열을 0으로 처리할 수 있어 오류 입력을 정상 값처럼 저장할 가능성이 있었다.
- 범위 오류가 있어도 이후 설정 저장이 호출될 수 있었다.

변경 내용:

- `strtol()`을 사용해 숫자 변환 종료 위치를 확인한다.
- 입력 전체가 숫자로 변환된 경우만 정상으로 처리한다.
- 허용 범위를 `-648000` 이상, `648000` 이하로 검사한다.
- `commandError`가 없는 경우에만 `nv().kv().put()`을 호출한다.

효과:

- 잘못된 홈 오프셋 값이 비휘발성 설정에 저장되는 위험을 줄인다.
- 홈 센싱 기준값이 입력 오류로 오염될 가능성을 낮춘다.

### `src/lib/convert/Convert.cpp`

수정 위치:

- `Convert::dmsToDouble()`

기존 문제:

- 초 단위 구분자를 확인할 때 `*dms++ != ':' && *dms++ != '\''` 형태라 첫 번째 비교가 실패하면 포인터가 한 번 더 증가했다.
- 이로 인해 정상 문자열에서도 초 단위 파싱 위치가 어긋날 수 있었다.

변경 내용:

- 구분자 문자를 `char sep = *dms++`로 한 번만 읽는다.
- `sep`가 `:` 또는 `'`인지 검사한다.

효과:

- DMS 좌표 문자열의 초 단위 파싱이 안정적으로 동작한다.
- 좌표 입력 명령에서 정상 문자열이 잘못 거부되거나 잘못 해석될 가능성을 줄인다.

### `docs/README.md`

수정 위치:

- Core Documents 목록

변경 내용:

- `CHANGE_HISTORY.md` 항목을 추가했다.

효과:

- 문서 목록에서 전체 소스 수정 히스토리를 바로 찾을 수 있다.

## 검증 이력

### 정적 패턴 확인

다음 위험 패턴이 남아 있지 않은 것을 확인했다.

- `pb[cbp-4]`
- `response[strlen(response) - 1]`
- 웹 명령 경로의 직접 `SERIAL_ONSTEP.receive/transmit/available/read`
- 시간대와 홈 오프셋의 잘못된 `||` 범위 검사
- DMS 구분자 검사 중 `*dms++`를 두 번 소비하는 패턴

### PlatformIO 빌드

빌드 명령:

```powershell
C:\Users\hjoun\.platformio\penv\Scripts\pio.exe run
```

빌드 결과:

| 항목 | 결과 |
| --- | --- |
| Environment | `onstepx_esp32_mf_oozoo_e4` |
| Build | Success |
| RAM | 19.3% (`63268 / 327680` bytes) |
| Flash | 38.9% (`1224589 / 3145728` bytes) |
| 소요 시간 | 66.84 seconds |

## 장비 연결 후 확인 권장 순서

1. 웹 UI에서 응답이 있는 명령과 응답이 없는 명령을 각각 실행한다.
2. WiFi 명령 서버에서 일반 LX200 명령 응답을 확인한다.
3. Ethernet 명령 서버에서 같은 명령 응답을 확인한다.
4. 시간대 설정 명령에 정상값과 범위 밖 값을 넣어 저장 여부를 확인한다.
5. 날짜 설정 명령에서 `MM/DD/YY`, `MM/DD/YYYY` 형식을 각각 확인한다.
6. 홈 오프셋 설정 명령에서 정상 숫자, 범위 밖 숫자, 비숫자 입력을 확인한다.
7. DMS 좌표 입력 명령에서 초 단위가 포함된 좌표 문자열을 확인한다.
8. 추적 상태에서 명령 부하가 있을 때 모터 동작과 별 추적이 끊기지 않는지 확인한다.

## 의도적으로 변경하지 않은 영역

- 모터 step 생성 주기
- 축별 추적률 계산
- Goto 이동 프로파일
- TMC 드라이버 전류, 마이크로스텝, 스텔스/스프레드 설정
- 하드웨어 핀맵
- UART 1-wire 연결 구조
- `DRIVER_STATUS` 설정값

위 항목은 실제 장비 연결 후 별도 측정 결과를 기준으로 조정하는 것이 안전하다.
