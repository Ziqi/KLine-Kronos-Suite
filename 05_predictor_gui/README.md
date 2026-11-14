# Stage 05 · Autoregressive Inference & Candlestick Trajectory Desk (`05_predictor_gui/`)

## Overview

Loads fine-tuned Kronos Tokenizer & Predictor checkpoints from `KRONOS_HOME/models/`, applies cross-sectional z-score normalization (`clip[-5.0, 5.0]`), runs multi-step rollout trajectories aligned to the A-share trading calendar (`09:35–11:30`, `13:05–15:00`, skipping lunch breaks and weekends), inverse-transforms predictions back to price space, and renders interactive candlestick trajectories.

## Components

- **`gui_predictor.py`** — Interactive `ttkbootstrap` inference & candlestick visualization workstation.
- **`run_predictor_inference.py`** — Subprocess inference runner invoked by the GUI or standalone CLI.
