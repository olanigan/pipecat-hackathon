import streamlit as st
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import os
import re

# --- Session State Initialization ---
if 'recording' not in st.session_state:
    st.session_state.recording = False
if 'audio_data' not in st.session_state:
    st.session_state.audio_data = []

# Define the directory to save audio files
SAVE_DIR = os.path.dirname(__file__)
SAMPLE_RATE = 16000  # 16kHz
CHANNELS = 1  # Mono

st.set_page_config(
    page_title="Audio Test Recorder",
    page_icon="🎙️",
    layout="centered"
)

st.title("🎙️ Audio Test Recorder")
st.write(
    "Use this tool to record audio phrases for testing the voice agent. "
    "The audio will be saved as a 16-bit, 16kHz mono WAV file."
)



# --- Audio Recording Logic ---

def start_recording():
    st.session_state.audio_data = []
    st.session_state.recording = True
    st.info("Recording started... Speak into your microphone.")

def stop_recording():
    st.session_state.recording = False
    st.success("Recording stopped.")

# This is the callback function that gets called for each audio chunk
def audio_callback(indata, frames, time, status):
    if status:
        st.warning(f"Audio input status: {status}")
    if st.session_state.recording:
        st.session_state.audio_data.append(indata.copy())

# --- Streamlit UI ---

st.subheader("Step 1: Enter the phrase to record")
phrase_text = st.text_input(
    "Test Phrase",
    placeholder='e.g., "What are the latest advancements in large language models?"',
    label_visibility="collapsed"
)

st.subheader("Step 2: Control Recording")
col1, col2 = st.columns(2)
with col1:
    if st.button("Start Recording", on_click=start_recording, disabled=st.session_state.recording):
        pass
with col2:
    if st.button("Stop Recording", on_click=stop_recording, disabled=not st.session_state.recording):
        pass

# We need to keep the audio stream open to record
# This is a bit of a hack, but it's the standard way to do this in Streamlit
# with sounddevice. We'll open a stream and let it run in the background.
# The callback will only append data when st.session_state.recording is True.
try:
    stream = sd.InputStream(
        callback=audio_callback,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype='int16' # 16-bit audio
    )
    with stream:
        st.subheader("Step 3: Save the Recording")
        if st.button("Save Recording", type="primary", disabled=st.session_state.recording or not st.session_state.audio_data):
            if st.session_state.audio_data:
                # Concatenate the list of numpy arrays into a single array
                audio_np = np.concatenate(st.session_state.audio_data, axis=0)
                
                # Sanitize the phrase text to create a valid filename
                if phrase_text:
                    base_filename = re.sub(r'[^a-z0-9_]+', '', phrase_text.lower().replace(' ', '_'))
                    filename = f"{base_filename[:50]}.wav"
                else:
                    filename = "test_audio.wav"
                
                filepath = os.path.join(SAVE_DIR, filename)

                try:
                    # Save the NumPy array as a WAV file
                    write(filepath, SAMPLE_RATE, audio_np)
                    st.success(f"✅ Audio saved successfully as `{filename}`")
                    
                    # Provide a download button
                    with open(filepath, "rb") as f:
                        st.download_button(
                            label=f"Download {filename}",
                            data=f,
                            file_name=filename,
                            mime="audio/wav",
                        )
                    
                    # Clear the audio data after saving
                    st.session_state.audio_data = []

                except Exception as e:
                    st.error(f"❌ Failed to save audio file: {e}")
            else:
                st.warning("⚠️ No audio data to save. Please record something first.")
        
        # Keep the app running while the stream is open
        if st.session_state.recording:
            st.write("...") # Show some activity while recording
            st.rerun()

except Exception as e:
    st.error(f"❌ An error occurred with the audio device: {e}")
    st.info("Please ensure you have a microphone connected and have granted the necessary permissions.")

st.markdown("---")
st.info(
    "**How it works:** This app uses the `sounddevice` library to capture audio "
    "directly from your microphone. The audio is saved to the `app/server` directory."
)
