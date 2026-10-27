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

일정의 본문(`.it p`, `.rs p`)과 강조 숫자(`b.nm`)는 `calendar-text.css`의 작은 Pretendard 조각을
HTML에 직접 넣고 같은 data URL을 미리 읽어 첫 그리기부터 최종 폭을 사용한다.
미리 읽지 않으면 작은 조각도 첫 화면을 그린 다음 적용되어 줄이 이동한다. `ek.js`의 `numHi`가
만드는 숫자·부호·단위와 영문 ASCII·일반 문장부호를 포함하며, 가변 굵기와 `tnum`을 유지한다.
숫자만 먼저 읽으면 입력에 따라 영문 본문과 섞여 줄바꿈이 달라질 수 있어 본문도 같은 글꼴을 쓴다.
원래 동적 CSS가 제공하지 않는 U+2212(마이너스)는 기존 대체 글꼴을 유지한다.
`calendar-text.json`에 고정 원본·결과 해시·글자 목록을 기록한다.
원본과 라이선스는 기존 QA의 Pretendard 1.3.9와 `Pretendard-OFL.txt`다.

수정한 일정·메뉴 조각의 내부 가족·고유·전체·PostScript·가변 인스턴스 이름은
각각 `DF Calendar Text`·`DF Nav`로 바꾼다. 원본의 저작권과 OFL은 보존한다.
기존 `pretendard-nav.woff2` 파일 경로는 캐시·참조 호환을 위해 유지하지만 글꼴의
내부 식별 이름으로 예약 이름을 사용하지 않는다. [OFL FAQ 2.6](https://openfontlicense.org/ofl-faq/#2-6-is-subsetting-a-webfont-considered-modification)에 따라
웹 글꼴 조각도 수정본으로 취급한다. `tests/perf/test_font_names.py`가 재발을 검사한다.

```sh
python -m tests.perf.calendar_font --out web/assets/fonts
```
