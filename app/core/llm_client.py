import openai
from typing import List, Dict, Any, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE

    async def generate_response(
            self,
            messages: List[Dict[str, str]],
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None
    ) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            raise

    async def generate_response_with_system_prompt(
            self,
            system_prompt: str,
            user_message: str,
            temperature: Optional[float] = None
    ) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        return await self.generate_response(messages, temperature)