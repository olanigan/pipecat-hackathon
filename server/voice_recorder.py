import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
import numpy as np
import wave
import os
import re
import queue

# Define the directory to save audio files
SAVE_DIR = os.path.dirname(__file__)

st.set_page_config(
    page_title="Voice Test Recorder",
    page_icon="🎙️",
    layout="centered"
)

st.title("🎙️ Voice Test Recorder")
st.write(
    "Use this tool to record short audio phrases for testing the voice agent. "
    "The audio will be saved as a 16-bit, 16kHz mono WAV file, which is the "
    "required format for the `test_voice_agent.py` script."
)

# --- WebRTC and Audio Processing ---

# This class will process and buffer audio frames from the browser
class AudioFrameProcessor(AudioProcessorBase):
    def __init__(self) -> None:
        self.frame_queue = queue.Queue()
        self.is_recording = True

    def recv(self, frame):
        if not self.is_recording:
            return frame
        
        # The frame from streamlit-webrtc is a PyAV AudioFrame
        # We need to convert it to a NumPy array
        audio_array = frame.to_ndarray(format="s16", layout="mono")
        self.frame_queue.put(audio_array)
        return frame

    def stop(self):
        self.is_recording = False

    def get_recorded_data(self):
        """Concatenates all frames in the queue and returns as a single numpy array."""
        frames = []
        while not self.frame_queue.empty():
            frames.append(self.frame_queue.get())
        
        if not frames:
            return None
            
        return np.concatenate(frames, axis=0)

# --- Streamlit UI ---

st.subheader("Step 1: Enter the phrase to record")
phrase_text = st.text_input(
    "Test Phrase",
    placeholder='e.g., "What are the latest advancements in large language models?"',
    label_visibility="collapsed"
)

st.subheader("Step 2: Record Audio")
st.write("Click 'START' to begin recording from your microphone.")

webrtc_ctx = webrtc_streamer(
    key="voice-recorder",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=AudioFrameProcessor,
    media_stream_constraints={"video": False, "audio": True},
)

st.subheader("Step 3: Save the Recording")

if st.button("Save Recording", type="primary", disabled=not webrtc_ctx.state.playing):
    if webrtc_ctx.audio_processor:
        audio_processor = webrtc_ctx.audio_processor
        audio_processor.stop()  # Stop accumulating frames
        
        recorded_data = audio_processor.get_recorded_data()

        if recorded_data is not None and recorded_data.size > 0:
            # Sanitize the phrase text to create a valid filename
            if phrase_text:
                base_filename = re.sub(r'[^a-z0-9_]+', '', phrase_text.lower().replace(' ', '_'))
                filename = f"{base_filename[:50]}.wav"
            else:
                filename = "test_audio.wav"
            
            filepath = os.path.join(SAVE_DIR, filename)

            # Save the NumPy array as a WAV file
            try:
                with wave.open(filepath, "wb") as wf:
                    wf.setnchannels(1)  # Mono
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(16000)  # 16kHz
                    wf.writeframes(recorded_data.tobytes())
                
                st.success(f"✅ Audio saved successfully as `{filename}`")
                st.info("You can now use this file with `test_voice_agent.py`.")

                # Provide a download button
                with open(filepath, "rb") as f:
                    st.download_button(
                        label=f"Download {filename}",
                        data=f,
                        file_name=filename,
                        mime="audio/wav",
                    )

            except Exception as e:
                st.error(f"❌ Failed to save audio file: {e}")
        else:
            st.warning("⚠️ No audio was recorded. Please start the recorder and speak.")
    else:
        st.error("❌ Audio processor is not available. Please start the recorder first.")

st.markdown("---")
st.info(
    "**How it works:** The audio is captured in your browser, processed, and then "
    "saved directly to the `app/server` directory when you click 'Save Recording'."
)
