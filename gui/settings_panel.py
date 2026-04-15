"""
Settings Panel - Panel de configuración para GUI
"""

import customtkinter as ctk
from tkinter import messagebox
import subprocess

from core.config import get_config


class SettingsPanel:
    """Panel de configuración de ARS"""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.config = get_config()
        
        self._create_widgets()
        self._load_settings()
        
    def _create_widgets(self):
        """Crea los widgets del panel"""
        
        # Scrollable frame
        scroll_frame = ctk.CTkScrollableFrame(self.parent)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        title = ctk.CTkLabel(
            scroll_frame,
            text="⚙️ Configuración",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(pady=10)
        
        # Sección IA
        ai_frame = ctk.CTkFrame(scroll_frame)
        ai_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            ai_frame,
            text="🤖 Configuración de IA",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=10, padx=10, anchor="w")
        
        ctk.CTkLabel(ai_frame, text="API Key de Groq:").pack(pady=(5, 0), padx=10, anchor="w")
        
        api_key_frame = ctk.CTkFrame(ai_frame)
        api_key_frame.pack(fill="x", padx=10, pady=5)
        
        self.api_key_entry = ctk.CTkEntry(
            api_key_frame,
            show="*",
            width=300
        )
        self.api_key_entry.pack(side="left", fill="x", expand=True)
        
        self.show_key_btn = ctk.CTkButton(
            api_key_frame,
            text="👁",
            command=self._toggle_api_key,
            width=40
        )
        self.show_key_btn.pack(side="left", padx=5)
        
        ctk.CTkButton(
            ai_frame,
            text="💾 Guardar API Key",
            command=self._save_api_key,
            width=150
        ).pack(pady=5, padx=10, anchor="w")
        
        ctk.CTkLabel(
            ai_frame,
            text="💡 Obtén tu API key gratis en: console.groq.com",
            text_color="gray"
        ).pack(pady=5, padx=10, anchor="w")
        
        ctk.CTkLabel(ai_frame, text="Modelo:").pack(pady=(10, 0), padx=10, anchor="w")
        
        self.model_combo = ctk.CTkOptionMenu(
            ai_frame,
            values=["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
            width=250
        )
        self.model_combo.pack(pady=5, padx=10, anchor="w")
        
        # Sección Serial
        serial_frame = ctk.CTkFrame(scroll_frame)
        serial_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            serial_frame,
            text="📡 Configuración Serial",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=10, padx=10, anchor="w")
        
        ctk.CTkLabel(serial_frame, text="Baudrate por defecto:").pack(pady=(5, 0), padx=10, anchor="w")
        
        self.baudrate_combo = ctk.CTkOptionMenu(
            serial_frame,
            values=["115200", "57600", "38400", "19200", "9600"],
            width=150
        )
        self.baudrate_combo.pack(pady=5, padx=10, anchor="w")
        
        # Sección FEL
        fel_frame = ctk.CTkFrame(scroll_frame)
        fel_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            fel_frame,
            text="⚡ Configuración FEL",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=10, padx=10, anchor="w")
        
        ctk.CTkLabel(fel_frame, text="Método de escritura:").pack(pady=(5, 0), padx=10, anchor="w")
        
        self.fel_method_combo = ctk.CTkOptionMenu(
            fel_frame,
            values=["pipe", "chunk"],
            width=150
        )
        self.fel_method_combo.pack(pady=5, padx=10, anchor="w")
        
        ctk.CTkLabel(fel_frame, text="Tamaño de chunk (MB):").pack(pady=(5, 0), padx=10, anchor="w")
        
        self.chunk_size_entry = ctk.CTkEntry(
            fel_frame,
            width=150
        )
        self.chunk_size_entry.pack(pady=5, padx=10, anchor="w")
        
        # Sección Recovery
        recovery_frame = ctk.CTkFrame(scroll_frame)
        recovery_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            recovery_frame,
            text="🔧 Configuración de Recovery",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=10, padx=10, anchor="w")
        
        self.auto_interrupt_var = ctk.BooleanVar()
        self.auto_interrupt_check = ctk.CTkCheckBox(
            recovery_frame,
            text="Interrumpir boot automáticamente",
            variable=self.auto_interrupt_var
        )
        self.auto_interrupt_check.pack(pady=5, padx=10, anchor="w")
        
        ctk.CTkLabel(recovery_frame, text="Timeout de boot (segundos):").pack(pady=(5, 0), padx=10, anchor="w")
        
        self.boot_timeout_entry = ctk.CTkEntry(
            recovery_frame,
            width=150
        )
        self.boot_timeout_entry.pack(pady=5, padx=10, anchor="w")
        
        # Sección UI
        ui_frame = ctk.CTkFrame(scroll_frame)
        ui_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            ui_frame,
            text="🎨 Configuración de UI",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=10, padx=10, anchor="w")
        
        self.theme_var = ctk.StringVar(value="dark")
        theme_frame = ctk.CTkFrame(ui_frame)
        theme_frame.pack(pady=5, padx=10, anchor="w")
        
        ctk.CTkRadioButton(
            theme_frame,
            text="Oscuro",
            variable=self.theme_var,
            value="dark",
            command=self._change_theme
        ).pack(side="left", padx=10)
        
        ctk.CTkRadioButton(
            theme_frame,
            text="Claro",
            variable=self.theme_var,
            value="light",
            command=self._change_theme
        ).pack(side="left", padx=10)
        
        # Botones de guardar
        save_frame = ctk.CTkFrame(scroll_frame)
        save_frame.pack(fill="x", pady=20)
        
        ctk.CTkButton(
            save_frame,
            text="💾 Guardar Configuración",
            command=self._save_all_settings,
            fg_color="green",
            height=40
        ).pack(pady=5, padx=10)
        
        ctk.CTkButton(
            save_frame,
            text="🔄 Restaurar Valores Predeterminados",
            command=self._reset_settings,
            fg_color="gray"
        ).pack(pady=5, padx=10)
        
        # Info del sistema
        info_frame = ctk.CTkFrame(scroll_frame)
        info_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            info_frame,
            text="ℹ️ Información del Sistema",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=10, padx=10, anchor="w")
        
        self.sysinfo_label = ctk.CTkLabel(
            info_frame,
            text="",
            text_color="gray",
            justify="left"
        )
        self.sysinfo_label.pack(pady=5, padx=10, anchor="w")
        
        ctk.CTkButton(
            info_frame,
            text="🔍 Verificar Herramientas",
            command=self._check_tools
        ).pack(pady=10, padx=10, anchor="w")
        
    def _load_settings(self):
        """Carga la configuración actual"""
        api_key = self.config.groq_api_key
        if api_key:
            self.api_key_entry.insert(0, "*" * len(api_key))
            
        self.model_combo.set(self.config.groq_model)
        self.baudrate_combo.set(str(self.config.get("serial.default_baudrate", 115200)))
        self.fel_method_combo.set(self.config.get("fel.write_method", "pipe"))
        self.chunk_size_entry.insert(0, str(self.config.get("fel.chunk_size_mb", 4)))
        self.auto_interrupt_var.set(self.config.get("recovery.auto_interrupt_boot", True))
        self.boot_timeout_entry.insert(0, str(self.config.get("recovery.boot_timeout_seconds", 30)))
        self.theme_var.set(self.config.get("ui.theme", "dark"))
        
        self._update_sysinfo()
        
    def _toggle_api_key(self):
        """Muestra/oculta la API key"""
        current = self.api_key_entry.get()
        if current and current[0] == "*":
            self.api_key_entry.delete(0, "end")
            self.api_key_entry.insert(0, self.config.groq_api_key or "")
        else:
            self.api_key_entry.delete(0, "end")
            if self.config.groq_api_key:
                self.api_key_entry.insert(0, "*" * len(self.config.groq_api_key))
                
    def _save_api_key(self):
        """Guarda la API key"""
        raw_input = self.api_key_entry.get()
        api_key = raw_input if not raw_input.startswith("*") else self.config.groq_api_key
        
        if api_key:
            self.config.groq_api_key = api_key
            self.app.ai_assistant.set_api_key(api_key)
            messagebox.showinfo("Éxito", "API Key guardada correctamente")
            self.app._log_activity("✓ API Key de Groq guardada")
        else:
            messagebox.showwarning("Aviso", "Ingresa una API Key válida")
            
    def _save_all_settings(self):
        """Guarda toda la configuración"""
        self.config.set("ai.model", self.model_combo.get())
        self.config.set("serial.default_baudrate", int(self.baudrate_combo.get()))
        self.config.set("fel.write_method", self.fel_method_combo.get())
        self.config.set("fel.chunk_size_mb", int(self.chunk_size_entry.get()))
        self.config.set("recovery.auto_interrupt_boot", self.auto_interrupt_var.get())
        self.config.set("recovery.boot_timeout_seconds", int(self.boot_timeout_entry.get()))
        self.config.set("ui.theme", self.theme_var.get())
        
        self.config.save()
        
        messagebox.showinfo("Éxito", "Configuración guardada")
        self.app._log_activity("✓ Configuración guardada")
        
    def _reset_settings(self):
        """Restaura valores predeterminados"""
        confirm = messagebox.askyesno(
            "Confirmar",
            "¿Restaurar valores predeterminados?\n\nEsto no eliminará el historial."
        )
        
        if confirm:
            from core.config import ARSConfig
            default_config = ARSConfig.DEFAULT_CONFIG
            
            self.model_combo.set("llama-3.3-70b-versatile")
            self.baudrate_combo.set("115200")
            self.fel_method_combo.set("pipe")
            self.chunk_size_entry.delete(0, "end")
            self.chunk_size_entry.insert(0, "4")
            self.auto_interrupt_var.set(True)
            self.boot_timeout_entry.delete(0, "end")
            self.boot_timeout_entry.insert(0, "30")
            self.theme_var.set("dark")
            
            messagebox.showinfo("Info", "Valores restaurados. Guarda para aplicar.")
            
    def _change_theme(self):
        """Cambia el tema de la aplicación"""
        theme = self.theme_var.get()
        ctk.set_appearance_mode(theme)
        
    def _update_sysinfo(self):
        """Actualiza información del sistema"""
        info_lines = []
        
        info_lines.append(f"ARS Version: 1.2.0")
        
        try:
            result = subprocess.run(
                ["sunxi-fel", "ver"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                info_lines.append(f"sunxi-fel: ✓ Instalado")
            else:
                info_lines.append(f"sunxi-fel: ✗ No disponible")
        except:
            info_lines.append(f"sunxi-fel: ✗ No encontrado")
            
        try:
            result = subprocess.run(
                ["which", "binwalk"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                info_lines.append(f"binwalk: ✓ Instalado")
            else:
                info_lines.append(f"binwalk: ✗ No disponible")
        except:
            info_lines.append(f"binwalk: ✗ No encontrado")
            
        info_lines.append(f"Config: {self.config.CONFIG_FILE}")
        
        self.sysinfo_label.configure(text="\n".join(info_lines))
        
    def _check_tools(self):
        """Verifica herramientas del sistema"""
        self.app._log_activity("Verificando herramientas...")
        
        tools = [
            ("sunxi-fel", "FEL Protocol"),
            ("binwalk", "Firmware Analysis"),
            ("python3", "Python Runtime")
        ]
        
        results = []
        for tool, desc in tools:
            try:
                result = subprocess.run(
                    ["which", tool],
                    capture_output=True,
                    text=True
                )
                status = "✓" if result.returncode == 0 else "✗"
                results.append(f"{status} {tool} - {desc}")
            except:
                results.append(f"✗ {tool} - {desc}")
                
        messagebox.showinfo("Herramientas del Sistema", "\n".join(results))
        self._update_sysinfo()
