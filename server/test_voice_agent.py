import asyncio
import wave
import os
from dotenv import load_dotenv
from loguru import logger

from pipecat.frames.frames import AudioRawFrame, EndFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.transports.services.daily import DailyParams, DailyTransport

load_dotenv(override=True)

# IMPORTANT: Create a test_audio.wav file in the same directory as this script.
# This file should be a 16-bit, 16kHz mono WAV file.
# You can use an online text-to-speech service to generate this file.
# For example, you can record yourself saying:
# "What are the latest advancements in large language models?"
TEST_AUDIO_FILE = "test_audio.wav"
RESPONSE_AUDIO_FILE = "response_audio.wav"

async def main():
    """
    This script acts as a voice test client for the Pipecat agent.
    It connects to a Daily.co room, streams a pre-recorded audio file,
    and saves the agent's audio response to a file.
    """
    room_url = os.getenv("DAILY_ROOM_URL")
    if not room_url:
        logger.error("DAILY_ROOM_URL environment variable not set.")
        return

    if not os.path.exists(TEST_AUDIO_FILE):
        logger.error(f"Test audio file not found: {TEST_AUDIO_FILE}")
        logger.error("Please create this file before running the test.")
        return

    logger.info(f"Connecting to Daily room: {room_url}")

    transport = DailyTransport(
        room_url=room_url,
        token=None,
        bot_name="Test Client",
        params=DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
    )

    # This list will store the audio frames received from the bot
    response_frames = []

    async def send_audio_task(transport):
        """A task to send audio frames from the WAV file."""
        try:
            with wave.open(TEST_AUDIO_FILE, "rb") as wav_file:
                # Ensure the WAV file has the correct format
                if wav_file.getnchannels() != 1 or wav_file.getsampwidth() != 2 or wav_file.getframerate() != 16000:
                    logger.error(f"{TEST_AUDIO_FILE} must be a 16-bit, 16kHz mono WAV file.")
                    return

                logger.info(f"Streaming audio from {TEST_AUDIO_FILE}...")
                while True:
                    frames = wav_file.readframes(160)  # 10ms of audio at 16kHz
                    if not frames:
                        break
                    await transport.push_frame(AudioRawFrame(audio=frames, sample_rate=16000, num_channels=1))
                    await asyncio.sleep(0.01)  # Simulate real-time streaming
                logger.info("Finished streaming audio.")
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
        finally:
            # Signal the end of the stream
            await transport.push_frame(EndFrame())


    async def receive_audio_task(transport):
        """A task to receive and store audio frames from the bot."""
        logger.info("Listening for response audio...")
        async for frame in transport.stream():
            if isinstance(frame, AudioRawFrame):
                response_frames.append(frame.audio)
            elif isinstance(frame, EndFrame):
                logger.info("Received end of stream frame.")
                break
        logger.info("Finished receiving audio.")


    pipeline = Pipeline([transport.input(), transport.output()])
    task = PipelineTask(pipeline)

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, participant):
        logger.info(f"Connected to room. Participant: {participant['id']}")
        # Start sending and receiving audio in the background
        asyncio.create_task(send_audio_task(transport))
        asyncio.create_task(receive_audio_task(transport))


    runner = PipelineRunner()
    await runner.run(task)

    # Save the received audio to a WAV file
    if response_frames:
        logger.info(f"Saving response audio to {RESPONSE_AUDIO_FILE}...")
        with wave.open(RESPONSE_AUDIO_FILE, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"".join(response_frames))
        logger.info("Response audio saved.")
    else:
        logger.warning("No response audio received.")

if __name__ == "__main__":
    asyncio.run(main())
