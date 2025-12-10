#!/usr/bin/env python3
"""Sample a few parquet rows and extract rule and identifier details."""

from __future__ import annotations

import argparse
import random
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

RULE_RE = re.compile(r"R\s?400\.\d+(?:\.\d+)?(?:\([0-9A-Za-z]+\))?")
LICENSE_RE = re.compile(r"License\s*#?\s*:\s*([A-Z0-9-]+)", re.IGNORECASE)
SPECIAL_INVESTIGATION_RE = re.compile(
    r"Special\s+Investigation\s*#?\s*:\s*([A-Z0-9-]+)", re.IGNORECASE
)
NUMERIC_DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")
MONTH_DATE_RE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4}\b",
    re.IGNORECASE,
)


def _normalize_rule(rule: str) -> str:
    return rule.replace(" ", "")


def _status_from_window(window: str) -> str | None:
    lower = window.lower()
    if "violation not established" in lower:
        return "Violation Not Established"
    if "violation established" in lower:
        return "Violation Established"
    if "not in compliance" in lower:
        return "Not in Compliance"
    if "in compliance" in lower:
        return "In Compliance"
    return None


def extract_rules(text: str) -> dict[str, str]:
    rules: dict[str, str] = {}
    for match in RULE_RE.finditer(text):
        rule = _normalize_rule(match.group(0))
        if rule in rules:
            continue
        start = max(match.start() - 160, 0)
        end = match.end() + 160
        status = _status_from_window(text[start:end])
        if status is None:
            status = _status_from_window(text)
        rules[rule] = status or "Unknown"
    return rules


def extract_date(text: str) -> str | None:
    month_match = MONTH_DATE_RE.search(text)
    if month_match:
        return month_match.group(0)
    numeric_match = NUMERIC_DATE_RE.search(text)
    if numeric_match:
        return numeric_match.group(0)
    return None


def extract_identifier(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(1) if match else None


def coerce_text_value(text_value) -> str:
    parts: Iterable[str] | None = None
    if isinstance(text_value, (list, tuple)):
        parts = text_value
    elif hasattr(text_value, "tolist"):
        parts = text_value.tolist()

    if parts is not None and not isinstance(parts, (str, bytes)):
        return "\n".join(parts)
    return str(text_value)


def has_rule_reference(text_value) -> bool:
    return bool(RULE_RE.search(coerce_text_value(text_value)))


def load_records(parquet_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for parquet_file in sorted(parquet_dir.glob("*.parquet")):
        df = pd.read_parquet(parquet_file)
        df["source_file"] = parquet_file.name
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"No parquet files found in {parquet_dir}")
    return pd.concat(frames, ignore_index=True)


def summarize_records(records: Iterable[dict]) -> None:
    for idx, row in enumerate(records, 1):
        full_text = coerce_text_value(row.get("text"))
        license_id = extract_identifier(LICENSE_RE, full_text)
        investigation_id = extract_identifier(SPECIAL_INVESTIGATION_RE, full_text)
        date = extract_date(full_text) or row.get("dateprocessed")
        rules = extract_rules(full_text)
        excerpt = full_text.split("\n", 1)[0] if full_text else ""

        print(f"Record {idx} ({row.get('source_file', 'unknown source')})")
        print(f"  sha256: {row.get('sha256', 'unknown')}")
        print(f"  License #: {license_id or 'unknown'}")
        if investigation_id:
            print(f"  Special Investigation #: {investigation_id}")
        print(f"  Date: {date or 'unknown'}")
        if rules:
            print("  Rules mentioned:")
            for rule_code, status in sorted(rules.items()):
                print(f"    - {rule_code}: {status}")
        else:
            print("  Rules mentioned: none found")
        if excerpt:
            print(f"  First line: {excerpt[:120]}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sample parquet rows and extract rule, identifier, and date details."
    )
    parser.add_argument(
        "-p",
        "--parquet-dir",
        default=Path(__file__).parent / "parquet_files",
        type=Path,
        help="Directory containing parquet files (default: pdf_parsing/parquet_files)",
    )
    parser.add_argument(
        "-n",
        "--num-records",
        type=int,
        default=3,
        help="Number of random records to inspect (default: 3)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible sampling",
    )
    args = parser.parse_args()

    data = load_records(args.parquet_dir)
    rng = random.Random(args.seed)
    sample_size = min(args.num_records, len(data))
    sampled_records = data.sample(n=sample_size, random_state=args.seed).to_dict(
        orient="records"
    )

    if not any(has_rule_reference(rec.get("text")) for rec in sampled_records):
        rule_records = [
            rec for rec in data.to_dict(orient="records") if has_rule_reference(rec.get("text"))
        ]
        if rule_records:
            rng.shuffle(rule_records)
            sampled_records = rule_records[:sample_size]

    summarize_records(sampled_records)


if __name__ == "__main__":
    main()
