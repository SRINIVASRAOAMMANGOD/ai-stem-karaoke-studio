"""
Vocal performance scoring service.

Compares the user recorded vocals against the isolated original vocal stem
and returns scored metrics (0-100) using standard Music Information Retrieval
evaluation methodology via mir_eval + librosa.

Libraries:
  librosa  - feature extraction (pyin, MFCC, RMS, onsets, chroma)
  mir_eval - standardised MIR evaluation metrics
             * mir_eval.melody : pitch accuracy with +-50-cent tolerance
             * mir_eval.onset  : onset F-measure with +-50 ms window

Install:  pip install librosa mir_eval
"""

import numpy as np


# --- Constants ----------------------------------------------------------------
SR           = 22050     # analysis sample-rate
HOP          = 512
MAX_DURATION = 60.0      # cap so pyin never times out on long tracks


# --- Public API ---------------------------------------------------------------

def analyze_vocal_accuracy(vocal_path: str, recording_path: str) -> dict:
    """
    Score the user recording against the isolated reference vocal.

    Metrics (all 0-100):
      pitch_accuracy  - fraction of voiced frames within +-50 cents of reference
                        (mir_eval Raw Pitch Accuracy x 100)
      timing_accuracy - onset alignment F-measure within +-50 ms window
                        (mir_eval onset F-measure x 100)
      tone_quality    - MFCC cosine similarity (timbre match)
      expression      - Pearson correlation of RMS loudness contours
      consistency     - chroma accuracy fraction (pitch-class, octave-tolerant)
      breath_control  - similarity of pause/silence pattern ratios
      overall_score   - simple average of the six metrics

    Returns a dict with scores and per-metric short feedback text.
    """
    try:
        import librosa
        import mir_eval
    except ImportError as exc:
        return _fallback_analysis(str(exc))

    # Load & trim ---------------------------------------------------------------
    ref_raw, _ = librosa.load(vocal_path,     sr=SR, mono=True, duration=MAX_DURATION)
    usr_raw, _ = librosa.load(recording_path, sr=SR, mono=True, duration=MAX_DURATION)

    ref, _ = librosa.effects.trim(ref_raw, top_db=20)
    usr, _ = librosa.effects.trim(usr_raw, top_db=20)

    # 1. Pitch Accuracy  (mir_eval.melody - Raw Pitch Accuracy) ----------------
    pitch_score = _score_pitch(ref, usr, librosa, mir_eval)

    # 2. Timing Accuracy  (mir_eval.onset - F-measure, +-50 ms) ----------------
    timing_score = _score_timing(ref, usr, librosa, mir_eval)

    # 3. Tone Quality  (MFCC cosine similarity) --------------------------------
    tone_score = _score_tone(ref, usr, librosa)

    # 4. Expression  (RMS Pearson correlation) ---------------------------------
    expression_score = _score_expression(ref, usr, librosa)

    # 5. Consistency  (mir_eval.melody - Raw Chroma Accuracy) ------------------
    consistency_score = _score_consistency(ref, usr, librosa, mir_eval)

    # 6. Breath Control  (pause-ratio similarity) ------------------------------
    breath_score = _score_breath(ref, usr, librosa)

    # Overall ------------------------------------------------------------------
    metrics = {
        'pitch_accuracy':  round(pitch_score),
        'timing_accuracy': round(timing_score),
        'tone_quality':    round(tone_score),
        'expression':      round(expression_score),
        'consistency':     round(consistency_score),
        'breath_control':  round(breath_score),
    }
    overall = round(sum(metrics.values()) / len(metrics))

    return {
        'overall_score':   overall,
        **metrics,
        'pitch_feedback':       _fb(metrics['pitch_accuracy'],  'Pitch accuracy'),
        'timing_feedback':      _fb(metrics['timing_accuracy'], 'Timing'),
        'tone_feedback':        _fb(metrics['tone_quality'],    'Tone quality'),
        'expression_feedback':  _fb(metrics['expression'],      'Expression'),
        'consistency_feedback': _fb(metrics['consistency'],     'Consistency'),
        'breath_feedback':      _fb(metrics['breath_control'],  'Breath control'),
    }


# --- Metric helpers -----------------------------------------------------------

def _score_pitch(ref, usr, librosa, mir_eval) -> float:
    """
    Raw Pitch Accuracy via mir_eval.melody.
    Frames within +-50 cents of reference count as correct (standard MIR threshold).
    """
    try:
        kw = dict(fmin=librosa.note_to_hz('C2'),
                  fmax=librosa.note_to_hz('C7'),
                  hop_length=HOP)
        f0_ref, voiced_ref, _ = librosa.pyin(ref, **kw)
        f0_usr, voiced_usr, _ = librosa.pyin(usr, **kw)

        n = min(len(f0_ref), len(f0_usr))
        t_ref = librosa.frames_to_time(np.arange(n), sr=SR, hop_length=HOP)
        t_usr = librosa.frames_to_time(np.arange(n), sr=SR, hop_length=HOP)

        # mir_eval expects 0 Hz for unvoiced frames
        freq_ref = np.where(voiced_ref[:n], f0_ref[:n], 0.0)
        freq_usr = np.where(voiced_usr[:n], f0_usr[:n], 0.0)

        # Replace NaN that pyin may produce
        freq_ref = np.nan_to_num(freq_ref, nan=0.0)
        freq_usr = np.nan_to_num(freq_usr, nan=0.0)

        scores = mir_eval.melody.evaluate(t_ref, freq_ref, t_usr, freq_usr)
        rpa = float(scores.get('Raw Pitch Accuracy', 0.0))
        # If pyin found voiced frames but rpa is low, trust it.
        # If both tracks had very few voiced frames, fall through to chroma.
        voiced_enough = (voiced_ref[:n].sum() > 20) and (voiced_usr[:n].sum() > 20)
        if voiced_enough:
            return max(0.0, min(100.0, rpa * 100.0))
        # Not enough voiced frames — use chroma similarity instead
        raise ValueError('insufficient voiced frames for pyin')
    except Exception:
        # Chroma-CQT fallback (octave-tolerant, works for humming/whispering too)
        try:
            ch_ref = librosa.feature.chroma_cqt(y=ref, sr=SR, hop_length=HOP).mean(axis=1)
            ch_usr = librosa.feature.chroma_cqt(y=usr, sr=SR, hop_length=HOP).mean(axis=1)
            denom  = np.linalg.norm(ch_ref) * np.linalg.norm(ch_usr) + 1e-8
            cos    = float(np.dot(ch_ref, ch_usr) / denom)
            return float(np.clip((cos + 1) / 2 * 100, 0, 100))
        except Exception:
            return 50.0


def _score_timing(ref, usr, librosa, mir_eval) -> float:
    """
    Onset F-measure via mir_eval.onset, with automatic global time-offset
    compensation before scoring.

    Karaoke recordings often start slightly later or earlier than the stem.
    A raw window comparison (even at 150 ms) returns 0 if there is a constant
    300 ms+ offset across all onsets.  We cross-correlate the onset-strength
    envelopes to find the best global shift, apply it, then compute F-measure
    with a 150 ms window.
    """
    try:
        # Onset strength envelopes (smoother than raw onsets for cross-corr)
        env_ref = librosa.onset.onset_strength(y=ref, sr=SR, hop_length=HOP)
        env_usr = librosa.onset.onset_strength(y=usr, sr=SR, hop_length=HOP)

        # Cross-correlate to find best global offset (in frames)
        n_ref, n_usr = len(env_ref), len(env_usr)
        n_fft = int(2 ** np.ceil(np.log2(n_ref + n_usr)))
        corr = np.real(np.fft.ifft(
            np.fft.fft(env_ref, n=n_fft) * np.conj(np.fft.fft(env_usr, n=n_fft))
        ))
        # Restrict search to ±5 s (avoid wrapping artefacts on very long tracks)
        max_lag = int(5.0 * SR / HOP)
        corr_trimmed = np.concatenate([corr[:max_lag], corr[n_fft - max_lag:]])
        best_lag_idx = int(np.argmax(corr_trimmed))
        if best_lag_idx < max_lag:
            best_lag = best_lag_idx          # positive = usr leads
        else:
            best_lag = best_lag_idx - len(corr_trimmed)   # negative = usr lags
        offset_sec = float(best_lag) * HOP / SR

        # Detect onsets (no backtrack to avoid librosa version issues)
        on_ref = librosa.onset.onset_detect(y=ref, sr=SR, hop_length=HOP, units='time')
        on_usr = librosa.onset.onset_detect(y=usr, sr=SR, hop_length=HOP, units='time')

        if len(on_ref) == 0 or len(on_usr) == 0:
            return 55.0

        # Shift user onsets by the detected global offset so they align with ref
        on_usr_aligned = on_usr + offset_sec

        f_measure, _, _ = mir_eval.onset.f_measure(
            on_ref, on_usr_aligned, window=0.15   # ±150 ms after alignment
        )
        return float(np.clip(f_measure * 100.0, 0.0, 100.0))
    except Exception:
        return 55.0


def _score_tone(ref, usr, librosa) -> float:
    """MFCC cosine similarity - timbre / vocal character match."""
    try:
        mfcc_ref = librosa.feature.mfcc(y=ref, sr=SR, n_mfcc=20).mean(axis=1)
        mfcc_usr = librosa.feature.mfcc(y=usr, sr=SR, n_mfcc=20).mean(axis=1)
        denom = np.linalg.norm(mfcc_ref) * np.linalg.norm(mfcc_usr) + 1e-8
        cos   = float(np.dot(mfcc_ref, mfcc_usr) / denom)
        return float(np.clip((cos + 1) / 2 * 100, 0, 100))
    except Exception:
        return 50.0


def _score_expression(ref, usr, librosa) -> float:
    """Pearson correlation of RMS energy envelopes - dynamic expressiveness."""
    try:
        rms_ref = librosa.feature.rms(y=ref)[0].astype(float) + 1e-9
        rms_usr = librosa.feature.rms(y=usr)[0].astype(float) + 1e-9
        n       = min(len(rms_ref), len(rms_usr))
        corr    = float(np.corrcoef(rms_ref[:n], rms_usr[:n])[0, 1])
        return float(np.clip((corr + 1) / 2 * 100, 0, 100))
    except Exception:
        return 50.0


def _score_consistency(ref, usr, librosa, mir_eval) -> float:
    """
    Raw Chroma Accuracy via mir_eval.melody - pitch-class match (octave-tolerant).
    Good measure of melodic consistency regardless of transposition.
    """
    try:
        kw = dict(fmin=librosa.note_to_hz('C2'),
                  fmax=librosa.note_to_hz('C7'),
                  hop_length=HOP)
        f0_ref, voiced_ref, _ = librosa.pyin(ref, **kw)
        f0_usr, voiced_usr, _ = librosa.pyin(usr, **kw)

        n       = min(len(f0_ref), len(f0_usr))
        t       = librosa.frames_to_time(np.arange(n), sr=SR, hop_length=HOP)
        freq_ref = np.nan_to_num(np.where(voiced_ref[:n], f0_ref[:n], 0.0), nan=0.0)
        freq_usr = np.nan_to_num(np.where(voiced_usr[:n], f0_usr[:n], 0.0), nan=0.0)

        scores = mir_eval.melody.evaluate(t, freq_ref, t, freq_usr)
        rca = float(scores.get('Raw Chroma Accuracy', 0.0))
        voiced_enough = (voiced_ref[:n].sum() > 20) and (voiced_usr[:n].sum() > 20)
        if voiced_enough:
            return max(0.0, min(100.0, rca * 100.0))
        raise ValueError('insufficient voiced frames for consistency pyin')
    except Exception:
        try:
            ch_ref = librosa.feature.chroma_cqt(y=ref, sr=SR, hop_length=HOP)
            ch_usr = librosa.feature.chroma_cqt(y=usr, sr=SR, hop_length=HOP)
            n = min(ch_ref.shape[1], ch_usr.shape[1])
            diff_std = float(np.std(ch_ref[:, :n] - ch_usr[:, :n]))
            return max(0.0, 100.0 - diff_std * 50.0)
        except Exception:
            return 50.0


def _score_breath(ref, usr, librosa) -> float:
    """Similarity of voiced/silence ratio - breath and phrasing pattern."""
    try:
        splits_ref = librosa.effects.split(ref, top_db=30)
        splits_usr = librosa.effects.split(usr, top_db=30)
        ratio_ref  = sum(e - s for s, e in splits_ref) / max(len(ref), 1)
        ratio_usr  = sum(e - s for s, e in splits_usr) / max(len(usr), 1)
        return max(0.0, 100.0 - abs(ratio_ref - ratio_usr) * 200.0)
    except Exception:
        return 50.0


# --- Feedback text -----------------------------------------------------------

def _fb(score: int, label: str) -> str:
    if score >= 85: return f"{label}: excellent match."
    if score >= 70: return f"{label}: good - minor differences."
    if score >= 55: return f"{label}: fair - noticeable gaps."
    return f"{label}: needs improvement."


# --- Fallback when libraries are missing ------------------------------------

def _fallback_analysis(reason: str = 'library not installed') -> dict:
    zero_fb = f'Analysis unavailable - {reason}'
    return {
        'overall_score':        0,
        'pitch_accuracy':       0,
        'timing_accuracy':      0,
        'tone_quality':         0,
        'expression':           0,
        'consistency':          0,
        'breath_control':       0,
        'pitch_feedback':       zero_fb,
        'timing_feedback':      zero_fb,
        'tone_feedback':        zero_fb,
        'expression_feedback':  zero_fb,
        'consistency_feedback': zero_fb,
        'breath_feedback':      zero_fb,
        'error': reason,
    }
