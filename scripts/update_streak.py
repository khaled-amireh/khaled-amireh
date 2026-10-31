"""Publish a validated streak card and its retrieval time; never invent stats."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo


START = "<!-- streak-snapshot:start -->"
END = "<!-- streak-snapshot:end -->"
SVG = "{http://www.w3.org/2000/svg}"


def validate_card(card):
    root = ET.fromstring(card)
    if root.tag != f"{SVG}svg" or root.get("viewBox", "").split() != ["0", "0", "495", "195"]:
        raise ValueError("Expected a 495 by 195 SVG streak card")
    texts = ["".join(node.itertext()).strip() for node in root.iter(f"{SVG}text")]
    if not {"Total Contributions", "Current Streak", "Longest Streak"}.issubset(texts):
        raise ValueError("Streak card is missing its contribution/streak labels")
    if len([text for text in texts if re.fullmatch(r"\d+(?:,\d{3})*", text)]) != 3:
        raise ValueError("Streak card must contain three numeric statistics")


def publish_snapshot(candidate, output, readme, retrieved_at=None):
    card = candidate.read_bytes()
    validate_card(card)
    content = readme.read_text(encoding="utf-8")
    if content.count(START) != 1 or content.count(END) != 1 or content.index(START) >= content.index(END):
        raise ValueError("README must have exactly one ordered snapshot marker pair")
    retrieved_at = retrieved_at or datetime.now(timezone.utc)
    if retrieved_at.tzinfo is None:
        raise ValueError("Retrieval time must include its timezone")
    local_time = retrieved_at.astimezone(ZoneInfo("Asia/Amman")).strftime("%Y-%m-%d %H:%M")
    caption = f'<p align="center"><sub>Latest available snapshot · Retrieved {local_time} (Asia/Amman)</sub></p>'
    # Validate everything before touching either published file. A failure also
    # prevents the workflow's commit step, preserving both last-known files.
    before, rest = content.split(START)
    _, after = rest.split(END)
    updated = f"{before}{START}\n{caption}\n{END}{after}"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".svg.tmp")
    temporary.write_bytes(card)
    temporary.replace(output)
    readme.write_text(updated, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, default=Path("assets/github-streak.svg"))
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    parser.add_argument("--retrieved-at", type=datetime.fromisoformat)
    args = parser.parse_args()
    publish_snapshot(args.candidate, args.output, args.readme, args.retrieved_at)
