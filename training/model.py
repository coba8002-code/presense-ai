"""Small deterministic softmax regression baseline, serialized as JSON (no pickle)."""
import numpy as np


def probabilities(x: np.ndarray, weights: np.ndarray) -> np.ndarray:
    scores = np.column_stack([x, np.ones(len(x))]) @ weights
    scores -= scores.max(axis=1, keepdims=True)
    exp = np.exp(scores)
    return exp / exp.sum(axis=1, keepdims=True)


def fit(x: np.ndarray, y: np.ndarray, classes: int, penalty: float) -> np.ndarray:
    design = np.column_stack([x, np.ones(len(x))])
    weights = np.zeros((design.shape[1], classes))
    target = np.eye(classes)[y]
    for _ in range(600):
        gradient = design.T @ (probabilities(x, weights) - target) / len(x)
        gradient[:-1] += penalty * weights[:-1]
        weights -= .05 * gradient
    return weights


def predict(model: dict, x: np.ndarray) -> np.ndarray:
    from training.audio import FEATURE_VERSION
    if model.get('feature_version') != FEATURE_VERSION:
        raise ValueError('Unsupported feature version')
    mean, scale, weights = (np.array(model[key]) for key in ('mean', 'scale', 'weights'))
    if (mean.shape != (x.shape[1],) or scale.shape != mean.shape
            or weights.shape != (x.shape[1] + 1, len(model['labels']))
            or not all(np.isfinite(a).all() for a in (mean, scale, weights))
            or np.any(scale <= 0)):
        raise ValueError('Invalid model parameters')
    return probabilities((x - mean) / scale, weights)
