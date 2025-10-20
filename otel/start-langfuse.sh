#!/bin/bash

# Start Langfuse locally with Docker Compose

echo "🚀 Starting Langfuse services..."
docker-compose up -d

echo "⏳ Waiting for services to be healthy..."
sleep 10

echo "🔍 Checking service status..."
docker-compose ps

echo ""
echo "✅ Langfuse should be available at:"
echo "   Web UI: http://localhost:3000"
echo "   OTEL Endpoint: http://localhost:3000/api/public/otel"
echo ""
echo "📝 First time setup:"
echo "   1. Open http://localhost:3000"
echo "   2. Create your admin account"
echo "   3. Get your API keys from Settings > API Keys"
echo ""
echo "🛑 To stop: docker-compose down"
echo "🗑️  To reset: docker-compose down -v"