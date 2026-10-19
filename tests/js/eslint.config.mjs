// 화면 JS 기본 검사: 정의 안 된 변수 · 안 쓰는 변수 · 도달 못 하는 코드 같은 실제 버그 후보만(모양 · 띄어쓰기 규칙 없음)
// 실행(저장소 루트에서): tests/js/node_modules/.bin/eslint -c tests/js/eslint.config.mjs web/assets/df
import js from '@eslint/js';
import globals from 'globals';

export default [
  { files: ['web/assets/df/**/*.js'],
    languageOptions: { ecmaVersion: 2023, sourceType: 'module',
      globals: { ...globals.browser, DFI: 'readonly', DFD: 'readonly', LightweightCharts: 'readonly', gsap: 'readonly', ScrollTrigger: 'readonly', THREE: 'readonly' } },
    rules: { ...js.configs.recommended.rules, 'no-empty': ['error', { allowEmptyCatch: true }],
      // catch (e) {} 와 콜백의 안 쓰는 인자는 관용 — 안 쓰는 import · 변수 · 함수만 잡는다
      'no-unused-vars': ['error', { args: 'none', caughtErrors: 'none' }] } },
  // data.js 는 모듈이 아니라 일반 스크립트(window.DFD 를 만든다)
  { files: ['web/assets/df/data.js'], languageOptions: { sourceType: 'script' } },
];
