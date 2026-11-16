"""Locks in that dataset writers cannot destroy an existing corpus."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_dataset  # noqa: E402


def _row(text: str, lang: str = "python") -> dict:
    return {
        "messages": [
            {"role": "user", "content": f"ask {text}"},
            {"role": "assistant", "content": text},
        ],
        "meta": {"lang": lang, "topic": "test", "source": "test"},
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class BuildDatasetSafetyTest(unittest.TestCase):
    def test_empty_ingestion_does_not_truncate_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "rhino_sft.jsonl"
            original = [_row("keep-me"), _row("keep-me-too")]
            _write_jsonl(out, original)
            before = out.read_bytes()

            old_argv = sys.argv
            try:
                sys.argv = [
                    "build_dataset.py",
                    "--out",
                    str(out),
                    "--eval-out",
                    str(Path(tmp) / "eval.jsonl"),
                ]
                rc = build_dataset.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(rc, 1)
            self.assertEqual(out.read_bytes(), before)
            self.assertEqual(_read_jsonl(out), original)

    def test_finalize_only_missing_file_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "missing.jsonl"
            old_argv = sys.argv
            try:
                sys.argv = [
                    "build_dataset.py",
                    "--finalize-only",
                    "--out",
                    str(out),
                    "--eval-out",
                    str(Path(tmp) / "eval.jsonl"),
                ]
                rc = build_dataset.main()
            finally:
                sys.argv = old_argv
            self.assertEqual(rc, 1)
            self.assertFalse(out.exists())

    def test_append_seed_keeps_existing_rows_when_ingestion_adds_some(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "rhino_sft.jsonl"
            _write_jsonl(out, [_row("already-there")])
            added = [_row("from-raw")]

            orig_samples = build_dataset.ingest_samples
            orig_docs = build_dataset.ingest_docs
            build_dataset.ingest_samples = lambda *a, **k: added
            build_dataset.ingest_docs = lambda *a, **k: []
            old_argv = sys.argv
            try:
                sys.argv = [
                    "build_dataset.py",
                    "--append-seed",
                    "--out",
                    str(out),
                    "--eval-out",
                    str(Path(tmp) / "eval.jsonl"),
                ]
                rc = build_dataset.main()
            finally:
                sys.argv = old_argv
                build_dataset.ingest_samples = orig_samples
                build_dataset.ingest_docs = orig_docs

            self.assertEqual(rc, 0)
            texts = [r["messages"][1]["content"] for r in _read_jsonl(out)]
            self.assertEqual(texts, ["already-there", "from-raw"])


class InitSeedSafetyTest(unittest.TestCase):
    def test_refuses_to_overwrite_nonempty_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "rhino_sft.jsonl"
            out.write_text('{"messages":[{"role":"user","content":"u"},{"role":"assistant","content":"kept"}]}\n', encoding="utf-8")
            before = out.read_bytes()
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "init_seed.py"), "--out", str(out)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("Keeping existing dataset", proc.stdout)
            self.assertEqual(out.read_bytes(), before)

    def test_force_replaces_and_missing_file_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "nested" / "rhino_sft.jsonl"
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "init_seed.py"), "--out", str(out)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            rows = _read_jsonl(out)
            self.assertGreaterEqual(len(rows), 50)
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "init_seed.py"), "--out", str(out), "--force"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertGreaterEqual(len(_read_jsonl(out)), 50)


if __name__ == "__main__":
    unittest.main()
