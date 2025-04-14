import base64
import tempfile
import os
from pydub import AudioSegment
from src.config import logger
import httpx

def transcribe_audio(audio_base64: str) -> str:
    """
    Transcribe base64-encoded audio using whisper.cpp
    
    Args:
        audio_base64: Base64-encoded audio data
    
    Returns:
        Transcribed text
    """
    # Decode base64 audio data
    audio_data = base64.b64decode(audio_base64)
    
    # Create a temporary file to store the OGG audio
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_ogg_file:
        temp_ogg_path = temp_ogg_file.name
        temp_ogg_file.write(audio_data)
    
    # Convert OGG to WAV using pydub
    sound = AudioSegment.from_ogg(temp_ogg_path)
    temp_wav_path = temp_ogg_path.replace('.ogg', '.wav')
    sound.export(temp_wav_path, format="wav")
    
    try:
        with open(temp_wav_path, 'rb') as f:
            files = {'file': ('audio.wav', f)}
            data = {
                'temperature': '0.0',
                'temperature_inc': '0.2',
                'language': 'ru',
                'response_format': 'json'
            }

            response = httpx.post(
                'http://127.0.0.1:8080/inference',
                files=files,
                data=data,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"Whisper server error: {response.status_code}, {response.text}")
                return ""

            result = response.json()
            transcription = result.get('text', '').strip()

            return transcription
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
    