# 성능·화면 비교

```sh
python -m tests.perf.vitals --site BUILD --flash SNAPSHOT/flash \
  --output REPORT.json --details .qa/raw-resources.json
python -m tests.perf.vitals --live https://mash1384.github.io/signal-desk/ \
  --output .qa/public-vitals.json
python -m tests.perf.visuals --site BUILD --flash SNAPSHOT/flash --out CAPTURES
python -m tests.perf.visuals --compare BEFORE AFTER --out DIFFS
```

Python 3.9+, 시스템 Chrome(`--channel chrome`, 기본값),
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

고정 스냅샷: gh-pages `74eafc2c5f9e3ed638a60bd7300489e303076d6b`,
flash `b172cc2299f4d94caeafbb00642e4c0798bc9710`.
