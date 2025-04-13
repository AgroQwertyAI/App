import base64
import tempfile
import subprocess
import os
from pydub import AudioSegment

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
        # Call whisper-cli to transcribe the audio (now using WAV file)
        whisper_cli_path = '/whisper.cpp/build/bin/whisper-cli'
        result = subprocess.run(
            [whisper_cli_path, '-l', 'ru', '-m', '/whisper.cpp/models/ggml-tiny.bin', '-f', temp_wav_path],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Extract transcription from output
        transcription = result.stdout.strip()

        return transcription
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)
    