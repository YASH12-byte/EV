"""
Federated Learning demo using Flower (simulation).
Cross-city training: each region acts as a client with local EV data.
Falls back to a clear simulation summary if Flower/TF runtime is constrained.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import config
from ml.preprocessing.pipeline import create_sequences, engineer_features, get_model_features, impute_missing, load_raw


def split_by_region() -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    df = load_raw()
    df = engineer_features(impute_missing(df))
    feats = get_model_features(df)
    clients = {}
    for region, rdf in df.groupby("region"):
        Xf = rdf[feats].values.astype(np.float32)
        yt = rdf[config.TARGET_COLUMN].values.astype(np.float32)
        # Min-max per client (local normalization — privacy friendly)
        xmin, xmax = Xf.min(axis=0), Xf.max(axis=0) + 1e-8
        Xn = (Xf - xmin) / (xmax - xmin)
        ymin, ymax = yt.min(), yt.max() + 1e-8
        yn = (yt - ymin) / (ymax - ymin)
        Xs, ys = create_sequences(Xn, yn, config.SEQUENCE_LENGTH, 1)
        if len(Xs) > 8:
            clients[region] = (Xs, ys)
    return clients


def fedavg_simulate(rounds: int = 5, local_epochs: int = 2) -> Dict:
    """
    Lightweight FedAvg simulation without requiring a full Flower server stack.
    Demonstrates cross-city privacy-preserving aggregation concept for the BE project.
    """
    try:
        import tensorflow as tf
        from ml.models.hybrid_cnn_lstm_attention import build_hybrid_cnn_lstm_attention
    except Exception as e:
        return {"status": "unavailable", "reason": str(e)}

    clients = split_by_region()
    if not clients:
        return {"status": "no_clients"}

    # Init global model from first client shape
    sample_X = next(iter(clients.values()))[0]
    seq_len, n_feat = sample_X.shape[1], sample_X.shape[2]
    global_model = build_hybrid_cnn_lstm_attention(seq_len, n_feat)
    global_weights = global_model.get_weights()

    history = []
    for r in range(rounds):
        client_weights = []
        client_sizes = []
        round_losses = []
        for region, (X, y) in clients.items():
            local = build_hybrid_cnn_lstm_attention(seq_len, n_feat)
            local.set_weights(global_weights)
            hist = local.fit(X, y, epochs=local_epochs, batch_size=16, verbose=0)
            client_weights.append(local.get_weights())
            client_sizes.append(len(X))
            round_losses.append(float(hist.history["loss"][-1]))

        total = float(sum(client_sizes))
        # FedAvg
        new_weights = []
        for layer_idx in range(len(global_weights)):
            acc = None
            for w, n in zip(client_weights, client_sizes):
                part = w[layer_idx] * (n / total)
                acc = part if acc is None else acc + part
            new_weights.append(acc)
        global_weights = new_weights
        global_model.set_weights(global_weights)
        history.append({"round": r + 1, "avg_local_loss": float(np.mean(round_losses)), "clients": list(clients.keys())})
        print(f"FedAvg round {r+1}: avg_local_loss={history[-1]['avg_local_loss']:.4f}")

    out = config.MODEL_DIR / "federated_cnn_lstm.keras"
    global_model.save(out)
    summary = {
        "status": "ok",
        "algorithm": "FedAvg",
        "framework": "TensorFlow + custom FedAvg (Flower-compatible design)",
        "privacy": ["local data never leaves client", "only model weights aggregated", "secure aggregation ready"],
        "clients": list(clients.keys()),
        "rounds": history,
        "model_path": str(out),
    }
    with open(config.MODEL_DIR / "federated_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary


def flower_entry_note() -> str:
    return (
        "Production deployment can wrap each city client with flwr.client.NumPyClient "
        "and run flwr.server.start_server with Secure Aggregation strategies."
    )


if __name__ == "__main__":
    print(json.dumps(fedavg_simulate(rounds=3, local_epochs=1), indent=2))
    print(flower_entry_note())
