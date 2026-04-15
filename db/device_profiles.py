"""
Device Profiles - Perfiles de dispositivos y SOCs

Sistema extensible de perfiles para múltiples fabricantes y SOCs.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Manufacturer(Enum):
    """Fabricantes de SOCs"""
    ALLWINNER = "allwinner"
    ROCKCHIP = "rockchip"
    AMLOGIC = "amlogic"
    MEDIATEK = "mediatek"
    QUALCOMM = "qualcomm"
    INTEL = "intel"
    ACTIONS_SEMI = "actions"
    NOVATEK = "novatek"


@dataclass
class MemoryConfig:
    """Configuración de memoria"""
    dram_base: int = 0x40000000
    dram_max_size: int = 0x10000000
    supported_sizes: List[int] = field(default_factory=lambda: [512, 1024, 2048, 4096])
    ddr_type: str = "DDR3"
    bus_width: int = 32


@dataclass
class StorageConfig:
    """Configuración de almacenamiento"""
    emmc_base: int = 0x0
    emmc_max_size: int = 0x1000000000
    supports_sdcards: bool = True
    sdcard_base: str = "/dev/mmcblk1"
    partitions: List[str] = field(default_factory=lambda: [
        "boot0", "boot1", "uboot", "env", "boot", "system", "vendor", "data"
    ])


@dataclass
class BootConfig:
    """Configuración de arranque"""
    boot0_offset: int = 0x0
    boot1_offset: int = 0x40000
    uboot_offset: int = 0x400000
    uboot_entry: int = 0x40000000
    spl_size: int = 0x40000
    boot_mode: str = "emmc"
    supported_modes: List[str] = field(default_factory=lambda: ["emmc", "sdcard", "nand", "nor"])
    fel_mode_id: int = 0x1F3A


@dataclass
class USBConfig:
    """Configuración USB"""
    fel_vid: int = 0x1F3A
    fel_pid: int = 0x1823
    device_name: str = "Allwinner FID"
    otg_port: int = 0
    usb_version: str = "2.0"


@dataclass
class RecoveryMethod:
    """Método de recuperación"""
    method: str
    difficulty: str
    steps: List[str]
    tools_required: List[str]
    notes: str


@dataclass
class SOCProfile:
    """Perfil de SOC"""
    id: str
    name: str
    manufacturer: str
    cores: int
    architecture: str
    max_frequency: int
    process_node: str
    memory: MemoryConfig
    storage: StorageConfig
    boot: BootConfig
    usb: USBConfig
    recovery_methods: List[RecoveryMethod]
    known_issues: List[str]
    firmware_format: str
    recovery_tool: str
    community: str
    year_released: int
    

@dataclass
class DeviceProfile:
    """Perfil de dispositivo específico"""
    id: str
    name: str
    brand: str
    model: str
    soc_id: str
    ram_size: int
    emmc_size: int
    display_resolution: str
    hw_revision: str
    serial_console_baudrate: int
    buttons: Dict[str, int]
    led_colors: Dict[str, str]
    tested_firmwares: List[Dict]
    custom_config: Dict


class SOCDatabase:
    """Base de datos de SOCs"""
    
    def __init__(self):
        self.socs: Dict[str, SOCProfile] = {}
        self._load_default_profiles()
        
    def _load_default_profiles(self):
        """Carga perfiles de SOCs por defecto"""
        
        # ALLWINNER SOCs
        self.socs["h616"] = SOCProfile(
            id="h616",
            name="Allwinner H616",
            manufacturer="allwinner",
            cores=4,
            architecture="ARMv8-A",
            max_frequency=1800000000,
            process_node="28nm",
            memory=MemoryConfig(
                dram_base=0x40000000,
                dram_max_size=0x20000000,
                supported_sizes=[1024, 1536, 2048, 4096],
                ddr_type="DDR3/LPDDR3",
                bus_width=32
            ),
            storage=StorageConfig(
                emmc_base=0x0,
                emmc_max_size=0x1000000000,
                supports_sdcards=True,
                partitions=["boot0", "boot1", "uboot", "env", "boot", "system", "vendor", "data", "cache"]
            ),
            boot=BootConfig(
                boot0_offset=0x0,
                boot1_offset=0x40000,
                uboot_offset=0x400000,
                uboot_entry=0x40000000,
                spl_size=0x40000,
                boot_mode="emmc",
                supported_modes=["emmc", "sdcard"],
                fel_mode_id=0x1F3A
            ),
            usb=USBConfig(
                fel_vid=0x1F3A,
                fel_pid=0x1823,
                device_name="Allwinner H616"
            ),
            recovery_methods=[
                RecoveryMethod(
                    method="serial_recovery",
                    difficulty="easy",
                    steps=[
                        "Conectar serial console (115200 baud)",
                        "Encender dispositivo",
                        "Interrumpir autoboot",
                        "Ejecutar 'run update' o 'run recovery'"
                    ],
                    tools_required=["CH340 USB-TTL", "Cable serial"],
                    notes="Método más común para TV Boxes"
                ),
                RecoveryMethod(
                    method="fel_recovery",
                    difficulty="medium",
                    steps=[
                        "Abrir dispositivo",
                        "Localizar botón FEL",
                        "Presionar y mantener FEL",
                        "Conectar cable USB",
                        "Usar sunxi-fel para escribir a RAM",
                        "Ejecutar loader y flashear eMMC"
                    ],
                    tools_required=["Cables jumper", "USB OTG cable", "Destornilladores"],
                    notes="Para dispositivos completamente muertos"
                )
            ],
            known_issues=[
                "Bootloop por firmware corrupto",
                "Nagra DRM en firmwares oficiales",
                "eMMC defectuoso causa errores de lectura"
            ],
            firmware_format="img",
            recovery_tool="sunxi-fel",
            community="amltoys, x96q community",
            year_released=2020
        )
        
        self.socs["h313"] = SOCProfile(
            id="h313",
            name="Allwinner H313",
            manufacturer="allwinner",
            cores=4,
            architecture="ARMv8-A",
            max_frequency=1500000000,
            process_node="28nm",
            memory=MemoryConfig(
                dram_base=0x40000000,
                ddr_type="DDR3/LPDDR3"
            ),
            storage=StorageConfig(
                supports_sdcards=True
            ),
            boot=BootConfig(
                fel_mode_id=0x1F3A
            ),
            usb=USBConfig(
                fel_vid=0x1F3A,
                fel_pid=0x1823
            ),
            recovery_methods=[
                RecoveryMethod(
                    method="serial_recovery",
                    difficulty="easy",
                    steps=[
                        "Conectar serial (115200)",
                        "Interrumpir boot",
                        "Factory reset"
                    ],
                    tools_required=["CH340"],
                    notes="Similar a H616"
                )
            ],
            known_issues=["Firmware encryption"],
            firmware_format="img",
            recovery_tool="sunxi-fel",
            community="budget tv boxes",
            year_released=2019
        )
        
        self.socs["h618"] = SOCProfile(
            id="h618",
            name="Allwinner H618",
            manufacturer="allwinner",
            cores=4,
            architecture="ARMv8-A",
            max_frequency=2000000000,
            process_node="28nm",
            memory=MemoryConfig(
                dram_base=0x40000000,
                ddr_type="DDR4/LPDDR4"
            ),
            storage=StorageConfig(supports_sdcards=True),
            boot=BootConfig(fel_mode_id=0x1F3A),
            usb=USBConfig(fel_vid=0x1F3A, fel_pid=0x1823),
            recovery_methods=[
                RecoveryMethod(
                    method="serial_recovery",
                    difficulty="easy",
                    steps=["Serial console", "Factory reset"],
                    tools_required=["CH340"],
                    notes="Similar a H616/H313"
                )
            ],
            known_issues=["Compatibility issues with some firmwares"],
            firmware_format="img",
            recovery_tool="sunxi-fel",
            community="new generation boxes",
            year_released=2021
        )
        
        self.socs["h3"] = SOCProfile(
            id="h3",
            name="Allwinner H3",
            manufacturer="allwinner",
            cores=4,
            architecture="ARMv7-A",
            max_frequency=1296000000,
            process_node="28nm",
            memory=MemoryConfig(
                dram_base=0x40000000,
                ddr_type="DDR3"
            ),
            storage=StorageConfig(supports_sdcards=True),
            boot=BootConfig(fel_mode_id=0x1F3A),
            usb=USBConfig(fel_vid=0x1F3A, fel_pid=0x1823),
            recovery_methods=[
                RecoveryMethod(
                    method="fel_recovery",
                    difficulty="medium",
                    steps=["FEL mode", "sunxi-fel write"],
                    tools_required=["USB OTG"],
                    notes="Común en SBCs como Orange Pi"
                )
            ],
            known_issues=["Older, mostly obsolete"],
            firmware_format="img",
            recovery_tool="sunxi-fel",
            community="SBC community",
            year_released=2014
        )
        
        self.socs["a64"] = SOCProfile(
            id="a64",
            name="Allwinner A64",
            manufacturer="allwinner",
            cores=4,
            architecture="ARMv8-A",
            max_frequency=1152000000,
            process_node="28nm",
            memory=MemoryConfig(
                dram_base=0x40000000,
                ddr_type="DDR3/LPDDR3"
            ),
            storage=StorageConfig(supports_sdcards=True),
            boot=BootConfig(fel_mode_id=0x1F3A),
            usb=USBConfig(fel_vid=0x1F3A, fel_pid=0x1823),
            recovery_methods=[
                RecoveryMethod(
                    method="fel_recovery",
                    difficulty="easy",
                    steps=["FEL mode", "sunxi-fel"],
                    tools_required=["USB OTG"],
                    notes="Bien documentado en comunidad Pine64"
                )
            ],
            known_issues=[" DRAM calibration issues"],
            firmware_format="img",
            recovery_tool="sunxi-fel",
            community="Pine64, A64 boards",
            year_released=2015
        )
        
        # ROCKCHIP SOCs
        self.socs["rk3588"] = SOCProfile(
            id="rk3588",
            name="Rockchip RK3588",
            manufacturer="rockchip",
            cores=8,
            architecture="ARMv8-A",
            max_frequency=2400000000,
            process_node="8nm",
            memory=MemoryConfig(
                dram_base=0x200000,
                dram_max_size=0x80000000,
                ddr_type="DDR4/LPDDR4/LPDDR5",
                bus_width=64
            ),
            storage=StorageConfig(
                emmc_base=0x0,
                supports_sdcards=True,
                partitions=["uboot", "trust", "boot", "system", "vendor", "data"]
            ),
            boot=BootConfig(
                boot0_offset=0x6000,
                uboot_offset=0x4000000,
                uboot_entry=0x200000,
                boot_mode="emmc",
                supported_modes=["emmc", "sdcard", "nand", "spi"]
            ),
            usb=USBConfig(
                fel_vid=0x2207,
                fel_pid=0x3588,
                device_name="Rockchip"
            ),
            recovery_methods=[
                RecoveryMethod(
                    method="maskrom_mode",
                    difficulty="medium",
                    steps=[
                        "Apagar dispositivo",
                        "Conectar USB",
                        "Esperar entrada en modo MaskROM",
                        "Usar rkdeveloptool o Android Tool"
                    ],
                    tools_required=["USB-C cable", "rk_driver_tool"],
                    notes="Nuevo método RK3588"
                ),
                RecoveryMethod(
                    method="serial_recovery",
                    difficulty="easy",
                    steps=[
                        "Conectar serial",
                        "Interrumpir boot",
                        "load kernel from storage",
                        "recovery mode"
                    ],
                    tools_required=["Serial adapter"],
                    notes="Si el bootloader está intacto"
                )
            ],
            known_issues=[
                "Nuevo en el mercado",
                "Pocos firmwares disponibles",
                "MaskROM requiere drivers específicos"
            ],
            firmware_format="img",
            recovery_tool="rkdeveloptool",
            community="developer boards",
            year_released=2022
        )
        
        self.socs["rk3399"] = SOCProfile(
            id="rk3399",
            name="Rockchip RK3399",
            manufacturer="rockchip",
            cores=6,
            architecture="ARMv8-A",
            max_frequency=2000000000,
            process_node="28nm",
            memory=MemoryConfig(
                dram_base=0x200000,
                ddr_type="DDR3/LPDDR4",
                bus_width=64
            ),
            storage=StorageConfig(supports_sdcards=True),
            boot=BootConfig(
                fel_mode_id=0x2207
            ),
            usb=USBConfig(
                fel_vid=0x2207,
                fel_pid=0x3399
            ),
            recovery_methods=[
                RecoveryMethod(
                    method="maskrom_mode",
                    difficulty="medium",
                    steps=[
                        "Identificar pin MASKROM",
                        "Corto con GND",
                        "Conectar USB",
                        "Usar rkdeveloptool"
                    ],
                    tools_required=["Jumper wire", "USB-C"],
                    notes="Bien documentado"
                )
            ],
            known_issues=["Dual-core A72 puede dar problemas"],
            firmware_format="img",
            recovery_tool="rkdeveloptool",
            community="SBC community, Rock Pi",
            year_released=2016
        )
        
        # AMLOGIC SOCs
        self.socs["s905x4"] = SOCProfile(
            id="s905x4",
            name="Amlogic S905X4",
            manufacturer="amlogic",
            cores=4,
            architecture="ARMv8-A",
            max_frequency=2000000000,
            process_node="12nm",
            memory=MemoryConfig(
                dram_base=0x0,
                ddr_type="DDR4/LPDDR4"
            ),
            storage=StorageConfig(supports_sdcards=True),
            boot=BootConfig(
                boot_mode="emmc",
                supported_modes=["emmc", "sdcard", "nand"]
            ),
            usb=USBConfig(
                fel_vid=0x1B8E,
                fel_pid=0x6001,
                device_name="Amlogic"
            ),
            recovery_methods=[
                RecoveryMethod(
                    method="aml_usbdl",
                    difficulty="medium",
                    steps=[
                        "Crear disco de recovery USB",
                        "Conectar USB al puerto靠近",
                        "Iniciar desde USB",
                        "Flashear desde terminal"
                    ],
                    tools_required=["USB drive", "Amlogic USB Burning Tool"],
                    notes="Software específico de Amlogic"
                ),
                RecoveryMethod(
                    method="serial_recovery",
                    difficulty="easy",
                    steps=["Serial console", "Factory reset"],
                    tools_required=["CH340"],
                    notes="Si el bootloader funciona"
                )
            ],
            known_issues=[
                "Bootloader con firma",
                "Firmwares oficiales cifrados"
            ],
            firmware_format="img",
            recovery_tool="Amlogic USB Burning Tool",
            community="TV Boxes community",
            year_released=2021
        )
        
        self.socs["s905x3"] = SOCProfile(
            id="s905x3",
            name="Amlogic S905X3",
            manufacturer="amlogic",
            cores=4,
            architecture="ARMv8-A",
            max_frequency=1900000000,
            process_node="12nm",
            memory=MemoryConfig(ddr_type="DDR4/LPDDR4"),
            storage=StorageConfig(supports_sdcards=True),
            boot=BootConfig(fel_mode_id=0x1B8E),
            usb=USBConfig(fel_vid=0x1B8E, fel_pid=0x6001),
            recovery_methods=[
                RecoveryMethod(
                    method="aml_usbdl",
                    difficulty="medium",
                    steps=["USB Burning Tool"],
                    tools_required=["USB Burning Tool"],
                    notes="Popular en X96 Air"
                )
            ],
            known_issues=["Similar a S905X4"],
            firmware_format="img",
            recovery_tool="Amlogic USB Burning Tool",
            community="Popular boxes",
            year_released=2020
        )
        
        self.socs["s912"] = SOCProfile(
            id="s912",
            name="Amlogic S912",
            manufacturer="amlogic",
            cores=8,
            architecture="ARMv8-A",
            max_frequency=1500000000,
            process_node="28nm",
            memory=MemoryConfig(ddr_type="DDR3/LPDDR3"),
            storage=StorageConfig(supports_sdcards=True),
            boot=BootConfig(fel_mode_id=0x1B8E),
            usb=USBConfig(fel_vid=0x1B8E, fel_pid=0x6001),
            recovery_methods=[
                RecoveryMethod(
                    method="aml_usbdl",
                    difficulty="medium",
                    steps=["USB Burning Tool"],
                    tools_required=["USB Burning Tool"],
                    notes="8-core popular"
                )
            ],
            known_issues=["Calentamiento"],
            firmware_format="img",
            recovery_tool="Amlogic USB Burning Tool",
            community="Beelink, MiniM8S",
            year_released=2016
        )
        
        # MEDIATEK SOCs
        self.socs["mt8581"] = SOCProfile(
            id="mt8581",
            name="MediaTek MT8581",
            manufacturer="mediatek",
            cores=6,
            architecture="ARMv8-A",
            max_frequency=2000000000,
            process_node="12nm",
            memory=MemoryConfig(ddr_type="DDR4"),
            storage=StorageConfig(supports_sdcards=False),
            boot=BootConfig(boot_mode="emmc"),
            usb=USBConfig(
                fel_vid=0x0E8D,
                fel_pid=0x0002,
                device_name="MediaTek"
            ),
            recovery_methods=[
                RecoveryMethod(
                    method="sp_flash_tool",
                    difficulty="hard",
                    steps=[
                        "Descargar Scatter file",
                        "Abrir SP Flash Tool",
                        "Cargar firmware",
                        "Presionar download"
                    ],
                    tools_required=["SP Flash Tool", "USB VCOM drivers"],
                    notes="Complejo, requiere scatter file específico"
                )
            ],
            known_issues=[
                "SP Flash Tool solo para Windows",
                "Drivers problemáticos"
            ],
            firmware_format="scatter",
            recovery_tool="SP Flash Tool",
            community="Limited",
            year_released=2020
        )
        
        # Novatek
        self.socs["nt96678"] = SOCProfile(
            id="nt96678",
            name="Novatek NT96678",
            manufacturer="novatek",
            cores=2,
            architecture="ARMv7-A",
            max_frequency=800000000,
            process_node="28nm",
            memory=MemoryConfig(ddr_type="DDR2"),
            storage=StorageConfig(supports_sdcards=True),
            boot=BootConfig(),
            usb=USBConfig(fel_vid=0x0603),
            recovery_methods=[
                RecoveryMethod(
                    method="factory_uart",
                    difficulty="hard",
                    steps=["UART console", "Manual commands"],
                    tools_required=["Serial adapter"],
                    notes="Común en dashcams"
                )
            ],
            known_issues=["Documentation limited"],
            firmware_format="bin",
            recovery_tool="Custom",
            community="Dashcam community",
            year_released=2019
        )
        
    def get(self, soc_id: str) -> Optional[SOCProfile]:
        """Obtiene perfil de SOC"""
        return self.socs.get(soc_id.lower())
        
    def get_by_manufacturer(self, manufacturer: str) -> List[SOCProfile]:
        """Obtiene SOCs por fabricante"""
        return [s for s in self.socs.values() 
                if s.manufacturer == manufacturer.lower()]
        
    def get_all(self) -> List[SOCProfile]:
        """Obtiene todos los SOCs"""
        return list(self.socs.values())
        
    def search(self, query: str) -> List[SOCProfile]:
        """Busca SOCs por nombre"""
        query = query.lower()
        return [s for s in self.socs.values()
                if query in s.name.lower() or query in s.id.lower()]
        
    def format_profile(self, soc_id: str) -> str:
        """Formatea perfil para mostrar"""
        soc = self.get(soc_id)
        if not soc:
            return "SOC no encontrado"
            
        recovery_text = "\n".join([
            f"  {r.method}: {r.difficulty}" for r in soc.recovery_methods
        ])
        
        return f"""
╔══════════════════════════════════════════════════╗
║ {soc.name}
╠══════════════════════════════════════════════════╣
║ Fabricante: {soc.manufacturer.upper()}
║ Núcleos: {soc.cores} ({soc.architecture})
║ Frecuencia: {soc.max_frequency/1000000:.0f} MHz
║ Proceso: {soc.process_node}
╠══════════════════════════════════════════════════╣
║ MEMORIA
║ Base DRAM: {hex(soc.memory.dram_base)}
║ Tipo: {soc.memory.ddr_type}
╠══════════════════════════════════════════════════╣
║ MÉTODOS DE RECOVERY
{recovery_text}
╠══════════════════════════════════════════════════╣
║ Herramienta: {soc.recovery_tool}
║ Comunidad: {soc.community}
╚══════════════════════════════════════════════════╝
"""


class DeviceProfileManager:
    """Gestor de perfiles de dispositivos"""
    
    def __init__(self):
        self.soc_db = SOCDatabase()
        self.profiles_dir = Path.home() / ".local" / "share" / "ars" / "device_profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.profiles: Dict[str, DeviceProfile] = {}
        self._load_custom_profiles()
        
    def _load_custom_profiles(self):
        """Carga perfiles personalizados"""
        for file in self.profiles_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                profile = DeviceProfile(**data)
                self.profiles[profile.id] = profile
            except Exception as e:
                logger.error(f"Error loading profile {file}: {e}")
                
    def save_profile(self, profile: DeviceProfile):
        """Guarda perfil de dispositivo"""
        self.profiles[profile.id] = profile
        path = self.profiles_dir / f"{profile.id}.json"
        path.write_text(json.dumps(asdict(profile), indent=2))
        
    def get_profile(self, device_id: str) -> Optional[DeviceProfile]:
        """Obtiene perfil de dispositivo"""
        return self.profiles.get(device_id)
        
    def list_profiles(self) -> List[DeviceProfile]:
        """Lista todos los perfiles"""
        return list(self.profiles.values())
        
    def delete_profile(self, device_id: str) -> bool:
        """Elimina perfil"""
        if device_id in self.profiles:
            del self.profiles[device_id]
            path = self.profiles_dir / f"{device_id}.json"
            if path.exists():
                path.unlink()
            return True
        return False
