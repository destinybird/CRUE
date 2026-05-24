"""
LLM API调用模块
使用requests原生同步stream调用，兼容OpenAI API格式
"""

import os
import json
import time
import requests
from typing import Optional, Dict, Any


class LLMApi:
    """LLM API调用封装（requests原生stream实现）"""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 model: str = "gpt-4",
                 temperature: float = 0.7,
                 max_tokens: int = 2000):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = 120

        if not self.api_key:
            raise ValueError("API key not provided. Set OPENAI_API_KEY environment variable or pass api_key parameter.")

    def _build_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _parse_sse_stream(self, response: requests.Response) -> str:
        """解析SSE stream响应，拼接delta content"""
        collected = []
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        collected.append(content)
                except json.JSONDecodeError:
                    continue
        return "".join(collected)

    def call(self,
             system_prompt: str,
             user_prompt: str,
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None,
             retries: int = 5,
             retry_delay: float = 2.0) -> str:
        """
        调用LLM API（requests原生同步stream）

        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            temperature: 覆盖默认温度
            max_tokens: 覆盖默认最大token
            retries: 重试次数
            retry_delay: 重试延迟（秒）

        Returns:
            LLM响应文本
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
            "stream": True,
        }

        for attempt in range(retries):
            try:
                resp = requests.post(
                    url,
                    headers=self._build_headers(),
                    json=payload,
                    stream=True,
                    timeout=self.timeout,
                )

                if resp.status_code != 200:
                    error_text = resp.text[:500]
                    raise RuntimeError(f"HTTP {resp.status_code}: {error_text}")

                resp.encoding = 'utf-8'
                content = self._parse_sse_stream(resp)

                if not content:
                    raise ValueError("API返回了空内容，请检查模型是否支持当前请求")

                return content

            except Exception as e:
                error_str = str(e)
                is_rate_limit = 'rate_limit' in error_str.lower() or '429' in error_str or 'concurrency' in error_str.lower()

                if attempt < retries - 1:
                    wait_time = retry_delay * (3 if is_rate_limit else 1)
                    print(f"API调用失败(第{attempt+1}次)，{wait_time:.1f}秒后重试: {e}")
                    time.sleep(wait_time)
                    retry_delay *= 2
                else:
                    raise e

    def call_with_json(self,
                       system_prompt: str,
                       user_prompt: str,
                       temperature: Optional[float] = None,
                       max_tokens: Optional[int] = None,
                       retries: int = 5) -> Any:
        """
        调用LLM API并解析JSON响应

        Returns:
            解析后的JSON对象
        """
        response_text = self.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            retries=retries
        )

        if response_text is None:
            raise ValueError("LLM返回了空响应(None)，无法解析JSON")

        try:
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()

            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"原始响应: {response_text}")
            raise ValueError(f"无法解析LLM响应为JSON: {e}")


# 便捷函数
def create_llm_client(model: str = "gpt-4") -> LLMApi:
    """创建LLM客户端的便捷函数"""
    return LLMApi(model=model)