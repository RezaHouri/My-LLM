#!/usr/bin/env python3
"""
Build data/processed/rhino_sft.jsonl from data/raw/ sources.

Merges:
  - rhino-developer-samples code files (with prompt augmentation)
  - developer_docs JSON chunks
  - optional existing seed / synthetic rows

Usage:
  python scripts/build_dataset.py
  python scripts/build_dataset.py --append-seed
  python scripts/build_dataset.py --augment 6 --split-eval
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"
OUT_PATH = REPO_ROOT / "data" / "processed" / "rhino_sft.jsonl"
EVAL_PATH = REPO_ROOT / "data" / "processed" / "rhino_sft_eval.jsonl"

SAMPLES_DIR = RAW_DIR / "rhino-developer-samples"
DOCS_DIR = RAW_DIR / "developer_docs"

PROMPT_VARIANTS = [
    "In {lang}, write a script based on the sample '{name}'. Context: {rel}.",
    "Implement this Rhino task in {lang} (sample '{name}'): {hint}",
    "Provide runnable {lang} code for '{name}'. Path: {rel}",
    "Rhino 3D: complete the following workflow in {lang} — {name}. {hint}",
    "As a Rhino developer, write {lang} for: {name}. Reference path: {rel}",
    "Debug-ready {lang} script for '{name}': {hint}",
]


def norm_hash(text: str) -> str:
    t = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(t.encode()).hexdigest()[:16]


def row(user: str, assistant: str, lang: str, topic: str, source: str = "built") -> dict:
    return {
        "messages": [
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "meta": {"lang": lang, "topic": topic, "source": source},
    }


def code_hint(code: str) -> str:
    for line in code.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and not s.startswith("//"):
            return s[:100]
    return "see sample behavior"


def prompt_variants(path: Path, code: str, n: int) -> list[str]:
    rel = path.as_posix()
    name = path.stem.replace("_", " ").replace("-", " ")
    lang_label = "Rhino.Python" if path.suffix.lower() == ".py" else "RhinoCommon C#"
    hint = code_hint(code)
    rng = random.Random(norm_hash(rel))
    templates = rng.sample(PROMPT_VARIANTS, min(n, len(PROMPT_VARIANTS)))
    return [
        t.format(lang=lang_label, name=name, rel=rel, hint=hint)
        for t in templates
    ]


def split_code_chunks(code: str, path: Path, min_lines: int = 8, max_chars: int = 6000) -> list[str]:
    """Split large files into function/method-sized chunks."""
    if len(code) < max_chars and code.count("\n") < min_lines * 3:
        return [code]

    chunks: list[str] = []
    if path.suffix.lower() == ".py":
        pattern = re.compile(r"^(def \w+\(.*\):)", re.MULTILINE)
    else:
        pattern = re.compile(
            r"^(\s*(?:public|private|protected|internal).*\{?\s*$)",
            re.MULTILINE,
        )

    matches = list(pattern.finditer(code))
    if len(matches) < 2:
        # paragraph split
        lines = code.splitlines()
        buf: list[str] = []
        size = 0
        for line in lines:
            buf.append(line)
            size += len(line)
            if size > max_chars and len(buf) >= min_lines:
                chunks.append("\n".join(buf))
                buf, size = [], 0
        if buf:
            chunks.append("\n".join(buf))
        return chunks if chunks else [code]

    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(code)
        part = code[start:end].strip()
        if len(part) >= 30:
            chunks.append(part)
    return chunks if chunks else [code]


def ingest_samples(samples_root: Path, augment: int = 4, chunk_files: bool = True) -> list[dict]:
    rows: list[dict] = []
    if not samples_root.exists():
        return rows
    for p in samples_root.rglob("*"):
        if p.suffix.lower() not in {".py", ".cs"}:
            continue
        if any(x in p.parts for x in ("bin", "obj", ".git", "packages", "node_modules")):
            continue
        try:
            code = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(code.strip()) < 30:
            continue

        lang = "python" if p.suffix.lower() == ".py" else "csharp"
        topic = "grasshopper" if "grasshopper" in p.as_posix().lower() else "sample"

        parts = split_code_chunks(code.strip(), p) if chunk_files else [code.strip()]
        for part in parts:
            prompts = prompt_variants(p, part, augment)
            for user in prompts:
                rows.append(row(user, part, lang, topic, source="mcneel_sample"))

    return rows


def chunk_text(text: str, max_chars: int = 3500) -> list[str]:
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


DOC_QUESTION_STYLES = [
    "Explain this Rhino developer guide section ({title}, part {i}). Source: {url}",
    "Summarize key APIs from the Rhino guide '{title}' (section {i}). {url}",
    "What should a Rhino developer know from '{title}' part {i}? {url}",
    "Teach me Rhino concepts from this documentation ({title}, chunk {i}). {url}",
]


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
            if len(chunk) < 150:
                continue
            lang = "concept"
            if "python" in url.lower() or "rhinopython" in url.lower():
                lang = "python"
            elif "rhinocommon" in url.lower() or "csharp" in url.lower():
                lang = "csharp"

            for style in DOC_QUESTION_STYLES:
                user = style.format(title=title, i=i + 1, url=url)
                assistant = (
                    f"Summary and key points from the guide:\n\n{chunk}\n\n"
                    "Verify API names on developer.rhino3d.com before production use."
                )
                rows.append(row(user, assistant, lang, "documentation", source="developer_docs"))
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


def train_eval_split(rows: list[dict], ratio: float = 0.1, seed: int = 42) -> tuple[list[dict], list[dict]]:
    rng = random.Random(seed)
    shuffled = rows[:]
    rng.shuffle(shuffled)
    n_eval = max(1, int(len(shuffled) * ratio))
    return shuffled[n_eval:], shuffled[:n_eval]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--append-seed", action="store_true", help="Keep existing OUT rows first")
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    parser.add_argument("--eval-out", type=Path, default=EVAL_PATH)
    parser.add_argument("--augment", type=int, default=4, help="Prompt variants per code file/chunk")
    parser.add_argument("--no-chunk", action="store_true", help="Disable splitting large sample files")
    parser.add_argument("--split-eval", action="store_true", help="Write held-out eval JSONL")
    parser.add_argument("--eval-ratio", type=float, default=0.1)
    parser.add_argument(
        "--finalize-only",
        action="store_true",
        help="Only dedupe/split existing JSONL (no raw ingestion)",
    )
    args = parser.parse_args()

    # Load before any write. An empty ingestion must not truncate a corpus
    # that is already on disk, and --finalize-only must not touch an unset name.
    on_disk = load_jsonl(args.out)
    if args.finalize_only:
        merged = dedupe(on_disk)
    else:
        existing = on_disk if args.append_seed else []
        built = ingest_samples(
            SAMPLES_DIR,
            augment=args.augment,
            chunk_files=not args.no_chunk,
        ) + ingest_docs(DOCS_DIR)
        merged = dedupe(existing + built)

    if not merged:
        if on_disk:
            print(
                f"No rows built; left {len(on_disk)} existing rows unchanged at {args.out}"
            )
            return 1
        print("No rows built. Run: python scripts/init_seed.py && python scripts/download_sources.py")
        if not args.finalize_only:
            write_jsonl(args.out, [])
        return 1

    if args.split_eval:
        train, eval_rows = train_eval_split(merged, args.eval_ratio)
        write_jsonl(args.out, train)
        write_jsonl(args.eval_out, eval_rows)
        print(f"Wrote {len(train)} train -> {args.out}")
        print(f"Wrote {len(eval_rows)} eval -> {args.eval_out}")
        rows_for_stats = train
    else:
        write_jsonl(args.out, merged)
        rows_for_stats = merged

    langs: dict[str, int] = {}
    sources: dict[str, int] = {}
    for r in rows_for_stats:
        langs[r["meta"]["lang"]] = langs.get(r["meta"]["lang"], 0) + 1
        src = r["meta"].get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1
    print(f"Total train rows: {len(rows_for_stats)}")
    print(f"  by lang: {langs}")
    print(f"  by source: {sources}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
