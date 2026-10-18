"""Explicit, read-only dependency provisioning; never called by a test.
Downloads pinned public static libraries/fonts into tests/e2e/vendor.
An existing manifest is immutable: remove/replace only after explicit review.
"""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import urllib.request
import urllib.parse

ROOT = Path(__file__).parent / "vendor"
URLS = [
    "https://cdn.jsdelivr.net/npm/axe-core@4.10.3/axe.min.js",
    "https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js",
    "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.min.js",
    "https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js",
    "https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/ScrollTrigger.min.js",
    "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css",
    "https://fonts.googleapis.com/css2?family=Michroma&family=Inter:opsz,wght@14..32,300..800&family=JetBrains+Mono:wght@400;500&display=swap",
]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as response:
        data, mime = response.read(), response.headers.get_content_type()
    name = hashlib.sha256(url.encode()).hexdigest()[:20] + (".css" if mime == "text/css" else ".js" if "javascript" in mime or url.endswith(".js") else ".woff2")
    (ROOT / name).write_bytes(data)
    return url, {"file": name, "type": mime, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}, data


def main():
    if (ROOT / "manifest.json").exists():
        raise FileExistsError("vendor baseline already exists; no automatic refresh")
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest, fonts = {}, set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for url, row, data in pool.map(download, URLS):
            manifest[url] = row
            if row["type"] == "text/css":
                fonts.update(urllib.parse.urljoin(url, u) for u in re.findall(r"url\(['\"]?([^)'\"]+)", data.decode()))
        for url, row, _ in pool.map(download, sorted(fonts)):
            manifest[url] = row
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("provisioned %d files, %d bytes" % (len(manifest), sum(r["bytes"] for r in manifest.values())))


if __name__ == "__main__":
    main()
