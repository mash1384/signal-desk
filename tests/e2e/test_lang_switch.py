"""언어를 바꾼 뒤에도 영어 화면에 한글이 남지 않는다(운영자 규칙: 영어 화면에 한글 금지).
2026-10-21 릴레이 X3-3: 테마 흐름 그래프의 비교 가격 이름(BENCH)을 모듈을 불러올 때 한 번만 골라, 한국어로 연 뒤 영어로 바꾸면 '미국 10년물'이 남았다."""
import re

import pytest

HANGUL = re.compile(r"[가-힣]")


@pytest.mark.parametrize("theme", ["nasdaq", "econ", "world"])
def test_flow_legend_follows_language(theme, session_page, site_server):
    page, context, _ = session_page
    context.add_init_script("localStorage.setItem('df-lang', 'ko')")
    page.goto(site_server + "themes/%s/" % theme, wait_until="networkidle")
    page.locator(".flow").scroll_into_view_if_needed()   # 차트는 화면에 들어올 때 그린다(charts.js whenVisible)
    page.wait_for_function("(document.querySelector('.flow .lgd') || {}).textContent && /·/.test(document.querySelector('.flow .lgd').textContent)", timeout=10000)
    assert HANGUL.search(page.locator(".flow .lgd").inner_text())        # 한국어 화면: 한국어 범례(비교 가격 이름 포함)
    page.locator('[data-lang="en"]').first.click()
    page.wait_for_function("document.documentElement.lang === 'en'")
    page.locator(".flow").scroll_into_view_if_needed()
    page.wait_for_function("(document.querySelector('.flow .lgd') || {}).textContent && /·/.test(document.querySelector('.flow .lgd').textContent)", timeout=10000)
    text = page.locator(".flow").inner_text()
    assert not HANGUL.search(text), text                                  # 영어 화면: 흐름 칸 전체에 한글 0
