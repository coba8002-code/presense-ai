import numpy as np


def classification_metrics(y: np.ndarray, probabilities: np.ndarray,
                           labels: list[str], threshold: float = .7) -> dict:
    y = np.asarray(y)
    p = np.asarray(probabilities)
    if (y.ndim != 1 or not len(y) or p.shape != (len(y), len(labels))
            or len(labels) < 2 or len(set(labels)) != len(labels)
            or not np.issubdtype(y.dtype, np.integer)
            or np.any(y < 0) or np.any(y >= len(labels))
            or not np.isfinite(p).all() or np.any(p < 0) or np.any(p > 1)
            or not np.allclose(p.sum(axis=1), 1) or not 0 <= threshold <= 1):
        raise ValueError('Invalid labels, probabilities or abstention threshold')
    prediction = p.argmax(axis=1)
    confidence = p.max(axis=1)
    correct = prediction == y
    confusion = np.zeros((len(labels), len(labels)), dtype=int)
    np.add.at(confusion, (y, prediction), 1)
    denom = confusion.sum(axis=0) + confusion.sum(axis=1)
    f1 = np.divide(2 * confusion.diagonal(), denom, out=np.zeros(len(labels)), where=denom > 0)
    ece = 0.0
    for i in range(10):
        mask = (confidence >= i/10) & ((confidence < (i+1)/10) if i < 9 else (confidence <= 1))
        if mask.any():
            ece += mask.mean() * abs(correct[mask].mean() - confidence[mask].mean())
    accepted = confidence >= threshold
    return {'labels': labels, 'count': len(y), 'accuracy': float(correct.mean()),
            'macro_f1': float(f1.mean()), 'per_class_f1': f1.tolist(),
            'class_counts': confusion.sum(axis=1).tolist(), 'confusion_matrix': confusion.tolist(),
            'brier': float(np.mean(np.sum((p - np.eye(len(labels))[y])**2, axis=1))),
            'ece': float(ece), 'calibration': 'uncalibrated; ECE uses 10 equal-width bins',
            'abstention_threshold': threshold, 'coverage': float(accepted.mean()),
            'selective_accuracy': float(correct[accepted].mean()) if accepted.any() else None}
