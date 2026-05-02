import json
import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class AIRefiner:
    SYSTEM_PROMPT = """你是 OCR 修复助手，任务是把混乱的识别结果整理成通顺文本。

【核心态度】
像整理自己的课堂笔记一样：大胆猜测乱码本该是什么，但要在旁边用铅笔轻轻标注"这里我猜猜看"。最终交上去的版本要干净，但留一份草稿记录修改。

【处理原则】

**1. 噪声识别与处理**
- 看到"吴吴吴"、"aaa"、"@@@"这种明显无意义的重复字符→这是噪声，直接删除或替换为[占位符]
- 看到"9年转技林e"这种半乱半正常的→结合上下文大胆改，可能是"植物的结果"
- 看到"莹e捐i-"这种完全乱码但位置在学术段落→基于生物知识推测为"传粉"

**2. 错字乱码的自然修正**
- 不要死扣字形相似度，要读句子：
  - "孟德f"→显然是"孟德尔"（生物学家）
  - "黄色圆l"→显然是"黄色圆粒"（豌豆性状）
  - "这委动黄色和阅粒"→"委动"不通，应为"表明"；"阅粒"应为"圆粒"
  - "1嘴硬心软1"→应该是「嘴硬心软」（书名号被识别成数字1）

**3. 特殊内容的识别**
- **金额**：看到"￥1,6??3"或"g$50897"→按数学逻辑补全（如总额减已还）
- **人名**：看到"仇辰宇"旁边有"Lv.1"→这是游戏角色名，保留；看到"孟德f"→这是科学家名，补全为"孟德尔"
- **敏感信息**：身份证号、手机号用[身份证号]、[手机号]占位，不显示原文
- **UI图标**：看到"□"、"凸"、"C"单独出现→转为[UI:按钮]、[UI:图标]等功能描述

**4. 场景感知（重要）**
- **academic（学术教材）**：荧光笔标记的文字重要，不要乱改专业术语（如"传粉"、"显性性状"），公式符号保真（"F₁"保持上标）
- **mobile（手机截图）**：绿色气泡是我说的话，白色气泡是对方说的，要分开排版；时间戳、头像转标记
- **print（印刷文档）**：保持段落结构，断裂句子大胆补全（"不得泄露个"→"不得泄露个人信息"）
- **notes（手写笔记）**：允许保留个人缩写，连笔字大胆推测（"的"写成"d"→恢复"的"）

【场景标签说明】
当前场景：{{scene}}
这只是倾向性指导，不要死板遵守。如果mobile场景里出现了化学公式，按academic逻辑修复公式；如果print场景里有手写批注，按notes逻辑处理笔迹。

【输出格式 - 严格JSON】
必须返回以下JSON格式，不要任何markdown代码块标记：

{
  "polished": "修复后的纯净文本，零标记，像印刷品",
  "diff": [
    {"original": "原文片段", "fixed": "修改后", "reason": "简短理由"}
  ],
  "uncertain": [
    {"position": 12, "context": "前后文", "guess": "推测内容"}
  ]
}

【规则】
- Polished版本必须零标记，用户直接复制使用
- Diff必须诚实记录每一处改动，哪怕是"删除了一个多余空格"
- uncertain用于标注不确定的推测，宁可标[推测]也不硬编
"""

    def __init__(
        self,
        enabled: bool = False,
        provider: str = "deepseek",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: str = "deepseek-chat",
        temperature: float = 0.3,
        trigger_mode: str = "auto",
    ):
        self.enabled = enabled
        self.provider = provider
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.temperature = temperature
        self.trigger_mode = trigger_mode  # auto / always / manual

    @property
    def _masked_key(self) -> str:
        """用于日志的脱敏 API Key。"""
        if not self.api_key:
            return "none"
        return self.api_key[:4] + "***" if len(self.api_key) > 4 else "***"

    def should_refine(self, ocr_confidence: float) -> bool:
        """判断是否需要进行 AI 修复。"""
        if not self.enabled:
            return False
        if not self.api_key:
            return False
        if self.trigger_mode == "manual":
            return False
        if self.trigger_mode == "always":
            return True
        # auto: 置信度 < 0.85 时触发
        return ocr_confidence < 0.85

    async def refine(self, raw_text: str, scene_type: str, ocr_confidence: float) -> dict:
        """调用 LLM API 修复 OCR 结果。"""
        if not self.should_refine(ocr_confidence):
            return {
                "polished": raw_text,
                "diff": [],
                "uncertain": [],
                "confidence": ocr_confidence,
            }

        prompt = self.SYSTEM_PROMPT.replace("{{scene}}", scene_type)
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"场景：{scene_type}\nOCR置信度：{ocr_confidence:.2f}\n\n【原始识别结果】\n{raw_text}\n\n请修复以上文本，严格按JSON格式返回。",
            },
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
        }

        base_url = self.api_base or self._default_base_url()
        url = f"{base_url}/chat/completions"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        logger.warning(f"AI Refiner API 错误: {resp.status} {text}")
                        return self._fallback(raw_text, ocr_confidence)

                    result = await resp.json()
                    content = result["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    return {
                        "polished": parsed.get("polished", raw_text),
                        "diff": parsed.get("diff", []),
                        "uncertain": parsed.get("uncertain", []),
                        "confidence": self._calc_confidence(parsed, ocr_confidence),
                    }
        except aiohttp.ClientError as e:
            logger.warning(f"AI Refiner 网络错误: {e}")
            return self._fallback(raw_text, ocr_confidence)
        except json.JSONDecodeError as e:
            logger.warning(f"AI Refiner JSON 解析错误: {e}")
            return self._fallback(raw_text, ocr_confidence)
        except Exception as e:
            logger.warning(f"AI Refiner 未知错误: {e}")
            return self._fallback(raw_text, ocr_confidence)

    def _default_base_url(self) -> str:
        urls = {
            "deepseek": "https://api.deepseek.com",
            "openai": "https://api.openai.com/v1",
            "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        }
        return urls.get(self.provider, "https://api.deepseek.com")

    def _calc_confidence(self, parsed: dict, ocr_confidence: float) -> float:
        """计算 AI 修复后的综合置信度。"""
        diff = parsed.get("diff", [])
        uncertain = parsed.get("uncertain", [])
        if not diff and not uncertain:
            return min(ocr_confidence + 0.05, 1.0)
        # 每处修改降低一点置信度，每处不确定再降低
        penalty = len(diff) * 0.01 + len(uncertain) * 0.03
        return max(0.0, ocr_confidence - penalty)

    def _fallback(self, raw_text: str, ocr_confidence: float) -> dict:
        """API 失败时回退到原始文本。"""
        return {
            "polished": raw_text,
            "diff": [],
            "uncertain": [],
            "confidence": ocr_confidence,
        }
