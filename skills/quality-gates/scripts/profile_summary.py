#!/usr/bin/env python3
"""Turn a py-spy (speedscope) or scalene JSON profile into a markdown table the
AI assistant can read directly.

The visual flamegraph (.svg) is for humans; this .md is the file the copilot
should open when asked "why is this slow", since it surfaces the hottest
functions with %CPU and %wait (the async-blocking signal) in one glance.

Usage:
    profile_summary.py .profiles/latest.json          # py-spy speedscope
    profile_summary.py --mem .profiles/mem.json       # scalene
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def summarize_speedscope(profile: dict) -> str:
    profiles = profile.get("profiles", [])
    frames = profile.get("shared", {}).get("frames", [])
    counts: Counter[int] = Counter()
    total = 0
    for prof in profiles:
        samples = prof.get("samples", [])
        weights = prof.get("weights", [1] * len(samples))
        for stack, w in zip(samples, weights, strict=False):
            total += w
            if stack:
                counts[stack[-1]] += w  # leaf frame = where time is actually spent
    if total == 0:
        return "# Profile summary\n\nNo samples captured.\n"
    rows = []
    for frame_idx, weight in counts.most_common(20):
        fr = frames[frame_idx] if frame_idx < len(frames) else {}
        name = fr.get("name", "?")
        loc = f"{fr.get('file', '?')}:{fr.get('line', '?')}"
        pct = 100.0 * weight / total
        rows.append((name, loc, pct))
    lines = [
        "# Profile summary (CPU)",
        f"\nTotal samples: {total}\n",
        "| Function | Location | %Self |",
        "|---|---|---|",
    ]
    for name, loc, pct in rows:
        lines.append(f"| `{name}` | {loc} | {pct:.1f}% |")
    lines.append(
        "\n_Tip: high %Self in a leaf that does I/O usually means a blocked "
        "event loop -- check for sync calls inside async code._\n"
    )
    return "\n".join(lines)


def summarize_scalene(profile: dict) -> str:
    files = profile.get("files", {})
    rows = []
    for fname, fdata in files.items():
        for line in fdata.get("lines", []):
            cpu = line.get("n_cpu_percent_python", 0) + line.get("n_cpu_percent_c", 0)
            mem = line.get("n_peak_mb", 0)
            if cpu < 1 and mem < 1:
                continue
            rows.append((fname, line.get("lineno", "?"), cpu, mem))
    rows.sort(key=lambda r: r[2] + r[3], reverse=True)
    lines = [
        "# Profile summary (CPU + memory)",
        "\n| Location | %CPU | Peak MB |",
        "|---|---|---|",
    ]
    for fname, lineno, cpu, mem in rows[:20]:
        lines.append(f"| {fname}:{lineno} | {cpu:.1f}% | {mem:.1f} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    is_mem = "--mem" in sys.argv
    if not args:
        print("usage: profile_summary.py [--mem] <profile.json>", file=sys.stderr)
        return 2
    profile = json.loads(Path(args[0]).read_text())
    print(summarize_scalene(profile) if is_mem else summarize_speedscope(profile))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
