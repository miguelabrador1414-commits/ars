"""
Firmware Tools Panel - Panel de herramientas de firmware para GUI
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import os
from typing import Optional
import subprocess

from utils.firmware_tools import (
    FirmwareAnalyzer, 
    FirmwareExtractor, 
    FirmwareComparator,
    FirmwareValidator
)


class FirmwareToolsPanel:
    """Panel de herramientas de firmware"""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.analyzer = FirmwareAnalyzer()
        self.extractor = FirmwareExtractor()
        self.comparator = FirmwareComparator()
        self.validator = FirmwareValidator()
        
        self.current_firmware = None
        self.compare_firmware = None
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Crea los widgets del panel"""
        
        title = ctk.CTkLabel(
            self.parent,
            text="📦 Herramientas de Firmware",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(pady=10)
        
        # Sección de análisis
        analyze_frame = ctk.CTkFrame(self.parent)
        analyze_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            analyze_frame,
            text="1. ANALIZAR FIRMWARE",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=5)
        
        self.firmware_path_label = ctk.CTkLabel(
            analyze_frame,
            text="Ningún archivo seleccionado",
            text_color="gray"
        )
        self.firmware_path_label.pack(pady=5)
        
        btn_frame = ctk.CTkFrame(analyze_frame)
        btn_frame.pack(pady=5)
        
        self.select_fw_btn = ctk.CTkButton(
            btn_frame,
            text="📂 Seleccionar Firmware",
            command=self._select_firmware,
            width=150
        )
        self.select_fw_btn.pack(side="left", padx=5)
        
        self.analyze_btn = ctk.CTkButton(
            btn_frame,
            text="🔍 Analizar",
            command=self._analyze_firmware,
            width=150,
            state="disabled"
        )
        self.analyze_btn.pack(side="left", padx=5)
        
        # Info del firmware
        self.firmware_info = ctk.CTkTextbox(
            self.parent,
            height=200,
            wrap="word"
        )
        self.firmware_info.pack(fill="x", padx=10, pady=5)
        
        # Sección de validación
        validate_frame = ctk.CTkFrame(self.parent)
        validate_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            validate_frame,
            text="2. VALIDAR FIRMWARE",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=5)
        
        self.validate_btn = ctk.CTkButton(
            validate_frame,
            text="✓ Validar",
            command=self._validate_firmware,
            width=150,
            state="disabled"
        )
        self.validate_btn.pack(pady=5)
        
        self.validate_result = ctk.CTkLabel(
            validate_frame,
            text="",
            text_color="gray"
        )
        self.validate_result.pack(pady=5)
        
        # Sección de extracción
        extract_frame = ctk.CTkFrame(self.parent)
        extract_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            extract_frame,
            text="3. EXTRAER COMPONENTES",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=5)
        
        self.extract_btn = ctk.CTkButton(
            extract_frame,
            text="📦 Extraer Particiones",
            command=self._extract_partitions,
            width=200,
            state="disabled"
        )
        self.extract_btn.pack(pady=5)
        
        self.extract_output = ctk.CTkLabel(
            extract_frame,
            text="",
            text_color="gray",
            wraplength=400
        )
        self.extract_output.pack(pady=5)
        
        # Sección de comparación
        compare_frame = ctk.CTkFrame(self.parent)
        compare_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            compare_frame,
            text="4. COMPARAR FIRMWARES",
            font=ctk.CTkFont(weight="bold")
        ).pack(pady=5)
        
        self.compare_path_label = ctk.CTkLabel(
            compare_frame,
            text="Firmware para comparar: No seleccionado",
            text_color="gray"
        )
        self.compare_path_label.pack(pady=5)
        
        compare_btn_frame = ctk.CTkFrame(compare_frame)
        compare_btn_frame.pack(pady=5)
        
        self.select_compare_btn = ctk.CTkButton(
            compare_btn_frame,
            text="📂 Seleccionar para Comparar",
            command=self._select_compare_firmware,
            width=180
        )
        self.select_compare_btn.pack(side="left", padx=5)
        
        self.compare_btn = ctk.CTkButton(
            compare_btn_frame,
            text="🔄 Comparar",
            command=self._compare_firmwares,
            width=150,
            state="disabled"
        )
        self.compare_btn.pack(side="left", padx=5)
        
        self.compare_result = ctk.CTkTextbox(
            self.parent,
            height=150,
            wrap="word"
        )
        self.compare_result.pack(fill="x", padx=10, pady=5)
        
    def _select_firmware(self):
        """Selecciona archivo de firmware"""
        filename = filedialog.askopenfilename(
            title="Seleccionar Firmware",
            filetypes=[
                ("Archivos IMG", "*.img"),
                ("Archivos BIN", "*.bin"),
                ("Archivos TAR", "*.tar"),
                ("Todos", "*.*")
            ]
        )
        
        if filename:
            self.current_firmware = filename
            name = os.path.basename(filename)
            size = os.path.getsize(filename) / (1024 * 1024)
            self.firmware_path_label.configure(text=f"{name} ({size:.2f} MB)")
            self.analyze_btn.configure(state="normal")
            self.validate_btn.configure(state="normal")
            self.extract_btn.configure(state="normal")
            
    def _select_compare_firmware(self):
        """Selecciona firmware para comparar"""
        filename = filedialog.askopenfilename(
            title="Seleccionar Firmware para Comparar",
            filetypes=[
                ("Archivos IMG", "*.img"),
                ("Archivos BIN", "*.bin"),
                ("Todos", "*.*")
            ]
        )
        
        if filename:
            self.compare_firmware = filename
            name = os.path.basename(filename)
            self.compare_path_label.configure(text=f"Comparar con: {name}")
            self.compare_btn.configure(state="normal")
            
    def _analyze_firmware(self):
        """Analiza el firmware seleccionado"""
        if not self.current_firmware:
            return
            
        self.app._log_activity(f"Analizando: {self.current_firmware}")
        self.firmware_info.delete("1.0", "end")
        self.firmware_info.insert("1.0", "Analizando...\n")
        
        def analyze():
            try:
                info = self.analyzer.analyze(self.current_firmware)
                summary = self.analyzer.get_summary()
                
                def update():
                    self.firmware_info.delete("1.0", "end")
                    self.firmware_info.insert("1.0", summary)
                    self.app._log_activity(f"✓ Análisis completado")
                self.parent.after(0, update)
                
            except Exception as e:
                def update():
                    self.firmware_info.delete("1.0", "end")
                    self.firmware_info.insert("1.0", f"Error: {str(e)}")
                    self.app._log_activity(f"✗ Error: {e}")
                self.parent.after(0, update)
                
        threading.Thread(target=analyze, daemon=True).start()
        
    def _validate_firmware(self):
        """Valida el firmware"""
        if not self.current_firmware:
            return
            
        self.app._log_activity("Validando firmware...")
        
        valid, warnings = self.validator.validate(self.current_firmware)
        
        if valid:
            self.validate_result.configure(text="✓ Firmware válido", text_color="green")
        else:
            self.validate_result.configure(text="✗ Firmware inválido", text_color="red")
            
        if warnings:
            msg = "\n".join(warnings)
            messagebox.showwarning("Advertencias", msg)
            
        self.app._log_activity(f"✓ Validación: {'Válido' if valid else 'Inválido'}")
        
    def _extract_partitions(self):
        """Extrae particiones del firmware"""
        if not self.current_firmware:
            return
            
        output_dir = filedialog.askdirectory(title="Seleccionar directorio de extracción")
        if not output_dir:
            return
            
        self.app._log_activity(f"Extrayendo a: {output_dir}")
        self.extract_output.configure(text="Extrayendo...")
        
        def extract():
            try:
                parts = self.extractor.extract_boot_partitions(
                    self.current_firmware,
                    output_dir
                )
                
                def update():
                    if parts:
                        names = ", ".join([p.name for p in parts])
                        self.extract_output.configure(
                            text=f"Extraídos: {names}",
                            text_color="green"
                        )
                        self.app._log_activity(f"✓ Extraídos {len(parts)} componentes")
                    else:
                        self.extract_output.configure(
                            text="No se encontraron particiones",
                            text_color="orange"
                        )
                self.parent.after(0, update)
                
            except Exception as e:
                def update():
                    self.extract_output.configure(text=f"Error: {str(e)}", text_color="red")
                self.parent.after(0, update)
                
        threading.Thread(target=extract, daemon=True).start()
        
    def _compare_firmwares(self):
        """Compara dos firmwares"""
        if not self.current_firmware or not self.compare_firmware:
            return
            
        self.app._log_activity("Comparando firmwares...")
        self.compare_result.delete("1.0", "end")
        self.compare_result.insert("1.0", "Comparando...\n")
        
        def compare():
            try:
                result = self.comparator.compare(
                    self.current_firmware,
                    self.compare_firmware
                )
                
                fw1_name = os.path.basename(self.current_firmware)
                fw2_name = os.path.basename(self.compare_firmware)
                
                output = f"""
COMPARACIÓN DE FIRMWARES
========================

Firmware 1: {fw1_name}
  - Tamaño: {result['size1'] / (1024*1024):.2f} MB
  - Checksum: {result['checksum1']}

Firmware 2: {fw2_name}
  - Tamaño: {result['size2'] / (1024*1024):.2f} MB
  - Checksum: {result['checksum2']}

RESULTADO
---------
¿Idénticos?: {'SÍ ✓' if result['identical'] else 'NO ✗'}
Diferencia de tamaño: {result['difference_percent']:.2f}%
"""
                
                def update():
                    self.compare_result.delete("1.0", "end")
                    self.compare_result.insert("1.0", output)
                    self.app._log_activity("✓ Comparación completada")
                self.parent.after(0, update)
                
            except Exception as e:
                def update():
                    self.compare_result.delete("1.0", "end")
                    self.compare_result.insert("1.0", f"Error: {str(e)}")
                self.parent.after(0, update)
                
        threading.Thread(target=compare, daemon=True).start()
