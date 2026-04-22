import os
from transformers import AutoProcessor, MusicgenForConditionalGeneration
import scipy
import io
import shutil

# ✅ Single cache directory inside /tmp
cache_dir = "/tmp/hf_cache"

# ✅ Clean up old cache before starting (optional but helpful)
shutil.rmtree(cache_dir, ignore_errors=True)
os.makedirs(cache_dir, exist_ok=True)

# ✅ Environment variables to keep Hugging Face cache ephemeral
os.environ["HF_HOME"] = cache_dir
os.environ["TRANSFORMERS_CACHE"] = cache_dir
os.environ["HF_DATASETS_CACHE"] = cache_dir
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

# Global variables to cache model and processor
_processor = None
_model = None


def _load_model():
    """Load model and processor only once (lazy loading)."""
    global _processor, _model
    if _processor is None:
        _processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
    if _model is None:
        _model = MusicgenForConditionalGeneration.from_pretrained(
            "facebook/musicgen-small"
        )
    return _processor, _model


def generate_music(prompt: str, max_new_tokens: int = 1024) -> bytes:
    """
    Generates music from a text prompt using MusicGen and returns the saved file path.

    Args:
        prompt (str): The input prompt describing the music.
        max_new_tokens (int): Controls duration (higher = longer audio).

    Returns:
        bytes: The generated audio in WAV format.
    """
    processor, model = _load_model()

    # Prepare input for the model
    inputs = processor(text=[prompt], padding=True, return_tensors="pt")

    # Generate music (increase max_new_tokens for longer audio)
    audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)

    # Save to WAV file
    sampling_rate = model.config.audio_encoder.sampling_rate
    buffer = io.BytesIO()
    scipy.io.wavfile.write(buffer, rate=sampling_rate, data=audio_values[0, 0].numpy())

    return buffer.getvalue()


if __name__ == "__main__":
    generate_music("make music for drake rap")
