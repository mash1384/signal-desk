import copy
import json
from pathlib import Path
import unittest

from tests.check_site import validate
from tests.schema.test_contracts import DOCS

RELEASE_PATH = Path(__file__).parent / 'fixtures/release-flash.json'
REGIME = {'current': {'q': 'stag', 'cpi': 3.7, 'dcpi': .2, 'nfp3': 56, 'nfp3p': 115},
          'quads': [{'k': 'stag', 'ko': '물가 상승·고용 둔화', 'en': 'Stagflation'}],
          'months': [['2026-10', 'stag', 0, 3.7, 56, .2, -59]],
          'analogs': [{'ym': '2000-08', 'q': 'stag', 'cpi': 3.6, 'nfp3': 45, 'un': 4.0}],
          'paths': {'analogs': {'2000-08': [0.0] * 13}}}


def documents():
    docs = copy.deepcopy(DOCS)
    docs['flash'] = json.loads(RELEASE_PATH.read_text())
    docs['econ']['regime'] = copy.deepcopy(REGIME)
    docs['econ']['fomc'] = {'now': {'outcomes': [{'k': 'hold', 'p': .8, 'ko': '동결', 'en': 'Hold'}]}, 'days': {'hold': [[100, .8], [200, .8]]}}
    return docs


# Nine exact failures in REVIEW R3, including the two separate base attacks.
ATTACKS = [('feed', ('items', 0, 'title'), 'delete'),
           ('econ', ('indicators', 0, 'latest', 'v'), 'object'),
           ('flash', ('release', 'items', 0, 'ts'), 'delete'),
           ('econ', ('regime', 'current'), 'delete'),
           ('econ', ('regime', 'months'), 'delete'),
           ('econ', ('fomc', 'now', 'outcomes'), 'delete'),
           ('flash', ('release', 'items', 0, 'market', 'BTC', 'pts'), 'delete'),
           ('flash', ('release', 'items', 0, 'market', 'BTC', 'base'), 'delete'),
           ('flash', ('release', 'items', 0, 'market', 'BTC', 'base'), 'string')]


class ReviewContracts(unittest.TestCase):
    def test_review_nine_attacks(self):
        docs = documents()
        for name, doc in docs.items():
            self.assertEqual(validate(name, doc), [], name)
        for name, path, action in ATTACKS:
            with self.subTest(schema=name, path=path, action=action):
                doc = copy.deepcopy(docs[name]); parent = doc
                for k in path[:-1]:
                    parent = parent[k]
                if action == 'delete':
                    del parent[path[-1]]
                else:
                    parent[path[-1]] = {} if action == 'object' else 'bad'
                self.assertTrue(validate(name, doc))

    def test_optional_parents_and_strict_nested_data(self):
        for key in ('regime', 'fomc', 'insight'):
            doc = copy.deepcopy(DOCS['econ']); doc[key] = None
            self.assertEqual(validate('econ', doc), [])
        for path in [('regime', 'current', 'cpi'), ('regime', 'quads', 0, 'ko'),
                     ('regime', 'months', 0, 3), ('regime', 'paths', 'analogs', '2000-08', 12),
                     ('regime', 'analogs', 0, 'un'), ('fomc', 'now', 'outcomes', 0, 'p')]:
            with self.subTest(path=path):
                doc = documents()['econ']; parent = doc
                for k in path[:-1]:
                    parent = parent[k]
                parent[path[-1]] = {}
                self.assertTrue(validate('econ', doc))
        for change in ({'base': 0}, {'base': -1}, {'pts': [[100]]}, {'pts': [[100, 101, 102]]}, {'pts': [['100', 101]]}):
            doc = documents()['flash']; doc['release']['items'][0]['market']['BTC'].update(change)
            self.assertTrue(validate('flash', doc), change)
