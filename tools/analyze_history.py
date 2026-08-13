#!/usr/bin/env python3
"""Analyze six Home Assistant CSV exports without third-party dependencies."""

from __future__ import annotations

import argparse
import csv
import json
from bisect import bisect_left
from datetime import datetime
from pathlib import Path
from statistics import median

PATTERNS = {
    "pv": ("solaredge", "pv"), "azimuth": ("azimuth",),
    "elevation": ("elevation",), "lux": ("illuminance", "lux"),
    "cloud": ("bewoelkung", "cloud"), "temperature": ("temperature", "temperatur"),
}
TIME_COLUMNS = ("last_updated", "last_changed", "timestamp", "datetime", "time")
VALUE_COLUMNS = ("state", "value", "wert")
FACADES = (
    ("northeast", 25, 340, 90), ("southwest", 205, 140, 270),
    ("northwest", 295, 250, 340),
)


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))


def read_series(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        names = {name.lower(): name for name in (reader.fieldnames or [])}
        tc = next((names[x] for x in TIME_COLUMNS if x in names), None)
        vc = next((names[x] for x in VALUE_COLUMNS if x in names), None)
        if not tc or not vc:
            raise ValueError(f"{path.name}: Zeit- oder Wertespalte fehlt")
        rows = []
        for row in reader:
            try:
                rows.append((parse_time(row[tc]), float(row[vc].replace(",", "."))))
            except (ValueError, TypeError):
                continue
    return sorted(rows)


def nearest(series, when, tolerance=600):
    times = [x[0] for x in series]
    pos = bisect_left(times, when)
    choices = series[max(0, pos - 1):pos + 1]
    if not choices:
        return None
    hit = min(choices, key=lambda x: abs((x[0] - when).total_seconds()))
    return hit[1] if abs((hit[0] - when).total_seconds()) <= tolerance else None


def facade_for(azimuth):
    def inside(value, start, end):
        return start <= value <= end if start <= end else value >= start or value <= end
    candidates = [f for f in FACADES if inside(azimuth, f[2], f[3])]
    if not candidates:
        return None
    return min(candidates, key=lambda f: abs((azimuth - f[1] + 180) % 360 - 180))[0]


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    return ordered[round((len(ordered) - 1) * fraction)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    files = list(args.directory.glob("*.csv"))
    selected = {}
    for key, patterns in PATTERNS.items():
        selected[key] = next((p for p in files if any(x in p.name.lower() for x in patterns)), None)
    missing = [k for k, p in selected.items() if p is None]
    if missing:
        raise SystemExit("Fehlende CSVs: " + ", ".join(missing))
    series = {key: read_series(path) for key, path in selected.items()}
    joined = []
    for when, pv in series["pv"]:
        row = {key: nearest(values, when) for key, values in series.items() if key != "pv"}
        if row["azimuth"] is not None and row["elevation"] is not None:
            joined.append({"time": when.isoformat(), "pv": pv, **row})
    daylight = [r for r in joined if r["elevation"] >= 5]
    clear = [r for r in daylight if r["lux"] is not None and r["lux"] >= 30_000
             and r["cloud"] is not None and r["cloud"] <= 30]
    bins = {}
    for row in clear:
        facade = facade_for(row["azimuth"])
        if facade is None:
            continue
        key = f"{round(row['azimuth'] / 10) * 10 % 360}:{round(row['elevation'] / 5) * 5}"
        bins.setdefault(facade, {}).setdefault(key, []).append(row["pv"])
    curves = {
        facade: {
            key: {"reference": percentile(values, 0.90), "samples": len(values)}
            for key, values in cells.items()
        } for facade, cells in bins.items()
    }
    report = {
        "files": {k: str(v) for k, v in selected.items()},
        "source_rows": {k: len(v) for k, v in series.items()},
        "joined_rows": len(joined), "daylight_rows": len(daylight),
        "period": [joined[0]["time"], joined[-1]["time"]] if joined else None,
        "daylight_pv": {
            "minimum": min((r["pv"] for r in daylight), default=None),
            "median": median((r["pv"] for r in daylight)) if daylight else None,
            "maximum": max((r["pv"] for r in daylight), default=None),
        },
        "initial_reference_curves": curves,
        "curve_method": "90th percentile of clear samples (lux >= 30000, cloud <= 30)",
        "note": "Use raw joined data for validation; online learning remains the source of truth.",
    }
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
