"""
AI Manager - Gestor de Inteligencia Artificial Híbrido

Provee asistencia IA usando múltiples backends:
1. Groq (default) - Rápido, gratis, solo internet
2. opencode (alternativa) - Más inteligente, especializado
3. Guías offline - Fallback cuando no hay conexión
"""

import os
import requests
import json
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Proveedores de IA disponibles"""
    GROQ = "groq"
    OPENSEARCH = "opencode"
    OFFLINE = "offline"
    NONE = "none"


@dataclass
class AIResponse:
    """Respuesta de la IA"""
    success: bool
    message: str
    provider: AIProvider
    model: str = ""
    tokens_used: int = 0
    latency_ms: int = 0


class OfflineGuideDB:
    """Base de datos de guías offline pre-cargadas"""
    
    def __init__(self):
        self.guides = self._load_guides()
        
    def _load_guides(self) -> Dict[str, str]:
        """Carga guías pre-cargadas para diagnóstico"""
        return {
            "no_boot": """
📺 DISPOSITIVO NO ENCIENDE

POSIBLES CAUSAS:
1. Fuente de alimentación defectuosa
2. Cable de poder dañado
3. Placa base dañada

PASOS A SEGUIR:
1. Verificar LED de power
   - ¿LED rojo/azul enciende?
   
2. Probar con otro cable de poder

3. Medir voltajes en la placa:
   - 5V (principal)
   - 3.3V (lógica)
   - 1.8V (DRAM)
   
4. Si no hay voltaje → Fuente muerta
5. Si hay voltaje → Revisar capacitores inflados
""",
            "bootloop": """
🔄 BOOT LOOP (REINICIOS EN BUCLE)

POSIBLES CAUSAS:
1. Firmware corrupto
2. eMMC defectuoso
3. Configuración de memoria incorrecta

PASOS A SEGUIR:
1. Conectar serial console (115200 baud)
2. Capturar bootlog completo
3. Identificar dónde falla:
   - boot0 → SPL corrupto
   - U-Boot → bootloader dañado
   - Kernel → system partition corrupta
   
4. Usar Auto Recovery para reinstalar firmware
5. Si persiste → dump eMMC para diagnóstico
""",
            "black_screen": """
🖥️ PANTALLA NEGRA (PERO LED PRENDE)

POSIBLES CAUSAS:
1. HDMI handshake fallido
2. LCD controller dañado
3. Bootloop sin video output

PASOS A SEGUIR:
1. Probar otro cable HDMI
2. Probar en otro TV/Monitor
3. Conectar serial console
4. Capturar bootlog para ver si llega al kernel

5. Si el kernel inicia pero no hay video:
   -尝试 Composite AV output
   - Verificar config de display en bootloader
""",
            "fel_mode": """
⚡ DISPOSITIVO EN MODO FEL

El dispositivo está en modo FEL (USB download mode).

CAUSAS:
1. Botón FEL presionado al encender
2. Boot0 corrupto/missing
3. eMMC completamente vacío

PASOS A SEGUIR:
1. Desconectar cable USB
2. Soltar botón FEL
3. Intentar encender normalmente
4. Si vuelve a FEL → boot0 corrupto

PARA RECUPERAR EN FEL:
1. Usar pestaña "FEL Recovery"
2. Seleccionar firmware .img
3. Cargar a RAM primero
4. Luego usar serial para flashear eMMC
""",
            "emmc_error": """
💾 ERROR DE eMMC

POSIBLES CAUSAS:
1. eMMC corrupto
2. Firmware incompatible
3. Bad blocks en memoria

DIAGNÓSTICO:
1. Conectar serial console
2. Dump bootlog completo
3. Buscar errores como:
   - "mmc init failed"
   - "read error"
   - "timeout"

SOLUCIONES:
1. Auto Recovery → Factory Reset
2. Flashear firmware stock
3. Si eMMC dañado físicamente → reemplazar
""",
            "usb_error": """
🔌 ERROR DE USB

POSIBLES CAUSAS:
1. Cable USB defectuoso
2. Puerto USB del PC dañado
3. Controlador USB del SOC dañado

PASOS:
1. Probar otro cable USB
2. Probar otro puerto USB del PC
3. Usar puerto USB 2.0 (no 3.0)
4. En Linux: verificar con 'lsusb'
5. Reinstalar driver aw_usb si existe
""",
            "recovery_menu": """
🔧 MENÚ DE RECOVERY

ACCESO:
1. Conectar serial console
2. Encender dispositivo
3. Presionar cualquier tecla en "Hit any key to stop autoboot"
4. Escribir 'recovery' o 'update'

OPCIONES COMUNES:
- Factory Reset → Reinstalar firmware
- Update → Actualizar desde SD/USB
- Wipe cache → Limpiar cache
- Backup → Respaldar particiones

NOTA: Recovery borra datos del usuario pero preserva el firmware.
""",
            "general_recovery": """
🔄 PROCESO GENERAL DE RECOVERY

MÉTODO 1 - AUTO RECOVERY (Recomendado):
1. Conectar serial console (CH340)
2. Ir a pestaña "Auto Recovery"
3. Seleccionar puerto serial
4. Encender dispositivo
5. Click "Iniciar Recovery"
6. Seguir instrucciones en pantalla

MÉTODO 2 - MANUAL:
1. Conectar serial console
2. Interrumpir autoboot (tecla cualquier)
3. Escribir 'run recovery' o 'update'
4. Esperar menú de recovery
5. Seleccionar Factory Reset

MÉTODO 3 - FEL (Dispositivo muerto):
1. Mantener botón FEL presionado
2. Conectar USB
3. Usar pestaña "FEL Recovery"
4. Cargar firmware a RAM
5. Flashear eMMC
"""
        }
        
    def search(self, query: str) -> str:
        """Busca guía relevante para la query"""
        query_lower = query.lower()
        
        keywords = {
            "no enciende": "no_boot",
            "no prende": "no_boot",
            "no power": "no_boot",
            "black screen": "black_screen",
            "pantalla negra": "black_screen",
            "sin video": "black_screen",
            "bootloop": "bootloop",
            "reinicia": "bootloop",
            "reboot": "bootloop",
            "fel": "fel_mode",
            "fel mode": "fel_mode",
            "emmc": "emmc_error",
            "memoria": "emmc_error",
            "usb": "usb_error",
            "recovery": "recovery_menu",
            "factory reset": "recovery_menu",
            "recovery menu": "recovery_menu",
        }
        
        for key, guide_key in keywords.items():
            if key in query_lower:
                return self.guides.get(guide_key, self.guides["general_recovery"])
                
        return self.guides["general_recovery"]


class GroqAI:
    """Cliente para Groq API (gratis, rápido)"""
    
    BASE_URL = "https://api.groq.com/openai/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self.model = "llama-3.3-70b-versatile"
        self.available_models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant", 
            "mixtral-8x7b-32768"
        ]
        
    def is_configured(self) -> bool:
        """Verifica si está configurado"""
        return bool(self.api_key)
        
    def check_connection(self) -> bool:
        """Verifica conexión a Groq"""
        if not self.api_key:
            return False
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(
                f"{self.BASE_URL}/models",
                headers=headers,
                timeout=5
            )
            return resp.status_code == 200
        except:
            return False
            
    def set_model(self, model: str):
        """Cambia el modelo"""
        if model in self.available_models:
            self.model = model
            
    def ask(self, prompt: str, context: str = "") -> AIResponse:
        """
        Envía pregunta a Groq.
        
        Args:
            prompt: Pregunta del usuario
            context: Contexto adicional (bootlog, etc.)
        """
        import time
        start_time = time.time()
        
        if not self.api_key:
            return AIResponse(
                success=False,
                message="Groq API key no configurada.\n\nPara configurar:\n1. Crear cuenta en https://console.groq.com\n2. Generar API key\n3. Guardar en config o variable GROQ_API_KEY",
                provider=AIProvider.GROQ
            )
            
        system_prompt = """Eres un asistente especializado en recuperación de dispositivos Allwinner (TV Boxes, SBC, etc.).

TU ROL:
- Ayudar a diagnosticar problemas de dispositivos que no arrancan
- Guiar al usuario en procesos de recovery
- Analizar bootlogs para identificar errores
- Proporcionar soluciones paso a paso

REGLAS:
1. Sé conciso y práctico
2. Da pasos específicos y verificables
3. Si no estás seguro, dilo
4. Prioriza soluciones seguras sobre arriesgadas
5. Siempre pregunta por información adicional si es necesaria

CONOCIMIENTO:
- Allwinner H616, H313, H618, H3, A64, R328
- Modo FEL para recuperación
- U-Boot y serial console
- eMMC y NAND flash
"""
        
        full_prompt = prompt
        if context:
            full_prompt = f"CONTEXTO:\n{context}\n\nPREGUNTA:\n{prompt}"
            
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2048
            }
            
            resp = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            latency = int((time.time() - start_time) * 1000)
            
            if resp.status_code == 200:
                result = resp.json()
                message = result["choices"][0]["message"]["content"]
                tokens = result.get("usage", {}).get("total_tokens", 0)
                
                return AIResponse(
                    success=True,
                    message=message,
                    provider=AIProvider.GROQ,
                    model=self.model,
                    tokens_used=tokens,
                    latency_ms=latency
                )
            else:
                error = resp.json().get("error", {}).get("message", "Unknown error")
                return AIResponse(
                    success=False,
                    message=f"Error de Groq: {error}",
                    provider=AIProvider.GROQ,
                    latency_ms=latency
                )
                
        except requests.exceptions.Timeout:
            return AIResponse(
                success=False,
                message="Timeout conectando a Groq. Verifica tu conexión a internet.",
                provider=AIProvider.GROQ
            )
        except Exception as e:
            return AIResponse(
                success=False,
                message=f"Error: {str(e)}",
                provider=AIProvider.GROQ
            )
            
    def analyze_bootlog(self, bootlog: str) -> AIResponse:
        """Analiza un bootlog completo"""
        prompt = f"""Analiza este bootlog de un dispositivo Allwinner y dame:
1. ¿Qué SOC y configuración tiene?
2. ¿Dónde falló el boot?
3. ¿Qué recomiendas hacer para recovery?

BOOTLOG:
```
{bootlog[:3000]}
```
"""
        return self.ask("Analiza este bootlog", context=bootlog)


class OpenCodeAI:
    """Cliente para integración con opencode"""
    
    def __init__(self):
        self.enabled = False
        
    def is_available(self) -> bool:
        """Verifica si opencode está disponible"""
        return False
        
    def ask(self, prompt: str, context: str = "") -> AIResponse:
        """Envía pregunta via opencode"""
        return AIResponse(
            success=False,
            message="opencode no disponible en esta sesión.\n\nPara usar opencode como backend:\n1. Conectar con un agente opencode\n2. Este módulo permite integración futura",
            provider=AIProvider.OPENSEARCH
        )


class AIBridge:
    """
    Puente inteligente que selecciona el mejor backend disponible.
    """
    
    def __init__(self):
        self.groq = GroqAI()
        self.opencode = OpenCodeAI()
        self.offline = OfflineGuideDB()
        
        self.current_provider = AIProvider.NONE
        self._detect_provider()
        
    def _detect_provider(self):
        """Detecta el mejor proveedor disponible"""
        if self.groq.check_connection():
            self.current_provider = AIProvider.GROQ
            logger.info("AI: Usando Groq")
        elif self.opencode.is_available():
            self.current_provider = AIProvider.OPENSEARCH
            logger.info("AI: Usando opencode")
        else:
            self.current_provider = AIProvider.OFFLINE
            logger.info("AI: Modo offline")
            
    def is_available(self) -> bool:
        """Verifica si hay algún backend disponible"""
        return self.current_provider != AIProvider.NONE
        
    def get_status(self) -> Dict:
        """Obtiene estado de los backends"""
        return {
            "groq_configured": self.groq.is_configured(),
            "groq_connected": self.groq.check_connection(),
            "opencode_available": self.opencode.is_available(),
            "current_provider": self.current_provider.value,
            "models": self.groq.available_models if self.groq.is_configured() else []
        }
        
    def ask(self, prompt: str, context: str = "") -> AIResponse:
        """Envía pregunta al mejor backend disponible"""
        
        if self.current_provider == AIProvider.GROQ:
            return self.groq.ask(prompt, context)
            
        elif self.current_provider == AIProvider.OPENSEARCH:
            return self.opencode.ask(prompt, context)
            
        else:
            guide = self.offline.search(prompt)
            return AIResponse(
                success=True,
                message=f"[MODO OFFLINE]\n\n{guide}\n\n---"
                        f"\n\nTu pregunta: {prompt}\n\n"
                        f"Notas:\n"
                        f"- Para IA avanzada, configura GROQ_API_KEY\n"
                        f"- O usa modo online cuando haya conexión",
                provider=AIProvider.OFFLINE
            )
            
    def analyze_bootlog(self, bootlog: str) -> AIResponse:
        """Analiza bootlog con el mejor backend"""
        
        if self.current_provider in [AIProvider.GROQ, AIProvider.OPENSEARCH]:
            return self.groq.analyze_bootlog(bootlog)
        else:
            guide = self.offline.search("bootlog error")
            return AIResponse(
                success=True,
                message=f"[ANÁLISIS OFFLINE]\n\n{guide}\n\n---"
                        f"\n\nBOOTLOG CAPTURADO:\n{bootlog[:2000]}",
                provider=AIProvider.OFFLINE
            )
            
    def set_api_key(self, api_key: str):
        """Configura API key de Groq"""
        self.groq.api_key = api_key
        self._detect_provider()


class AIAssistant:
    """
    Asistente IA principal para ARS.
    Wrapper simple sobre AIBridge.
    """
    
    def __init__(self):
        self.bridge = AIBridge()
        self.model = "llama-3.3-70b-versatile"
        
    @property
    def is_available(self) -> bool:
        """Verifica si IA está disponible"""
        return self.bridge.is_available()
        
    def ask(self, question: str) -> AIResponse:
        """Envía pregunta"""
        return self.bridge.ask(question)
        
    def analyze_bootlog(self, bootlog: str) -> AIResponse:
        """Analiza bootlog"""
        return self.bridge.analyze_bootlog(bootlog)
        
    def set_model(self, model: str) -> bool:
        """Cambia modelo Groq"""
        if model in self.bridge.groq.available_models:
            self.model = model
            self.bridge.groq.set_model(model)
            return True
        return False
        
    def set_api_key(self, api_key: str):
        """Configura API key"""
        self.bridge.set_api_key(api_key)
        
    def get_status(self) -> Dict:
        """Obtiene estado completo"""
        return self.bridge.get_status()
