"""
Error Database - Base de datos de errores conocidos

Contiene:
- Errores comunes de Allwinner
- Causas probables
- Soluciones verificadas
- Tags para búsqueda
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class ErrorCategory(Enum):
    """Categoría de error"""
    BOOT = "boot"
    USB = "usb"
    MMC = "mmc"
    MEMORY = "memory"
    KERNEL = "kernel"
    FIRMWARE = "firmware"
    HARDWARE = "hardware"
    RECOVERY = "recovery"


@dataclass
class KnownError:
    """Error conocido"""
    id: str
    patterns: List[str]
    category: ErrorCategory
    title: str
    description: str
    cause: str
    solution: str
    commands: List[str]
    soc_models: List[str]
    severity: str  # "info", "warning", "critical"
    verified: bool


class ErrorDatabase:
    """Base de datos de errores Allwinner"""
    
    def __init__(self):
        self.errors = self._load_errors()
        
    def _load_errors(self) -> List[KnownError]:
        """Carga errores conocidos"""
        return [
            KnownError(
                id="FEL_NO_DEVICE",
                patterns=["no device found", "unable to connect", "fel mode"],
                category=ErrorCategory.USB,
                title="Dispositivo no detectado en FEL",
                description="El dispositivo no responde en modo FEL",
                cause="Boot0 corrupto, USB cable defectuoso, o botón FEL no presionado",
                solution="1. Verificar cable USB\n2. Mantener botón FEL presionado al conectar\n3. Probar otro puerto USB\n4. Reiniciar driver USB: sudo modprobe -r aw_usb && sudo modprobe aw_usb",
                commands=["lsusb", "sunxi-fel ver"],
                soc_models=["H616", "H313", "H618", "H3", "A64"],
                severity="warning",
                verified=True
            ),
            
            KnownError(
                id="MMC_INIT_FAILED",
                patterns=["mmc init failed", "sdmmc error", "mmc0 error", "card did not respond"],
                category=ErrorCategory.MMC,
                title="Error inicializando eMMC/SD",
                description="El controlador MMC no puede inicializar el almacenamiento",
                cause="eMMC defectuoso, conexión física mala, o firmware corrupto",
                solution="1. Verificar soldaduras del eMMC\n2. Medir voltajes (VCC, VCCQ)\n3. Intentar con tarjeta SD\n4. Flashear firmware de fábrica",
                commands=["mmc dev", "mmc list"],
                soc_models=["H616", "H313", "H618", "H3", "A64"],
                severity="critical",
                verified=True
            ),
            
            KnownError(
                id="BOOT0_CORRUPT",
                patterns=["boot0 error", "boot0 header error", "校验失败", "check error"],
                category=ErrorCategory.BOOT,
                title="Boot0 corrupto o faltante",
                description="El bootloader primario no es válido",
                cause="Firmware corrupto, escritura incompleta, o apagado durante flash",
                solution="1. Entrar en modo FEL\n2. Cargar boot0 original a RAM\n3. Ejecutar boot0\n4. Flashear desde boot0 funcionando",
                commands=["sunxi-fel write 0x40000000 boot0.bin", "sunxi-fel exec 0x40000000"],
                soc_models=["H616", "H313", "H618", "H3", "A64"],
                severity="critical",
                verified=True
            ),
            
            KnownError(
                id="UBOOT_FAIL",
                patterns=["uboot error", "bad uboot", "invalid header"],
                category=ErrorCategory.BOOT,
                title="U-Boot corrupto",
                description="El bootloader secundario tiene errores",
                cause="Firmware corrupto o actualización incompleta",
                solution="1. Usar recovery mode\n2. Factory reset desde menú U-Boot\n3. Flashear firmware completo",
                commands=["setenv bootcmd run recovery", "run update"],
                soc_models=["H616", "H313", "H618", "H3", "A64"],
                severity="critical",
                verified=True
            ),
            
            KnownError(
                id="KERNEL_PANIC",
                patterns=["kernel panic", "not syncing", "vfs: unable to mount root fs"],
                category=ErrorCategory.KERNEL,
                title="Kernel panic - Filesystem corrupto",
                description="El kernel no puede montar el sistema de archivos",
                cause="Partición system corrupta, firmware incompleto, o incompatible",
                solution="1. Recovery mode → Factory Reset\n2. Flashear firmware completo\n3. Verificar integridad del .img",
                commands=["ext4ls mmc 0:2", "fatls mmc 0:1"],
                soc_models=["H616", "H313", "H618", "H3", "A64"],
                severity="warning",
                verified=True
            ),
            
            KnownError(
                id="DRAM_INIT_FAIL",
                patterns=["dram init failed", "dram error", "ddr init"],
                category=ErrorCategory.MEMORY,
                title="Error inicializando DRAM",
                description="La memoria RAM no puede inicializar",
                cause="Configuración de DRAM incorrecta, hardware defectuoso, o voltaje bajo",
                solution="1. Verificar voltajes de alimentación\n2. Revisar señales de DRAM\n3. Si es config, buscar DDR init correto para el SOC",
                commands=["md.l 0x40000000 10"],
                soc_models=["H616", "H313", "H618", "H3", "A64"],
                severity="critical",
                verified=False
            ),
            
            KnownError(
                id="USB_UNSTABLE",
                patterns=["usb timeout", "usb error", "sw usb", "error -110"],
                category=ErrorCategory.USB,
                title="Conexión USB inestable",
                description="La comunicación USB con el SOC es intermitente",
                cause="Cable largo, puerto USB 3.0 problemático, o SOC con problemas de USB",
                solution="1. Usar cable USB corto\n2. Usar puerto USB 2.0\n3. Conectar directamente al PC (no hub)\n4. Reiniciar USB: echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/unbind",
                commands=["lsusb -d 1f3a:", "dmesg | grep -i usb"],
                soc_models=["H616", "H313", "H618"],
                severity="warning",
                verified=True
            ),
            
            KnownError(
                id="FIRMWARE_ENCRYPTED",
                patterns=["nagra", "encrypted", "drm"],
                category=ErrorCategory.FIRMWARE,
                title="Firmware cifrado con DRM",
                description="El firmware está protegido con Nagra u otro DRM",
                cause="Firmware oficial con protección anticopia",
                solution="1. Buscar firmware desofuscado\n2. Extraer install.img de actualizaciones OTA\n3. Usar firmware de fuentes alternativas",
                commands=["binwalk X96Q.img | grep -i nagra"],
                soc_models=["H616", "H313"],
                severity="info",
                verified=True
            ),
            
            KnownError(
                id="RECOVERY_NOT_FOUND",
                patterns=["no recovery", "recovery not found", "boot recovery failed"],
                category=ErrorCategory.RECOVERY,
                title="Partición de recovery no encontrada",
                description="No hay partición de recovery válida",
                cause="Firmware sin recovery, partición borrada, o corrupta",
                solution="1. Usar FEL para cargar firmware completo\n2. Crear partición de recovery\n3. Flashear firmware con recovery incluido",
                commands=["ext4ls mmc 0:3"],
                soc_models=["H616", "H313", "H618"],
                severity="warning",
                verified=False
            ),
            
            KnownError(
                id="OVERHEAT_SHUTDOWN",
                patterns=["thermal", "overheat", "temperature"],
                category=ErrorCategory.HARDWARE,
                title="Apagado por sobrecalentamiento",
                description="El SOC se apaga por temperatura excesiva",
                cause="Dissipador mal colocado, pasta térmica seca, o ventilación deficiente",
                solution="1. Verificar disipador de calor\n2. Limpiar y aplicar pasta térmica\n3. Mejorar ventilación\n4. Reducir overclock si aplica",
                commands=["cat /sys/class/thermal/thermal_zone0/temp"],
                soc_models=["H616", "H313", "H618", "H3", "A64"],
                severity="warning",
                verified=False
            ),
            
            KnownError(
                id="HDMI_NO_SIGNAL",
                patterns=["hdmi no signal", "no video output", "display init failed"],
                category=ErrorCategory.HARDWARE,
                title="Sin señal de video HDMI",
                description="El HDMI no produce señal de video",
                cause="Cable HDMI defectuoso, config de display incorrecta, o hardware dañado",
                solution="1. Probar cable HDMI diferente\n2. Probar en otro TV/monitor\n3. Verificar config de display en U-Boot\n4. Probar salida composite AV",
                commands=["setenv hdmi_output 1", "setenv display_mode 1080p60"],
                soc_models=["H616", "H313", "H618", "H3", "A64"],
                severity="info",
                verified=True
            ),
            
            KnownError(
                id="BOOTLOOP",
                patterns=["rebooting", "restarting", "bootloop", "watchdog"],
                category=ErrorCategory.BOOT,
                title="Bootloop - Reinicios en bucle",
                description="El dispositivo reinicia continuamente",
                cause="Firmware corrupto, bootloader incompatible, o bad blocks en eMMC",
                solution="1. Capturar bootlog para ver dónde falla\n2. Factory reset\n3. Flashear firmware completo\n4. Dump eMMC para verificar bad blocks",
                commands=["printenv", "setenv bootdelay 3"],
                soc_models=["H616", "H313", "H618", "H3", "A64"],
                severity="warning",
                verified=True
            ),
            
            KnownError(
                id="ANDROID_STUCK_LOGO",
                patterns=["android", "logo", "bootanimation", "stuck"],
                category=ErrorCategory.BOOT,
                title="Android congelado en logo",
                description="El logo de Android aparece pero no avanza",
                cause="Firmware parcial, datos corruptos, o animación de boot fallida",
                solution="1. Hacer factory reset desde recovery\n2. Si no hay recovery, usar FEL para flashear\n3. Wipe data/cache manualmente",
                commands=["wipe data", "wipe cache"],
                soc_models=["H616", "H313", "H618"],
                severity="info",
                verified=True
            ),
        ]
        
    def search(self, query: str) -> List[KnownError]:
        """
        Busca errores por query.
        
        Args:
            query: Término de búsqueda
            
        Returns:
            Lista de errores que coinciden
        """
        query_lower = query.lower()
        results = []
        
        for error in self.errors:
            if query_lower in error.title.lower():
                results.append(error)
                continue
                
            if query_lower in error.description.lower():
                results.append(error)
                continue
                
            if any(query_lower in p.lower() for p in error.patterns):
                results.append(error)
                continue
                
            if query_lower in error.cause.lower():
                results.append(error)
                
        return results
        
    def get_by_category(self, category: ErrorCategory) -> List[KnownError]:
        """Obtiene errores por categoría"""
        return [e for e in self.errors if e.category == category]
        
    def get_by_soc(self, soc: str) -> List[KnownError]:
        """Obtiene errores para un SOC específico"""
        soc_upper = soc.upper()
        return [e for e in self.errors if soc_upper in e.soc_models]
        
    def get_by_severity(self, severity: str) -> List[KnownError]:
        """Obtiene errores por severidad"""
        return [e for e in self.errors if e.severity == severity]
        
    def diagnose_bootlog(self, bootlog: str) -> List[KnownError]:
        """
        Diagnostica un bootlog y retorna errores potenciales.
        
        Args:
            bootlog: Bootlog capturado
            
        Returns:
            Lista de errores detectados
        """
        bootlog_lower = bootlog.lower()
        detected = []
        
        for error in self.errors:
            for pattern in error.patterns:
                if pattern.lower() in bootlog_lower:
                    if error not in detected:
                        detected.append(error)
                    break
                    
        return detected
        
    def get_all_categories(self) -> List[str]:
        """Lista todas las categorías disponibles"""
        return [cat.value for cat in ErrorCategory]
        
    def get_all_socs(self) -> List[str]:
        """Lista todos los SOCs mencionados"""
        socs = set()
        for error in self.errors:
            socs.update(error.soc_models)
        return sorted(list(socs))
        
    def format_error(self, error: KnownError) -> str:
        """Formatea un error para mostrar"""
        verified_icon = "✓" if error.verified else "⚠"
        
        return f"""
{'='*60}
{error.title} {verified_icon}
{'='*60}

📋 DESCRIPCIÓN:
{error.description}

⚠️ CAUSA PROBABLE:
{error.cause}

✅ SOLUCIÓN:
{error.solution}

🔧 COMANDOS:
{chr(10).join(f'  • {cmd}' for cmd in error.commands)}

📱 MODELOS: {', '.join(error.soc_models)}
🏷️ CATEGORÍA: {error.category.value}
📊 SEVERIDAD: {error.severity.upper()}
"""


class ErrorMatcher:
    """Coincidencia automática de errores"""
    
    def __init__(self):
        self.db = ErrorDatabase()
        
    def match(self, bootlog: str, device_info: Dict = None) -> Dict:
        """
        Encuentra errores en bootlog y proporciona soluciones.
        
        Args:
            bootlog: Bootlog a analizar
            device_info: Info adicional del dispositivo
            
        Returns:
            Dict con errores encontrados y recomendaciones
        """
        errors = self.db.diagnose_bootlog(bootlog)
        
        results = {
            "errors_found": len(errors),
            "errors": [],
            "critical": [],
            "warnings": [],
            "recommendations": []
        }
        
        for error in errors:
            error_dict = {
                "id": error.id,
                "title": error.title,
                "severity": error.severity,
                "solution": error.solution,
                "commands": error.commands
            }
            
            results["errors"].append(error_dict)
            
            if error.severity == "critical":
                results["critical"].append(error)
            elif error.severity == "warning":
                results["warnings"].append(error)
                
        if errors:
            results["recommendations"].append(
                "Se detectaron errores en el bootlog. Revisa las soluciones arriba."
            )
        else:
            results["recommendations"].append(
                "No se detectaron errores conocidos. Captura más bootlog para diagnóstico."
            )
            
        return results
