"""Compare pass flags and ordered citations from two cold challenge reports (no new grading)."""
import argparse
import hashlib
import json
from pathlib import Path


def compare(first, second):
    differences = []
    if set(first['sets']) != set(second['sets']):
        raise ValueError('Cold runs contain different sets')
    for name, run in first['sets'].items():
        left = {r['id']: (r['pass'], r['cited_chunk_ids']) for r in run['results']}
        right = {r['id']: (r['pass'], r['cited_chunk_ids']) for r in second['sets'][name]['results']}
        for item in sorted(left.keys() | right.keys()):
            if left.get(item) != right.get(item):
                differences.append({'set': name, 'id': item, 'first': left.get(item), 'second': right.get(item)})
    return differences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('first', type=Path)
    parser.add_argument('second', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    first, second = [json.loads(p.read_text()) for p in (args.first, args.second)]
    result = {'inputs': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.first, args.second)},
              'questions': sum(len(s['results']) for s in first['sets'].values()),
              'differences': compare(first, second)}
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(f"{result['questions']} questions; {len(result['differences'])} pass/citation differences")


if __name__ == '__main__':
    main()
