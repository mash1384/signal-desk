# design/ — 미리보기 원본

사이트(`web/`, `pipeline/`)에는 쓰이지 않는 작업 원본이다. 배포 전 후보 화면, 로고 영상 스크립트, 검사 스크립트를 잃지 않으려고 저장소에 둔다.

| 폴더 | 내용 |
|---|---|
| `concepts/` | 미리보기 후보 화면 전체(/preview/… 로 올라가는 것). `l/` 라이브(R1–R3), `t/` 테마(T1–T3), `y/` 내 자산(Y1–Y3), `h/` 첫 화면, `brand/` 로고 등. 각 폴더의 `build.py` 가 `<이름>/index.html` 을 만든다 |
| `blender/` | 로고 오프닝 영상(M1 = `c1.py`) Blender 스크립트와 머리글 로고 치수(`header_metrics.json`) |
| `qa/` | 브라우저 검사: `chart_qa.py`(차트 위 마우스·터치로 크기 흔들림 검사), `themes_qa.py`(테마 페이지 전체 동작) |
| `research/` | 요약 모델 비교(`cmp.py`), 이야기 줄기 시험(`threads.py`), 해외 선행 시간(`unique.py`) |

## 작업 환경 다시 만들기 (Mac 재시동 뒤)

빌드 스크립트는 `/tmp/concepts` 경로를 쓴다. 재시동하면 `/tmp` 의 연결이 사라지므로 다시 걸어 준다.

```sh
ln -s ~/Documents/signal-desk/design/concepts /tmp/concepts
mkdir -p /tmp/sdroot && ln -s /tmp/concepts /tmp/sdroot/concepts
cd /tmp/sdroot && python3 -m http.server 8001 --bind 127.0.0.1   # http://localhost:8001/concepts/r3/
```

## 빌드

```sh
python3 /tmp/concepts/l/build.py r1 r2 r3
python3 /tmp/concepts/t/build.py t1 t2 t3
python3 /tmp/concepts/y/build.py y1 y2 y3
```

세 빌드는 `l/`·`t/`·`y/` 의 모든 모듈 주소에 같은 `?v=` 를 붙인다. 버전이 다르면 공통 모듈(lk.js)이 두 번 실행된다.

## 미리보기 올리기

`gh-pages` 브랜치의 `preview/<이름>/` 에 복사해 올린다. 사이트 배포(15분마다)가 gh-pages 를 덮어쓸 수 있으니, 올린 뒤 다음 배포가 끝나고 주소가 살아 있는지 다시 확인한다.
