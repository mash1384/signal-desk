# 성능·화면 비교

```sh
python -m tests.perf.vitals --site BUILD --flash SNAPSHOT/flash \
  --output REPORT.json --details .qa/raw-resources.json
python -m tests.perf.vitals --live https://mash1384.github.io/signal-desk/ \
  --output .qa/public-vitals.json
python -m tests.perf.visuals --site BUILD --flash SNAPSHOT/flash --out CAPTURES
python -m tests.perf.visuals --compare BEFORE AFTER --out DIFFS
```

Python 3.9+, Node 24+(공유 마크업 빌드), OpenSSL, 시스템 Chrome(`--channel chrome`, 기본값),
`tests/requirements.txt` + `tests/perf/requirements.txt`를 사용한다.
CI에서는 설치한 Chromium에 `--channel chromium`을 지정한다.

측정 v5는 8페이지×1440/390px×3회 새 브라우저 컨텍스트의 중앙값이다.
높이 1000px, DPR 1, `reduced_motion=reduce`, 한국어, 고정 스냅샷 시각을
쓴다. 모바일은 CDP 지연 150ms, 내려받기 200,000B/s(1.6Mbps), 올리기
93,750B/s다. 공개 모드는 실제 시각/데이터이므로 로컬 회귀 기준이 아니다.

로컬 외부 요청은 기존 오프라인 fixture로만 처리한다. `route.fulfill`은
Chrome 다운로드 제한을 우회하므로, 요청을 임시 TLS 서버로 보내 실제
소켓에서 전달한다. 자체 서명 인증서는 임시 디렉터리에만 있고 해당
컨텍스트에서만 허용한다. HTML/CSS/JS/JSON/SVG는 gzip level 6으로
압축하며 폰트·이미지는 그대로 보낸다. 공개 Pages에서 gzip 사용을
확인했다. `--compression identity`는 별도 진단용이며 gzip 기준과
비교하면 안 된다.

전송량은 `Network.loadingFinished.encodedDataLength`(응답 헤더 포함),
요청 수는 HTTP(S)만 센다. CDP에 나타나는 `data:` 이미지는 요청 수에
넣지 않는다. `--from-raw`는 저장한 CDP 원자료를 같은 합산 함수로
재계산하며 브라우저를 다시 방문하지 않는다. 측정 종료 전에 다운로드
완료를 확인하고, 오류·미완료 응답이 있으면 종료 코드 1을 반환한다.

CLS는 사용자 입력 제외, 간격 1초 미만·길이 5초 미만인 세션의 최대값이다.
LCP는 buffered PerformanceObserver 값을 사용한다. 첫 networkidle 뒤
3초를 관찰하고 이후 진행 중인 요청까지 기다린다. 병렬 브라우저·빌드를
같이 돌리지 않는다. 스크린샷은 같은 시각·난수 시드로 페이지 전체를
스크롤한 뒤 맨 위로 돌아와 찍는다(성능 측정은 스크롤하지 않는다).
랜딩의 GSAP 고정 장면은 전체 페이지 촬영의 임시 뷰포트 변경에 영향을
받으므로 첫 화면을 뷰포트로 찍는다. `--landing-scenes`를 주면 동일한
스크롤 진행률의 파형·지구본·로고도 별도로 찍고 촬영 전후 높이를 검증한다.
가짜 시계로 rAF가 멈춘 동안 WebGL의 마지막 프레임만 보존한다.
`--pages ''`로 랜딩만 다시 찍으면 기존 capture.json의 다른 페이지는 유지한다.

## 회귀 검사

```sh
python -m tests.perf.budgets --before BEFORE.json --after AFTER.json
python -m tests.perf.browser --site BUILD
python -m tests.perf.visuals --site BUILD --forbid-raw --out CAPTURES
python -m tests.perf.fonts CAPTURES/capture.json
node --test tests/perf/candles.test.mjs
python -m tests.perf.candle_visuals --before OLD_BUILD --after BUILD --out CANDLES
python -m tests.perf.incremental --work NEW_EMPTY_DIRECTORY
python -m tests.perf.components --site BUILD --old-site OLD_BUILD
python -m tests.perf.negative --site BUILD --before BEFORE.json --after AFTER.json \
  --capture CAPTURES/capture.json --work ANOTHER_NEW_DIRECTORY
python -m tests.perf.stages --published SNAPSHOT/gh-pages --flash SNAPSHOT/flash \
  --out NEW_BUILD --output .qa/stages.json
```

각 스냅샷 인수의 기본값은 `.qa/snapshot-r/`이다. 다른 스냅샷을 쓰면
모든 도구에 같은 `--flash`와 필요한 `--published`를 명시한다.
`components --old-site`는 여러 번 지정할 수 있다. `browser`는 지연,
데이터 차단, 새/기존/실패 Worker 경로와 숨김 탭을 검사한다.

budgets는 48개 원시 기록, 16개 중앙값, 방법 일치를 검증한 뒤 모바일
LCP 2500ms/CLS 0.1, 전 대비 LCP +20%, 커밋된 전송 상한을 검사한다.
최초 실측 후 `--write-caps`로 실측+15% 상한을 만들 수 있지만 기존
상한과 전 측정+15%보다 높이지 않는다. CI는 상한을 다시 생성하지 않는다.

font 검사는 원본이 지원한 문자의 손실과 미검토 대체 문자를 거부한다.
원본 JetBrains Mono에도 없는 한글·일부 기호는 기존 시스템 대체 글꼴을
유지하며 manifest에 명시한다. 모든 문자가 WOFF 안에 있다는 뜻은 아니다.
negative는 숫자 변조뿐 아니라 실제 폰트/HTML/JS/빌드 사본을 손상시켜
각 검사의 실패를 확인한다. 원본 코드·빌드는 수정하지 않는다.

CI의 `qa-harness.yml` performance job은 같은 runner에서 원본/현재를
연속 측정한다. 로컬 수치를 다른 OS의 CPU 수치와 직접 비교하지 않는다.
이 도구들은 배포 전 `tests.gate`에 추가되지 않는다.

고정 스냅샷: gh-pages `74eafc2c5f9e3ed638a60bd7300489e303076d6b`,
flash `b172cc2299f4d94caeafbb00642e4c0798bc9710`.
운영 gh-pages는 매번 amend/force-push하므로 과거 SHA만으로는 CI 자료를
영구 재현할 수 없다. `fixtures/snapshot-r.tar.gz`에 당시 공개 JSON 22개를
보관했다(2,098,979B). manifest에는 출처 커밋, 압축 파일과 각 JSON의
SHA-256이 있다. 다음 명령은 새 디렉터리에만 복원하며 해시·파일 목록·경로를
검사한다. 고장 주입은 압축 파일 1바이트를 바꾸어 복원 실패를 확인한다.

```sh
python -m tests.perf.snapshot --out .qa/snapshot-r
```

성능 브라우저가 받지 않는 소셜 미리보기 OG JPEG 85MB는 제외했다.
이 자료로 다시 빌드한 비-OG 산출물 6,101개는 원래 입력의 결과와 해시가 같다.
일반 모션의 인트로 영상, 실제 기기·현장 네트워크의 LCP는 이 reduced-motion
비교로 검증되지 않는다.
