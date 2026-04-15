"""
Allwinner Recovery Studio (ARS) v1.3.0
Sistema profesional de recuperación de dispositivos
"""

__version__ = "1.3.0"
__author__ = "ARS Development Team"
__license__ = "MIT"

# Core
from core.device_manager import DeviceManager, DeviceState, DeviceInfo
from core.fel_handler import FELHandler
from core.serial_console import SerialConsole
from core.serial_recovery import SerialAutoRecovery, UBootCommandExecutor, BootState, BootInfo
from core.fel_recovery import FELRecovery, FELBootloader, FELProtocol
from core.recovery_procedures import RecoveryEngine, RecoveryProfile
from core.recovery_logger import RecoveryLogger, RecoveryReport
from core.config import ARSConfig, get_config
from core.data_exchange import ConfigExporter, ConfigImporter, BackupManager
from core.update_system import AutoUpdater, UpdateChecker, UpdateInfo

# AI
from ai.assistant import AIAssistant, AIProvider, AIResponse
from ai.ai_manager import AIBridge, GroqAI, OfflineGuideDB

# Database
from db.device_profiles import SOCDatabase, DeviceProfileManager, SOCProfile
from db.error_database import ErrorDatabase, ErrorMatcher, KnownError, ErrorCategory
from db.cloud_database import CloudDatabase, CommunityHub

# Utils
from utils.firmware_tools import FirmwareAnalyzer, FirmwareExtractor, FirmwareComparator, FirmwareValidator

# Plugins
from plugins import PluginManager, BasePlugin, PluginInfo

# Integrations
from integrations.opencode_bridge import OpenCodeBridge, OpenCodeIntegration

__all__ = [
    # Version
    "__version__",
    
    # Core
    "DeviceManager", "DeviceState", "DeviceInfo",
    "FELHandler", "SerialConsole",
    "SerialAutoRecovery", "UBootCommandExecutor", "BootState", "BootInfo",
    "FELRecovery", "FELBootloader", "FELProtocol",
    "RecoveryEngine", "RecoveryProfile",
    "RecoveryLogger", "RecoveryReport",
    "ARSConfig", "get_config",
    "ConfigExporter", "ConfigImporter", "BackupManager",
    "AutoUpdater", "UpdateChecker", "UpdateInfo",
    
    # AI
    "AIAssistant", "AIProvider", "AIResponse",
    "AIBridge", "GroqAI", "OfflineGuideDB",
    
    # Database
    "SOCDatabase", "DeviceProfileManager", "SOCProfile",
    "ErrorDatabase", "ErrorMatcher", "KnownError", "ErrorCategory",
    "CloudDatabase", "CommunityHub",
    
    # Utils
    "FirmwareAnalyzer", "FirmwareExtractor", "FirmwareComparator", "FirmwareValidator",
    
    # Plugins
    "PluginManager", "BasePlugin", "PluginInfo",
    
    # Integrations
    "OpenCodeBridge", "OpenCodeIntegration",
]
