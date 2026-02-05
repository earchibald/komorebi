"""Async Ollama client wrapper for LLM integration.

Provides a clean interface to Ollama's async capabilities,
ensuring the FastAPI event loop is never blocked by inference.
"""

import json
import os
from typing import AsyncIterator, Optional

from ollama import AsyncClient


class KomorebiLLM:
    """Async LLM client for Komorebi's summarization pipeline.
    
    Integrates with Ollama for local, privacy-preserving LLM inference.
    All operations are async to prevent blocking the FastAPI event loop.
    """
    
    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        """Initialize the LLM client.
        
        Args:
            host: Ollama server host. Defaults to OLLAMA_HOST env var or localhost:11434
            model: Model name. Defaults to OLLAMA_MODEL env var or llama3.2
        """
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.client = AsyncClient(host=self.host)
    
    async def is_available(self) -> bool:
        """Health check for the Ollama sidecar.
        
        Returns:
            True if Ollama is reachable and responsive, False otherwise.
        """
        try:
            await self.client.list()
            return True
        except Exception:
            return False

    async def summarize(
        self, 
        content: str, 
        max_words: int = 100, 
        system_anchor: Optional[str] = None
    ) -> str:
        """Generate a concise summary of content.
        
        Args:
            content: The text to summarize
            max_words: Target summary length in words
            system_anchor: Optional context to keep summary relevant to project goals
            
        Returns:
            Concise summary as a string
            
        Raises:
            Exception: If inference fails (should be caught by caller)
        """
        system_prompt = "You are a precise technical summarizer."
        if system_anchor:
            system_prompt += f" Focus on details relevant to: {system_anchor}"

        response = await self.client.generate(
            model=self.model,
            prompt=f"Summarize the following text in under {max_words} words. Capture key technical details (errors, IDs, decisions):\n\n{content}",
            system=system_prompt,
            stream=False
        )
        return response['response'].strip()
    
    async def stream_summary(self, content: str) -> AsyncIterator[str]:
        """Stream summary generation for real-time UI feedback.
        
        Args:
            content: The text to summarize
            
        Yields:
            Summary text chunks as they're generated
        """
        async for chunk in await self.client.generate(
            model=self.model,
            prompt=f"Summarize this concisely without extra explanation:\n\n{content}",
            stream=True
        ):
            yield chunk['response']

    async def extract_entities(self, content: str) -> dict:
        """Extract structured entities from text using JSON mode.
        
        Returns a dictionary with keys matching EntityType values:
        error, url, tool_id, decision, code_ref
        """
        schema = {
            "error": ["list of error strings"],
            "url": ["list of urls"],
            "tool_id": ["list of tool identifiers"],
            "decision": ["list of decisions made"],
            "code_ref": ["list of filenames or functions"],
        }
        
        prompt = (
            "Analyze this text and extract entities into JSON format matching this schema: "
            f"{schema}\n"
            "Only include entities strictly found in the text. If none, return empty lists.\n\n"
            f"Text:\n{content}\n"
        )

        response = await self.client.generate(
            model=self.model,
            prompt=prompt,
            format="json",
            stream=False,
        )

        raw = response.get("response", "{}")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
