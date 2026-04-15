"""
Configuration Manager - Gestor de configuración de ARS
"""

import os
import json
import configparser
from pathlib import Path
from typing import Dict, Optional


class ARSConfig:
    """Configuración de Allwinner Recovery Studio"""
    
    CONFIG_DIR = Path.home() / ".config" / "ars"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    
    DEFAULT_CONFIG = {
        "ai": {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "api_key": ""
        },
        "serial": {
            "default_baudrate": 115200,
            "preferred_port": ""
        },
        "fel": {
            "write_method": "pipe",
            "chunk_size_mb": 4
        },
        "recovery": {
            "auto_interrupt_boot": True,
            "boot_timeout_seconds": 30
        },
        "ui": {
            "theme": "dark",
            "language": "es"
        }
    }
    
    def __init__(self):
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Carga configuración desde archivo"""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    loaded = json.load(f)
                    return {**self.DEFAULT_CONFIG, **loaded}
            except:
                pass
        return self.DEFAULT_CONFIG.copy()
        
    def save(self):
        """Guarda configuración a archivo"""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
            
    def get(self, key: str, default=None):
        """Obtiene valor de configuración"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
        
    def set(self, key: str, value):
        """Establece valor de configuración"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.save()
        
    @property
    def groq_api_key(self) -> str:
        """Obtiene API key de Groq"""
        return self.get("ai.api_key", "")
        
    @groq_api_key.setter
    def groq_api_key(self, value: str):
        """Establece API key de Groq"""
        self.set("ai.api_key", value)
        
    @property
    def groq_model(self) -> str:
        """Obtiene modelo de Groq"""
        return self.get("ai.model", "llama-3.3-70b-versatile")
        
    @groq_model.setter
    def groq_model(self, value: str):
        """Establece modelo de Groq"""
        self.set("ai.model", value)


_config = None

def get_config() -> ARSConfig:
    """Obtiene instancia global de configuración"""
    global _config
    if _config is None:
        _config = ARSConfig()
    return _config
