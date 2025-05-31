# streamlit_app.py
import streamlit as st
import sounddevice as sd
import numpy as np
import speech_recognition
import requests


DURATION = 5 # seconds
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
    transcript = speech_recognition.transcribe((SAMPLING_RATE, audio))
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