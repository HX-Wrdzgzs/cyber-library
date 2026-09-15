from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class LLMError(RuntimeError):
    pass


@dataclass(slots=True)
class LLMConfig:
    base_url: str
    model: str
    api_key: str | None = None
    timeout: float = 90.0
    temperature: float = 0.15

    @classmethod
    def from_env(cls) -> "LLMConfig | None":
        base_url = os.getenv("CYBER_LIBRARY_LLM_BASE_URL", "").strip()
        model = os.getenv("CYBER_LIBRARY_LLM_MODEL", "").strip()
        if not base_url or not model:
            return None
        return cls(base_url=base_url, model=model, api_key=os.getenv("CYBER_LIBRARY_LLM_API_KEY") or None, timeout=float(os.getenv("CYBER_LIBRARY_LLM_TIMEOUT", "90")), temperature=float(os.getenv("CYBER_LIBRARY_LLM_TEMPERATURE", "0.15")))


class LLMClient:
    """Small OpenAI-compatible chat-completions client."""
    def __init__(self, config: LLMConfig) -> None: self.config = config
    @classmethod
    def from_env(cls) -> "LLMClient | None":
        config = LLMConfig.from_env(); return cls(config) if config else None
    @property
    def model_name(self) -> str: return self.config.model
    def _endpoint(self) -> str:
        base=self.config.base_url.rstrip("/"); return base if base.endswith("/chat/completions") else base+"/chat/completions"
    def _request(self, payload: dict) -> dict:
        headers={"Content-Type":"application/json","Accept":"application/json"}
        if self.config.api_key: headers["Authorization"]=f"Bearer {self.config.api_key}"
        req=Request(self._endpoint(),data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),headers=headers,method="POST")
        try:
            with urlopen(req,timeout=self.config.timeout) as response:return json.load(response)
        except HTTPError as exc:
            detail=""
            try: detail=exc.read(2000).decode("utf-8","replace")
            except Exception: pass
            raise LLMError(f"LLM HTTP {exc.code}: {detail or exc.reason}") from exc
        except (URLError,TimeoutError,json.JSONDecodeError) as exc: raise LLMError(f"LLM request failed: {exc}") from exc
    @staticmethod
    def _content(response: dict) -> str:
        try: content=response["choices"][0]["message"]["content"]
        except (KeyError,IndexError,TypeError) as exc: raise LLMError("LLM response did not contain choices[0].message.content") from exc
        if isinstance(content,str): return content
        if isinstance(content,list):
            parts=[item["text"] for item in content if isinstance(item,dict) and isinstance(item.get("text"),str)]
            if parts:return "\n".join(parts)
        raise LLMError("LLM response content was not text")
    @staticmethod
    def _parse_json(text: str) -> dict:
        text=text.strip(); fenced=re.match(r"^```(?:json)?\s*(.*?)\s*```$",text,flags=re.S|re.I)
        if fenced:text=fenced.group(1).strip()
        try:
            result=json.loads(text)
            if isinstance(result,dict):return result
        except json.JSONDecodeError:pass
        start=text.find("{"); end=text.rfind("}")
        if start>=0 and end>start:
            try:
                result=json.loads(text[start:end+1])
                if isinstance(result,dict):return result
            except json.JSONDecodeError:pass
        raise LLMError("LLM did not return a JSON object")
    def complete_json(self, system: str, user: str, max_tokens: int = 2400) -> dict:
        payload={"model":self.config.model,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":self.config.temperature,"max_tokens":max_tokens,"response_format":{"type":"json_object"}}
        try: response=self._request(payload)
        except LLMError as exc:
            if "400" not in str(exc): raise
            payload.pop("response_format",None); response=self._request(payload)
        return self._parse_json(self._content(response))
