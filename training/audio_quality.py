"""Dependency-light signal quality cues; no model or web dependencies."""
import numpy as np

def audio_quality(signal):
    signal=np.asarray(signal,dtype=np.float64)
    if (signal.ndim != 1 or not 1600 <= len(signal) <= 160000
            or not np.all(np.isfinite(signal)) or np.max(np.abs(signal)) > 1):
        raise ValueError('Expected 0.1–10 s finite normalized mono 16 kHz signal')
    rms=float(np.sqrt(np.mean(signal*signal)))
    clipping=float(np.mean(np.abs(signal)>=.999))
    warnings=[]
    if rms < .001: warnings.append('near_silence')
    if clipping >= .01: warnings.append('clipping')
    return {'rms_dbfs':float(20*np.log10(max(rms,1e-12))),
        'clipping_fraction':clipping,'warnings':warnings,'thresholds_validated':False,
        'species_verified':False,'scope':'Engineering quality cues only; not noise SNR or dog event confidence'}
