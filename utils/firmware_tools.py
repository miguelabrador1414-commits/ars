"""
Firmware Tools - Herramientas para análisis y manipulación de firmware

Provee funcionalidades para:
- Análisis de estructura
- Extracción de componentes
- Comparación de firmwares
- Validación de integridad
"""

import os
import subprocess
import struct
import hashlib
import tarfile
import zipfile
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class FirmwareInfo:
    """Información del firmware"""
    path: str
    size: int
    size_mb: float
    format: str
    checksum: str
    is_encrypted: bool
    has_nagra: bool
    partitions: List[str]
    soc_compatible: List[str]


@dataclass
class PartitionInfo:
    """Información de partición"""
    name: str
    offset: int
    size: int
    type: str
    extracted_path: Optional[str] = None


class FirmwareAnalyzer:
    """Analizador de firmware Allwinner"""
    
    KNOWN_SIGNATURES = {
        b'ANDROID!': 'android',
        b'Nagra': 'nagra_encrypted',
        b'<?xml': 'xml_config',
        b'\x7fELF': 'elf_binary',
        b'MZ': 'dos_executable',
        b'\x1f\x8b': 'gzip_compressed',
        b'PK\x03\x04': 'zip_archive',
    }
    
    def __init__(self):
        self.info: Optional[FirmwareInfo] = None
        
    def analyze(self, firmware_path: str) -> FirmwareInfo:
        """
        Analiza un firmware y retorna información detallada.
        
        Args:
            firmware_path: Ruta al archivo de firmware
            
        Returns:
            FirmwareInfo con datos del análisis
        """
        if not os.path.exists(firmware_path):
            raise FileNotFoundError(f"Firmware no encontrado: {firmware_path}")
            
        size = os.path.getsize(firmware_path)
        checksum = self._calculate_checksum(firmware_path)
        
        with open(firmware_path, 'rb') as f:
            header = f.read(1024)
            
        format_type = self._detect_format(header, firmware_path)
        is_encrypted, has_nagra = self._check_encryption(header)
        partitions = self._extract_partition_info(header)
        soc_compatible = self._detect_soc_compatibility(firmware_path)
        
        self.info = FirmwareInfo(
            path=firmware_path,
            size=size,
            size_mb=size / (1024 * 1024),
            format=format_type,
            checksum=checksum,
            is_encrypted=is_encrypted,
            has_nagra=has_nagra,
            partitions=partitions,
            soc_compatible=soc_compatible
        )
        
        return self.info
        
    def _calculate_checksum(self, path: str) -> str:
        """Calcula checksum SHA256 del archivo"""
        sha256 = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]
        
    def _detect_format(self, header: bytes, path: str) -> str:
        """Detecta el formato del firmware"""
        for sig, fmt in self.KNOWN_SIGNATURES.items():
            if sig in header:
                return fmt
                
        ext = Path(path).suffix.lower()
        if ext == '.img':
            return 'raw_image'
        elif ext == '.bin':
            return 'binary'
        elif ext == '.tar':
            return 'tar_archive'
            
        return 'unknown'
        
    def _check_encryption(self, header: bytes) -> Tuple[bool, bool]:
        """Verifica si el firmware está cifrado"""
        has_nagra = b'Nagra' in header
        is_encrypted = has_nagra or b'encrypted' in header.lower()
        
        return is_encrypted, has_nagra
        
    def _extract_partition_info(self, header: bytes) -> List[str]:
        """Extrae información de particiones"""
        partitions = []
        
        common_partitions = [
            'boot0', 'boot1', 'uboot', 'boot', 'system',
            'vendor', 'recovery', 'data', 'cache'
        ]
        
        header_str = header.decode('utf-8', errors='ignore').lower()
        
        for part in common_partitions:
            if part in header_str:
                partitions.append(part)
                
        return partitions
        
    def _detect_soc_compatibility(self, path: str) -> List[str]:
        """Detecta SOCs compatibles con el firmware"""
        socs = []
        
        try:
            result = subprocess.run(
                ['binwalk', '-y', 'allwinner', path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if 'H616' in result.stdout or 'h616' in result.stdout:
                socs.append('H616')
            if 'H313' in result.stdout or 'h313' in result.stdout:
                socs.append('H313')
            if 'H618' in result.stdout or 'h618' in result.stdout:
                socs.append('H618')
            if 'H3' in result.stdout:
                socs.append('H3')
            if 'A64' in result.stdout or 'a64' in result.stdout:
                socs.append('A64')
                
        except:
            pass
            
        return socs if socs else ['Unknown']
        
    def extract_with_binwalk(self, firmware_path: str, output_dir: str) -> bool:
        """
        Extrae componentes usando binwalk.
        
        Args:
            firmware_path: Ruta al firmware
            output_dir: Directorio de extracción
            
        Returns:
            True si fue exitoso
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            result = subprocess.run(
                ['binwalk', '-e', '-C', output_dir, firmware_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Binwalk extraction failed: {e}")
            return False
            
    def get_summary(self) -> str:
        """Obtiene resumen del firmware analizado"""
        if not self.info:
            return "No hay información. Ejecuta analyze() primero."
            
        info = self.info
        
        summary = f"""
╔══════════════════════════════════════════════════╗
║            ANÁLISIS DE FIRMWARE                 ║
╠══════════════════════════════════════════════════╣
║ Archivo: {Path(info.path).name:<37} ║
║ Tamaño: {info.size_mb:.2f} MB ({info.size:,} bytes){'':<19} ║
║ Formato: {info.format:<40} ║
║ Checksum: {info.checksum:<38} ║
║ Cifrado: {'Sí ⚠️' if info.is_encrypted else 'No ✓':<41} ║
║ Nagra DRM: {'Sí ⚠️' if info.has_nagra else 'No':<40} ║
╠══════════════════════════════════════════════════╣
║ SOCs Compatibles: {', '.join(info.soc_compatible):<28} ║
║ Particiones: {', '.join(info.partitions) if info.partitions else 'N/A':<33} ║
╚══════════════════════════════════════════════════╝
"""
        return summary


class FirmwareExtractor:
    """Extractor de componentes de firmware"""
    
    def __init__(self):
        self.extracted_parts: List[PartitionInfo] = []
        
    def extract_boot_partitions(self, 
                                 firmware_path: str,
                                 output_dir: str) -> List[PartitionInfo]:
        """
        Extrae particiones de boot del firmware.
        
        Args:
            firmware_path: Ruta al firmware
            output_dir: Directorio de salida
            
        Returns:
            Lista de PartitionInfo
        """
        os.makedirs(output_dir, exist_ok=True)
        extracted = []
        
        with open(firmware_path, 'rb') as f:
            data = f.read()
            
        boot_markers = {
            b'sunxi': ('boot0_sunxi', 0x1000),
            b'UBOOT': ('uboot', 0x10000),
            b'ANDROID!': ('android_header', 0x1000),
        }
        
        for marker, (name, default_size) in boot_markers.items():
            offset = data.find(marker)
            if offset >= 0:
                size = self._detect_partition_size(data, offset)
                
                partition_data = data[offset:offset+size]
                out_path = os.path.join(output_dir, f"{name}.bin")
                
                with open(out_path, 'wb') as out:
                    out.write(partition_data)
                    
                extracted.append(PartitionInfo(
                    name=name,
                    offset=offset,
                    size=size,
                    type='boot',
                    extracted_path=out_path
                ))
                
                logger.info(f"Extraído: {name} @ 0x{offset:x} ({size} bytes)")
                
        self.extracted_parts = extracted
        return extracted
        
    def _detect_partition_size(self, data: bytes, offset: int) -> int:
        """Detecta el tamaño de una partición"""
        marker_size = 0x100
        
        for size in [0x100000, 0x200000, 0x400000, 0x800000]:
            chunk = data[offset:offset+size]
            
            if b'\x00\x00\x00\x00\x00\x00\x00\x00' in chunk[0x100:]:
                null_pos = chunk.find(b'\x00\x00\x00\x00\x00\x00\x00\x00', 0x100)
                if null_pos > 0:
                    return null_pos
                    
        return 0x100000
        
    def extract_install_img(self, firmware_path: str, output_dir: str) -> Optional[str]:
        """
        Extrae install.img de un firmware tar.
        
        Args:
            firmware_path: Ruta al firmware
            output_dir: Directorio de salida
            
        Returns:
            Ruta al install.img extraído o None
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            with tarfile.open(firmware_path, 'r:*') as tar:
                for member in tar.getmembers():
                    if 'install.img' in member.name:
                        tar.extract(member, output_dir)
                        extracted_path = os.path.join(output_dir, member.name)
                        logger.info(f"Extraído: {member.name}")
                        return extracted_path
                        
        except Exception as e:
            logger.error(f"Error extrayendo install.img: {e}")
            
        return None
        
    def extract_from_sparse(self, firmware_path: str, output_path: str) -> bool:
        """
        Convierte firmware sparse (Android) a raw.
        
        Args:
            firmware_path: Ruta al firmware sparse
            output_path: Ruta de salida raw
            
        Returns:
            True si fue exitoso
        """
        try:
            import shutil
            
            header = b'\x3a\xff\x26\xed'
            
            with open(firmware_path, 'rb') as src:
                data = src.read()
                
            if header in data:
                offset = data.index(header)
                raw_data = data[offset:]
                
                with open(output_path, 'wb') as dst:
                    dst.write(raw_data)
                    
                return True
                
        except Exception as e:
            logger.error(f"Error en conversión sparse: {e}")
            
        return False


class FirmwareComparator:
    """Compara dos firmwares"""
    
    def compare(self, 
                firmware1: str,
                firmware2: str) -> Dict:
        """
        Compara dos firmwares.
        
        Args:
            firmware1: Primer firmware
            firmware2: Segundo firmware
            
        Returns:
            Dict con diferencias
        """
        size1 = os.path.getsize(firmware1)
        size2 = os.path.getsize(firmware2)
        
        sha1 = hashlib.sha256(open(firmware1, 'rb').read()).hexdigest()
        sha2 = hashlib.sha256(open(firmware2, 'rb').read()).hexdigest()
        
        is_same = sha1 == sha2
        size_diff = abs(size1 - size2)
        
        return {
            "identical": is_same,
            "size1": size1,
            "size2": size2,
            "size_diff": size_diff,
            "checksum1": sha1[:16],
            "checksum2": sha2[:16],
            "difference_percent": (size_diff / max(size1, size2)) * 100 if max(size1, size2) > 0 else 0
        }


class FirmwareValidator:
    """Validador de firmware"""
    
    def validate(self, firmware_path: str) -> Tuple[bool, List[str]]:
        """
        Valida un firmware.
        
        Args:
            firmware_path: Ruta al firmware
            
        Returns:
            Tuple de (válido, lista de advertencias)
        """
        warnings = []
        valid = True
        
        if not os.path.exists(firmware_path):
            return False, ["Archivo no encontrado"]
            
        size = os.path.getsize(firmware_path)
        
        if size < 1024 * 1024:
            warnings.append("Firmware muy pequeño (< 1MB)")
            
        if size > 8 * 1024 * 1024 * 1024:
            warnings.append("Firmware muy grande (> 8GB)")
            
        with open(firmware_path, 'rb') as f:
            header = f.read(1024)
            
        if b'Nagra' in header:
            warnings.append("⚠️ Firmware cifrado con Nagra DRM")
            warnings.append("   No se puede modificar directamente")
            
        if b'\x00\x00\x00\x00\x00\x00\x00\x00' in header[:100]:
            warnings.append("⚠️ Header parece estar vacío o corrupto")
            valid = False
            
        if not any(x in header for x in [b'ANDROID', b'sunxi', b'UBOOT', b'boot']):
            warnings.append("⚠️ No se reconoció formato estándar")
            
        return valid, warnings
