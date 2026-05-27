# Rhino Colab LLM

A **Rhino 3D specialist** chat model: fine-tune [Gemma 4 E4B](https://huggingface.co/google/gemma-4-E4B-it) with **QLoRA** on Google Colab or a local GPU, then chat and export **GGUF Q4_K_M** for small-GPU inference.

Covers **Rhino.Python** (`rhinoscriptsyntax`, `scriptcontext`), **RhinoCommon C#**, and conceptual Rhino SDK topics.

> **Disclaimer:** This model is a coding *helper*. Always verify APIs against [developer.rhino3d.com](https://developer.rhino3d.com/) and test scripts inside Rhino.

> **Gemma license:** Accept the model terms on Hugging Face for [`google/gemma-4-E4B-it`](https://huggingface.co/google/gemma-4-E4B-it) before training.

## Quick start

### 1. Local data prep (optional)

The repo includes a **13k+** training set. Rebuild anytime:

```bash
cd "My LLM"
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
python scripts/build_huge_dataset.py
```

Outputs:

- `data/processed/rhino_sft.jsonl` (~13k train rows)
- `data/processed/rhino_sft_eval.jsonl` (~1.5k eval rows)

### 2. Train on Colab (GPU)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/RezaHouri/My-LLM/blob/main/notebooks/02_train_rhino_llm.ipynb)

1. Runtime → **GPU** (T4 or better).
2. Hugging Face login (`HF_TOKEN`) + accept Gemma 4 license on HF.
3. Clone this repo (dataset is in `data/processed/rhino_sft.jsonl`).
4. Run all cells; adapter saved to Drive (`rhino-gemma4-e4b-lora/`).

### 3. Chat & export

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/RezaHouri/My-LLM/blob/main/notebooks/03_chat_and_export.ipynb)

- Gradio chat with LoRA
- Optional merge to full HF weights
- GGUF **Q4_K_M** export for Ollama / LM Studio / llama.cpp

### 4. Dataset notebook

[`notebooks/01_prepare_dataset.ipynb`](notebooks/01_prepare_dataset.ipynb) — wrapper over `build_huge_dataset.py`.

## Repository layout

```
├── configs/train_qlora.yaml      # Gemma 4 E4B + E2B fallback
├── data/processed/
│   ├── rhino_sft.jsonl           # train (in repo)
│   └── rhino_sft_eval.jsonl      # eval (in repo)
├── scripts/build_huge_dataset.py
└── notebooks/
    ├── 02_train_rhino_llm.ipynb
    └── 03_chat_and_export.ipynb
```

## GPU notes

| Hardware | Training | Inference |
|----------|----------|-----------|
| Colab T4 16 GB | QLoRA Gemma 4 E4B, seq 2048 | 4-bit + LoRA |
| OOM on T4 | Use E2B fallback, seq 1024, rank 16 | See `configs/train_qlora.yaml` |
| RTX 4090 / 5090 | E4B or E2B comfortably | Merged 4-bit or GGUF |
| 4 GB local | — | E2B + Q4_K_M GGUF |

## Model card (summary)

- **Base:** `google/gemma-4-E4B-it` (fallback `google/gemma-4-E2B-it`)
- **Method:** QLoRA SFT via Unsloth, chat template + Rhino system prompt
- **Data:** ~13k train / ~1.5k eval (McNeel samples + docs + synthetic)

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CUDA OOM | `USE_FALLBACK = True` (E2B), `max_seq_length=1024` |
| HF 403 on Gemma | Accept license on model page; login with `HF_TOKEN` |
| Unsloth install fails | Upgrade transformers; see Unsloth Gemma 4 docs |
| Colab 404 on clone | Make repo **public** or upload `rhino_sft.jsonl` to Drive |
