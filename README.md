# AI Research Copilot

This project demonstrates an AI research copilot built with [Pipecat](https://github.com/pipecat-ai/pipecat) for voice interactions, integrated with [Langfuse](https://langfuse.com/) for conversation tracing and analysis.

[![AI Research Copilot demo video](https://img.youtube.com/vi/BnudWaCOQeg/0.jpg)](https://www.youtube.com/watch?v=BnudWaCOQeg)

## Prerequisites

- Python 3+
- Node.js 20+
- Langfuse stack ([Cloud](https://cloud.langfuse.com/) or [Self-Hosted](https://langfuse.com/docs/deployment/self-host))
- Langfuse API key
- Gemini API key
- Daily.co API key

## How to run 

### Running the server

1. Configure environment variables

   Create a `.env` file:

   ```sh
   cd server
   cp env.example .env
   ```

   Then fill in the values.

2. Install dependencies, uses [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

   ```sh
   uv sync
   ```

3. Run the AI research copilot:

   ```sh
   uv run bot.py --transport daily # we're using daily.co for Real-Time communications
   ```
### Running the client

1. Configure environment variables

   Create a `.env` file:

   ```sh
   cd client
   cp env.example .env
   ```

   Then fill in the values.

2. Install dependencies

   ```sh
   npm install
   ```

3. Run the client

   ```sh
   npm run dev
   ```

Open [http://localhost:3000](http://localhost:3000) with your browser to access the AI research copilot interface.

### Deploying to production

Follow the instructions to [deploying the server](https://docs.pipecat.ai/deployment/overview) and [deploying the frontend app](https://vercel.com/docs/frameworks/full-stack/nextjs).
