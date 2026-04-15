"""
Session History Panel - Panel de historial de sesiones para GUI
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
from datetime import datetime

from core.recovery_logger import RecoveryLogger, RecoveryReport
from core.data_exchange import ConfigExporter, ConfigImporter, BackupManager


class SessionHistoryPanel:
    """Panel de historial de sesiones de recovery"""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.logger = RecoveryLogger()
        self.report_gen = RecoveryReport(self.logger)
        self.exporter = ConfigExporter()
        self.importer = ConfigImporter()
        self.backup_mgr = BackupManager()
        
        self.selected_session = None
        self.sessions_list = []
        
        self._create_widgets()
        # No llamar _refresh_sessions aquí, se llama después de layout
        
    def _create_widgets(self):
        """Crea los widgets del panel"""
        
        title = ctk.CTkLabel(
            self.parent,
            text="📜 Historial de Sesiones",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(pady=10)
        
        # Barra de herramientas
        toolbar_frame = ctk.CTkFrame(self.parent)
        toolbar_frame.pack(fill="x", padx=10, pady=5)
        
        self.refresh_btn = ctk.CTkButton(
            toolbar_frame,
            text="🔄 Actualizar",
            command=self._refresh_sessions,
            width=100
        )
        self.refresh_btn.pack(side="left", padx=5)
        
        self.export_all_btn = ctk.CTkButton(
            toolbar_frame,
            text="📤 Exportar Todo",
            command=self._export_all,
            width=120
        )
        self.export_all_btn.pack(side="left", padx=5)
        
        self.backup_btn = ctk.CTkButton(
            toolbar_frame,
            text="💾 Backup",
            command=self._create_backup,
            width=100
        )
        self.backup_btn.pack(side="left", padx=5)
        
        self.restore_btn = ctk.CTkButton(
            toolbar_frame,
            text="📥 Restaurar",
            command=self._restore_backup,
            width=100
        )
        self.restore_btn.pack(side="left", padx=5)
        
        # Lista de sesiones
        list_frame = ctk.CTkFrame(self.parent)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.sessions_listbox = tk.Listbox(
            list_frame,
            bg="#1a1a1a",
            fg="white",
            selectbackground="#2196F3",
            selectforeground="white",
            font=("monospace", 10),
            height=10
        )
        self.sessions_listbox.pack(side="left", fill="both", expand=True)
        self.sessions_listbox.bind("<<ListboxSelect>>", self._on_session_select)
        
        scrollbar = ctk.CTkScrollbar(list_frame, command=self.sessions_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.sessions_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Detalles de sesión
        details_frame = ctk.CTkFrame(self.parent)
        details_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            details_frame,
            text="Detalles de Sesión",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=5)
        
        self.session_details = ctk.CTkTextbox(
            details_frame,
            height=150,
            wrap="word"
        )
        self.session_details.pack(fill="x", padx=5, pady=5)
        
        # Acciones de sesión
        actions_frame = ctk.CTkFrame(self.parent)
        actions_frame.pack(fill="x", padx=10, pady=5)
        
        self.view_report_btn = ctk.CTkButton(
            actions_frame,
            text="📋 Ver Reporte",
            command=self._view_report,
            width=130
        )
        self.view_report_btn.pack(side="left", padx=5)
        
        self.export_session_btn = ctk.CTkButton(
            actions_frame,
            text="📤 Exportar Sesión",
            command=self._export_session,
            width=130
        )
        self.export_session_btn.pack(side="left", padx=5)
        
        self.view_bootlog_btn = ctk.CTkButton(
            actions_frame,
            text="📄 Ver Bootlog",
            command=self._view_bootlog,
            width=130
        )
        self.view_bootlog_btn.pack(side="left", padx=5)
        
        # Estadísticas
        stats_frame = ctk.CTkFrame(self.parent)
        stats_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            stats_frame,
            text="📊 Estadísticas",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=5)
        
        self.stats_label = ctk.CTkLabel(
            stats_frame,
            text="Cargando...",
            text_color="gray",
            justify="left"
        )
        self.stats_label.pack(pady=5)
        
    def _refresh_sessions(self):
        """Actualiza la lista de sesiones"""
        self.app._log_activity("Actualizando historial...")
        
        def load():
            sessions = self.logger.get_all_sessions(limit=50)
            
            def update():
                self.sessions_listbox.delete(0, tk.END)
                self.sessions_list = sessions
                
                for session in sessions:
                    status_icon = "✓" if session.status == "success" else "✗" if session.status == "failed" else "⏳"
                    date = session.timestamp[:19] if session.timestamp else "N/A"
                    line = f"{status_icon} #{session.id} | {date} | {session.device_soc or 'N/A'} | {session.method or 'N/A'} | {session.status}"
                    self.sessions_listbox.insert(tk.END, line)
                    
                self._update_stats()
                self.app._log_activity(f"✓ {len(sessions)} sesiones cargadas")
            self.parent.after(0, update)
            
        threading.Thread(target=load, daemon=True).start()
        
    def _update_stats(self):
        """Actualiza las estadísticas"""
        stats = self.logger.get_statistics()
        
        text = f"""Total sesiones: {stats['total_sessions']}
Éxitos: {stats['successful']} | Fallidos: {stats['failed']}
Tasa de éxito: {stats['success_rate']:.1f}%
Duración promedio: {stats['average_duration_seconds']}s"""
        
        self.stats_label.configure(text=text)
        
    def _on_session_select(self, event):
        """Callback al seleccionar una sesión"""
        selection = self.sessions_listbox.curselection()
        if not selection:
            return
            
        idx = selection[0]
        self.selected_session = self.sessions_list[idx]
        
        self._show_session_details()
        
    def _show_session_details(self):
        """Muestra detalles de la sesión seleccionada"""
        if not self.selected_session:
            return
            
        session = self.selected_session
        
        details = f"""ID: #{session.id}
Fecha: {session.timestamp}
SOC: {session.device_soc or 'N/A'}
Estado: {session.device_state or 'N/A'}
Método: {session.method or 'N/A'}
Firmware: {session.firmware_used or 'N/A'}

Estado: {session.status.upper()}
Duración: {session.duration_seconds}s

Error: {session.error_message or 'Ninguno'}
Notas: {session.notes or 'Ninguna'}"""
        
        self.session_details.delete("1.0", "end")
        self.session_details.insert("1.0", details)
        
    def _view_report(self):
        """Muestra reporte de la sesión"""
        if not self.selected_session:
            messagebox.showwarning("Aviso", "Selecciona una sesión primero")
            return
            
        report = self.report_gen.generate_report(self.selected_session.id)
        
        report_window = ctk.CTkToplevel(self.app)
        report_window.title(f"Reporte - Sesión #{self.selected_session.id}")
        report_window.geometry("600x500")
        
        text = ctk.CTkTextbox(report_window, wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.insert("1.0", report)
        
    def _export_session(self):
        """Exporta la sesión seleccionada"""
        if not self.selected_session:
            messagebox.showwarning("Aviso", "Selecciona una sesión primero")
            return
            
        try:
            path = self.exporter.export_session_package(self.selected_session.id)
            messagebox.showinfo("Éxito", f"Sesión exportada a:\n{path}")
            self.app._log_activity(f"✓ Sesión exportada: {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            
    def _view_bootlog(self):
        """Muestra el bootlog de la sesión"""
        if not self.selected_session:
            messagebox.showwarning("Aviso", "Selecciona una sesión primero")
            return
            
        if not self.selected_session.bootlog_path:
            messagebox.showinfo("Info", "No hay bootlog guardado para esta sesión")
            return
            
        try:
            with open(self.selected_session.bootlog_path, 'r') as f:
                content = f.read()
                
            bootlog_window = ctk.CTkToplevel(self.app)
            bootlog_window.title(f"Bootlog - Sesión #{self.selected_session.id}")
            bootlog_window.geometry("800x600")
            
            text = ctk.CTkTextbox(bootlog_window, wrap="word")
            text.pack(fill="both", expand=True, padx=10, pady=10)
            text.insert("1.0", content)
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir bootlog:\n{str(e)}")
            
    def _export_all(self):
        """Exporta todas las configuraciones"""
        try:
            path = self.exporter.export_config(include_history=True)
            messagebox.showinfo("Éxito", f"Configuración exportada a:\n{path}")
            self.app._log_activity(f"✓ Config exportada: {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            
    def _create_backup(self):
        """Crea un backup"""
        try:
            path = self.backup_mgr.create_backup()
            messagebox.showinfo("Éxito", f"Backup creado:\n{path}")
            self.app._log_activity(f"✓ Backup creado: {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            
    def _restore_backup(self):
        """Restaura un backup"""
        from tkinter import filedialog
        
        path = filedialog.askopenfilename(
            title="Seleccionar Backup",
            filetypes=[("ZIP", "*.zip"), ("Todos", "*.*")]
        )
        
        if not path:
            return
            
        confirm = messagebox.askyesno(
            "Confirmar",
            "¿Remplazar configuración actual con este backup?"
        )
        
        if confirm:
            try:
                self.backup_mgr.restore_backup(path)
                messagebox.showinfo("Éxito", "Backup restaurado")
                self.app._log_activity("✓ Backup restaurado")
                self._refresh_sessions()
            except Exception as e:
                messagebox.showerror("Error", str(e))
