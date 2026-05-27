# Rhino Colab LLM

A **Rhino 3D specialist** chat model: fine-tune [Qwen2.5-Coder-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct) with **QLoRA** on Google Colab (T4), then chat and export **GGUF Q4_K_M** for small-GPU inference.

Covers **Rhino.Python** (`rhinoscriptsyntax`, `scriptcontext`), **RhinoCommon C#**, and conceptual Rhino SDK topics.

> **Disclaimer:** This model is a coding *helper*. Always verify APIs against [developer.rhino3d.com](https://developer.rhino3d.com/) and test scripts inside Rhino.

## Quick start

### 1. Local data prep (optional)

```bash
cd "My LLM"
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python scripts/init_seed.py          # ~52 seed examples (included in repo)
python scripts/download_sources.py   # McNeel samples + doc pages
python scripts/build_dataset.py --append-seed
python scripts/make_synthetic.py --count 50
```

Training file: `data/processed/rhino_sft.jsonl` (chat JSONL with `messages` + `meta.lang`).

### 2. Train on Colab (GPU)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/RezaHouri/My-LLM/blob/main/notebooks/02_train_rhino_llm.ipynb)

1. Runtime → **GPU** (T4).
2. Hugging Face login (`HF_TOKEN`) for model download.
3. Upload `rhino_sft.jsonl` to Drive or clone this repo.
4. Run all cells; adapter saved to Drive (`rhino-qwen3b-lora/`).

### 3. Chat & export

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/RezaHouri/My-LLM/blob/main/notebooks/03_chat_and_export.ipynb)

- Gradio chat with LoRA
- Optional merge to full HF weights
- GGUF **Q4_K_M** export for Ollama / LM Studio / llama.cpp

### 4. Dataset notebook

[`notebooks/01_prepare_dataset.ipynb`](notebooks/01_prepare_dataset.ipynb) — UI wrapper over `download_sources.py` and `build_dataset.py`.

## Repository layout

```
├── configs/train_qlora.yaml
├── data/
│   ├── SOURCES.md
│   ├── raw/              # downloads (gitignored except .gitkeep)
│   └── processed/rhino_sft.jsonl
├── scripts/
│   ├── download_sources.py
│   ├── build_dataset.py
│   ├── make_synthetic.py
│   └── init_seed.py
├── eval/
│   ├── prompts.jsonl
│   └── score_outputs.py
└── notebooks/
    ├── 01_prepare_dataset.ipynb
    ├── 02_train_rhino_llm.ipynb
    └── 03_chat_and_export.ipynb
```

## GPU notes

| Hardware | Training | Inference |
|----------|----------|-----------|
| Colab T4 16 GB | QLoRA 3B, seq 2048, rank 32 (default) | 4-bit + LoRA in notebook |
| OOM on T4 | Use 1.5B base, seq 1024, rank 16 | See `configs/train_qlora.yaml` `oom_fallbacks` |
| 8 GB local | — | Merged 4-bit or GGUF Q4_K_M |
| 4 GB local | — | 1.5B + Q4_K_M GGUF |

Set `HF_HOME` on Google Drive to avoid re-downloading base weights between sessions.

## Licenses & data

See [`data/SOURCES.md`](data/SOURCES.md). Primary public sources:

- [mcneel/rhino-developer-samples](https://github.com/mcneel/rhino-developer-samples)
- [developer.rhino3d.com](https://developer.rhino3d.com/) (polite, rate-limited fetch)

Do not bulk-scrape Rhino Discourse without permission.

## Evaluation

- Held-out prompts: `eval/prompts.jsonl` (40 tasks)
- Heuristic scorer: `python eval/score_outputs.py --predictions eval/runs/latest.jsonl`
- Training notebook runs 5 prompts before/after fine-tune

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CUDA OOM | Switch to 1.5B, `max_seq_length=1024`, LoRA rank 16 |
| Unsloth install fails | Notebook includes fallback `peft` + `bitsandbytes` notes |
| HF 401 | `huggingface-cli login` or set `HF_TOKEN` in Colab secrets |
| Empty dataset after build | Run `init_seed.py` or `download_sources.py` first |

## Model card (summary)

- **Base:** Qwen2.5-Coder-3B-Instruct (fallback 1.5B)
- **Method:** QLoRA SFT, chat template + Rhino system prompt
- **Target:** 3k–15k curated examples (expand via scripts)
