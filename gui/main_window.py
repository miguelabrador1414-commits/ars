"""
Allwinner Recovery Studio - Interfaz Gráfica Principal
Incluye todas las funcionalidades: Bootlog, Firmware, IA, Recovery, Settings, etc.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import os
from typing import Optional
import logging

from core.device_manager import DeviceManager, DeviceState, DeviceInfo
from core.fel_handler import FELHandler
from core.serial_console import SerialConsole
from core.serial_recovery import SerialAutoRecovery, BootState
from core.fel_recovery import FELRecovery, FELBootloader
from ai.assistant import AIAssistant, AIProvider
from core.config import get_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ARSMainWindow(ctk.CTk):
    """Ventana principal de Allwinner Recovery Studio"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Allwinner Recovery Studio v1.2.0")
        self.geometry("1500x950")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.config = get_config()
        
        self.device_manager = DeviceManager(on_device_change=self._on_device_change)
        self.fel_handler = FELHandler()
        self.serial_console = SerialConsole(on_data=self._on_serial_data)
        self.ai_assistant = AIAssistant()
        
        if self.config.groq_api_key:
            self.ai_assistant.set_api_key(self.config.groq_api_key)
        if self.config.groq_model:
            self.ai_assistant.set_model(self.config.groq_model)
            
        self.auto_recovery = None
        self.auto_recovery_running = False
        self.current_firmware = None
        self.is_connected = False
        
        self._create_widgets()
        self._create_layout()
        self._restore_ui_from_config()
        
        # Iniciar paneles que necesitan el layout
        try:
            self.history_panel._refresh_sessions()
        except:
            pass
            
        self.device_manager.start_monitoring()
        self._check_services()
        
        logger.info("ARS GUI initialized")
        
    def _create_widgets(self):
        """Crea todos los widgets"""
        
        self.title_bar = ctk.CTkFrame(self, height=60)
        
        self.logo_label = ctk.CTkLabel(
            self.title_bar,
            text="🎯 Allwinner Recovery Studio v1.2",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        
        self.status_indicator = ctk.CTkLabel(self.title_bar, text="⚫", font=ctk.CTkFont(size=20))
        self.status_label = ctk.CTkLabel(self.title_bar, text="Dispositivo desconectado", font=ctk.CTkFont(size=14))
        
        self.refresh_btn = ctk.CTkButton(self.title_bar, text="🔄 Actualizar", command=self._refresh_devices, width=120)
        
        self.left_panel = ctk.CTkFrame(self, width=280)
        
        self._create_device_section()
        self._create_serial_section()
        
        self.center_panel = ctk.CTkFrame(self)
        self._create_tabs()
        
        self.right_panel = ctk.CTkFrame(self, width=350)
        self._create_right_panel()
        
    def _create_device_section(self):
        """Sección de dispositivo"""
        self.device_section = ctk.CTkFrame(self.left_panel)
        
        self.device_title = ctk.CTkLabel(
            self.device_section,
            text="📱 Dispositivo",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        
        self.device_info_frame = ctk.CTkFrame(self.device_section)
        
        self.soc_label = ctk.CTkLabel(self.device_info_frame, text="SOC: -")
        self.memory_label = ctk.CTkLabel(self.device_info_frame, text="RAM: -")
        self.emmc_label = ctk.CTkLabel(self.device_info_frame, text="eMMC: -")
        self.fel_ver_label = ctk.CTkLabel(self.device_info_frame, text="FEL: -")
        
        self.connect_fel_btn = ctk.CTkButton(
            self.device_section, text="🔌 Conectar FEL",
            command=self._connect_fel, fg_color="green"
        )
        
        self.reload_usb_btn = ctk.CTkButton(
            self.device_section, text="🔃 Recargar USB",
            command=self._reload_usb
        )
        
    def _create_serial_section(self):
        """Sección serial"""
        self.serial_section = ctk.CTkFrame(self.left_panel)
        
        self.serial_title = ctk.CTkLabel(
            self.serial_section,
            text="📡 Consola Serial",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        
        self.serial_port_combo = ctk.CTkOptionMenu(self.serial_section, values=["Auto-detectar"])
        self.serial_baud_combo = ctk.CTkOptionMenu(
            self.serial_section,
            values=["115200", "57600", "38400", "19200", "9600"]
        )
        self.serial_baud_combo.set("115200")
        
        self.serial_connect_btn = ctk.CTkButton(
            self.serial_section, text="Conectar Serial",
            command=self._connect_serial, fg_color="orange"
        )
        
    def _create_tabs(self):
        """Crea las pestañas principales"""
        self.tab_view = ctk.CTkTabview(self.center_panel)
        
        self._create_bootlog_tab()
        self._create_firmware_tools_tab()
        self._create_ai_tab()
        self._create_auto_recovery_tab()
        self._create_fel_recovery_tab()
        self._create_errors_tab()
        self._create_history_tab()
        self._create_settings_tab()
        
    def _create_bootlog_tab(self):
        """Pestaña de bootlog"""
        self.bootlog_tab = self.tab_view.add("📋 Bootlog")
        
        self.bootlog_text = ctk.CTkTextbox(self.bootlog_tab, wrap="word")
        self.bootlog_scroll = ctk.CTkScrollbar(self.bootlog_tab)
        self.bootlog_text.configure(yscrollcommand=self.bootlog_scroll.set)
        self.bootlog_scroll.configure(command=self.bootlog_text.yview)
        
        self.capture_bootlog_btn = ctk.CTkButton(
            self.bootlog_tab, text="🎬 Capturar Bootlog",
            command=self._capture_bootlog
        )
        self.clear_bootlog_btn = ctk.CTkButton(
            self.bootlog_tab, text="🗑️ Limpiar",
            command=lambda: self.bootlog_text.delete("1.0", "end")
        )
        
    def _create_firmware_tools_tab(self):
        """Pestaña de herramientas de firmware"""
        from gui.firmware_tools_panel import FirmwareToolsPanel
        self.firmware_tools_tab = self.tab_view.add("📦 Firmware Tools")
        self.firmware_tools_panel = FirmwareToolsPanel(self.firmware_tools_tab, self)
        
    def _create_ai_tab(self):
        """Pestaña de IA"""
        self.ai_tab = self.tab_view.add("🤖 Asistente IA")
        
        self.ai_status_frame = ctk.CTkFrame(self.ai_tab)
        self.ai_status = ctk.CTkLabel(
            self.ai_status_frame, text="IA: Verificando...",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.ai_provider_label = ctk.CTkLabel(
            self.ai_status_frame, text="Provider: -",
            font=ctk.CTkFont(size=12)
        )
        
        self.ai_config_frame = ctk.CTkFrame(self.ai_tab)
        self.ai_api_key_entry = ctk.CTkEntry(self.ai_config_frame, show="*", width=250)
        self.ai_save_key_btn = ctk.CTkButton(
            self.ai_config_frame, text="Guardar",
            command=self._save_api_key, width=80
        )
        
        self.ai_quick_help = ctk.CTkLabel(
            self.ai_tab,
            text="💡 Obtén API key gratis en console.groq.com",
            text_color="gray"
        )
        
        self.ai_model_combo = ctk.CTkOptionMenu(
            self.ai_tab,
            values=["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
        )
        self.ai_model_combo.set("llama-3.3-70b-versatile")
        
        self.ai_input = ctk.CTkTextbox(self.ai_tab, height=80)
        self.ai_input.insert("1.0", "Describe el problema...")
        
        self.ai_ask_btn = ctk.CTkButton(
            self.ai_tab, text="❓ Preguntar",
            command=self._ask_ai, fg_color="purple"
        )
        self.analyze_bootlog_btn = ctk.CTkButton(
            self.ai_tab, text="🔍 Analizar Bootlog",
            command=self._analyze_current_bootlog
        )
        self.ai_help_btn = ctk.CTkButton(
            self.ai_tab, text="📖 Guías Rápidas",
            command=self._show_offline_guides, fg_color="gray"
        )
        
        self.ai_output = ctk.CTkTextbox(self.ai_tab, wrap="word")
        
    def _create_auto_recovery_tab(self):
        """Pestaña de recovery automático"""
        self.recovery_tab = self.tab_view.add("🔧 Auto Recovery")
        
        self.recovery_status_label = ctk.CTkLabel(
            self.recovery_tab, text="Estado: No iniciado",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        
        self.recovery_info_text = ctk.CTkTextbox(self.recovery_tab, height=80, wrap="word")
        self.recovery_log = ctk.CTkTextbox(self.recovery_tab, height=150, wrap="word")
        self.recovery_progress = ctk.CTkProgressBar(self.recovery_tab)
        self.recovery_progress.set(0)
        
        self.start_recovery_btn = ctk.CTkButton(
            self.recovery_tab,
            text="🚀 INICIAR RECUPERACIÓN",
            command=self._start_auto_recovery,
            fg_color="green", height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.stop_recovery_btn = ctk.CTkButton(
            self.recovery_tab,
            text="⏹️ DETENER",
            command=self._stop_auto_recovery,
            fg_color="red", state="disabled"
        )
        
    def _create_fel_recovery_tab(self):
        """Pestaña de FEL recovery"""
        self.fel_tab = self.tab_view.add("⚡ FEL Recovery")
        
        self.fel_device_frame = ctk.CTkFrame(self.fel_tab)
        self.fel_device_label = ctk.CTkLabel(
            self.fel_device_frame, text="📱 Dispositivo FEL",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        
        self.fel_soc_label = ctk.CTkLabel(self.fel_device_frame, text="SOC: No detectado")
        self.fel_dram_label = ctk.CTkLabel(self.fel_device_frame, text="DRAM: -")
        self.fel_version_label = ctk.CTkLabel(self.fel_device_frame, text="FEL: -")
        
        self.fel_detect_btn = ctk.CTkButton(
            self.fel_device_frame, text="🔍 Detectar FEL",
            command=self._fel_detect, fg_color="blue"
        )
        self.fel_reload_btn = ctk.CTkButton(
            self.fel_device_frame, text="🔃 Recargar USB",
            command=self._fel_reload_usb, fg_color="orange"
        )
        
        self.fel_file_frame = ctk.CTkFrame(self.fel_tab)
        self.fel_firmware_label = ctk.CTkLabel(
            self.fel_file_frame, text="📦 Firmware",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.fel_firmware_path = ctk.CTkLabel(
            self.fel_file_frame, text="Ningún archivo seleccionado",
            wraplength=400
        )
        self.fel_select_fw_btn = ctk.CTkButton(
            self.fel_file_frame, text="📂 Seleccionar Firmware",
            command=self._fel_select_firmware
        )
        
        self.fel_method_var = ctk.StringVar(value="pipe")
        self.fel_method_menu = ctk.CTkOptionMenu(
            self.fel_file_frame, values=["pipe", "chunk"],
            variable=self.fel_method_var
        )
        
        self.fel_write_ram_btn = ctk.CTkButton(
            self.fel_tab,
            text="⚡ Escribir Firmware a RAM",
            command=self._fel_write_ram,
            fg_color="green", height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.fel_flash_btn = ctk.CTkButton(
            self.fel_tab,
            text="💿 Flashear a eMMC (via Loader)",
            command=self._fel_flash_emmc,
            fg_color="red", height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        
        self.fel_log_text = ctk.CTkTextbox(self.fel_tab, height=150, wrap="word")
        self.fel_progress = ctk.CTkProgressBar(self.fel_tab)
        self.fel_progress.set(0)
        self.fel_status_label = ctk.CTkLabel(
            self.fel_tab, text="Estado: Listo",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        
    def _create_errors_tab(self):
        """Pestaña de errores"""
        from gui.error_database_panel import ErrorDatabasePanel
        self.errors_tab = self.tab_view.add("🔧 Errores")
        self.errors_panel = ErrorDatabasePanel(self.errors_tab, self)
        
    def _create_history_tab(self):
        """Pestaña de historial"""
        from gui.session_history_panel import SessionHistoryPanel
        self.history_tab = self.tab_view.add("📜 Historial")
        self.history_panel = SessionHistoryPanel(self.history_tab, self)
        
    def _create_settings_tab(self):
        """Pestaña de configuración"""
        from gui.settings_panel import SettingsPanel
        self.settings_tab = self.tab_view.add("⚙️ Settings")
        self.settings_panel = SettingsPanel(self.settings_tab, self)
        
    def _create_right_panel(self):
        """Panel derecho con consola serial"""
        self.serial_console_section = ctk.CTkFrame(self.right_panel)
        self.serial_console_title = ctk.CTkLabel(
            self.serial_console_section,
            text="💬 Terminal Serial",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        
        self.serial_output = ctk.CTkTextbox(self.serial_console_section, wrap="word", height=280)
        self.serial_input = ctk.CTkEntry(self.serial_console_section)
        self.serial_input.bind("<Return>", self._send_serial_command)
        
        self.send_cmd_btn = ctk.CTkButton(
            self.serial_console_section, text="Enviar",
            command=lambda: self._send_serial_command(None), width=80
        )
        self.interrupt_boot_btn = ctk.CTkButton(
            self.serial_console_section, text="⏹️ Interrumpir Boot",
            command=self._interrupt_boot, fg_color="orange"
        )
        
        self.activity_section = ctk.CTkFrame(self.right_panel)
        self.activity_title = ctk.CTkLabel(
            self.activity_section,
            text="📜 Actividad",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.activity_log = ctk.CTkTextbox(self.activity_section, wrap="word", height=150)
        
        self.progress_section = ctk.CTkFrame(self.right_panel)
        self.progress_label = ctk.CTkLabel(self.progress_section, text="Listo")
        self.progress_bar = ctk.CTkProgressBar(self.progress_section)
        self.progress_bar.set(0)
        
    def _create_layout(self):
        """Organiza los widgets"""
        self.title_bar.pack(fill="x", padx=10, pady=(10, 5))
        self.logo_label.pack(side="left", padx=10)
        self.refresh_btn.pack(side="right", padx=10)
        self.status_label.pack(side="right", padx=5)
        self.status_indicator.pack(side="right", padx=5)
        
        self.left_panel.pack(side="left", fill="y", padx=(10, 5), pady=10)
        self.center_panel.pack(side="left", fill="both", expand=True, padx=5, pady=10)
        self.right_panel.pack(side="right", fill="y", padx=(5, 10), pady=10)
        
        self._layout_device_section()
        self._layout_serial_section()
        self._layout_tabs()
        self._layout_right_panel()
        
    def _layout_device_section(self):
        self.device_section.pack(fill="x", padx=10, pady=10)
        self.device_title.pack(pady=5)
        self.device_info_frame.pack(fill="x", padx=10, pady=5)
        
        for label in [self.soc_label, self.memory_label, self.emmc_label, self.fel_ver_label]:
            label.pack(anchor="w")
            
        self.connect_fel_btn.pack(fill="x", padx=10, pady=5)
        self.reload_usb_btn.pack(fill="x", padx=10, pady=(0, 10))
        
    def _layout_serial_section(self):
        self.serial_section.pack(fill="x", padx=10, pady=10)
        self.serial_title.pack(pady=5)
        self.serial_port_combo.pack(fill="x", padx=10, pady=5)
        self.serial_baud_combo.pack(fill="x", padx=10, pady=5)
        self.serial_connect_btn.pack(fill="x", padx=10, pady=(0, 10))
        
    def _layout_tabs(self):
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.bootlog_text.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        self.bootlog_scroll.pack(side="right", fill="y", padx=(0, 10), pady=10)
        
        btn_frame = ctk.CTkFrame(self.bootlog_tab)
        btn_frame.pack(pady=5)
        self.capture_bootlog_btn.pack(side="left", padx=5)
        self.clear_bootlog_btn.pack(side="left", padx=5)
        
        self._layout_ai_tab()
        self._layout_recovery_tab()
        self._layout_fel_tab()
        
    def _layout_ai_tab(self):
        self.ai_status_frame.pack(fill="x", padx=10, pady=10)
        self.ai_status.pack(pady=5)
        self.ai_provider_label.pack(pady=2)
        
        self.ai_config_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(self.ai_config_frame, text="Groq API Key:").pack(side="left", padx=5)
        self.ai_api_key_entry.pack(side="left", padx=5)
        self.ai_save_key_btn.pack(side="left", padx=5)
        
        self.ai_quick_help.pack(pady=5)
        self.ai_model_combo.pack(pady=5)
        
        ai_btn_frame = ctk.CTkFrame(self.ai_tab)
        ai_btn_frame.pack(pady=5)
        self.ai_ask_btn.pack(side="left", padx=5)
        self.analyze_bootlog_btn.pack(side="left", padx=5)
        self.ai_help_btn.pack(side="left", padx=5)
        
        self.ai_input.pack(fill="x", padx=10, pady=5)
        self.ai_output.pack(fill="both", expand=True, padx=10, pady=5)
        
    def _layout_recovery_tab(self):
        self.recovery_status_label.pack(pady=10)
        ctk.CTkLabel(self.recovery_tab, text="Log de recuperación:").pack()
        self.recovery_log.pack(fill="x", padx=10, pady=5)
        self.recovery_progress.pack(fill="x", padx=10, pady=5)
        
        rec_btn_frame = ctk.CTkFrame(self.recovery_tab)
        rec_btn_frame.pack(pady=10)
        self.start_recovery_btn.pack(side="left", padx=10)
        self.stop_recovery_btn.pack(side="left", padx=10)
        
    def _layout_fel_tab(self):
        fel_device_inner = ctk.CTkFrame(self.fel_tab)
        fel_device_inner.pack(fill="x", padx=10, pady=10)
        
        self.fel_device_label.pack(pady=5)
        self.fel_soc_label.pack(anchor="w", padx=10)
        self.fel_dram_label.pack(anchor="w", padx=10)
        self.fel_version_label.pack(anchor="w", padx=10)
        
        fel_btn_frame = ctk.CTkFrame(self.fel_device_frame)
        fel_btn_frame.pack(pady=10)
        self.fel_detect_btn.pack(side="left", padx=5)
        self.fel_reload_btn.pack(side="left", padx=5)
        
        fel_file_inner = ctk.CTkFrame(self.fel_tab)
        fel_file_inner.pack(fill="x", padx=10, pady=5)
        
        self.fel_firmware_label.pack(pady=5)
        self.fel_firmware_path.pack(pady=2)
        self.fel_select_fw_btn.pack(pady=2)
        
        fel_method_frame = ctk.CTkFrame(self.fel_tab)
        fel_method_frame.pack(pady=5)
        ctk.CTkLabel(fel_method_frame, text="Método:").pack(side="left", padx=5)
        self.fel_method_menu.pack(side="left", padx=5)
        
        self.fel_status_label.pack(pady=5)
        self.fel_progress.pack(fill="x", padx=10, pady=5)
        
        fel_action_frame = ctk.CTkFrame(self.fel_tab)
        fel_action_frame.pack(pady=10)
        self.fel_write_ram_btn.pack(side="left", padx=5)
        self.fel_flash_btn.pack(side="left", padx=5)
        
        ctk.CTkLabel(self.fel_tab, text="Log:").pack(pady=5)
        self.fel_log_text.pack(fill="both", expand=True, padx=10, pady=5)
        
    def _layout_right_panel(self):
        self.serial_console_section.pack(fill="x", padx=10, pady=10)
        self.serial_console_title.pack(pady=5)
        self.serial_output.pack(fill="x", padx=10, pady=5)
        self.serial_input.pack(fill="x", padx=10, pady=5)
        
        serial_btn_frame = ctk.CTkFrame(self.serial_console_section)
        serial_btn_frame.pack(pady=5)
        self.send_cmd_btn.pack(side="left", padx=5)
        self.interrupt_boot_btn.pack(side="left", padx=5)
        
        self.activity_section.pack(fill="x", padx=10, pady=10)
        self.activity_title.pack(pady=5)
        self.activity_log.pack(fill="x", padx=10, pady=5)
        
        self.progress_section.pack(fill="x", padx=10, pady=10)
        self.progress_label.pack(pady=5)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        
    def _check_services(self):
        self._log_activity("Verificando servicios...")
        
        if self.device_manager.check_fel_availability():
            self._log_activity("✓ sunxi-fel disponible")
        else:
            self._log_activity("✗ sunxi-fel no encontrado")
            
        ai_status = self.ai_assistant.bridge.get_status()
        provider = ai_status.get("current_provider", "none")
        
        if provider == "groq":
            self.ai_status.configure(text=f"🤖 IA: Groq (online)", text_color="green")
            self.ai_provider_label.configure(text=f"Provider: Groq - {self.ai_assistant.model}")
        elif provider == "opencode":
            self.ai_status.configure(text="🤖 IA: opencode", text_color="cyan")
        else:
            self.ai_status.configure(text="🤖 IA: Offline", text_color="orange")
            self.ai_provider_label.configure(text="Provider: Guías offline")
            
        ports = SerialConsole.list_usb_serial()
        if ports:
            self.serial_port_combo.configure(values=[p["device"] for p in ports])
            self._log_activity(f"✓ {len(ports)} puertos seriales")
        else:
            self._log_activity("⚠ No hay puertos seriales USB")
            
    def _log_activity(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.activity_log.insert("end", f"[{timestamp}] {message}\n")
        self.activity_log.see("end")
        
    def _refresh_devices(self):
        self._log_activity("Buscando dispositivos...")
        devices = self.device_manager.detect_devices()
        self._log_activity(f"Encontrados: {len(devices)} dispositivos")
        
    def _on_device_change(self, state: DeviceState, devices: list):
        if state == DeviceState.FEL_MODE:
            self.status_indicator.configure(text="🟢")
            self.status_label.configure(text="FEL Conectado")
            self.is_connected = True
            self._log_activity("✓ Dispositivo FEL detectado")
        else:
            self.status_indicator.configure(text="⚫")
            self.status_label.configure(text="Desconectado")
            self.is_connected = False
            
    def _connect_fel(self):
        if self.device_manager.get_device_info():
            self.is_connected = True
            self._log_activity("✓ Conexión FEL exitosa")
        else:
            messagebox.showerror("Error", "No se detectó dispositivo FEL")
            
    def _reload_usb(self):
        if self.device_manager.reload_usb_driver():
            self._log_activity("✓ Driver USB recargado")
            
    def _connect_serial(self):
        if self.serial_console.is_connected:
            self.serial_console.disconnect()
            self.serial_connect_btn.configure(text="Conectar Serial", fg_color="orange")
            return
            
        port = self.serial_port_combo.get()
        baudrate = int(self.serial_baud_combo.get())
        
        if self.serial_console.connect(port, baudrate):
            self.serial_console.start_reading()
            self.serial_connect_btn.configure(text="✓ Conectado", fg_color="gray")
            self._log_activity(f"✓ Serial: {port}")
        else:
            self._log_activity("✗ Error conectando serial")
            
    def _on_serial_data(self, data: str):
        self.serial_output.insert("end", data)
        self.serial_output.see("end")
        
    def _send_serial_command(self, event):
        if not self.serial_console.is_connected:
            return
        cmd = self.serial_input.get()
        self.serial_console.send(cmd + "\r\n")
        self.serial_input.delete(0, "end")
        
    def _interrupt_boot(self):
        if self.serial_console.interrupt_boot():
            self._log_activity("✓ Boot interrumpido")
        else:
            self._log_activity("⚠ No se pudo interrumpir")
            
    def _capture_bootlog(self):
        self._log_activity("Capturando bootlog (30s)...")
        self.bootlog_text.delete("1.0", "end")
        
        def capture():
            log = self.serial_console.capture_bootlog(duration=30.0)
            self.bootlog_text.insert("1.0", log)
            self._log_activity(f"Bootlog: {len(log)} caracteres")
        threading.Thread(target=capture, daemon=True).start()
        
    def _save_api_key(self):
        api_key = self.ai_api_key_entry.get().strip()
        if api_key:
            self.config.groq_api_key = api_key
            self.ai_assistant.set_api_key(api_key)
            self._check_services()
            
    def _ask_ai(self):
        question = self.ai_input.get("1.0", "end").strip()
        if not question:
            return
        self.ai_ask_btn.configure(state="disabled")
        self.ai_output.delete("1.0", "end")
        self.ai_output.insert("1.0", "Procesando...\n")
        
        def ask():
            response = self.ai_assistant.ask(question)
            def update():
                self.ai_output.delete("1.0", "end")
                self.ai_output.insert("1.0", response.message)
                self.ai_ask_btn.configure(state="normal")
            self.after(0, update)
        threading.Thread(target=ask, daemon=True).start()
        
    def _analyze_current_bootlog(self):
        bootlog = self.bootlog_text.get("1.0", "end").strip()
        if len(bootlog) < 50:
            messagebox.showwarning("Aviso", "No hay bootlog para analizar")
            return
        self.ai_input.delete("1.0", "end")
        self.ai_input.insert("1.0", f"Analiza este bootlog:\n\n{bootlog[:2000]}")
        self._ask_ai()
        
    def _show_offline_guides(self):
        guides = """
GUÍAS RÁPIDAS OFFLINE
=====================

1. DISPOSITIVO NO ENCIENDE → Verificar LED, cable poder
2. BOOT LOOP → Serial console + Auto Recovery
3. PANTALLA NEGRA → Probar HDMI, conectar serial
4. MODO FEL → Usar pestaña FEL Recovery
5. ERROR eMMC → Factory Reset desde recovery

Configura Groq API Key para IA avanzada.
        """
        self.ai_output.delete("1.0", "end")
        self.ai_output.insert("1.0", guides)
        
    def _start_auto_recovery(self):
        if self.auto_recovery_running:
            return
        if not self.serial_console.is_connected:
            messagebox.showwarning("Serial", "Conecta el serial primero")
            return
            
        port = self.serial_port_combo.get()
        self._log_activity("=== INICIANDO RECOVERY ===")
        self.auto_recovery_running = True
        self.start_recovery_btn.configure(state="disabled")
        self.stop_recovery_btn.configure(state="normal")
        
        self.auto_recovery = SerialAutoRecovery(self.serial_console)
        self.auto_recovery.on_log = lambda m: self._update_recovery_log(m)
        self.auto_recovery.on_progress = lambda s, p: self._update_recovery_progress(s, p)
        
        def run():
            success, msg = self.auto_recovery.full_auto_recovery(port)
            def finalize():
                self.auto_recovery_running = False
                self.start_recovery_btn.configure(state="normal")
                self.stop_recovery_btn.configure(state="disabled")
                if success:
                    messagebox.showinfo("Éxito", "¡Dispositivo recuperado!")
                else:
                    messagebox.showerror("Error", msg)
            self.after(0, finalize)
        threading.Thread(target=run, daemon=True).start()
        
    def _stop_auto_recovery(self):
        if self.auto_recovery:
            self.auto_recovery.cancel()
            
    def _update_recovery_log(self, message: str):
        def update():
            self.recovery_log.insert("end", f"{message}\n")
            self.recovery_log.see("end")
        self.after(0, update)
        
    def _update_recovery_progress(self, step: str, percent: int):
        def update():
            self.recovery_progress.set(percent / 100)
            self.recovery_status_label.configure(text=f"{step} ({percent}%)")
        self.after(0, update)
        
    def _fel_detect(self):
        self._fel_log("Detectando FEL...")
        fel = FELRecovery()
        fel.on_log = self._fel_log
        
        def detect():
            info = fel.detect_device()
            def update():
                if info:
                    self.fel_soc_label.configure(text=f"SOC: {info.soc_type}")
                    self.fel_dram_label.configure(text=f"DRAM: {hex(info.dram_base)}")
                else:
                    self.fel_soc_label.configure(text="SOC: No detectado")
            self.after(0, update)
        threading.Thread(target=detect, daemon=True).start()
        
    def _fel_reload_usb(self):
        fel = FELRecovery()
        if fel.reload_usb_driver():
            self._fel_log("✓ USB recargado")
            self._fel_detect()
            
    def _fel_select_firmware(self):
        filename = filedialog.askopenfilename(title="Firmware", filetypes=[("IMG", "*.img"), ("BIN", "*.bin"), ("Todos", "*.*")])
        if filename:
            self.current_firmware = filename
            name = os.path.basename(filename)
            size = os.path.getsize(filename) / (1024*1024)
            self.fel_firmware_path.configure(text=f"{name} ({size:.1f} MB)")
            
    def _fel_write_ram(self):
        if not self.current_firmware:
            messagebox.showwarning("Firmware", "Selecciona un firmware")
            return
        self._fel_log("Escribiendo a RAM...")
        
        fel = FELRecovery()
        fel.on_log = self._fel_log
        
        def write():
            success, msg = fel.full_fel_recovery(self.current_firmware, method=self.fel_method_var.get())
            def update():
                if success:
                    messagebox.showinfo("Éxito", "Firmware en RAM")
                else:
                    messagebox.showerror("Error", msg)
            self.after(0, update)
        threading.Thread(target=write, daemon=True).start()
        
    def _fel_flash_emmc(self):
        messagebox.showinfo("Info", "Carga loader y firmware a RAM primero, luego usa serial para flashear")
        
    def _fel_log(self, message: str):
        def update():
            self.fel_log_text.insert("end", f"{message}\n")
            self.fel_log_text.see("end")
        self.after(0, update)
        
    def _restore_ui_from_config(self):
        api_key = self.config.groq_api_key
        if api_key:
            self.ai_api_key_entry.insert(0, "*" * len(api_key))
        self.ai_model_combo.set(self.config.groq_model)
        
    def on_closing(self):
        self.device_manager.stop_monitoring()
        self.serial_console.disconnect()
        self.destroy()


def main():
    app = ARSMainWindow()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
