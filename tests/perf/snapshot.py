"""Restore the reviewed public JSON fixture without a mutable remote branch."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

FIXTURES = Path(__file__).parent / 'fixtures'


def restore(archive, manifest, out):
    spec = json.loads(manifest.read_text())
    if hashlib.sha256(archive.read_bytes()).hexdigest() != spec['archive_sha256']:
        raise ValueError('fixture archive checksum mismatch')
    if out.exists():
        raise FileExistsError('fixture output must be a new directory')
    with tarfile.open(archive, 'r:gz') as bundle:
        members = bundle.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)) or set(names) != set(spec['files']):
            raise ValueError('fixture member list mismatch')
        for member in members:
            path = PurePosixPath(member.name)
            if not member.isfile() or path.is_absolute() or '..' in path.parts or path.parts[0] not in ('gh-pages', 'flash'):
                raise ValueError('unsafe fixture member')
            body = bundle.extractfile(member).read()
            if hashlib.sha256(body).hexdigest() != spec['files'][member.name]['sha256']:
                raise ValueError('fixture file checksum mismatch: ' + member.name)
            dest = out.joinpath(*path.parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
    # OGs are social metadata, not fetched by the performance browser cases.
    # Keep the build's input directory contract without 85MB of unused JPEGs.
    (out / 'gh-pages/og').mkdir()
    return {'ok': True, 'files': len(names), 'source_commits': spec['source_commits']}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--archive', type=Path, default=FIXTURES / 'snapshot-r.tar.gz')
    parser.add_argument('--manifest', type=Path, default=FIXTURES / 'snapshot-r.json')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(restore(args.archive, args.manifest, args.out)))


if __name__ == '__main__':
    main()
