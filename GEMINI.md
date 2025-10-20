# Gemini Code Understanding

This document outlines the structure and functionality of the Voice AI Copilot application.

## Project Overview

The project is a conversational voice application that acts as an AI Copilot, specializing in AI news, research, and the latest developments in the field. It's built using the Pipecat framework and integrates with several external services to provide its core functionality.

## Architecture

The application is divided into a client and a server component.

### Client

The client is a [Next.js](https://nextjs.org/) application located in the `app/client` directory. It uses the `@pipecat-ai/client-react` library to handle real-time voice communication with the server. The UI is built with React and styled with Tailwind CSS.

### Server

The server is a Python application located in the `app/server` directory. It's built on top of the [Pipecat](https://github.com/pipecat-ai/pipecat) framework and orchestrates the entire voice conversation flow.

#### Key Components:

*   **`bot.py`**: This is the main entry point for the server application. It defines the pipeline, services, and event handlers for the voice agent.
*   **Pipeline**: The core of the server is a Pipecat `Pipeline` that processes audio and text streams. The pipeline is configured as follows:
    *   **Input/Output**: `DailyTransport` is used for real-time audio communication via [Daily.co](https://www.daily.co/).
    *   **UI Events**: `RTVIProcessor` is used to send events to the client for UI updates.
    *   **LLM**: `GoogleLLMService` is used to process user input and generate responses.
    *   **TTS**: `CartesiaTTSService` is used for text-to-speech synthesis.
    *   **Context Management**: `LLMContextAggregatorPair` is used to maintain the conversation history.
*   **MCP (MetaCall Protocol)**: The server uses MCP to connect to external tools and services. It integrates with:
    *   **ArXiv**: To search for and retrieve research papers.
    *   **HuggingFace**: To access models and other resources.
*   **Tracing and Observability**: The application uses [Langfuse](https://langfuse.com/) for tracing and observability, allowing developers to monitor and debug conversations.

## How it Works

1.  The client establishes a connection with the server using the `@pipecat-ai/client-react` library and the `DailyTransport`.
2.  The user speaks, and the audio is streamed to the server.
3.  The `DailyTransport` on the server receives the audio and passes it through the pipeline.
4.  The audio is transcribed to text.
5.  The transcribed text is sent to the `GoogleLLMService` along with the conversation history.
6.  The LLM processes the input and may use the registered MCP tools (ArXiv, HuggingFace) to gather information.
7.  The LLM generates a response, which is sent to the `CartesiaTTSService`.
8.  The TTS service converts the text response into audio.
9.  The audio is streamed back to the client via the `DailyTransport` and played to the user.
10. Throughout this process, events are sent to Langfuse for tracing and observability.

## How to Run

Refer to the main `README.md` file in the `app` directory for detailed instructions on how to set up and run the client and server.
