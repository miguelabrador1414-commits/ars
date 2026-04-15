"""
Tests para Allwinner Recovery Studio
Ejecutar con: python3 -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class TestConfig:
    """Tests para módulo de configuración"""
    
    def test_config_load(self):
        from core.config import get_config
        config = get_config()
        assert config is not None
        assert hasattr(config, 'config')
        
    def test_config_get_set(self):
        from core.config import get_config
        config = get_config()
        
        model = config.get("ai.model")
        assert model is not None
        
    def test_config_save(self):
        from core.config import get_config
        config = get_config()
        config.set("test_key", "test_value")
        assert config.get("test_key") == "test_value"


class TestDeviceManager:
    """Tests para DeviceManager"""
    
    def test_device_manager_init(self):
        from core.device_manager import DeviceManager
        dm = DeviceManager()
        assert dm is not None
        assert hasattr(dm, 'check_fel_availability')
        
    def test_check_fel_availability(self):
        from core.device_manager import DeviceManager
        dm = DeviceManager()
        result = dm.check_fel_availability()
        assert isinstance(result, bool)


class TestSerialConsole:
    """Tests para SerialConsole"""
    
    def test_serial_init(self):
        from core.serial_console import SerialConsole
        sc = SerialConsole()
        assert sc is not None
        assert hasattr(sc, 'connect')
        
    def test_list_ports(self):
        from core.serial_console import SerialConsole
        ports = SerialConsole.list_ports()
        assert isinstance(ports, list)
        
    def test_list_usb_serial(self):
        from core.serial_console import SerialConsole
        ports = SerialConsole.list_usb_serial()
        assert isinstance(ports, list)


class TestAI:
    """Tests para módulo de IA"""
    
    def test_ai_assistant_init(self):
        from ai.assistant import AIAssistant
        ai = AIAssistant()
        assert ai is not None
        assert hasattr(ai, 'ask')
        assert hasattr(ai, 'bridge')
        
    def test_ai_bridge_init(self):
        from ai.ai_manager import AIBridge
        bridge = AIBridge()
        assert bridge is not None
        assert hasattr(bridge, 'current_provider')
        
    def test_offline_guides(self):
        from ai.ai_manager import OfflineGuideDB
        db = OfflineGuideDB()
        assert len(db.guides) > 0
        
    def test_offline_search(self):
        from ai.ai_manager import OfflineGuideDB
        db = OfflineGuideDB()
        result = db.search("bootloop")
        assert isinstance(result, str)


class TestErrorDatabase:
    """Tests para base de datos de errores"""
    
    def test_error_db_init(self):
        from db.error_database import ErrorDatabase
        db = ErrorDatabase()
        assert db is not None
        assert len(db.errors) > 0
        
    def test_error_search(self):
        from db.error_database import ErrorDatabase
        db = ErrorDatabase()
        results = db.search("emmc")
        assert isinstance(results, list)
        
    def test_error_diagnose_bootlog(self):
        from db.error_database import ErrorDatabase
        db = ErrorDatabase()
        bootlog = "mmc init failed error"
        results = db.diagnose_bootlog(bootlog)
        assert isinstance(results, list)


class TestFirmwareTools:
    """Tests para herramientas de firmware"""
    
    def test_firmware_analyzer_init(self):
        from utils.firmware_tools import FirmwareAnalyzer
        fa = FirmwareAnalyzer()
        assert fa is not None
        
    def test_firmware_extractor_init(self):
        from utils.firmware_tools import FirmwareExtractor
        fe = FirmwareExtractor()
        assert fe is not None
        
    def test_firmware_comparator_init(self):
        from utils.firmware_tools import FirmwareComparator
        fc = FirmwareComparator()
        assert fc is not None
        
    def test_firmware_validator_init(self):
        from utils.firmware_tools import FirmwareValidator
        fv = FirmwareValidator()
        assert fv is not None


class TestRecoveryLogger:
    """Tests para logging de recovery"""
    
    def test_logger_init(self):
        from core.recovery_logger import RecoveryLogger
        logger = RecoveryLogger()
        assert logger is not None
        assert logger.db_path is not None
        
    def test_start_session(self):
        from core.recovery_logger import RecoveryLogger
        logger = RecoveryLogger()
        session_id = logger.start_session(
            device_soc="H616",
            device_state="bootloop",
            method="auto"
        )
        assert isinstance(session_id, int)
        logger.end_session(session_id, "success")
        
    def test_get_statistics(self):
        from core.recovery_logger import RecoveryLogger
        logger = RecoveryLogger()
        stats = logger.get_statistics()
        assert isinstance(stats, dict)
        assert 'total_sessions' in stats


class TestOpenCodeBridge:
    """Tests para integración OpenCode"""
    
    def test_bridge_init(self):
        from integrations.opencode_bridge import OpenCodeBridge
        bridge = OpenCodeBridge()
        assert bridge is not None
        assert hasattr(bridge, 'is_available')
        
    def test_integration_init(self):
        from integrations.opencode_bridge import OpenCodeIntegration
        integration = OpenCodeIntegration()
        assert integration is not None


class TestFELRecovery:
    """Tests para recovery FEL"""
    
    def test_fel_recovery_init(self):
        from core.fel_recovery import FELRecovery
        fel = FELRecovery()
        assert fel is not None
        
    def test_fel_protocol(self):
        from core.fel_recovery import FELProtocol
        assert FELProtocol.CHUNK_SIZE > 0


class TestSerialRecovery:
    """Tests para recovery serial"""
    
    def test_serial_auto_recovery_init(self):
        from core.serial_recovery import SerialAutoRecovery
        from core.serial_console import SerialConsole
        sc = SerialConsole()
        sar = SerialAutoRecovery(sc)
        assert sar is not None
        
    def test_boot_state(self):
        from core.serial_recovery import BootState
        assert BootState.UNKNOWN is not None


class TestDataExchange:
    """Tests para export/import"""
    
    def test_exporter_init(self):
        from core.data_exchange import ConfigExporter
        exporter = ConfigExporter()
        assert exporter is not None
        
    def test_importer_init(self):
        from core.data_exchange import ConfigImporter
        importer = ConfigImporter()
        assert importer is not None
        
    def test_backup_manager_init(self):
        from core.data_exchange import BackupManager
        bm = BackupManager()
        assert bm is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
