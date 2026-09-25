import pytest

from backend.app.preprocessing.audio_processor import AudioProcessor


def test_corrupt_wav_does_not_return_synthetic_silence(tmp_path):
    audio = tmp_path / "broken.wav"
    audio.write_bytes(b"not a wave file")
    processor = AudioProcessor(audio, "audit")
    with pytest.raises(ValueError, match="Unable to decode WAV audio"):
        processor.load_wav()
