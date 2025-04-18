import base64
import tempfile
import os
import ffmpeg
import httpx

def transcribe_audio(audio_base64: str) -> str:
    """
    Transcribe base64-encoded audio using whisper.cpp
    
    Args:
        audio_base64: Base64-encoded audio data
    
    Returns:
        Transcribed text
    """
    
    # Check if the string is a data URL and extract the base64 part
    if audio_base64.startswith('data:'):
        # Split by comma and take the second part (the actual base64 data)
        audio_base64 = audio_base64.split(',', 1)[1]
    
    # Decode base64 audio data
    audio_data = base64.b64decode(audio_base64)
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_ogg_file:
        temp_ogg_path = temp_ogg_file.name
        temp_ogg_file.write(audio_data)
    
    # Convert OGG to WAV using ffmpeg
    temp_wav_path = temp_ogg_path.replace('.ogg', '.wav')
    ffmpeg.input(temp_ogg_path).output(temp_wav_path).run(quiet=True, overwrite_output=True)
    
    try:
        # Rest of your code remains the same
        whisper_api_url = os.environ.get('WHISPER_API_URL', 'http://192.168.191.96:6666/inference')
        
        with open(temp_wav_path, 'rb') as f:
            files = {'file': ('audio.wav', f)}
            data = {
                'temperature': '0.0',
                'temperature_inc': '0.2',
                'language': 'ru',
                'response_format': 'json'
            }

            response = httpx.post(
                whisper_api_url,
                files=files,
                data=data,
                timeout=30
            )

            if response.status_code != 200:
                return ""

            result = response.json()
            transcription = result.get('text', '').strip()

            return transcription
    finally:
        # Clean up the temporary files
        if os.path.exists(temp_ogg_path):
            os.remove(temp_ogg_path)
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)