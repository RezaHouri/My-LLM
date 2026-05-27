#!/usr/bin/env python3
"""
Build data/processed/rhino_sft.jsonl from data/raw/ sources.

Merges:
  - rhino-developer-samples code files
  - developer_docs JSON chunks
  - existing seed / synthetic rows (optional append)

Usage:
  python scripts/build_dataset.py
  python scripts/build_dataset.py --append-seed
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"
OUT_PATH = REPO_ROOT / "data" / "processed" / "rhino_sft.jsonl"
SEED_PATH = OUT_PATH  # seed lives in same file when using --append-seed

SAMPLES_DIR = RAW_DIR / "rhino-developer-samples"
DOCS_DIR = RAW_DIR / "developer_docs"


def norm_hash(text: str) -> str:
    t = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(t.encode()).hexdigest()[:16]


def row(user: str, assistant: str, lang: str, topic: str = "general") -> dict:
    return {
        "messages": [
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": {"lang": lang, "topic": topic},
    }


def prompt_from_path(path: Path, code: str) -> str:
    rel = path.as_posix()
    name = path.stem.replace("_", " ").replace("-", " ")
    lang = "Rhino.Python" if path.suffix.lower() == ".py" else "RhinoCommon C#"
    first_line = ""
    for line in code.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and not s.startswith("//"):
            first_line = s[:80]
            break
    return (
        f"In {lang}, write a script based on the sample '{name}'. "
        f"Context path: {rel}. "
        f"The code should accomplish: {first_line or 'see sample behavior'}."
    )


def ingest_samples(samples_root: Path) -> list[dict]:
    rows: list[dict] = []
    if not samples_root.exists():
        return rows
    for p in samples_root.rglob("*"):
        if p.suffix.lower() not in {".py", ".cs"}:
            continue
        if any(x in p.parts for x in ("bin", "obj", ".git")):
            continue
        try:
            code = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(code.strip()) < 30:
            continue
        lang = "python" if p.suffix.lower() == ".py" else "csharp"
        topic = "grasshopper" if "grasshopper" in p.as_posix().lower() else "sample"
        rows.append(row(prompt_from_path(p, code), code.strip(), lang, topic))
    return rows


def chunk_text(text: str, max_chars: int = 4000) -> list[str]:
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for p in paras:
        if size + len(p) > max_chars and buf:
            chunks.append("\n\n".join(buf))
            buf, size = [], 0
        buf.append(p)
        size += len(p)
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def ingest_docs(docs_dir: Path) -> list[dict]:
    rows: list[dict] = []
    if not docs_dir.exists():
        return rows
    for jf in sorted(docs_dir.glob("*.json")):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        title = data.get("title", "guide")
        url = data.get("url", "")
        text = data.get("text", "")
        for i, chunk in enumerate(chunk_text(text)):
            if len(chunk) < 200:
                continue
            user = (
                f"Explain this Rhino developer guide section ({title}, part {i + 1}). "
                f"Source: {url}"
            )
            assistant = (
                f"Summary and key points from the guide:\n\n{chunk}\n\n"
                "Use the official Rhino SDK docs to verify API names before production use."
            )
            lang = "concept"
            if "python" in url.lower() or "rhinopython" in url.lower():
                lang = "python"
            elif "rhinocommon" in url.lower() or "csharp" in url.lower():
                lang = "csharp"
            rows.append(row(user, assistant, lang, "documentation"))
    return rows


def dedupe(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for r in rows:
        assistant = r["messages"][1]["content"]
        h = norm_hash(assistant)
        if h in seen:
            continue
        seen.add(h)
        out.append(r)
    return out


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--append-seed", action="store_true", help="Keep existing OUT rows first")
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    existing = load_jsonl(args.out) if args.append_seed else []
    built = ingest_samples(SAMPLES_DIR) + ingest_docs(DOCS_DIR)
    merged = dedupe(existing + built)

    if not merged and not existing:
        print("No rows built. Ensure seed rhino_sft.jsonl exists or run download_sources.py first.")
        write_jsonl(args.out, [])
        return 1

    write_jsonl(args.out, merged if merged else existing)
    langs = {}
    for r in (merged if merged else existing):
        langs[r["meta"]["lang"]] = langs.get(r["meta"]["lang"], 0) + 1
    print(f"Wrote {len(merged if merged else existing)} rows -> {args.out}")
    print(f"  by lang: {langs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
