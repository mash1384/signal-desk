# 글꼴 출처와 재현

`manifest.json`은 Google Fonts에서 받은 원본의 URL·버전·SHA-256과
서브셋의 SHA-256·글자 목록을 기록한다. 원본은 기존 QA의 고정 자산
`tests/e2e/vendor`와 동일하다. OFL 라이선스 전문과 그 출처/해시는
각 `*-OFL.txt`, `licenses.json`에 있다.

JetBrains Mono 2.211(v24), Michroma 1.100(v21)의 윤곽·힌팅·가변 축은
유지한다. 로고는 대문자 `ADEFLNO`, mono는 8페이지×한/영×두 폭의
DOM/캔버스에서 수집한 글자와 동적 가격·티커용 ASCII/기호를 사용한다.
`font-display: swap`을 지정한다. Inter의 기존 CSS만 분리해 두어
Inter 제거를 별도 커밋으로 되돌릴 수 있게 한다.

```sh
python -m tests.perf.fonts CAPTURE/capture.json --build
python -m tests.perf.fonts CAPTURE/capture.json
```

재현 도구: FontTools 4.60.2 / Brotli 1.2.0 / Zopfli 0.2.3.post1.
[FontTools subset](https://fonttools.readthedocs.io/en/latest/subset/index.html)을
사용하며, 수집 원자료는 최적화 캡처와 함께 보관한다.

원본 JetBrains Mono에는 한글과 일부 화살표/도형이 없다. 이 글자들은
원래부터 시스템 대체 글꼴로 그려졌으므로 그대로 유지한다. 검사 결과는
서브셋 누락과 기존 대체 글자를 따로 출력한다. 기존 대체 글자를
JetBrains Mono에 들어 있는 것처럼 보고하지 않는다.
