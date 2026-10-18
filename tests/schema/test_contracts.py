import copy
import json
from pathlib import Path
import tempfile
import unittest
from tests.check_site import validate, check

STORY = {"id": "fixture", "t": 100, "ko": "회사가 발표했다", "en": "The company announced results", "v": "중립", "s": 1, "kind": "event", "coins": ["BTC"], "sectors": [], "mw": False, "n": 1, "link": "https://example.org/news"}
RELATED = {"t0": 100, "title": "News", "src": "Example", "assets": ["BTC"], "url": "https://example.org/news"}
IND = {"k": "cpi", "en": "CPI", "ko": "소비자물가", "unit": "%", "grp": "prices", "dec": 1, "hot": 1, "latest": {"d": "2026-10-17", "ts": 100, "period": "2026-09-01", "v": 3.7, "prev": 3.6}, "sit": {"dir": "up", "chg": .1, "trend": "up", "rank10y": .5, "vs_avg12": 0}, "rows": [{"d": "2026-10-17", "ts": 100, "v": 3.7}], "long": [["2026-10-17", 3.7]], "similar": [], "stats": {}, "paths": {}}
DOCS = {
    "feed": {"at": 100, "items": [dict(RELATED, id="fixture", lang="en", cat="crypto", imp=1, etype="other", sum=[], ex="short", llm=False, st="skip", h=None, rx=None, ai=None)]},
    "related": {"at": 100, "items": [RELATED]},
    "flash": {"at": 100, "items": [STORY], "release": {"items": [{"ts": 100, "ko": "발표", "en": "Release", "values": {"cpi": {"disp": ["3.7%", "3.7%"], "disp_prev": ["3.6%", "3.6%"]}}, "ai": {lang: {"head": "Release", "s": ["Data released"], "by": "program"} for lang in ("ko", "en")}}]}},
    "econ": {"made": 100, "groups": [{"k": "prices", "ko": "물가", "en": "Prices"}], "assets": [], "horizons": ["d1"], "indicators": [IND], "upcoming": [{"ts": 200, "keys": ["cpi"], "en": "CPI", "ko": "물가", "impact": "high"}]},
    "threads": {"made": 100, "stories": {"fixture": STORY}, "threads": [{"id": "thread", "ids": ["fixture"], "n": 1, "first": 100, "last": 100, "days": 1, "new24": 1, "u": 0, "d": 0, "th": ["crypto"]}]},
    "themes": {"made": 100, "themes": [{"k": "crypto", "n": 1, "u": 0, "d": 0, "s_ko": ["회사가 발표했다"], "s_en": ["The company announced results"], "hours": [[100, 0, 0]], "sectors": [], "mentions": {}, "top": [STORY], "latest": [STORY]}]},
    "daily": {"date": "2026-10-17", "made": 100, "headline": "하루 정리", "review": "발표를 정리했다", "counts": {"stories": 1}, "balance": {"호재": 0, "악재": 0, "중립": 1}, "market": {}, "sections": {}},
}


def write_fixture(root):
    root = Path(root)
    paths = {"feed": root / "site/data/feed.json", "related": root / "site/data/related.json", "flash": root / "flash/flash.json"}
    paths.update({k: root / "flash/daily" / (("2026-10-17" if k == "daily" else k) + ".json") for k in ("econ", "themes", "threads", "daily")})
    for name, path in paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(DOCS[name], ensure_ascii=False))
    return paths


class SchemaInjection(unittest.TestCase):
    def test_all_clean_contracts(self):
        for name, doc in DOCS.items():
            self.assertEqual(validate(name, doc), [], name)

    def test_every_root_required_field_deleted(self):
        for name, doc in DOCS.items():
            schema = json.loads((Path(__file__).parent / (name + ".schema.json")).read_text())
            for field in schema["required"]:
                bad = copy.deepcopy(doc)
                del bad[field]
                self.assertTrue(validate(name, bad), (name, field))

    def test_nested_deletions_and_wrong_types(self):
        cases = [("feed", ("items", 0, "title")), ("related", ("items", 0, "t0")), ("flash", ("items", 0, "ko")), ("flash", ("release", "items", 0, "ts")), ("econ", ("indicators", 0, "latest", "v")), ("themes", ("themes", 0, "s_ko")), ("threads", ("threads", 0, "ids")), ("daily", ("counts", "stories"))]
        for name, keys in cases:
            for action in ("delete", "wrong-type"):
                bad = copy.deepcopy(DOCS[name])
                parent = bad
                for k in keys[:-1]:
                    parent = parent[k]
                if action == "delete":
                    del parent[keys[-1]]
                else:
                    parent[keys[-1]] = {"invalid": True}
                self.assertTrue(validate(name, bad), (name, keys, action))

    def test_combined_command_clean_and_contaminated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture(root)
            good = check(root / "site", root / "flash")
            self.assertEqual(good["schema"], [])
            self.assertTrue(all(not p["errors"] for p in good["policy"].values()))
            paths["feed"].write_text('{"items": [{"title":"https://t.me/example"}]}')
            bad = check(root / "site", root / "flash")
            self.assertTrue(bad["schema"])
            self.assertTrue(bad["policy"]["site"]["errors"])
