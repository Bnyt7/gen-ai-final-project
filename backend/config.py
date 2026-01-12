"""
Configuration for the LLM Council
"""
import os
from typing import List

# Ollama Configuration
OLLAMA_BASE_URLS = {
    "council_1": os.getenv("OLLAMA_URL_1", "http://localhost:11434"),
    "council_2": os.getenv("OLLAMA_URL_2", "http://localhost:11434"),
    "council_3": os.getenv("OLLAMA_URL_3", "http://localhost:11434"),
    "chairman": os.getenv("OLLAMA_CHAIRMAN_URL", "http://localhost:11434"),
}

# Models for each council member
# These should be pulled from Ollama beforehand
# Example: ollama pull llama3.2, ollama pull gemma3:1b, ollama pull qwen3:1.7b
COUNCIL_MODELS = [
    {"name": "llama3.2", "url": OLLAMA_BASE_URLS["council_1"]},
    {"name": "gemma3:1b", "url": OLLAMA_BASE_URLS["council_2"]},
    {"name": "qwen3:1.7b", "url": OLLAMA_BASE_URLS["council_3"]},
]

# Chairman model - synthesizes final response
# Example: ollama pull qwen3:4b
CHAIRMAN_MODEL = {
    "name": os.getenv("CHAIRMAN_MODEL", "qwen3:4b"),
    "url": OLLAMA_BASE_URLS["chairman"]
}

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Timeout settings (in seconds)
TIMEOUTREQUEST_ = 900

# Storage
CONVERSATIONS_DIR = "data/conversations"
