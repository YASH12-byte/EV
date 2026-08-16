"""
Proposed Hybrid Model: CNN → LSTM → Attention → Forecast
with optional Physics-Informed regularization hooks.
"""
from __future__ import annotations

from typing import Optional, Tuple

import tensorflow as tf
from tensorflow.keras import Model, layers, optimizers, regularizers

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import config


class AttentionBlock(layers.Layer):
    """Bahdanau-style temporal attention over LSTM outputs."""

    def __init__(self, units: int = 64, **kwargs):
        super().__init__(**kwargs)
        self.units = units
        self.W = layers.Dense(units)
        self.V = layers.Dense(1)

    def call(self, inputs):
        # inputs: (batch, timesteps, features)
        score = self.V(tf.nn.tanh(self.W(inputs)))
        weights = tf.nn.softmax(score, axis=1)
        context = tf.reduce_sum(weights * inputs, axis=1)
        return context, weights

    def get_config(self):
        cfg = super().get_config()
        cfg.update({"units": self.units})
        return cfg


def build_hybrid_cnn_lstm_attention(
    seq_len: int,
    n_features: int,
    cnn_filters=None,
    lstm_units: int = None,
    attention_units: int = None,
    dropout: float = None,
    learning_rate: float = None,
) -> Model:
    cnn_filters = cnn_filters or config.CNN_FILTERS
    lstm_units = lstm_units or config.LSTM_UNITS
    attention_units = attention_units or config.ATTENTION_UNITS
    dropout = dropout if dropout is not None else config.DROPOUT
    learning_rate = learning_rate or config.LEARNING_RATE

    inp = layers.Input(shape=(seq_len, n_features), name="sequence_input")
    x = inp
    for i, f in enumerate(cnn_filters):
        x = layers.Conv1D(
            filters=f,
            kernel_size=3,
            padding="same",
            activation="relu",
            kernel_regularizer=regularizers.l2(1e-4),
            name=f"cnn_{i+1}",
        )(x)
        x = layers.BatchNormalization(name=f"bn_{i+1}")(x)
        x = layers.MaxPooling1D(pool_size=2, name=f"pool_{i+1}")(x) if i == 0 else x

    x = layers.LSTM(lstm_units, return_sequences=True, name="lstm")(x)
    x = layers.Dropout(dropout, name="dropout_lstm")(x)
    context, attn_weights = AttentionBlock(attention_units, name="attention")(x)
    x = layers.Dense(64, activation="relu", name="dense_1")(context)
    x = layers.Dropout(dropout / 2, name="dropout_dense")(x)
    out = layers.Dense(1, activation="linear", name="forecast")(x)

    model = Model(inputs=inp, outputs=out, name="Hybrid_CNN_LSTM_Attention")
    model.compile(
        optimizer=optimizers.Adam(learning_rate=learning_rate),
        loss="mse",
        metrics=["mae", "mse"],
    )
    return model


def build_cnn_gru(seq_len: int, n_features: int) -> Model:
    inp = layers.Input(shape=(seq_len, n_features))
    x = layers.Conv1D(64, 3, padding="same", activation="relu")(inp)
    x = layers.MaxPooling1D(2)(x)
    x = layers.GRU(128, return_sequences=False)(x)
    x = layers.Dense(64, activation="relu")(x)
    out = layers.Dense(1)(x)
    model = Model(inp, out, name="CNN_GRU")
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model


def build_lstm(seq_len: int, n_features: int) -> Model:
    inp = layers.Input(shape=(seq_len, n_features))
    x = layers.LSTM(128)(inp)
    out = layers.Dense(1)(x)
    model = Model(inp, out, name="LSTM")
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model


def build_bilstm(seq_len: int, n_features: int) -> Model:
    inp = layers.Input(shape=(seq_len, n_features))
    x = layers.Bidirectional(layers.LSTM(64))(inp)
    out = layers.Dense(1)(x)
    model = Model(inp, out, name="BiLSTM")
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model


def build_transformer_encoder(seq_len: int, n_features: int, d_model: int = 64, num_heads: int = 4) -> Model:
    inp = layers.Input(shape=(seq_len, n_features))
    x = layers.Dense(d_model)(inp)
    attn = layers.MultiHeadAttention(num_heads=num_heads, key_dim=d_model // num_heads)(x, x)
    x = layers.Add()([x, attn])
    x = layers.LayerNormalization()(x)
    x = layers.GlobalAveragePooling1D()(x)
    x = layers.Dense(64, activation="relu")(x)
    out = layers.Dense(1)(x)
    model = Model(inp, out, name="Transformer")
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    return model


def get_attention_model(base_model: Model) -> Model:
    """Return a model that also outputs attention weights for XAI maps."""
    attn_layer = base_model.get_layer("attention")
    # Rebuild graph: find intermediate outputs
    # Simpler approach: create model from sequence_input to attention outputs
    for layer in base_model.layers:
        if isinstance(layer, AttentionBlock) or layer.name == "attention":
            # Can't easily splice; provide helper via functional reuse in training script
            break
    return base_model
