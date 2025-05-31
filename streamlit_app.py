# streamlit_app.py
import streamlit as st
import sounddevice as sd
import numpy as np
#import speech_recognition
import requests
import os
import io
from scipy.io.wavfile import write
from groq import Groq

from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("VOICE_KEY")


DURATION = 7 # seconds
SAMPLING_RATE = 16000

st.set_page_config(page_title="Zero-Waste Grocery Helper", layout="wide")
st.title("🥕 Zero-Waste Grocery Helper")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "state" not in st.session_state:
    st.session_state.state = {}

transcript = ""

if st.button("Start Recording"):
    st.write("Recording... Speak now!")
    audio = sd.rec(int(DURATION * SAMPLING_RATE), samplerate=SAMPLING_RATE, channels=1, dtype='float32')
    sd.wait()
    st.write("Transcribing...")

    # Transcribe with your custom ASR function
        # Step 2: Convert float32 audio to int16
    audio_int16 = np.int16(audio.flatten() * 32767)

    # Step 3: Write WAV to in-memory buffer
    buffer = io.BytesIO()
    write(buffer, SAMPLING_RATE, audio_int16)
    buffer.seek(0)  # rewind the buffer to the beginning

    # Step 4: Transcribe using Groq API (in-memory file-like object)
    client = Groq(api_key=api_key)
    transcription = client.audio.transcriptions.create(
        file=("audio.wav", buffer.read()),  # name, byte content
        model="whisper-large-v3-turbo",
        response_format="verbose_json",
    )
    #transcript = speech_recognition.transcribe((SAMPLING_RATE, audio))
    transcript = transcription.text
    st.success("Transcription:")
    st.write(transcript)

txt = st.chat_input("Type your message here:", key="user_input")
user_input = transcript if transcript else txt

if user_input:
    st.session_state.chat_history.append(("user", user_input))
    
    # Send to FastAPI
    payload = {
        "message": user_input,
        "state": st.session_state.state
    }
    response = requests.post("http://localhost:8000/chat", json=payload)
    print(response.text)
    response_data = response.json()
    
    bot_reply = response_data["response"]
    st.session_state.state = response_data["state"]
    st.session_state.chat_history.append(("assistant", bot_reply))

# Display history
chat_history = st.session_state.state.get("chat_history", [])

# Skip displaying the first message
for i, (role, msg) in enumerate(chat_history):
    if i == 0:
        continue
    with st.chat_message(role):
        st.markdown(msg)