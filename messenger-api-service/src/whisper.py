import base64
import tempfile
import subprocess
import os

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
    
    # Create a temporary file to store the audio
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
        temp_audio_path = temp_audio_file.name
        temp_audio_file.write(audio_data)
    
    try:
        # Call whisper-cli to transcribe the audio
        whisper_cli_path = '/whisper.cpp/build/bin/whisper-cli'
        result = subprocess.run(
            [whisper_cli_path, '-l', 'ru', '-m', '/whisper.cpp/models/ggml-tiny.bin', '-f', temp_audio_path],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Extract transcription from output
        transcription = result.stdout.strip()
        
        return transcription
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
    