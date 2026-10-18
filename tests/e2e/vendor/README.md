# Pinned browser dependencies

`manifest.json` records the original public URL, SHA-256, content type and byte
size of each file. Tests verify hashes and fulfill requests from these files;
they do not download dependencies. `provision.py` is an explicit preparation
command, separate from tests, and refuses to overwrite an existing manifest.

Upstream licenses and source projects:

- [axe-core 4.10.3 (MPL-2.0)](https://github.com/dequelabs/axe-core/blob/v4.10.3/LICENSE)
- [Lightweight Charts 4.2.3 (Apache-2.0)](https://github.com/tradingview/lightweight-charts/blob/v4.2.3/LICENSE)
- [Three.js r170 (MIT)](https://github.com/mrdoob/three.js/blob/r170/LICENSE)
- [GSAP 3.13.0 license](https://github.com/greensock/GSAP/blob/3.13.0/LICENSE)
- [Pretendard v1.3.9 (SIL OFL)](https://github.com/orioncactus/pretendard/blob/v1.3.9/LICENSE)
- Google Fonts CSS selects Michroma, Inter and JetBrains Mono; their downloaded
  font files are covered by their respective SIL Open Font Licenses.

These files are test-only; no production asset is replaced or removed.
