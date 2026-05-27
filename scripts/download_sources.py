#!/usr/bin/env python3
"""
Download public Rhino training sources into data/raw/.

Sources:
  - mcneel/rhino-developer-samples (GitHub archive or sparse clone)
  - developer.rhino3d.com guide pages (polite, rate-limited)

Usage:
  python scripts/download_sources.py
  python scripts/download_sources.py --samples-only
  python scripts/download_sources.py --docs-only --max-pages 20
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw"
SAMPLES_ARCHIVE_URL = (
    "https://github.com/mcneel/rhino-developer-samples/archive/refs/heads/master.zip"
)
SAMPLES_DIR = RAW_DIR / "rhino-developer-samples"
DOCS_DIR = RAW_DIR / "developer_docs"
MANIFEST_PATH = RAW_DIR / "download_manifest.json"

# Curated developer.rhino3d.com entry points (expand in phase 2)
DOC_SEED_URLS = [
    "https://developer.rhino3d.com/guides/rhinopython/python-rhinoscriptsyntax-introduction/",
    "https://developer.rhino3d.com/guides/rhinopython/python-rhinoscriptsyntax-object-selection/",
    "https://developer.rhino3d.com/guides/rhinopython/python-rhinoscriptsyntax-geometry/",
    "https://developer.rhino3d.com/guides/rhinocommon/what-is-rhinocommon/",
    "https://developer.rhino3d.com/guides/rhinocommon/creating-a-rhinocommon-plugin/",
    "https://developer.rhino3d.com/guides/grasshopper/csharp-gh-scripting/",
]

USER_AGENT = "RhinoColabLLM/1.0 (educational; +https://github.com/mcneel/rhino-developer-samples)"
REQUEST_DELAY_SEC = 1.5


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def download_developer_samples(force: bool = False) -> Path:
    """Fetch mcneel/rhino-developer-samples as a zip into data/raw/."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    marker = SAMPLES_DIR / ".downloaded"
    if marker.exists() and not force:
        print(f"Samples already present: {SAMPLES_DIR}")
        return SAMPLES_DIR

    zip_path = RAW_DIR / "rhino-developer-samples-master.zip"
    print(f"Downloading {SAMPLES_ARCHIVE_URL} ...")
    sess = _session()
    with sess.get(SAMPLES_ARCHIVE_URL, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done = 0
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        print(f"\r  {100 * done // total}%", end="", flush=True)
    print()

    print("Extracting archive ...")
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        # Extract into SAMPLES_DIR (strip top-level folder name)
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            parts = name.split("/", 1)
            if len(parts) < 2:
                continue
            rel = parts[1]
            if not rel:
                continue
            dest = SAMPLES_DIR / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, open(dest, "wb") as dst:
                dst.write(src.read())

    marker.write_text(SAMPLES_ARCHIVE_URL, encoding="utf-8")
    zip_path.unlink(missing_ok=True)
    print(f"Samples ready: {SAMPLES_DIR}")
    return SAMPLES_DIR


def _extract_main_text(html: str) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return re.sub(r"<[^>]+>", " ", html)

    soup = BeautifulSoup(html, "lxml")
    article = soup.find("article") or soup.find("main") or soup.body
    if not article:
        return ""
    for tag in article.find_all(["script", "style", "nav"]):
        tag.decompose()
    text = article.get_text("\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text)


def download_doc_pages(urls: list[str], max_pages: int | None = None) -> list[Path]:
    """Politely fetch developer.rhino3d.com guide HTML/text."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    sess = _session()
    saved: list[Path] = []
    targets = urls[: max_pages or len(urls)]

    for url in targets:
        slug = hashlib.md5(url.encode()).hexdigest()[:12]
        out = DOCS_DIR / f"{slug}.json"
        if out.exists():
            saved.append(out)
            continue
        print(f"Fetching doc: {url}")
        try:
            resp = sess.get(url, timeout=60)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  skip ({e})")
            time.sleep(REQUEST_DELAY_SEC)
            continue

        text = _extract_main_text(resp.text)
        payload = {
            "url": url,
            "title": urlparse(url).path.rstrip("/").split("/")[-1],
            "text": text[:50000],
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        saved.append(out)
        time.sleep(REQUEST_DELAY_SEC)

    return saved


def iter_sample_code_files(samples_root: Path) -> list[Path]:
    """Walk rhino-developer-samples for .py and .cs files."""
    exts = {".py", ".cs"}
    skip_parts = {"bin", "obj", ".git", "packages", "node_modules"}
    files: list[Path] = []
    if not samples_root.exists():
        return files
    for p in samples_root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        if any(part in skip_parts for part in p.parts):
            continue
        if p.stat().st_size > 200_000:
            continue
        files.append(p)
    return sorted(files)


def write_manifest(samples: Path | None, doc_files: list[Path]) -> None:
    manifest = {
        "samples_dir": str(samples) if samples else None,
        "sample_code_count": len(list(iter_sample_code_files(samples))) if samples else 0,
        "doc_files": [str(p) for p in doc_files],
        "doc_seed_urls": DOC_SEED_URLS,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest: {MANIFEST_PATH}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Rhino training sources")
    parser.add_argument("--force", action="store_true", help="Re-download samples")
    parser.add_argument("--samples-only", action="store_true")
    parser.add_argument("--docs-only", action="store_true")
    parser.add_argument("--max-pages", type=int, default=None)
    args = parser.parse_args()

    samples_path: Path | None = None
    doc_files: list[Path] = []

    if not args.docs_only:
        samples_path = download_developer_samples(force=args.force)

    if not args.samples_only:
        doc_files = download_doc_pages(DOC_SEED_URLS, max_pages=args.max_pages)

    write_manifest(samples_path, doc_files)
    print("Done. Run: python scripts/build_dataset.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
