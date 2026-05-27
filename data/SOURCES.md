# Rhino LLM training data sources

Document every source used in `data/raw/` and how it was transformed into `data/processed/rhino_sft.jsonl`.

## Primary sources

| Source | URL | License | Usage |
|--------|-----|---------|-------|
| Rhino Developer Samples | https://github.com/mcneel/rhino-developer-samples | See repo LICENSE (typically permissive McNeel sample code) | Python/C# sample files → user prompt + code assistant reply |
| Rhino Developer Guides | https://developer.rhino3d.com/ | McNeel documentation (reference; do not bulk-scrape without rate limits) | Chunked guides via polite fetch in `download_sources.py` |
| Seed / synthetic | This repo | MIT (project) | `make_synthetic.py` + hand-curated seed rows |

## Secondary / optional (phase 2)

| Source | Notes |
|--------|-------|
| mcneel/compute.rhino3d | Advanced; verify license per folder |
| Grasshopper examples | Tag `topic: grasshopper` when included |

## What we avoid (v1)

- **Rhino Discourse** — community posts; permission unclear for redistribution/training.
- **Private SDK dumps** — use public docs only.
- **Paywalled content** — excluded.

## Attribution

When expanding the dataset, append rows to this file:

```
YYYY-MM-DD | source-id | N rows added | script version
```

## Data rules

- Chat JSONL with `messages` + `meta.lang` (`python` | `csharp` | `concept`).
- Deduplicate by normalized assistant text hash (`build_dataset.py`).
- 90/10 train/eval split at build time (eval held in separate file or tagged).
