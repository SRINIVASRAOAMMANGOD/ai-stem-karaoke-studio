"""
================================================================================
KARAOKE STUDIO - DEMUCS AUDIO STEM SEPARATION SERVICE
================================================================================
AI-powered audio stem separation using Demucs (Meta's Facebook Research model).

What It Does:
Separates mixed audio into individual stems:
- vocals (lead singer)
- drums (percussion)
- bass (bass guitar/low frequencies)
- other (guitar, keys, strings, etc)

Key Features:
1. MODEL CACHING: Load models once, reuse in memory (massive speedup)
2. GPU ACCELERATION: Use CUDA > MPS > CPU (falls back automatically)
3. BATCH PROCESSING: Process multiple audio files
4. OPTIONAL TWO-STEM: Isolate vocals + backing track (for karaoke)

Performance:
- First call: ~30-60 seconds (model loads from disk)
- Subsequent calls: Instant (model cached in memory)
- Processing time: 1-3 minutes depending on audio length

Usage:
    from services.demucs_service import separate_audio
    stems_folder = separate_audio('song.mp3', model='htdemucs')
    # Returns: projects/20240101_120000/stems/htdemucs/song/{vocals,drums,bass,other}.wav
================================================================================
"""

import os
import torch
import torchaudio


# ── Module-level Model Cache ─────────────────────────────────────────────────
# Store loaded models in memory to avoid reloading (huge performance boost)
# Key: model name (e.g. 'htdemucs'), Value: loaded model object
_model_cache: dict = {}


def _get_device() -> str:
    """
    Detect best available device for running inference.
    Priority: CUDA (NVIDIA GPU) > MPS (Apple Metal) > CPU
    
    Returns:
        'cuda' if NVIDIA GPU available
        'mps' if Apple GPU available
        'cpu' as fallback
    """
    if torch.cuda.is_available():
        return 'cuda'
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return 'mps'
    return 'cpu'


def _load_model(model_name: str = 'htdemucs'):
    """
    Load Demucs model, caching it for future calls.
    
    First call for a model: ~30-60 seconds (downloads/loads from disk)
    Subsequent calls: Instant (uses cached model in memory)
    
    Args:
        model_name: Name of Demucs model
                   'htdemucs' (default, 4 stems)
                   'htdemucs_ft' (fine-tuned)
                   'htdemucs_6s' (6 stems with piano/guitar)
                   'mdx_extra', 'mdx_extra_q'
    
    Returns:
        demucs.Separator: A loaded model ready for inference
    """
    # OPTIMIZATION: Return cached model if already loaded
    if model_name in _model_cache:
        print(f"[Demucs] Using cached model '{model_name}'")
        return _model_cache[model_name]

    # LOAD: First-time load (slow, but only happens once)
    print(f"[Demucs] Loading '{model_name}' for first time (this takes a moment)…")
    from demucs.pretrained import get_model

    device = _get_device()
    model = get_model(model_name)
    model.to(device)
    model.eval()  # Inference mode (no gradients)

    # CACHE: Store for future use
    _model_cache[model_name] = model
    print(f"[Demucs] ✓ '{model_name}' loaded and cached on {device}")
    return model


def separate_audio(file_path, model='htdemucs', output_folder='separated', two_stems=None):
    """
    Separate audio file into stems (vocals, drums, bass, other).
    
    PROCESS:
    1. Load the AI model (cached after first load)
    2. Load audio file and convert to model's format
    3. Run neural network inference
    4. Save 4 stem files (vocals.wav, drums.wav, bass.wav, other.wav)
    
    Optional: If two_stems='vocals', save ONLY vocals + combined backing track
              (useful for karaoke - user sings over backing)
    
    Args:
        file_path: Path to audio file (MP3, WAV, FLAC, M4A, OGG, AAC)
        model: Demucs model name (default 'htdemucs' for 4 stems)
        output_folder: Root folder for output (creates subfolders automatically)
        two_stems: If set (e.g. 'vocals'), isolate that stem + backing
    
    Returns:
        Path to stems folder on success (e.g. 'projects/20240101_120000/stems/htdemucs/song/')
        None on failure
    
    Output Structure:
        output_folder/
        └── model_name/
            └── track_name/
                ├── vocals.wav
                ├── drums.wav
                ├── bass.wav
                └── other.wav
    
    Time:
        First call: 1-3 minutes (depends on audio length)
        Subsequent calls: Still 1-3 minutes (processing time, not model loading)
    """
    try:
        # INIT: Create output folder, detect hardware
        os.makedirs(output_folder, exist_ok=True)
        device = _get_device()

        print(f"\n[Demucs] ═══════════════════════════════════════════════════════")
        print(f"[Demucs] SEPARATION STARTED")
        print(f"[Demucs] Input  : {file_path}")
        print(f"[Demucs] Model  : {model}")
        print(f"[Demucs] Device : {device} ({'GPU' if device != 'cpu' else 'CPU'})")
        print(f"[Demucs] ═══════════════════════════════════════════════════════")

        # STEP 1: Load model (once per session, then cached)
        demucs_model = _load_model(model)

        # STEP 2: Load audio and convert to model's format
        print(f"[Demucs] Loading audio file…")
        from demucs.audio import convert_audio
        from demucs.apply import apply_model

        wav, sr = torchaudio.load(file_path)
        print(f"[Demucs] Loaded {wav.shape[0]} channels @ {sr}Hz → converting…")
        
        # Convert to model's expected sample rate and channels
        wav = convert_audio(wav, sr, demucs_model.samplerate, demucs_model.audio_channels)
        wav = wav.to(device)

        # STEP 3: Run separation (AI inference)
        print(f"[Demucs] Running separation (this may take 1-3 minutes)…")
        with torch.no_grad():
            # Apply model: returns sources with shape [stems, channels, samples]
            sources = apply_model(demucs_model, wav[None], device=device, progress=True)[0]

        # Move results back to CPU for saving
        sources = sources.cpu()
        stem_names = demucs_model.sources  # e.g. ['drums', 'bass', 'other', 'vocals']

        # STEP 4: Save separated stems as WAV files
        track_name = os.path.splitext(os.path.basename(file_path))[0]
        stems_path = os.path.join(output_folder, model, track_name)
        os.makedirs(stems_path, exist_ok=True)

        if two_stems:
            # KARAOKE MODE: Save requested stem + combined remainder
            # Example: two_stems='vocals' → save vocals.wav + no_vocals.wav
            target_idx = stem_names.index(two_stems) if two_stems in stem_names else None
            for idx, (name, source) in enumerate(zip(stem_names, sources)):
                if target_idx is None:
                    # Stem not found — save all stems as fallback
                    out_name = f"{name}.wav"
                elif idx == target_idx:
                    # Save the isolated stem
                    out_name = f"{name}.wav"
                else:
                    continue  # Skip other stems (not needed for karaoke)

                out_path = os.path.join(stems_path, out_name)
                torchaudio.save(out_path, source, demucs_model.samplerate)
                print(f"[Demucs] Saved {out_name}")

            # Create combined backing track (all non-vocal stems mixed)
            if target_idx is not None:
                others = [s for i, s in enumerate(sources) if i != target_idx]
                if others:
                    combined = torch.stack(others).sum(dim=0)
                    no_stem_path = os.path.join(stems_path, f"no_{two_stems}.wav")
                    torchaudio.save(no_stem_path, combined, demucs_model.samplerate)
                    print(f"[Demucs] Saved no_{two_stems}.wav (backing track)")
        else:
            # NORMAL MODE: Save all 4 stems
            for name, source in zip(stem_names, sources):
                out_path = os.path.join(stems_path, f"{name}.wav")
                torchaudio.save(out_path, source, demucs_model.samplerate)
                print(f"[Demucs] Saved {name}.wav")

        # SUCCESS
        print(f"[Demucs] ═══════════════════════════════════════════════════════")
        print(f"[Demucs] ✓ SEPARATION COMPLETE")
        print(f"[Demucs] Output: {stems_path}")
        print(f"[Demucs] Files : {', '.join(os.listdir(stems_path))}")
        print(f"[Demucs] ═══════════════════════════════════════════════════════\n")
        
        return stems_path

    except Exception as e:
        print(f"\n[Demucs] ✗ ERROR during separation: {e}")
        import traceback
        traceback.print_exc()
        print()
        return None


def get_available_models():
    """
    Return list of supported Demucs model names.
    
    Returns:
        List of model names available
    """
    return [
        'htdemucs',       # ⭐ Default: 4 stems (vocals, drums, bass, other)
        'htdemucs_ft',    # Fine-tuned for better quality
        'htdemucs_6s',    # 6 stems (adds piano, guitar to 4 stems)
        'mdx_extra',      # Alternative model
        'mdx_extra_q',    # Quantized MDX (smaller, faster, slightly lower quality)
    ]


def check_demucs_installed():
    """
    Check if Demucs package is installed and available.
    
    Returns:
        True if Demucs can be imported, False otherwise
    """
    try:
        import demucs  # noqa: F401
        return True
    except ImportError:
        return False

