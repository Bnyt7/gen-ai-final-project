"""
Ollama API client for communicating with local LLM instances
"""
import httpx
from typing import Dict, List, Optional
from backend.config import REQUEST_TIMEOUT


class OllamaClient:
    """Client for interacting with Ollama API endpoints"""
    
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.5
    ) -> str:
        """
        Generate a response from the LLM
        
        Args:
            prompt: The user prompt
            system: Optional system message
            temperature: Sampling temperature (0.0 to 1.0)
            
        Returns:
            Generated text response
        """
        endpoint = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = await self.client.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except httpx.TimeoutException as e:
            raise Exception(f"Ollama API timeout for {self.model}: Request took longer than {REQUEST_TIMEOUT}s. The model may need more time to load or generate a response.")
        except httpx.HTTPStatusError as e:
            raise Exception(f"Ollama API error for {self.model}: HTTP {e.response.status_code} - {e.response.text}")
        except httpx.HTTPError as e:
            raise Exception(f"Ollama API error for {self.model}: {type(e).__name__} - {str(e)}")
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.5
    ) -> str:
        """
        Chat with the LLM using message history
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            
        Returns:
            Generated text response
        """
        endpoint = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        try:
            response = await self.client.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except httpx.TimeoutException as e:
            raise Exception(f"Ollama chat API timeout for {self.model}: Request took longer than {REQUEST_TIMEOUT}s. The model may need more time to load or generate a response.")
        except httpx.HTTPStatusError as e:
            raise Exception(f"Ollama chat API error for {self.model}: HTTP {e.response.status_code} - {e.response.text}")
        except httpx.HTTPError as e:
            raise Exception(f"Ollama chat API error for {self.model}: {type(e).__name__} - {str(e)}")
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
