# SIGNAL — 크립토 · AI · 매크로 시그널 데스크

해외 크립토·AI·경제 속보를 한곳에 모으고, 각 뉴스 뒤에 비트코인 등 가격이 실제로 얼마나 움직였는지(15분·1시간·24시간)를 실측해 보여 주는 정적 사이트입니다.

- 사이트: https://mash1384.github.io/signal-desk/
- 서버 없음. GitHub Actions가 15분마다 수집·측정·빌드하고 `gh-pages` 브랜치에 배포합니다.

## 구조

```
pipeline/            Python 3 표준 라이브러리만 사용 (이미지·요약은 선택 패키지)
  config.py          수집원, 자산 사전, 분류 키워드, 측정 구간, 알림 정책
  collect.py         RSS·Atom 수집, 정제, 중복 제거
  classify.py        키워드 분류 (카테고리, 자산, 중요도, 이벤트 유형)
  market.py          시세·1분봉(Binance → Coinbase), 업비트, 환율, 공포·탐욕, 경제 일정
  impact.py          임팩트 실측 (수익률, z 점수, 강·중·약)
  summarize.py       Claude 한국어 3줄 요약 (ANTHROPIC_API_KEY가 있을 때만)
  notify.py          텔레그램 알림 (토큰이 있을 때만)
  og.py              공유 카드 이미지 (Playwright + 크롬)
  build.py           정적 페이지 생성
  run.py             전체 실행
web/assets/          styles.css, app.js, icon.svg
tests/               단위 테스트
.github/workflows/   pipeline.yml (15분 주기)
```

상태(기사·측정값·알림 기록)는 배포된 사이트의 `data/` 폴더에 저장되고, 다음 실행이 그것을 읽어 이어 갑니다.

## 로컬 실행

```bash
python3 -m unittest discover -s tests
python3 -m pipeline.run --out dist --no-images          # 처음
python3 -m pipeline.run --prev dist --out dist2         # 이어서
```

`dist/`를 `/signal-desk/` 경로로 서빙하면 됩니다. 이미지까지 만들려면 `pip install playwright`와 크롬이 필요합니다.

## 선택 설정 (GitHub → Settings → Secrets and variables → Actions)

| 이름 | 종류 | 효과 |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Secret | 기사 한국어 제목·3줄 요약 생성. 기본 모델 `claude-opus-5-5`, effort `low`, 실행당 최대 20건 |
| `SIGNAL_LLM_MODEL` | Variable | 요약 모델 변경 (예: `claude-haiku-4-5`) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Secret | 강한 반응·업비트 상장·김프 급변·모닝 브리프 알림 (하루 최대 12건) |
| `TELEGRAM_CHANNEL_URL` | Variable | 마이 페이지에 구독 버튼 표시 |
| `SIGNAL_SITE_URL`, `SIGNAL_SITE_BASE` | Variable | 자체 도메인으로 옮길 때 (예: `https://signal.example.com`, `/`) |

## 데이터 출처와 유의 사항

뉴스는 각 매체 RSS의 제목·짧은 발췌와 원문 링크만 씁니다. 시세는 Binance·Coinbase·업비트 공개 API, 공포·탐욕 지수는 alternative.me, 환율은 ExchangeRate-API, 경제 일정은 Forex Factory 주간 일정입니다. 각 소스의 이용약관은 상업화 전에 다시 확인해야 합니다. 가격 반응은 같은 시간대의 변화를 잰 값이며 인과를 뜻하지 않고, 투자 조언이 아닙니다.

GitHub Pages는 상업적 거래·SaaS가 주목적인 사이트의 무료 호스팅으로 쓸 수 없습니다. 광고·유료 기능을 붙이기 전에 다른 호스팅으로 옮겨야 합니다.
