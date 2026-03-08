from dotenv import load_dotenv
import json
from io import BytesIO
from pathlib import Path
import signal
import time

from pydub import AudioSegment

from openai import OpenAI


load_dotenv()
with open ("config.json", "r") as file:
    config = json.load(file)

with open ("config.json", "r") as file:
    config = json.load(file)

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Speech-to-text operation timed out")

def speech_to_text(audio_stream, timeout_seconds=30):
    """
    Transcribes speech from an audio BytesIO stream to text using OpenAI's Whisper model.

    Parameters:
    - audio_stream: BytesIO, audio data
    - timeout_seconds: int, timeout for the API call

    Returns:
    - tuple: (transcription, language) or (None, None) if failed
    """
    
    if audio_stream is None:
        print("⚠️  Audio stream is None, cannot transcribe")
        return None, None
    
    # Set up timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        client = OpenAI()
        
        # Reset stream position to beginning
        audio_stream.seek(0)
        
        response = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_stream,
            response_format="verbose_json"
        )

        transcription = response.text.strip()
        language = response.language
        
        # Check if transcription is meaningful (not just empty or noise)
        if not transcription or len(transcription) < 2:
            print("⚠️  Transcription too short or empty, likely just noise")
            return None, None
        
        signal.alarm(0)  # Cancel the alarm
        return transcription, language
        
    except TimeoutError:
        print(f"🕐 Speech-to-text timed out after {timeout_seconds} seconds")
        return None, None
    except Exception as e:
        print(f"❌ Error in speech-to-text: {e}")
        return None, None
    finally:
        signal.alarm(0)  # Ensure alarm is cancelled

def query_chatgpt(question, prompt, messages):
    """
    Queries the ChatGPT model with a conversation history.

    Returns:
    - dict: The response from the ChatGPT model.
    """

    client = OpenAI()
    all_messages = [{"role": "system", "content": prompt}] + messages

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.85, 
        messages=all_messages
    )

    full_api_response = response
    response = response.choices[0].message.content

    return response, full_api_response

def text_to_speech(response):
    """
    Converts text to speech using the OpenAI API.

    Returns:
    - str: The path to the audio file.
    """

    client = OpenAI()
    response = client.audio.speech.create(
        model="tts-1",
        voice="onyx",
        input=response
    )
    
    # Create an in-memory bytes stream
    audio_stream = BytesIO()
    # Write the response content to the BytesIO stream
    audio_stream.write(response.content)
    # Reset the stream position to the beginning so it can be read from later
    audio_stream.seek(0)

    # Load audio with pydub
    audio_segment = AudioSegment.from_file(audio_stream, format="mp3")

    print(f"A new audio was generated successfully!")

    return audio_segment


if __name__ == "__main__":
    # Create conversation history
    history = []

    # Give initial person prompt
    prompt = f"""
        Du bist ein {config['tree']['alter']} Jahre alter sprechender {config['tree']['art_deutsch']}, 
        der in Berlin im Bezirk {config['tree']['bezirk']} steht. Denke Dir eine Persönlichkeit mit 
        spezifischen Vorlieben, die zu einem Straßenbaum in Berlin passen, aus.
        """

    question, languages = speech_to_text(config["tech_config"]["input_path"])
    print("question:", question)

    response, full_api_response = query_chatgpt(question, prompt)
    print("response:", response)

    text_to_speech(response)
    history.append((question, response))
