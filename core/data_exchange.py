"""
Data Exchange - Sistema de exportación e importación

Permite:
- Exportar configuraciones
- Importar sesiones
- Respaldar y restaurar
- Compartir configuraciones
"""

import os
import json
import zipfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import asdict
import logging

logger = logging.getLogger(__name__)


class ConfigExporter:
    """Exportador de configuraciones"""
    
    def __init__(self):
        self.export_dir = Path.home() / ".local" / "share" / "ars" / "exports"
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
    def export_config(self, 
                      output_path: str = None,
                      include_history: bool = True) -> str:
        """
        Exporta configuración actual de ARS.
        
        Args:
            output_path: Ruta de salida (opcional)
            include_history: Incluir historial de sesiones
            
        Returns:
            Ruta al archivo exportado
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.export_dir / f"ars_config_{timestamp}.json"
            
        from core.config import get_config
        config = get_config()
        
        export_data = {
            "version": "1.2.0",
            "timestamp": datetime.now().isoformat(),
            "config": config.config,
            "device_profiles": self._export_device_profiles(),
        }
        
        if include_history:
            from core.recovery_logger import RecoveryLogger
            logger_obj = RecoveryLogger()
            export_data["sessions"] = self._export_sessions(logger_obj)
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Config exported to: {output_path}")
        return str(output_path)
        
    def _export_device_profiles(self) -> List[Dict]:
        """Exporta perfiles de dispositivos"""
        profiles = []
        
        profile_path = Path.home() / ".local" / "share" / "ars" / "device_profiles.json"
        if profile_path.exists():
            with open(profile_path, 'r') as f:
                profiles = json.load(f)
                
        return profiles
        
    def _export_sessions(self, logger_obj) -> List[Dict]:
        """Exporta historial de sesiones"""
        sessions = []
        
        for session in logger_obj.get_all_sessions(limit=100):
            sessions.append(asdict(session))
            
        return sessions
        
    def export_session_package(self,
                               session_id: int,
                               output_dir: str = None) -> str:
        """
        Exporta una sesión completa con todos sus datos.
        
        Args:
            session_id: ID de la sesión
            output_dir: Directorio de salida
            
        Returns:
            Ruta al paquete exportado
        """
        if output_dir is None:
            output_dir = self.export_dir / f"session_{session_id}"
        else:
            output_dir = Path(output_dir)
            
        output_dir.mkdir(parents=True, exist_ok=True)
        
        from core.recovery_logger import RecoveryLogger
        logger_obj = RecoveryLogger()
        
        export_data = logger_obj.export_session(session_id)
        
        if not export_data:
            raise ValueError(f"Session {session_id} not found")
            
        with open(output_dir / "session_data.json", 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
            
        if export_data['session']['bootlog_path']:
            bootlog_src = Path(export_data['session']['bootlog_path'])
            if bootlog_src.exists():
                shutil.copy(bootlog_src, output_dir / "bootlog.txt")
                
        package_path = self.export_dir / f"session_{session_id}_{datetime.now().strftime('%Y%m%d')}.zip"
        
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in output_dir.iterdir():
                zf.write(file, file.name)
                
        shutil.rmtree(output_dir)
        
        return str(package_path)


class ConfigImporter:
    """Importador de configuraciones"""
    
    def __init__(self):
        self.import_dir = Path.home() / ".local" / "share" / "ars" / "imports"
        
    def import_config(self,
                      import_path: str,
                      merge: bool = True) -> bool:
        """
        Importa configuración desde archivo.
        
        Args:
            import_path: Ruta al archivo de importación
            merge: Si True, fusiona con config existente
            
        Returns:
            True si fue exitoso
        """
        import_path = Path(import_path)
        
        if not import_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {import_path}")
            
        with open(import_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        version = data.get("version", "unknown")
        logger.info(f"Importing config version: {version}")
        
        from core.config import get_config
        config = get_config()
        
        if merge and "config" in data:
            for section, values in data["config"].items():
                if section not in config.config:
                    config.config[section] = values
                else:
                    config.config[section].update(values)
        elif "config" in data:
            config.config = data["config"]
            
        config.save()
        
        if "device_profiles" in data:
            self._import_device_profiles(data["device_profiles"])
            
        if "sessions" in data and merge:
            self._import_sessions(data["sessions"])
            
        logger.info("Config imported successfully")
        return True
        
    def _import_device_profiles(self, profiles: List[Dict]):
        """Importa perfiles de dispositivos"""
        profile_path = Path.home() / ".local" / "share" / "ars" / "device_profiles.json"
        
        existing = []
        if profile_path.exists():
            with open(profile_path, 'r') as f:
                existing = json.load(f)
                
        existing_ids = {p.get("id") for p in existing}
        
        for profile in profiles:
            if profile.get("id") not in existing_ids:
                existing.append(profile)
                
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        with open(profile_path, 'w') as f:
            json.dump(existing, f, indent=2)
            
    def _import_sessions(self, sessions: List[Dict]):
        """Importa historial de sesiones"""
        from core.recovery_logger import RecoveryLogger
        logger_obj = RecoveryLogger()
        
        for session_data in sessions:
            existing = logger_obj.get_session(session_data.get("id"))
            
            if not existing:
                try:
                    session_id = logger_obj.start_session(
                        device_soc=session_data.get("device_soc", ""),
                        device_state=session_data.get("device_state", ""),
                        firmware_used=session_data.get("firmware_used", ""),
                        method=session_data.get("method", "")
                    )
                    
                    logger_obj.end_session(
                        session_id,
                        status=session_data.get("status", "unknown"),
                        error_message=session_data.get("error_message", ""),
                        notes=session_data.get("notes", "")
                    )
                except Exception as e:
                    logger.warning(f"Could not import session: {e}")
                    
    def import_session_package(self, package_path: str) -> Dict:
        """
        Importa un paquete de sesión.
        
        Args:
            package_path: Ruta al archivo .zip
            
        Returns:
            Dict con información de la importación
        """
        package_path = Path(package_path)
        
        if not package_path.exists():
            raise FileNotFoundError(f"Paquete no encontrado: {package_path}")
            
        temp_dir = self.import_dir / f"temp_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with zipfile.ZipFile(package_path, 'r') as zf:
                zf.extractall(temp_dir)
                
            session_file = temp_dir / "session_data.json"
            if not session_file.exists():
                raise ValueError("Invalid package: session_data.json not found")
                
            with open(session_file, 'r') as f:
                data = json.load(f)
                
            from core.recovery_logger import RecoveryLogger
            logger_obj = RecoveryLogger()
            
            session = data.get("session", {})
            
            session_id = logger_obj.start_session(
                device_soc=session.get("device_soc", ""),
                device_state=session.get("device_state", ""),
                firmware_used=session.get("firmware_used", ""),
                method=session.get("method", "")
            )
            
            logger_obj.end_session(
                session_id,
                status=session.get("status", "unknown"),
                error_message=session.get("error_message", ""),
                notes=f"Imported from package: {package_path.name}"
            )
            
            for cmd in data.get("commands", []):
                logger_obj.log_command(
                    session_id,
                    cmd.get("command", ""),
                    cmd.get("output", ""),
                    cmd.get("return_code", 0)
                )
                
            bootlog_file = temp_dir / "bootlog.txt"
            if bootlog_file.exists():
                with open(bootlog_file, 'r') as f:
                    logger_obj.save_bootlog(session_id, f.read())
                    
            return {
                "success": True,
                "session_id": session_id,
                "commands_count": len(data.get("commands", [])),
                "has_bootlog": bootlog_file.exists()
            }
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class BackupManager:
    """Gestor de respaldos"""
    
    def __init__(self):
        self.backup_dir = Path.home() / ".local" / "share" / "ars" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def create_backup(self, name: str = None) -> str:
        """
        Crea un respaldo completo.
        
        Args:
            name: Nombre del respaldo
            
        Returns:
            Ruta al respaldo
        """
        if name is None:
            name = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        backup_path = self.backup_dir / f"backup_{name}"
        backup_path.mkdir(parents=True, exist_ok=True)
        
        from core.config import get_config
        from core.recovery_logger import RecoveryLogger
        
        config = get_config()
        config_dir = config.CONFIG_DIR
        log = RecoveryLogger()
        
        if config_dir.exists():
            shutil.copytree(config_dir, backup_path / "config", dirs_exist_ok=True)
            
        if log.db_path.exists():
            shutil.copy2(log.db_path, backup_path / "recovery_log.db")
            
        log_dir = Path.home() / ".local" / "share" / "ars" / "bootlogs"
        if log_dir.exists():
            shutil.copytree(log_dir, backup_path / "bootlogs", dirs_exist_ok=True)
            
        backup_file = self.backup_dir / f"backup_{name}.zip"
        
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for item in backup_path.rglob("*"):
                if item.is_file():
                    zf.write(item, item.relative_to(backup_path))
                    
        shutil.rmtree(backup_path)
        
        logger.info(f"Backup created: {backup_file}")
        return str(backup_file)
        
    def restore_backup(self, backup_path: str) -> bool:
        """
        Restaura un respaldo.
        
        Args:
            backup_path: Ruta al archivo .zip de respaldo
            
        Returns:
            True si fue exitoso
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup no encontrado: {backup_path}")
            
        temp_dir = self.backup_dir / f"restore_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with zipfile.ZipFile(backup_path, 'r') as zf:
                zf.extractall(temp_dir)
                
            from core.config import get_config
            config = get_config()
            
            config_backup = temp_dir / "config"
            if config_backup.exists():
                for item in config_backup.rglob("*"):
                    if item.is_file():
                        dest = config.CONFIG_DIR / item.relative_to(config_backup)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest)
                        
            log_backup = temp_dir / "recovery_log.db"
            if log_backup.exists():
                from core.recovery_logger import RecoveryLogger
                log = RecoveryLogger()
                shutil.copy2(log_backup, log.db_path)
                
            bootlogs_backup = temp_dir / "bootlogs"
            if bootlogs_backup.exists():
                dest_dir = Path.home() / ".local" / "share" / "ars" / "bootlogs"
                shutil.copytree(bootlogs_backup, dest_dir, dirs_exist_ok=True)
                
            logger.info(f"Backup restored from: {backup_path}")
            return True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    def list_backups(self) -> List[Dict]:
        """Lista respaldos disponibles"""
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob("backup_*.zip"), reverse=True):
            stat = backup_file.stat()
            backups.append({
                "name": backup_file.name,
                "path": str(backup_file),
                "size": stat.st_size,
                "size_mb": stat.st_size / (1024 * 1024),
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
            
        return backups
        
    def delete_backup(self, backup_path: str) -> bool:
        """Elimina un respaldo"""
        backup_path = Path(backup_path)
        
        if backup_path.exists():
            backup_path.unlink()
            logger.info(f"Backup deleted: {backup_path}")
            return True
        return False
