"""Simple offline metrics for comparing single-agent and multi-agent reports.

Input JSONL rows:
{"system":"single|multi","quality_score":90,"citation_count":12,"invalid_citations":0,"critic_issues":1}
"""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def main(path: str) -> None:
    groups: dict[str, list[dict]] = defaultdict(list)
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            groups[row["system"]].append(row)
    for name, rows in groups.items():
        print(name)
        print("  samples:", len(rows))
        print("  avg quality:", round(statistics.mean(r["quality_score"] for r in rows), 2))
        print("  avg citations:", round(statistics.mean(r["citation_count"] for r in rows), 2))
        print("  invalid citations:", sum(r["invalid_citations"] for r in rows))
        print("  avg critic issues:", round(statistics.mean(r["critic_issues"] for r in rows), 2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/evaluate_reports.py results.jsonl")
    main(sys.argv[1])
