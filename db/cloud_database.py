"""
Cloud Database - Base de datos centralizada

Provee acceso a:
- Errores reportados por usuarios
- Firmwares verificados
- Dispositivos probados
- Soluciones compartidas

Nota: Esta es una implementación mock que simula la API.
En producción, esto se conectaría a un servidor real.
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReportedError:
    """Error reportado por usuario"""
    id: str
    soc_id: str
    error_pattern: str
    bootlog_excerpt: str
    solution: str
    user_rating: float
    times_reported: int
    verified: bool
    date_reported: str
    tags: List[str] = field(default_factory=list)


@dataclass
class VerifiedFirmware:
    """Firmware verificado"""
    id: str
    device_name: str
    soc_id: str
    version: str
    checksum: str
    download_url: str
    source: str
    tested: bool
    tested_by: int
    rating: float
    issues: List[str] = field(default_factory=list)
    date_added: str = ""


@dataclass
class TestedDevice:
    """Dispositivo probado"""
    id: str
    brand: str
    model: str
    soc_id: str
    ram_size: int
    emmc_size: int
    tested_firmwares: List[Dict]
    successful_recoveries: int
    community_notes: str
    verified: bool


class CloudDatabase:
    """
    Base de datos centralizada mock.
    
    En producción, esto se conectaría a:
    - API REST (FastAPI/Django)
    - Base de datos (PostgreSQL/MongoDB)
    - CDN para firmwares
    """
    
    API_BASE = "https://api.ars-project.dev/v1"
    
    def __init__(self, offline: bool = True):
        self.offline = offline
        self.cache_dir = Path.home() / ".local" / "share" / "ars" / "cloud_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._local_errors: List[ReportedError] = []
        self._local_firmwares: List[VerifiedFirmware] = []
        self._local_devices: List[TestedDevice] = []
        
        self._load_local_cache()
        
    def _load_local_cache(self):
        """Carga cache local"""
        errors_file = self.cache_dir / "errors.json"
        if errors_file.exists():
            try:
                data = json.loads(errors_file.read_text())
                self._local_errors = [ReportedError(**e) for e in data]
            except:
                pass
                
        firmwares_file = self.cache_dir / "firmwares.json"
        if firmwares_file.exists():
            try:
                data = json.loads(firmwares_file.read_text())
                self._local_firmwares = [VerifiedFirmware(**f) for f in data]
            except:
                pass
                
        devices_file = self.cache_dir / "devices.json"
        if devices_file.exists():
            try:
                data = json.loads(devices_file.read_text())
                self._local_devices = [TestedDevice(**d) for d in data]
            except:
                pass
                
    def _save_local_cache(self):
        """Guarda cache local"""
        (self.cache_dir / "errors.json").write_text(
            json.dumps([asdict(e) for e in self._local_errors], indent=2)
        )
        (self.cache_dir / "firmwares.json").write_text(
            json.dumps([asdict(f) for f in self._local_firmwares], indent=2)
        )
        (self.cache_dir / "devices.json").write_text(
            json.dumps([asdict(d) for d in self._local_devices], indent=2)
        )
        
    def sync(self) -> bool:
        """
        Sincroniza con servidor cloud.
        
        Returns:
            True si fue exitoso
        """
        if self.offline:
            logger.info("Offline mode - skipping sync")
            return False
            
        try:
            logger.info("Syncing with cloud database...")
            # En producción: requests.post(f"{API_BASE}/sync", json=data)
            return True
        except Exception as e:
            logger.error(f"Sync error: {e}")
            return False
            
    def search_errors(self, query: str, soc_id: str = None) -> List[ReportedError]:
        """
        Busca errores reportados.
        
        Args:
            query: Término de búsqueda
            soc_id: Filtrar por SOC (opcional)
        """
        results = self._local_errors
        
        if soc_id:
            results = [e for e in results if e.soc_id == soc_id]
            
        if query:
            query = query.lower()
            results = [
                e for e in results
                if query in e.error_pattern.lower()
                or query in e.solution.lower()
                or any(query in tag.lower() for tag in e.tags)
            ]
            
        return sorted(results, key=lambda e: e.user_rating * e.times_reported, reverse=True)
        
    def get_error_by_pattern(self, pattern: str) -> Optional[ReportedError]:
        """Obtiene error por patrón"""
        for error in self._local_errors:
            if pattern in error.error_pattern.lower():
                return error
        return None
        
    def report_error(self,
                    soc_id: str,
                    error_pattern: str,
                    bootlog: str,
                    solution: str,
                    tags: List[str] = None) -> str:
        """
        Reporta un nuevo error/solución.
        
        Returns:
            ID del reporte
        """
        error_id = hashlib.md5(
            f"{soc_id}{error_pattern}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]
        
        error = ReportedError(
            id=error_id,
            soc_id=soc_id,
            error_pattern=error_pattern,
            bootlog_excerpt=bootlog[:500],
            solution=solution,
            user_rating=0.0,
            times_reported=1,
            verified=False,
            date_reported=datetime.now().isoformat(),
            tags=tags or []
        )
        
        self._local_errors.append(error)
        self._save_local_cache()
        
        return error_id
        
    def rate_solution(self, error_id: str, rating: float):
        """Califica una solución"""
        for error in self._local_errors:
            if error.id == error_id:
                total = error.user_rating * error.times_reported
                error.times_reported += 1
                error.user_rating = (total + rating) / error.times_reported
                self._save_local_cache()
                break
                
    def search_firmwares(self,
                        device_name: str = None,
                        soc_id: str = None,
                        tested_only: bool = False) -> List[VerifiedFirmware]:
        """Busca firmwares verificados"""
        results = self._local_firmwares
        
        if tested_only:
            results = [f for f in results if f.tested]
            
        if soc_id:
            results = [f for f in results if f.soc_id == soc_id]
            
        if device_name:
            device_name = device_name.lower()
            results = [
                f for f in results
                if device_name in f.device_name.lower()
            ]
            
        return sorted(results, key=lambda f: f.tested_by * f.rating, reverse=True)
        
    def add_firmware(self,
                    device_name: str,
                    soc_id: str,
                    version: str,
                    checksum: str,
                    download_url: str,
                    source: str = "community") -> str:
        """Agrega un firmware a la base"""
        fw_id = hashlib.md5(f"{device_name}{version}{checksum}".encode()).hexdigest()[:12]
        
        firmware = VerifiedFirmware(
            id=fw_id,
            device_name=device_name,
            soc_id=soc_id,
            version=version,
            checksum=checksum,
            download_url=download_url,
            source=source,
            tested=False,
            tested_by=0,
            issues=[],
            date_added=datetime.now().isoformat(),
            rating=0.0
        )
        
        self._local_firmwares.append(firmware)
        self._save_local_cache()
        
        return fw_id
        
    def mark_firmware_tested(self, fw_id: str, success: bool, issues: List[str] = None):
        """Marca firmware como probado"""
        for fw in self._local_firmwares:
            if fw.id == fw_id:
                fw.tested = True
                fw.tested_by += 1
                if issues:
                    fw.issues.extend(issues)
                self._save_local_cache()
                break
                
    def get_devices(self, soc_id: str = None) -> List[TestedDevice]:
        """Obtiene dispositivos probados"""
        results = self._local_devices
        
        if soc_id:
            results = [d for d in results if d.soc_id == soc_id]
            
        return sorted(results, key=lambda d: d.successful_recoveries, reverse=True)
        
    def add_device_test(self,
                        brand: str,
                        model: str,
                        soc_id: str,
                        ram: int,
                        emmc: int,
                        recovery_success: bool) -> str:
        """Registra prueba de dispositivo"""
        device_id = hashlib.md5(f"{brand}{model}{soc_id}".encode()).hexdigest()[:8]
        
        existing = None
        for d in self._local_devices:
            if d.id == device_id:
                existing = d
                break
                
        if existing:
            if recovery_success:
                existing.successful_recoveries += 1
        else:
            device = TestedDevice(
                id=device_id,
                brand=brand,
                model=model,
                soc_id=soc_id,
                ram_size=ram,
                emmc_size=emmc,
                tested_firmwares=[],
                successful_recoveries=1 if recovery_success else 0,
                community_notes="",
                verified=False
            )
            self._local_devices.append(device)
            
        self._save_local_cache()
        return device_id
        
    def get_stats(self) -> Dict:
        """Obtiene estadísticas de la comunidad"""
        return {
            "total_errors": len(self._local_errors),
            "verified_errors": len([e for e in self._local_errors if e.verified]),
            "total_firmwares": len(self._local_firmwares),
            "tested_firmwares": len([f for f in self._local_firmwares if f.tested]),
            "total_devices": len(self._local_devices),
            "total_recoveries": sum(d.successful_recoveries for d in self._local_devices),
            "last_sync": datetime.now().isoformat()
        }


class CloudDatabaseAPI:
    """API REST para cloud database (mock)"""
    
    @staticmethod
    def report_error(soc_id: str, error: str, solution: str) -> Dict:
        """Reporta error via API"""
        return {
            "success": True,
            "id": "mock_id",
            "message": "Error reportado (mock mode)"
        }
        
    @staticmethod
    def get_firmwares(soc_id: str = None) -> List[Dict]:
        """Obtiene firmwares via API"""
        return [
            {
                "id": "mock_fw_1",
                "device": "X96Q",
                "soc": "h616",
                "version": "20200811",
                "rating": 4.5,
                "tested": True
            }
        ]
        
    @staticmethod
    def submit_firmware(device: str, soc: str, url: str) -> Dict:
        """Envía firmware via API"""
        return {
            "success": True,
            "id": "mock_submission_id",
            "message": "Firmware enviado (mock mode)"
        }


class CommunityHub:
    """Hub de comunidad"""
    
    def __init__(self):
        self.db = CloudDatabase()
        
    def get_popular_solutions(self, limit: int = 10) -> List[Dict]:
        """Obtiene soluciones más populares"""
        errors = sorted(
            self.db._local_errors,
            key=lambda e: e.user_rating * e.times_reported,
            reverse=True
        )[:limit]
        
        return [
            {
                "soc": e.soc_id,
                "error": e.error_pattern,
                "solution": e.solution[:200],
                "rating": e.user_rating,
                "uses": e.times_reported
            }
            for e in errors
        ]
        
    def get_recommended_firmwares(self, soc_id: str) -> List[Dict]:
        """Obtiene firmwares recomendados para un SOC"""
        firmwares = self.db.search_firmwares(soc_id=soc_id, tested_only=True)
        
        return [
            {
                "device": f.device_name,
                "version": f.version,
                "rating": f.rating,
                "issues": f.issues[:3]
            }
            for f in firmwares[:5]
        ]
        
    def get_device_compatibility(self, brand: str, model: str) -> Dict:
        """Obtiene compatibilidad de dispositivo"""
        devices = [d for d in self.db._local_devices
                   if d.brand.lower() == brand.lower()
                   and d.model.lower() == model.lower()]
                   
        if not devices:
            return {
                "found": False,
                "message": "Dispositivo no encontrado en la base de datos"
            }
            
        device = devices[0]
        return {
            "found": True,
            "soc": device.soc_id,
            "ram": device.ram_size,
            "emmc": device.emmc_size,
            "recoveries": device.successful_recoveries,
            "notes": device.community_notes
        }
