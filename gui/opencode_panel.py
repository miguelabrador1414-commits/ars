"""
OpenCode Panel - Panel de integración con opencode para GUI
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import subprocess
import threading
import os
from datetime import datetime

from integrations.opencode_bridge import OpenCodeBridge, OpenCodeIntegration


class OpenCodePanel:
    """Panel de integración con opencode"""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.bridge = OpenCodeBridge()
        self.integration = OpenCodeIntegration()
        
        self._create_widgets()
        self._check_availability()
        
    def _create_widgets(self):
        """Crea los widgets del panel"""
        
        title = ctk.CTkLabel(
            self.parent,
            text="🔗 Integración OpenCode",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(pady=10)
        
        # Estado de conexión
        status_frame = ctk.CTkFrame(self.parent)
        status_frame.pack(fill="x", padx=10, pady=5)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Estado: Verificando...",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.status_label.pack(pady=10)
        
        self.check_btn = ctk.CTkButton(
            status_frame,
            text="🔄 Verificar Conexión",
            command=self._check_availability,
            width=150
        )
        self.check_btn.pack(pady=5)
        
        # Diagnóstico automático
        diag_auto_frame = ctk.CTkFrame(self.parent)
        diag_auto_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            diag_auto_frame,
            text="🔍 Diagnóstico Automático con OpenCode",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=5)
        
        self.diagnose_btn = ctk.CTkButton(
            diag_auto_frame,
            text="🤖 Analizar Bootlog con OpenCode",
            command=self._diagnose_with_opencode,
            fg_color="cyan",
            height=40
        )
        self.diagnose_btn.pack(pady=10)
        
        # Bootlog input
        bootlog_frame = ctk.CTkFrame(self.parent)
        bootlog_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(
            bootlog_frame,
            text="Bootlog para análisis (pega desde pestaña Bootlog):",
            text_color="gray"
        ).pack(anchor="w", pady=5)
        
        self.bootlog_input = ctk.CTkTextbox(bootlog_frame, wrap="word")
        self.bootlog_input.pack(fill="both", expand=True, pady=5)
        
        self.paste_bootlog_btn = ctk.CTkButton(
            bootlog_frame,
            text="📋 Pegar Bootlog desde Pestaña",
            command=self._paste_bootlog,
            width=200
        )
        self.paste_bootlog_btn.pack(pady=5)
        
        # Generar reporte
        report_frame = ctk.CTkFrame(self.parent)
        report_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            report_frame,
            text="📋 Generar Reporte de Diagnóstico",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=5)
        
        ctk.CTkLabel(
            report_frame,
            text="Genera un reporte estructurado para consultar manualmente:",
            text_color="gray"
        ).pack(pady=5)
        
        self.generate_report_btn = ctk.CTkButton(
            report_frame,
            text="📄 Generar Reporte JSON",
            command=self._generate_report,
            width=200
        )
        self.generate_report_btn.pack(pady=5)
        
        self.export_prompt_btn = ctk.CTkButton(
            report_frame,
            text="📝 Exportar Prompt para OpenCode",
            command=self._export_prompt,
            width=200
        )
        self.export_prompt_btn.pack(pady=5)
        
        # Crear script
        script_frame = ctk.CTkFrame(self.parent)
        script_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            script_frame,
            text="🛠️ Herramientas",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=5)
        
        self.create_script_btn = ctk.CTkButton(
            script_frame,
            text="📜 Crear Script de Diagnóstico",
            command=self._create_diagnostic_script,
            width=200
        )
        self.create_script_btn.pack(pady=5)
        
        # Estado de sesiones
        sessions_frame = ctk.CTkFrame(self.parent)
        sessions_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            sessions_frame,
            text="💬 Historial de Consultas",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=5)
        
        self.conversation_text = ctk.CTkTextbox(
            sessions_frame,
            height=120,
            wrap="word"
        )
        self.conversation_text.pack(fill="x", pady=5)
        
        self.clear_history_btn = ctk.CTkButton(
            sessions_frame,
            text="🗑️ Limpiar Historial",
            command=self._clear_history,
            width=150
        )
        self.clear_history_btn.pack(pady=5)
        
    def _check_availability(self):
        """Verifica disponibilidad de opencode"""
        self.status_label.configure(text="Verificando...")
        
        def check():
            is_available = self.bridge.is_available()
            
            def update():
                if is_available:
                    self.status_label.configure(
                        text="✓ OpenCode: Disponible",
                        text_color="green"
                    )
                    self.diagnose_btn.configure(state="normal")
                else:
                    self.status_label.configure(
                        text="⚠ OpenCode: No disponible\nUsa Groq o guías offline",
                        text_color="orange"
                    )
                    self.diagnose_btn.configure(state="disabled")
            self.parent.after(0, update)
        threading.Thread(target=check, daemon=True).start()
        
    def _paste_bootlog(self):
        """Pega el bootlog desde la pestaña principal"""
        try:
            bootlog = self.app.bootlog_text.get("1.0", "end").strip()
            if bootlog:
                self.bootlog_input.delete("1.0", "end")
                self.bootlog_input.insert("1.0", bootlog)
                self.app._log_activity("✓ Bootlog pegado para análisis")
            else:
                messagebox.showwarning("Aviso", "No hay bootlog en la pestaña")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            
    def _diagnose_with_opencode(self):
        """Realiza diagnóstico usando opencode"""
        bootlog = self.bootlog_input.get("1.0", "end").strip()
        
        if len(bootlog) < 50:
            messagebox.showwarning("Aviso", "Ingresa un bootlog válido para analizar")
            return
            
        self.app._log_activity("Iniciando diagnóstico con OpenCode...")
        self.diagnose_btn.configure(state="disabled", text="Procesando...")
        
        device_info = {}
        try:
            info = self.app.device_manager.get_device_info()
            if info:
                device_info = {
                    "soc_type": info.soc_type,
                    "fel_version": info.fel_version,
                    "dram_size": info.dram_size
                }
        except:
            pass
            
        def diagnose():
            report = self.integration.get_consultation_prompt(
                diagnosis={"status": "pending", "issues": [], "confidence": 0.5},
                device_info=device_info,
                bootlog=bootlog
            )
            
            success, response = self.bridge.execute_query(
                "Diagnostica este problema de Allwinner:",
                context=report
            )
            
            def update():
                self.diagnose_btn.configure(state="normal", text="Analizar con OpenCode")
                
                if success:
                    self.conversation_text.insert("end", f"\n[{datetime.now().strftime('%H:%M:%S')}]\n")
                    self.conversation_text.insert("end", response)
                    self.conversation_text.see("end")
                    self.app._log_activity("✓ Diagnóstico completado")
                else:
                    self.conversation_text.insert("end", f"\nError: {response}\n")
                    self.app._log_activity(f"✗ Error: {response}")
            self.parent.after(0, update)
        threading.Thread(target=diagnose, daemon=True).start()
        
    def _generate_report(self):
        """Genera reporte de diagnóstico"""
        bootlog = self.bootlog_input.get("1.0", "end").strip()
        
        device_info = {}
        try:
            info = self.app.device_manager.get_device_info()
            if info:
                device_info = {"soc": info.soc_type}
        except:
            pass
            
        report = self.bridge.generate_diagnostic_report(
            bootlog=bootlog,
            device_info=device_info,
            error_state="pending_diagnosis"
        )
        
        output_path = filedialog.asksaveasfilename(
            title="Guardar Reporte",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")]
        )
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            messagebox.showinfo("Éxito", f"Reporte guardado:\n{output_path}")
            self.app._log_activity(f"✓ Reporte guardado: {output_path}")
            
    def _export_prompt(self):
        """Exporta prompt listo para opencode"""
        bootlog = self.bootlog_input.get("1.0", "end").strip()
        
        if len(bootlog) < 50:
            messagebox.showwarning("Aviso", "Ingresa un bootlog primero")
            return
            
        prompt = self.integration.generate_consultation_prompt(
            scenario="Diagnóstico de TV Box Allwinner",
            bootlog=bootlog,
            device_info={}
        )
        
        output_path = filedialog.asksaveasfilename(
            title="Guardar Prompt",
            defaultextension=".txt",
            filetypes=[("TXT", "*.txt"), ("Todos", "*.*")]
        )
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(prompt)
            messagebox.showinfo(
                "Éxito",
                f"Prompt guardado:\n{output_path}\n\n"
                "Copia el contenido y pégalo en una conversación con opencode."
            )
            self.app._log_activity(f"✓ Prompt exportado: {output_path}")
            
    def _create_diagnostic_script(self):
        """Crea script de diagnóstico"""
        bootlog = self.bootlog_input.get("1.0", "end").strip()
        
        device_info = {}
        try:
            info = self.app.device_manager.get_device_info()
            if info:
                device_info = {"soc": info.soc_type, "version": info.fel_version}
        except:
            pass
            
        script_path = self.bridge.create_opencode_script(
            device_info=device_info,
            bootlog=bootlog,
            recovery_log=""
        )
        
        messagebox.showinfo(
            "Script Creado",
            f"Script guardado en:\n{script_path}\n\n"
            "Ejecútalo con: bash {script_path}"
        )
        self.app._log_activity(f"✓ Script de diagnóstico creado")
        
    def _clear_history(self):
        """Limpia el historial de conversación"""
        self.bridge.clear_history()
        self.conversation_text.delete("1.0", "end")
        self.app._log_activity("Historial de consultas limpiado")
