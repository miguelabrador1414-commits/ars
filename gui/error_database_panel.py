"""
Error Database Panel - Panel de base de datos de errores para GUI
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from db.error_database import ErrorDatabase, ErrorMatcher, ErrorCategory


class ErrorDatabasePanel:
    """Panel de base de datos de errores"""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.db = ErrorDatabase()
        self.matcher = ErrorMatcher()
        
        self.selected_error = None
        self.all_errors = []
        
        self._create_widgets()
        self._load_errors()
        
    def _create_widgets(self):
        """Crea los widgets del panel"""
        
        title = ctk.CTkLabel(
            self.parent,
            text="🔧 Base de Datos de Errores",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(pady=10)
        
        # Buscador
        search_frame = ctk.CTkFrame(self.parent)
        search_frame.pack(fill="x", padx=10, pady=5)
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Buscar error...",
            width=300
        )
        self.search_entry.pack(side="left", padx=5, pady=10)
        self.search_entry.bind("<KeyRelease>", lambda e: self._search_errors())
        
        self.search_btn = ctk.CTkButton(
            search_frame,
            text="🔍 Buscar",
            command=self._search_errors,
            width=100
        )
        self.search_btn.pack(side="left", padx=5)
        
        self.clear_search_btn = ctk.CTkButton(
            search_frame,
            text="✕ Limpiar",
            command=self._clear_search,
            width=80
        )
        self.clear_search_btn.pack(side="left", padx=5)
        
        # Filtros
        filter_frame = ctk.CTkFrame(self.parent)
        filter_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(filter_frame, text="Filtrar por:").pack(side="left", padx=5)
        
        self.soc_filter = ctk.CTkOptionMenu(
            filter_frame,
            values=["Todos los SOCs"] + self.db.get_all_socs(),
            command=lambda x: self._apply_filters(),
            width=130
        )
        self.soc_filter.pack(side="left", padx=5)
        
        self.category_filter = ctk.CTkOptionMenu(
            filter_frame,
            values=["Todas las categorías"] + self.db.get_all_categories(),
            command=lambda x: self._apply_filters(),
            width=150
        )
        self.category_filter.pack(side="left", padx=5)
        
        self.severity_filter = ctk.CTkOptionMenu(
            filter_frame,
            values=["Todas", "critical", "warning", "info"],
            command=lambda x: self._apply_filters(),
            width=100
        )
        self.severity_filter.pack(side="left", padx=5)
        
        # Lista de errores
        list_frame = ctk.CTkFrame(self.parent)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.errors_listbox = tk.Listbox(
            list_frame,
            bg="#1a1a1a",
            fg="white",
            selectbackground="#2196F3",
            selectforeground="white",
            font=("monospace", 10),
            height=8
        )
        self.errors_listbox.pack(side="left", fill="both", expand=True)
        self.errors_listbox.bind("<<ListboxSelect>>", self._on_error_select)
        
        scrollbar = ctk.CTkScrollbar(list_frame, command=self.errors_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.errors_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Detalles del error
        details_frame = ctk.CTkFrame(self.parent)
        details_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            details_frame,
            text="Detalles del Error",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=5)
        
        self.error_details = ctk.CTkTextbox(
            details_frame,
            height=180,
            wrap="word"
        )
        self.error_details.pack(fill="x", padx=5, pady=5)
        
        # Acciones
        actions_frame = ctk.CTkFrame(self.parent)
        actions_frame.pack(fill="x", padx=10, pady=5)
        
        self.copy_solution_btn = ctk.CTkButton(
            actions_frame,
            text="📋 Copiar Solución",
            command=self._copy_solution,
            width=130
        )
        self.copy_solution_btn.pack(side="left", padx=5)
        
        self.apply_solution_btn = ctk.CTkButton(
            actions_frame,
            text="✅ Aplicar a Recovery",
            command=self._apply_to_recovery,
            width=140
        )
        self.apply_solution_btn.pack(side="left", padx=5)
        
        self.ask_ai_btn = ctk.CTkButton(
            actions_frame,
            text="🤖 Consultar IA",
            command=self._ask_ai_about_error,
            width=120
        )
        self.ask_ai_btn.pack(side="left", padx=5)
        
        # Sección de diagnóstico
        diag_frame = ctk.CTkFrame(self.parent)
        diag_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            diag_frame,
            text="🔍 Diagnosticar Bootlog",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=5)
        
        ctk.CTkLabel(
            diag_frame,
            text="Pega un bootlog para detectar errores automáticamente:",
            text_color="gray"
        ).pack(pady=5)
        
        self.bootlog_input = ctk.CTkTextbox(
            diag_frame,
            height=80,
            wrap="word"
        )
        self.bootlog_input.pack(fill="x", padx=5, pady=5)
        
        self.diagnose_btn = ctk.CTkButton(
            diag_frame,
            text="🔍 Diagnosticar",
            command=self._diagnose_bootlog,
            fg_color="orange"
        )
        self.diagnose_btn.pack(pady=10)
        
    def _load_errors(self):
        """Carga la lista de errores"""
        self.all_errors = self.db.errors
        self._display_errors(self.all_errors)
        
    def _display_errors(self, errors):
        """Muestra la lista de errores"""
        self.errors_listbox.delete(0, tk.END)
        
        severity_colors = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🟢"
        }
        
        for error in errors:
            icon = severity_colors.get(error.severity, "⚪")
            soc = ", ".join(error.soc_models[:2])
            if len(error.soc_models) > 2:
                soc += f"+{len(error.soc_models)-2}"
            line = f"{icon} [{error.category.value}] {error.title} ({soc})"
            self.errors_listbox.insert(tk.END, line)
            
    def _search_errors(self):
        """Busca errores"""
        query = self.search_entry.get().strip()
        
        if not query:
            self._load_errors()
            return
            
        results = self.db.search(query)
        self._display_errors(results)
        
    def _clear_search(self):
        """Limpia la búsqueda"""
        self.search_entry.delete(0, "end")
        self._load_errors()
        
    def _apply_filters(self):
        """Aplica filtros"""
        filtered = self.all_errors
        
        soc = self.soc_filter.get()
        if soc and soc != "Todos los SOCs":
            filtered = [e for e in filtered if soc in e.soc_models]
            
        category = self.category_filter.get()
        if category and category != "Todas las categorías":
            filtered = [e for e in filtered if e.category.value == category]
            
        severity = self.severity_filter.get()
        if severity and severity != "Todas":
            filtered = [e for e in filtered if e.severity == severity]
            
        self._display_errors(filtered)
        
    def _on_error_select(self, event):
        """Callback al seleccionar un error"""
        selection = self.errors_listbox.curselection()
        if not selection:
            return
            
        idx = selection[0]
        errors = self.errors_listbox.get(0, tk.END)
        
        for error in self.all_errors:
            if error.title in errors[idx]:
                self.selected_error = error
                break
                
        self._show_error_details()
        
    def _show_error_details(self):
        """Muestra detalles del error"""
        if not self.selected_error:
            return
            
        error = self.selected_error
        verified = "✓" if error.verified else "⚠"
        
        details = f"""╔══════════════════════════════════════════════════╗
║ {error.title} {verified}
╠══════════════════════════════════════════════════╣
║ Categoría: {error.category.value}
║ Severidad: {error.severity.upper()}
║ SOCs: {', '.join(error.soc_models)}
║ Verificado: {'Sí' if error.verified else 'No'}
╠══════════════════════════════════════════════════╣
║ DESCRIPCIÓN:
{error.description}
╠══════════════════════════════════════════════════╣
║ CAUSA PROBABLE:
{error.cause}
╠══════════════════════════════════════════════════╣
║ SOLUCIÓN:
{error.solution}
╠══════════════════════════════════════════════════╣
║ COMANDOS:
"""
        
        for cmd in error.commands:
            details += f"  • {cmd}\n"
            
        self.error_details.delete("1.0", "end")
        self.error_details.insert("1.0", details)
        
    def _copy_solution(self):
        """Copia la solución al portapapeles"""
        if not self.selected_error:
            messagebox.showwarning("Aviso", "Selecciona un error primero")
            return
            
        solution = f"{self.selected_error.title}\n\n"
        solution += f"{self.selected_error.solution}\n\n"
        solution += "Comandos:\n" + "\n".join(f"• {c}" for c in self.selected_error.commands)
        
        self.parent.clipboard_clear()
        self.parent.clipboard_append(solution)
        messagebox.showinfo("Copiado", "Solución copiada al portapapeles")
        self.app._log_activity(f"✓ Solución copiada: {self.selected_error.title}")
        
    def _apply_to_recovery(self):
        """Muestra cómo aplicar la solución"""
        if not self.selected_error:
            messagebox.showwarning("Aviso", "Selecciona un error primero")
            return
            
        messagebox.showinfo(
            "Aplicar Solución",
            f"Para aplicar la solución de '{self.selected_error.title}':\n\n"
            f"{self.selected_error.solution[:500]}\n\n"
            "Sigue los pasos en el panel de Auto Recovery."
        )
        
    def _ask_ai_about_error(self):
        """Consulta a la IA sobre el error"""
        if not self.selected_error:
            messagebox.showwarning("Aviso", "Selecciona un error primero")
            return
            
        query = f"Tengo el error '{self.selected_error.title}' en un Allwinner. "
        query += f"{self.selected_error.description}\n\n"
        query += "¿Qué más me recomiendas hacer?"
        
        self.app.ai_input.delete("1.0", "end")
        self.app.ai_input.insert("1.0", query)
        
        messagebox.showinfo(
            "IA",
            "La pregunta ha sido añadida al asistente de IA.\n"
            "Cambia a la pestaña de IA para ver la respuesta."
        )
        
    def _diagnose_bootlog(self):
        """Diagnostica un bootlog"""
        bootlog = self.bootlog_input.get("1.0", "end").strip()
        
        if not bootlog or len(bootlog) < 50:
            messagebox.showwarning("Aviso", "Ingresa un bootlog válido")
            return
            
        self.app._log_activity("Diagnosticando bootlog...")
        
        results = self.matcher.match(bootlog)
        
        if results["errors_found"] > 0:
            msg = f"Se detectaron {results['errors_found']} errores:\n\n"
            for error in results["errors"][:3]:
                msg += f"• {error['title']}\n"
                msg += f"  {error['solution'][:100]}...\n\n"
        else:
            msg = "No se detectaron errores conocidos.\n"
            msg += "El bootlog parece normal o el error no está en la base de datos."
            
        messagebox.showinfo("Resultado del Diagnóstico", msg)
        self.app._log_activity(f"✓ Diagnóstico: {results['errors_found']} errores")
