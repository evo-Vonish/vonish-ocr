import json
from typing import Optional

import aiohttp


class AIRefiner:
    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None, provider: str = "deepseek"):
        self.api_key = api_key
        self.api_base = api_base or "https://api.deepseek.com/v1"
        self.provider = provider
        self.enabled = bool(api_key)

    async def refine(self, raw_text: str, scene_type: str, ocr_confidence: float) -> dict:
        if not self.enabled:
            return {
                "polished": raw_text,
                "diff": [],
                "uncertain": [],
                "confidence": ocr_confidence,
            }

        prompt = self._build_prompt(raw_text, scene_type)

        try:
            result = await self._call_api(prompt)
            return {
                "polished": result.get("polished", raw_text),
                "diff": result.get("diff", []),
                "uncertain": result.get("uncertain", []),
                "confidence": result.get("confidence", ocr_confidence),
            }
        except Exception as e:
            return {
                "polished": raw_text,
                "diff": [],
                "uncertain": [{"position": 0, "context": raw_text[:50], "guess": f"API call failed: {e}"}],
                "confidence": ocr_confidence,
            }

    def _build_prompt(self, raw_text: str, scene_type: str) -> str:
        return f"""You are an OCR repair assistant. Your task is to reorganize messy OCR results into fluent, correct text.

Input scene type: {scene_type}
OCR raw text:
{raw_text}

Rules:
1. Boldly correct wrong characters and garbled text, but keep modification traces.
2. Do NOT alter professional terminology.
3. Redact sensitive personal information if present.
4. Output MUST be strictly valid JSON with fields: polished, diff, uncertain.

diff is a list of objects: {{"original": "...", "fixed": "...", "reason": "..."}}
uncertain is a list of objects: {{"position": 0, "context": "...", "guess": "..."}}
"""

    async def _call_api(self, prompt: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/chat/completions", headers=headers, json=payload
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
