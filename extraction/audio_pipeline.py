# extraction/audio_pipeline.py

import io
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, List

import numpy as np
import soundfile as sf
import librosa
import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration

from .schemas import AudioTranscript, AudioSegment


class WhisperModels:
    def __init__(self, model_name: str = "openai/whisper-large-v3"):
        print(f"[AudioPipeline] Loading Whisper model: {model_name}")
        self.processor = WhisperProcessor.from_pretrained(model_name)
        self.model = WhisperForConditionalGeneration.from_pretrained(
            model_name,
            torch_dtype="auto",
            device_map="auto",   # CPU / MPS / GPU otomatik
        )
        print(f"[AudioPipeline] Whisper model loaded successfully")


class AudioPipeline:
    """
    Torchaudio kullanmayan, tamamen soundfile + librosa tabanlı
    offline Whisper ses/video pipeline.
    """

    def __init__(self, model_name: str = "openai/whisper-small"):
        self.whisper = WhisperModels(model_name=model_name)

    # ----------------------------------------------------------- #
    #   AUDIO LOADING (NO TORCHAUDIO!)
    # ----------------------------------------------------------- #
    def _load_audio(self, path: str):
        """
        path → waveform(np.ndarray), sr(int)
        """
        audio, sr = sf.read(path)

        # Eğer stereo ise → mono
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)

        # Whisper genelde 16000 Hz ister
        if sr != 16000:
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
            sr = 16000

        return audio, sr

    # ----------------------------------------------------------- #
    #   AUDIO TRANSCRIBE
    # ----------------------------------------------------------- #
    def transcribe_audio(self, data: bytes, filename: str) -> AudioTranscript:
        suffix = Path(filename).suffix or ".wav"

        # 1) Geçici dosya oluştur
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            audio_path = tmp.name

        # 2) Yükle
        waveform, sr = self._load_audio(audio_path)

        # 3) Whisper input
        inputs = self.whisper.processor(
            waveform,
            sampling_rate=sr,
            return_tensors="pt",
        ).to(self.whisper.model.device)

        # 4) Generate
        with torch.no_grad():
            predicted_ids = self.whisper.model.generate(**inputs)

        text = self.whisper.processor.batch_decode(
            predicted_ids, skip_special_tokens=True
        )[0]

        duration_sec = len(waveform) / sr

        return AudioTranscript(
            text=text,
            language="tr",
            segments=[AudioSegment(start=0, end=duration_sec, text=text)],
            duration_seconds=duration_sec,
            source_type="audio",
        )

    # ----------------------------------------------------------- #
    #   VIDEO → AUDIO → TRANSCRIBE
    # ----------------------------------------------------------- #
    def transcribe_video(self, data: bytes, filename: str) -> AudioTranscript:
        suffix = Path(filename).suffix or ".mp4"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmpv:
            tmpv.write(data)
            video_path = tmpv.name

        audio_path = f"{video_path}.wav"

        # ffmpeg - extract mono audio
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            audio_path,
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Transcribe extracted audio
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        transcript = self.transcribe_audio(audio_bytes, Path(audio_path).name)
        transcript.source_type = "video"
        return transcript
