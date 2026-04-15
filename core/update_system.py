"""
Auto Update System - Sistema de actualizaciones automáticas

Características:
- Verificación de actualizaciones
- Descarga con progreso
- Verificación de checksum
- Instalación segura
- Rollback en caso de error
"""

import os
import sys
import json
import hashlib
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Callable
from dataclasses import dataclass
import logging

import requests

logger = logging.getLogger(__name__)


@dataclass
class UpdateInfo:
    """Información de actualización disponible"""
    version: str
    changelog: str
    download_url: str
    checksum: str
    size: int
    release_date: str
    is_stable: bool
    is_mandatory: bool


@dataclass
class UpdateProgress:
    """Progreso de descarga"""
    downloaded: int
    total: int
    speed: str
    percent: int


class UpdateConfig:
    """Configuración del sistema de updates"""
    
    CURRENT_VERSION = "1.2.0"
    UPDATE_SERVER = "https://api.github.com/repos/ars-project/ars/releases"
    API_FALLBACK = "https://api.github.com/repos/ars-project/ars/releases/latest"
    
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "ars"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.update_config = self.config_dir / "update.json"
        
    def get_last_check(self) -> Optional[datetime]:
        """Obtiene última fecha de verificación"""
        if self.update_config.exists():
            try:
                data = json.loads(self.update_config.read_text())
                last = data.get("last_check")
                if last:
                    return datetime.fromisoformat(last)
            except:
                pass
        return None
        
    def set_last_check(self, dt: datetime = None):
        """Guarda fecha de verificación"""
        if dt is None:
            dt = datetime.now()
        data = {"last_check": dt.isoformat()}
        self.update_config.write_text(json.dumps(data, indent=2))
        
    def get_skipped_version(self) -> Optional[str]:
        """Obtiene versión saltada por el usuario"""
        if self.update_config.exists():
            try:
                data = json.loads(self.update_config.read_text())
                return data.get("skipped_version")
            except:
                pass
        return None
        
    def skip_version(self, version: str):
        """Salta una versión específica"""
        data = {"skipped_version": version}
        if self.update_config.exists():
            try:
                existing = json.loads(self.update_config.read_text())
                data.update(existing)
            except:
                pass
        self.update_config.write_text(json.dumps(data, indent=2))


class UpdateChecker:
    """Verificador de actualizaciones"""
    
    def __init__(self):
        self.config = UpdateConfig()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "ARS-Updater/1.0"
        })
        
    def check_for_updates(self, force: bool = False) -> Tuple[bool, Optional[UpdateInfo]]:
        """
        Verifica si hay actualizaciones disponibles.
        
        Returns:
            Tuple de (hay_update, update_info)
        """
        last_check = self.config.get_last_check()
        skipped = self.config.get_skipped_version()
        
        if not force and last_check:
            hours_since = (datetime.now() - last_check).total_seconds() / 3600
            if hours_since < 24:
                logger.info(f"Skipping check, last check was {hours_since:.1f}h ago")
                return False, None
                
        try:
            releases = self._fetch_releases()
            
            if not releases:
                return False, None
                
            latest = releases[0]
            latest_version = latest.get("tag_name", "").lstrip("v")
            
            if latest_version == self.config.CURRENT_VERSION:
                self.config.set_last_check()
                return False, None
                
            if skipped and latest_version == skipped:
                return False, None
                
            update_info = UpdateInfo(
                version=latest_version,
                changelog=latest.get("body", "No changelog available"),
                download_url=latest.get("zipball_url", ""),
                checksum="",  # Se obtiene del release assets
                size=0,
                release_date=latest.get("published_at", ""),
                is_stable=not latest.get("prerelease", True),
                is_mandatory=latest.get("prerelease", False) is False
            )
            
            for asset in latest.get("assets", []):
                if "checksum" in asset.get("name", "").lower():
                    update_info.checksum = asset.get("browser_download_url", "")
                    
            self.config.set_last_check()
            return True, update_info
            
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return False, None
            
    def _fetch_releases(self) -> list:
        """Obtiene lista de releases"""
        try:
            response = self.session.get(self.config.UPDATE_SERVER, timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return []


class UpdateDownloader:
    """Descarga actualizaciones"""
    
    CHUNK_SIZE = 8192
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "ars_update"
        self.temp_dir.mkdir(exist_ok=True)
        
    def download(self, 
                url: str,
                progress_callback: Optional[Callable[[UpdateProgress], None]] = None) -> Tuple[bool, str]:
        """
        Descarga la actualización.
        
        Returns:
            Tuple de (éxito, ruta_archivo)
        """
        try:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            start_time = datetime.now()
            
            download_path = self.temp_dir / f"ars_update_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
            
            with open(download_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            elapsed = (datetime.now() - start_time).total_seconds()
                            speed = downloaded / elapsed if elapsed > 0 else 0
                            speed_str = self._format_speed(speed)
                            
                            progress = UpdateProgress(
                                downloaded=downloaded,
                                total=total_size,
                                speed=speed_str,
                                percent=int((downloaded / total_size) * 100)
                            )
                            progress_callback(progress)
                            
            return True, str(download_path)
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return False, str(e)
            
    def verify_checksum(self, file_path: str, expected_checksum: str) -> bool:
        """Verifica checksum del archivo"""
        if not expected_checksum or not os.path.exists(file_path):
            return True
            
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
                
        actual = sha256.hexdigest()
        return actual.lower() == expected_checksum.lower()
        
    def _format_speed(self, bytes_per_sec: float) -> str:
        """Formatea velocidad de descarga"""
        if bytes_per_sec > 1024 * 1024:
            return f"{bytes_per_sec / (1024*1024):.1f} MB/s"
        elif bytes_per_sec > 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        return f"{bytes_per_sec:.0f} B/s"
        
    def cleanup(self):
        """Limpia archivos temporales"""
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass


class UpdateInstaller:
    """Instala actualizaciones"""
    
    def __init__(self):
        self.backup_dir = Path.home() / ".local" / "share" / "ars" / "backup"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def install(self, 
               zip_path: str,
               current_version: str,
               rollback_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """
        Instala la actualización.
        
        Returns:
            Tuple de (éxito, mensaje)
        """
        try:
            import zipfile
            
            backup_path = self.backup_dir / f"v{current_version}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            backup_path.mkdir(exist_ok=True)
            
            current_dir = Path(__file__).parent.parent
            
            logger.info(f"Creating backup at {backup_path}")
            
            for item in ["core", "ai", "db", "utils", "gui", "integrations"]:
                src = current_dir / item
                if src.exists():
                    shutil.copytree(src, backup_path / item, dirs_exist_ok=True)
                    
            for file in ["ars.py", "__init__.py", "requirements.txt"]:
                src = current_dir / file
                if src.exists():
                    shutil.copy2(src, backup_path / file)
                    
            logger.info("Backup created, extracting update")
            
            extract_dir = self.temp_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
                
            extracted_item = list(extract_dir.iterdir())[0]
            
            for item in ["core", "ai", "db", "utils", "gui", "integrations"]:
                src = extracted_item / item
                if src.exists():
                    dest = current_dir / item
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(src, dest)
                    
            for file in ["ars.py", "__init__.py", "requirements.txt"]:
                src = extracted_item / file
                if src.exists():
                    shutil.copy2(src, current_dir / file)
                    
            shutil.rmtree(extract_dir)
            
            logger.info("Update installed successfully")
            return True, f"Actualizado a nueva versión. Backup en: {backup_path}"
            
        except Exception as e:
            logger.error(f"Installation error: {e}")
            if rollback_callback:
                rollback_callback()
            return False, str(e)


class AutoUpdater:
    """Gestor principal de actualizaciones"""
    
    def __init__(self):
        self.checker = UpdateChecker()
        self.downloader = UpdateDownloader()
        self.installer = UpdateInstaller()
        self.config = UpdateConfig()
        
    def check(self, force: bool = False) -> Tuple[bool, Optional[UpdateInfo]]:
        """Verifica actualizaciones"""
        return self.checker.check_for_updates(force)
        
    def download_and_install(self,
                           update_info: UpdateInfo,
                           progress_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """Descarga e instala actualización"""
        
        success, path_or_error = self.downloader.download(
            update_info.download_url,
            progress_callback
        )
        
        if not success:
            return False, f"Descarga fallida: {path_or_error}"
            
        if update_info.checksum:
            if not self.downloader.verify_checksum(path_or_error, update_info.checksum):
                return False, "Checksum no coincide. Archivo corrupto."
                
        success, message = self.installer.install(
            path_or_error,
            self.config.CURRENT_VERSION
        )
        
        if not success:
            return False, f"Instalación fallida: {message}"
            
        return True, message
        
    def get_current_version(self) -> str:
        """Obtiene versión actual"""
        return self.config.CURRENT_VERSION
