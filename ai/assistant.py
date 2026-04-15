"""
AI Assistant - Asistente de IA Híbrido para ARS

Usa el sistema de IA híbrida con backends:
1. Groq (default) - Rápido, gratis
2. opencode (futuro) - Más inteligente
3. Offline guides - Fallback

Para backwards compatibility, mantenemos la misma interfaz.
"""

from ai.ai_manager import (
    AIAssistant,
    AIProvider,
    AIResponse,
    AIBridge,
    GroqAI,
    OfflineGuideDB
)

__all__ = [
    'AIAssistant',
    'AIProvider', 
    'AIResponse',
    'AIBridge',
    'GroqAI',
    'OfflineGuideDB'
]
