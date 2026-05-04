"""
Anthropic-to-OpenAI Proxy for Claude Code + DeepSeek
Translates Claude Code's Anthropic Messages API requests to OpenAI Chat Completions format.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx

app = FastAPI(title="Claude Code ↔ DeepSeek Proxy")

# ── Config ────────────────────────────────────────────
UPSTREAM_BASE_URL = "https://api.deepseek.com"
UPSTREAM_API_KEY = "sk-1fdb7fef61d14156b7d5bec1e068e3c4"
MODEL = "deepseek-v4-pro"
MAX_OUTPUT_TOKENS = 8192
CONTEXT_WINDOW = 1000000

headers = {
    "Authorization": f"Bearer {UPSTREAM_API_KEY}",
    "Content-Type": "application/json",
}

# ── Helpers ───────────────────────────────────────────
def anthropic_to_openai_messages(body: dict) -> list:
    """Convert Anthropic messages format to OpenAI format."""
    messages = []
    
    # System prompt goes as first system message
    if "system" in body:
        system = body["system"]
        if isinstance(system, str):
            messages.append({"role": "system", "content": system})
        elif isinstance(system, list) and system:
            texts = [item.get("text", "") for item in system if isinstance(item, dict)]
            if texts:
                messages.append({"role": "system", "content": "\n".join(texts)})
    
    # Convert Anthropic messages to OpenAI format
    for msg in body.get("messages", []):
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # Handle Anthropic content blocks (text, image, etc.)
        if isinstance(content, list):
            openai_content = []
            for block in content:
                if isinstance(block, dict):
                    btype = block.get("type", "text")
                    if btype == "text":
                        openai_content.append({"type": "text", "text": block.get("text", "")})
                    elif btype == "image":
                        # Convert image block
                        src = block.get("source", {})
                        if src.get("type") == "base64":
                            media_type = src.get("media_type", "image/png")
                            data = src.get("data", "")
                            openai_content.append({
                                "type": "image_url",
                                "image_url": {"url": f"data:{media_type};base64,{data}"}
                            })
            messages.append({"role": role, "content": openai_content})
        else:
            messages.append({"role": role, "content": str(content)})
    
    return messages

def openai_to_anthropic_response(openai_body: dict) -> dict:
    """Convert OpenAI Chat Completions response to Anthropic Messages format."""
    choice = openai_body.get("choices", [{}])[0]
    msg = choice.get("message", {})
    content_text = msg.get("content", "")
    
    usage = openai_body.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    
    return {
        "id": openai_body.get("id", "msg_"),
        "type": "message",
        "role": "assistant",
        "model": openai_body.get("model", MODEL),
        "content": [{"type": "text", "text": content_text}],
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
        "stop_reason": "end_turn" if choice.get("finish_reason") == "stop" else None,
        "stop_sequence": None,
    }

def openai_stream_to_anthropic_sse(openai_line: str) -> str:
    """Convert OpenAI streaming SSE to Anthropic streaming SSE."""
    if not openai_line.strip():
        return ""
    
    if openai_line.startswith("data: "):
        data = openai_line[6:]
        if data == "[DONE]":
            return ""
        
        try:
            chunk = json.loads(data)
            choice = chunk.get("choices", [{}])[0]
            delta = choice.get("delta", {})
            content = delta.get("content", "")
            
            if content:
                anthropic_chunk = {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": content}
                }
                return f"data: {json.dumps(anthropic_chunk)}\n\n"
        except (json.JSONDecodeError, KeyError):
            pass
    
    return openai_line + "\n\n"

# ── Routes ────────────────────────────────────────────

@app.get("/v1/models")
async def list_models():
    """Return available models in Anthropic format."""
    return {
        "data": [{
            "type": "model",
            "id": MODEL,
            "display_name": "DeepSeek V4 Pro",
            "created_at": "2024-01-01T00:00:00Z",
            "context_window": CONTEXT_WINDOW,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
        }]
    }

@app.post("/v1/messages")
async def handle_messages(request: Request):
    """Handle Anthropic Messages API → OpenAI Chat Completions."""
    body = await request.json()
    
    # Translate request
    openai_body = {
        "model": MODEL,
        "messages": anthropic_to_openai_messages(body),
        "max_tokens": body.get("max_tokens", MAX_OUTPUT_TOKENS),
        "temperature": body.get("temperature", 1.0),
        "top_p": body.get("top_p", 1.0),
        "stream": body.get("stream", False),
    }
    
    # Optional: thinking mode translation
    if "thinking" in body:
        # DeepSeek doesn't support thinking mode natively, skip
        pass
    
    # Optional: tools translation
    if "tools" in body:
        openai_body["tools"] = []
        for tool in body["tools"]:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.get("name", tool.get("function", {}).get("name", "")),
                    "description": tool.get("description", tool.get("function", {}).get("description", "")),
                    "parameters": tool.get("input_schema", tool.get("function", {}).get("parameters", {"type": "object"})),
                }
            }
            openai_body["tools"].append(openai_tool)
    
    # Forward to DeepSeek
    async with httpx.AsyncClient(timeout=300.0) as client:
        if openai_body.get("stream"):
            # Streaming
            upstream_response = await client.post(
                f"{UPSTREAM_BASE_URL}/v1/chat/completions",
                headers=headers,
                json=openai_body,
            )
            
            async def stream_generator():
                async for line in upstream_response.aiter_lines():
                    if line.strip():
                        yield f"data: {json.dumps(openai_stream_to_anthropic_sse(line))}\n\n"
            
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
                headers={"X-Accel-Buffering": "no"},
            )
        else:
            # Non-streaming
            upstream_response = await client.post(
                f"{UPSTREAM_BASE_URL}/v1/chat/completions",
                headers=headers,
                json=openai_body,
            )
            openai_resp = upstream_response.json()
            anthropic_resp = openai_to_anthropic_response(openai_resp)
            return Response(content=json.dumps(anthropic_resp), media_type="application/json")

@app.get("/health")
async def health():
    return {"status": "ok", "proxy": "anthropic-to-openai", "model": MODEL}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8766, log_level="info")
