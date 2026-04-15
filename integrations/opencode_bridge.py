"""
OpenCode Bridge - Integración con opencode para diagnóstico avanzado

Permite que ARS consulte a opencode cuando necesita:
- Análisis profundo de bootlogs
- Resolución de problemas complejos
-咨询 sobre procedimientos específicos
"""

import subprocess
import json
import tempfile
import os
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class OpenCodeQuery:
    """Consulta para opencode"""
    topic: str
    context: str
    diagnostic_data: Dict
    priority: str  # "low", "medium", "high", "critical"


class OpenCodeBridge:
    """
    Puente de comunicación con opencode.
    
    Modos de operación:
    1. CLI - Ejecuta opencode como proceso
    2. Integration - Genera reporte estructurado
    3. Fallback - Proporciona instrucciones al usuario
    """
    
    def __init__(self):
        self.available = self._check_availability()
        self.conversation_history: List[Dict] = []
        
    def _check_availability(self) -> bool:
        """Verifica si opencode está disponible"""
        try:
            result = subprocess.run(
                ["which", "opencode"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
            
    def is_available(self) -> bool:
        """Verifica disponibilidad"""
        return self.available
        
    def generate_diagnostic_report(self,
                                   bootlog: str = "",
                                   device_info: Dict = None,
                                   error_state: str = "") -> str:
        """
        Genera un reporte de diagnóstico estructurado para consultar a opencode.
        
        Args:
            bootlog: Bootlog capturado
            device_info: Información del dispositivo
            error_state: Estado de error actual
            
        Returns:
            Reporte estructurado
        """
        report = {
            "timestamp": self._get_timestamp(),
            "topic": "Allwinner Device Recovery",
            "device": device_info or {},
            "bootlog_excerpt": (bootlog[:2000] + "...") if len(bootlog) > 2000 else bootlog,
            "error_state": error_state,
            "queries": [
                "¿Cuál es el diagnóstico basado en esta información?",
                "¿Qué pasos de recuperación recomiendas?",
                "¿Hay algún riesgo en el procedimiento sugerido?"
            ]
        }
        
        return json.dumps(report, indent=2, ensure_ascii=False)
        
    def execute_query(self, query: str, context: str = "") -> Tuple[bool, str]:
        """
        Ejecuta una consulta en opencode (si está disponible).
        
        Args:
            query: Pregunta específica
            context: Contexto adicional
            
        Returns:
            Tuple de (éxito, respuesta)
        """
        if not self.available:
            return False, "opencode no está disponible en este sistema"
            
        try:
            prompt = self._build_prompt(query, context)
            
            result = subprocess.run(
                ["opencode", "-q", prompt],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                self.conversation_history.append({
                    "role": "user",
                    "content": query
                })
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": result.stdout
                })
                return True, result.stdout
            else:
                return False, f"Error: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Timeout - opencode tardó demasiado"
        except Exception as e:
            return False, f"Error: {str(e)}"
            
    def _build_prompt(self, query: str, context: str) -> str:
        """Construye prompt para opencode"""
        system_context = """Eres un asistente especializado en recuperación de dispositivos Allwinner.
Tu conocimiento incluye:
- Protocolo FEL y modos de boot
- Estructura U-Boot y bootloaders
- Firmware para H616, H313, H618, H3, A64, R328
- Diagnóstico de bootlogs
- Recovery procedures

Responde de forma concisa y práctica."""
        
        full_prompt = f"{system_context}\n\n"
        
        if context:
            full_prompt += f"CONTEXTO:\n{context}\n\n"
            
        full_prompt += f"PREGUNTA:\n{query}"
        
        return full_prompt
        
    def create_opencode_script(self,
                               device_info: Dict,
                               bootlog: str,
                               recovery_log: str = "") -> str:
        """
        Crea un script que el usuario puede ejecutar para consultarme directamente.
        
        Args:
            device_info: Información del dispositivo
            bootlog: Bootlog capturado
            recovery_log: Log de recuperación
            
        Returns:
            Ruta al script creado
        """
        script_content = f'''#!/bin/bash
# Script de diagnóstico para opencode
# Ejecuta este script para consultar sobre tu dispositivo

cat << 'HEADER'
═══════════════════════════════════════════════════════════
CONSULTA DE DIAGNÓSTICO - ALLWINNER RECOVERY STUDIO
═══════════════════════════════════════════════════════════
HEADER

echo ""
echo "📱 INFORMACIÓN DEL DISPOSITIVO:"
echo "────────────────────────────────"
'''

        if device_info:
            for key, value in device_info.items():
                script_content += f'echo "  {key}: {value}"\n'
                
        script_content += '''
echo ""
echo "📋 BOOTLOG:"
echo "────────────────────────────────"
echo "'''
        
        if bootlog:
            escaped_bootlog = bootlog.replace('"', '\\"').replace('$', '\\$')
            script_content += escaped_bootlog[:3000]
            
        script_content += '''"
echo "..."
echo ""
echo "📝 LOG DE RECOVERY:"
echo "────────────────────────────────"
echo "'''
        
        if recovery_log:
            escaped_log = recovery_log.replace('"', '\\"').replace('$', '\\$')
            script_content += escaped_log[:1000]
            
        script_content += '''"
echo ""
echo "═══════════════════════════════════════════════════"
echo ""
echo "Ahora puedes pegar este contenido en una conversación"
echo "con opencode para recibir ayuda especializada."
'''

        script_path = "/tmp/ars_diagnostic_script.sh"
        
        with open(script_path, 'w') as f:
            f.write(script_content)
            
        os.chmod(script_path, 0o755)
        
        return script_path
        
    def generate_consultation_prompt(self,
                                     scenario: str,
                                     bootlog: str = "",
                                     device_info: Dict = None) -> str:
        """
        Genera un prompt listo para consultar a opencode sobre un escenario específico.
        
        Args:
            scenario: Descripción del escenario
            bootlog: Bootlog si está disponible
            device_info: Info del dispositivo
            
        Returns:
            Prompt estructurado
        """
        prompt = f"""CONSULTA DE DIAGNÓSTICO ALLWINNER
{'='*40}

ESCENARIO: {scenario}

"""
        
        if device_info:
            prompt += "INFORMACIÓN DEL DISPOSITIVO:\n"
            prompt += f"  SOC: {device_info.get('soc_type', 'N/A')}\n"
            prompt += f"  DRAM: {device_info.get('dram_size', 'N/A')}\n"
            prompt += f"  Estado: {device_info.get('state', 'N/A')}\n\n"
            
        if bootlog:
            prompt += "BOOTLOG:\n"
            prompt += "```\n"
            prompt += bootlog[:2000]
            if len(bootlog) > 2000:
                prompt += "\n... (truncado)"
            prompt += "\n```\n\n"
            
        prompt += """PREGUNTAS:
1. ¿Cuál es el diagnóstico?
2. ¿Qué procedimiento de recovery recomiendas?
3. ¿Hay riesgos en el procedimiento?
"""
        
        return prompt
        
    def _get_timestamp(self) -> str:
        """Obtiene timestamp actual"""
        from datetime import datetime
        return datetime.now().isoformat()
        
    def clear_history(self):
        """Limpia historial de conversación"""
        self.conversation_history = []


class OpenCodeIntegration:
    """
    Integración avanzada de opencode en ARS.
    
    Proporciona métodos para:
    - Diagnóstico automático
    - Generación de procedimientos
    - Análisis de errores
    """
    
    ALLWINNER_KNOWLEDGE = """
    CONOCIMIENTO ALLWINNER EMBEBIDO:
    
    SOCs SOPORTADOS:
    - H313: TV Boxes económicos, 4-core ARM Cortex-A53
    - H616: TV Boxes medianos, 4-core ARM Cortex-A53, 64-bit
    - H618: Variante de H616 con mejor GPU
    - H3: SBCs como Orange Pi, 4-core
    - A64: Pine64, 64-bit
    - R328: Asistentes de voz
    
    MODOS DE BOOT:
    1. Normal: boot0 → SPL → U-Boot → Kernel
    2. FEL: USB download mode para recovery
    3. Recovery: Partición dedicada para flasheo
    
    ESTRUCTURA DE MEMORIA:
    - DRAM base: 0x40000000
    - Boot0: Ejecuta desde SRAM, inicializa DRAM
    - SPL: Secondary Program Loader
    
    ERRORES COMUNES:
    - "boot0 error": Boot0 corrupto o missing
    - "mmc init failed": eMMC no responde
    - "FEL mode": Boot0 no válido
    - "kernel panic": System partition corrupta
    """
    
    def __init__(self):
        self.bridge = OpenCodeBridge()
        
    def diagnose(self, 
                 bootlog: str,
                 device_info: Dict,
                 scenario: str = "unknown") -> Dict:
        """
        Realiza diagnóstico usando opencode y conocimiento embebido.
        
        Args:
            bootlog: Bootlog capturado
            device_info: Info del dispositivo
            scenario: Escenario described
            
        Returns:
            Dict con diagnóstico
        """
        diagnosis = {
            "status": "unknown",
            "issues": [],
            "recommendations": [],
            "confidence": 0.0,
            "source": "embedded"
        }
        
        bootlog_lower = bootlog.lower()
        
        if "fel" in bootlog_lower and "usb" in bootlog_lower:
            diagnosis["status"] = "fel_mode"
            diagnosis["issues"].append("Dispositivo en modo FEL - bootloader corrupto")
            diagnosis["recommendations"].append("Usar FEL Recovery para cargar bootloader")
            
        elif "mmc init failed" in bootlog_lower or "sdmmc" in bootlog_lower and "error" in bootlog_lower:
            diagnosis["status"] = "emmc_error"
            diagnosis["issues"].append("Error inicializando eMMC/SD")
            diagnosis["recommendations"].append("Verificar conexión eMMC")
            diagnosis["recommendations"].append("Probar con Auto Recovery")
            
        elif "kernel panic" in bootlog_lower:
            diagnosis["status"] = "kernel_panic"
            diagnosis["issues"].append("Kernel no pudo montar rootfs")
            diagnosis["recommendations"].append("Flashear firmware completo")
            diagnosis["recommendations"].append("Factory Reset desde recovery")
            
        elif "bootloop" in scenario.lower() or bootlog.count("restarting") > 2:
            diagnosis["status"] = "bootloop"
            diagnosis["issues"].append("Bootloop detectado")
            diagnosis["recommendations"].append("Factory Reset recomendado")
            
        elif "android" in bootlog_lower and ("logo" in bootlog_lower or "bootanimation" in bootlog_lower):
            diagnosis["status"] = "android_stuck"
            diagnosis["issues"].append("Android iniciando pero no completa")
            diagnosis["recommendations"].append("Interrumpir boot y usar recovery")
            
        else:
            diagnosis["status"] = "unknown"
            diagnosis["issues"].append("No se identificó el problema automáticamente")
            diagnosis["recommendations"].append("Consultar con opencode para análisis avanzado")
            
        diagnosis["confidence"] = 0.7 if diagnosis["status"] != "unknown" else 0.3
        
        return diagnosis
        
    def generate_procedure(self,
                          diagnosis: Dict,
                          device_info: Dict) -> str:
        """
        Genera procedimiento de recovery basado en diagnóstico.
        
        Args:
            diagnosis: Resultado de diagnose()
            device_info: Info del dispositivo
            
        Returns:
            Procedimiento en texto
        """
        status = diagnosis.get("status", "unknown")
        soc = device_info.get("soc_type", "unknown")
        
        procedures = {
            "fel_mode": f"""
📋 PROCEDIMIENTO PARA MODO FEL ({soc})
═══════════════════════════════════════

1. Preparar archivos:
   - Firmware .img para {soc}
   - Boot0 compatible (si disponible)

2. Conexión:
   - Mantener botón FEL presionado
   - Conectar cable USB
   - Verificar con 'sunxi-fel ver'

3. Escritura a RAM:
   - Escribir firmware a RAM via sunxi-fel
   - Método: chunk o pipe (4MB por chunk)

4. Recovery via serial:
   - Conectar CH340 USB-TTL
   - Esperar prompt U-Boot
   - Ejecutar comandos de flasheo

5. Verificación:
   - Boot normal sin modo FEL
   - Verificar log de arranque
""",
            
            "emmc_error": """
📋 PROCEDIMIENTO PARA ERROR DE eMMC
═══════════════════════════════════════

1. Verificar hardware:
   - Revisar soldaduras del chip eMMC
   - Medir voltages (VCC, VCCQ)

2. Intentar recovery:
   - Auto Recovery via serial
   - Factory Reset desde menú

3. Si falla:
   - Dump eMMC para diagnóstico
   - Verificar bad blocks
   - Considerar reemplazo de eMMC
""",
            
            "kernel_panic": """
📋 PROCEDIMIENTO PARA KERNEL PANIC
═══════════════════════════════════════

1. Bootlog analysis:
   - Identificar última línea antes del panic
   - Buscar "VFS" o "unable to mount"

2. Recovery options:
   - Recovery mode → Factory Reset
   - Flashear firmware completo

3. Verificar:
   - Checksum del firmware
   - Compatibilidad con SOC
""",
            
            "bootloop": """
📋 PROCEDIMIENTO PARA BOOTLOOP
═══════════════════════════════════════

1. Conectar serial console
2. Capturar bootlog completo
3. Identificar punto de falla
4. Factory Reset desde recovery
5. Si persiste → Flashear firmware
""",
            
            "unknown": """
📋 PROCEDIMIENTO GENERAL
═══════════════════════════════════════

1. Capturar bootlog via serial
2. Identificar estado (FEL/normal/recovery)
3. Basado en diagnóstico:
   - Normal: Recovery menu → Factory Reset
   - FEL: Recovery vía USB
   - Recovery: Factory Reset

4. Si todo falla:
   - Consultar con opencode
   - Proporcionar bootlog completo
"""
        }
        
        return procedures.get(status, procedures["unknown"])
        
    def get_consultation_prompt(self,
                                diagnosis: Dict,
                                device_info: Dict,
                                bootlog: str) -> str:
        """
        Genera prompt para consultar a opencode.
        
        Args:
            diagnosis: Diagnóstico automático
            device_info: Info del dispositivo
            bootlog: Bootlog capturado
            
        Returns:
            Prompt estructurado
        """
        return f"""ANÁLISIS REQUERIDO - ALLWINNER RECOVERY
═══════════════════════════════════════════

DISPOSITIVO:
- SOC: {device_info.get('soc_type', 'N/A')}
- DRAM: {device_info.get('dram_size', 'N/A')}
- Estado: {diagnosis.get('status', 'unknown')}

DIAGNÓSTICO AUTOMÁTICO:
- Problemas: {', '.join(diagnosis.get('issues', ['ninguno']))}
- Confianza: {diagnosis.get('confidence', 0):.0%}

BOOTLOG:
```
{bootlog[:2000]}
```

AYUDA REQUERIDA:
1. ¿Confirmas el diagnóstico?
2. ¿Qué pasos adicionales sugieres?
3. ¿Hay algo específico para {device_info.get('soc_type', 'este SOC')}?
"""
