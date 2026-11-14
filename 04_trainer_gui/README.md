# Stage 04 · Two-Stage Kronos Fine-Tuning Supervisor (`04_trainer_gui/`)

## Overview

Desktop process supervisor (`gui_trainer.py`) for orchestrating isolated virtual-environment fine-tuning of **Kronos** ([`shiyu-coder/Kronos`](https://github.com/shiyu-coder/Kronos)) in two sequential phases:
1. **Stage A — Tokenizer Fine-Tuning** (discrete market state quantization)
2. **Stage B — Predictor Fine-Tuning** (autoregressive sequence modeling with Cosine Annealing LR & Early Stopping)

Set `KRONOS_HOME` (defaults to `./kronos_runtime`) to point to your local Kronos model runtime directory.
