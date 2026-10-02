#!/bin/bash
# Testa os endpoints do XAU_AI_PRO via Docker (WSL2)
echo "=== [1] Backend /api/health (3000) ==="
curl -s -m 5 http://localhost:3000/api/health
echo

echo "=== [2] LiteLLM /v1/models (4000) ==="
curl -s -m 8 -H "Authorization: Bearer sk-xau-ai-pro-local" http://localhost:4000/v1/models | head -c 400
echo

echo "=== [3] Estado dos containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
