"""
Device Database - Base de datos de dispositivos Allwinner
"""

import json
import os
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class DeviceSpec:
    """Especificación de un dispositivo"""
    name: str
    soc_type: str
    soc_id: str
    dram_size: str
    emmc_size: str
    usb_type: str
    has_serial: bool
    serial_pins: str
    fel_button: str
    notes: str
    recovery_steps: List[str]
    known_issues: List[str]


class DeviceDatabase:
    """
    Base de datos de dispositivos Allwinner conocidos.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            self.db_path = os.path.join(
                os.path.dirname(__file__), 
                "..", 
                "db", 
                "devices.json"
            )
        else:
            self.db_path = db_path
            
        self.devices: Dict[str, DeviceSpec] = {}
        self._load_database()
        
    def _load_database(self):
        """Carga la base de datos desde archivo"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, value in data.items():
                        self.devices[key] = DeviceSpec(**value)
                logger.info(f"Loaded {len(self.devices)} devices from database")
            except Exception as e:
                logger.error(f"Error loading database: {e}")
                self._create_default_database()
        else:
            self._create_default_database()
            
    def _create_default_database(self):
        """Crea base de datos con dispositivos conocidos"""
        self.devices = {
            "H616": DeviceSpec(
                name="Allwinner H616",
                soc_type="H616",
                soc_id="00001823",
                dram_size="1GB-4GB",
                emmc_size="8GB-128GB",
                usb_type="USB 2.0 OTG",
                has_serial=True,
                serial_pins="TX,RX,GND (3.3V)",
                fel_button="recovery button",
                notes="Common in TV Boxes like X96Q, Tanix, etc.",
                recovery_steps=[
                    "1. Connect USB cable while holding FEL button",
                    "2. Verify with: sg sunxi-fel -c 'sunxi-fel ver'",
                    "3. Write firmware to RAM using chunks",
                    "4. Load appropriate bootloader",
                    "5. Flash to eMMC via bootloader"
                ],
                known_issues=[
                    "SOC ID sometimes shows as unknown",
                    "USB connection may be unstable",
                    "Some units have encrypted firmware"
                ]
            ),
            "H313": DeviceSpec(
                name="Allwinner H313",
                soc_type="H313",
                soc_id="00001823",
                dram_size="1GB-2GB",
                emmc_size="8GB-32GB",
                usb_type="USB 2.0 OTG",
                has_serial=True,
                serial_pins="TX,RX,GND",
                fel_button="recovery button",
                notes="Budget variant of H616, similar recovery process",
                recovery_steps=[
                    "1. Enter FEL mode",
                    "2. Write bootloader to RAM",
                    "3. Flash firmware via UART or FEL"
                ],
                known_issues=[
                    "May show H616 ID in FEL mode",
                    "Limited RAM for firmware loading"
                ]
            ),
            "H618": DeviceSpec(
                name="Allwinner H618",
                soc_type="H618",
                soc_id="00001827",
                dram_size="2GB-4GB",
                emmc_size="16GB-128GB",
                usb_type="USB 2.0 OTG",
                has_serial=True,
                serial_pins="TX,RX,GND (3.3V)",
                fel_button="recovery button",
                notes="Newer chip, better support in tools",
                recovery_steps=[
                    "1. Connect in FEL mode",
                    "2. Use sunxi-fel for direct eMMC access",
                    "3. Flash with standard procedures"
                ],
                known_issues=[
                    "Relatively new, less documentation"
                ]
            ),
            "H3": DeviceSpec(
                name="Allwinner H3",
                soc_type="H3",
                soc_id="00001780",
                dram_size="512MB-2GB",
                emmc_size="8GB-64GB",
                usb_type="USB 2.0 OTG",
                has_serial=True,
                serial_pins="TX,RX,GND (3.3V)",
                fel_button="FEL/USB boot",
                notes="Older quad-core, very common in Orange Pi, etc.",
                recovery_steps=[
                    "1. Enter FEL mode",
                    "2. Use sunxi-fel spl to load SPL",
                    "3. Flash via FEL protocol"
                ],
                known_issues=[
                    "Good tool support",
                    "May need specific U-Boot version"
                ]
            ),
            "A64": DeviceSpec(
                name="Allwinner A64",
                soc_type="A64",
                soc_id="00001719",
                dram_size="1GB-3GB",
                emmc_size="eMMC 8GB-64GB",
                usb_type="USB 2.0 OTG",
                has_serial=True,
                serial_pins="TX,RX,GND (3.3V)",
                fel_button="FEL button",
                notes="Common in Pine64, laptops, etc.",
                recovery_steps=[
                    "1. Boot into FEL mode",
                    "2. Load appropriate bootloader",
                    "3. Flash via FEL"
                ],
                known_issues=[
                    "Requires 64-bit tools",
                    "eMMC boot requires special procedure"
                ]
            ),
            "R328": DeviceSpec(
                name="Allwinner R328",
                soc_type="R328",
                soc_id="00001821",
                dram_size="256MB-512MB",
                emmc_size="N/A (NAND)",
                usb_type="USB 2.0 OTG",
                has_serial=True,
                serial_pins="TX,RX,GND",
                fel_button="FEL button",
                notes="Dual-core, used in smart speakers",
                recovery_steps=[
                    "1. Enter FEL mode",
                    "2. Flash via USB"
                ],
                known_issues=[
                    "Limited RAM",
                    "Different boot process"
                ]
            )
        }
        
        self._save_database()
        logger.info(f"Created default database with {len(self.devices)} devices")
        
    def _save_database(self):
        """Guarda la base de datos a archivo"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            data = {
                key: asdict(device) 
                for key, device in self.devices.items()
            }
            
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Saved database to {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error saving database: {e}")
            
    def get_device(self, soc_type: str) -> Optional[DeviceSpec]:
        """Obtiene información de un dispositivo por SOC"""
        return self.devices.get(soc_type)
        
    def match_device(self, soc_id: str, soc_type_hint: str = "") -> Optional[DeviceSpec]:
        """
        Busca dispositivo coincidente por ID de SOC.
        
        Args:
            soc_id: ID del SOC (ej: 00001823)
            soc_type_hint: Sugerencia de tipo (ej: H616)
        """
        # Buscar por ID directo
        for device in self.devices.values():
            if device.soc_id.lower() == soc_id.lower():
                return device
                
        # Si hay sugerencia, buscar por tipo
        if soc_type_hint:
            return self.devices.get(soc_type_hint)
            
        return None
        
    def add_device(self, device: DeviceSpec):
        """Agrega un nuevo dispositivo a la base de datos"""
        self.devices[device.soc_type] = device
        self._save_database()
        logger.info(f"Added device: {device.name}")
        
    def update_device(self, soc_type: str, updates: Dict):
        """Actualiza información de un dispositivo"""
        if soc_type in self.devices:
            device = self.devices[soc_type]
            for key, value in updates.items():
                if hasattr(device, key):
                    setattr(device, key, value)
            self._save_database()
            logger.info(f"Updated device: {soc_type}")
            
    def get_all_devices(self) -> List[DeviceSpec]:
        """Obtiene lista de todos los dispositivos"""
        return list(self.devices.values())
        
    def get_recovery_steps(self, soc_type: str) -> List[str]:
        """Obtiene pasos de recuperación para un SOC"""
        device = self.devices.get(soc_type)
        if device:
            return device.recovery_steps
        return []
        
    def get_known_issues(self, soc_type: str) -> List[str]:
        """Obtiene problemas conocidos para un SOC"""
        device = self.devices.get(soc_type)
        if device:
            return device.known_issues
        return []
        
    def export_to_markdown(self, output_path: str):
        """Exporta la base de datos a formato Markdown"""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("# Base de Datos de Dispositivos Allwinner\n\n")
                
                for soc_type, device in self.devices.items():
                    f.write(f"## {device.name}\n\n")
                    f.write(f"**Tipo SOC:** {device.soc_type}\n")
                    f.write(f"**ID SOC:** {device.soc_id}\n")
                    f.write(f"**RAM:** {device.dram_size}\n")
                    f.write(f"**eMMC:** {device.emmc_size}\n\n")
                    
                    f.write("### Conexiones\n\n")
                    f.write(f"- **USB:** {device.usb_type}\n")
                    f.write(f"- **Serial:** {device.serial_pins}\n")
                    f.write(f"- **Botón FEL:** {device.fel_button}\n\n")
                    
                    f.write("### Pasos de Recuperación\n\n")
                    for step in device.recovery_steps:
                        f.write(f"- {step}\n")
                    f.write("\n")
                    
                    f.write("### Problemas Conocidos\n\n")
                    for issue in device.known_issues:
                        f.write(f"- {issue}\n")
                    f.write("\n")
                    
                    f.write(f"**Notas:** {device.notes}\n\n")
                    f.write("---\n\n")
                    
            logger.info(f"Exported database to {output_path}")
            
        except Exception as e:
            logger.error(f"Error exporting database: {e}")
