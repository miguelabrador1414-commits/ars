"""
FEL Handler - Manejo de protocolo FEL para Allwinner
"""

import subprocess
import os
import threading
from typing import Optional, Callable, Tuple
import logging

logger = logging.getLogger(__name__)


class FELHandler:
    """
    Manejador del protocolo FEL para Allwinner.
    Permite escribir a RAM, leer memoria y ejecutar código.
    """
    
    def __init__(self):
        self.base_address = 0x40000000
        self.current_address = self.base_address
        self.device_connected = False
        self._lock = threading.Lock()
        
    def check_connection(self) -> bool:
        """Verifica conexión FEL"""
        try:
            result = subprocess.run(
                ["sg", "sunxi-fel", "-c", "sunxi-fel ver"],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.device_connected = "AWUSBFEX" in (result.stdout + result.stderr)
            return self.device_connected
        except Exception as e:
            logger.error(f"FEL connection check failed: {e}")
            self.device_connected = False
            return False
            
    def get_device_info(self) -> dict:
        """Obtiene información del dispositivo"""
        try:
            result = subprocess.run(
                ["sg", "sunxi-fel", "-c", "sunxi-fel ver"],
                capture_output=True,
                text=True,
                timeout=10
            )
            output = result.stdout + result.stderr
            
            info = {}
            if "AWUSBFEX" in output:
                for line in output.split("\n"):
                    if "soc=" in line:
                        soc = line.split("soc=")[1].split()[0]
                        info["soc_id"] = soc
                        if "(" in soc and ")" in soc:
                            parts = soc.split("(")
                            info["soc_id"] = parts[0]
                            info["soc_name"] = parts[1].rstrip(")")
                    elif "ver=" in line:
                        info["fel_version"] = line.split("ver=")[1].split()[0]
                    elif "scratchpad=" in line:
                        info["scratchpad"] = line.split("scratchpad=")[1].split()[0]
                        
            return info
        except Exception as e:
            logger.error(f"Error getting FEL info: {e}")
            return {}
            
    def write_file_to_ram(self, filepath: str, address: Optional[int] = None,
                          progress_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """
        Escribe un archivo a la memoria RAM del dispositivo.
        
        Args:
            filepath: Ruta del archivo a escribir
            address: Dirección de memoria (default: 0x40000000)
            progress_callback: Función de callback para progreso
            
        Returns:
            Tuple de (éxito, mensaje)
        """
        if address is None:
            address = self.current_address
            
        if not os.path.exists(filepath):
            return False, f"File not found: {filepath}"
            
        file_size = os.path.getsize(filepath)
        logger.info(f"Writing {file_size} bytes to 0x{address:x}")
        
        try:
            # Método 1: Split en chunks y escribir
            chunks = self._create_chunks(filepath, 4 * 1024 * 1024)  # 4MB chunks
            current_addr = address
            
            for i, chunk_path in enumerate(chunks):
                result = subprocess.run(
                    ["dd", "if=" + chunk_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                fel_proc = subprocess.Popen(
                    ["sg", "sunxi-fel", "-c", f"cat > /dev/null"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                stdout, stderr = fel_proc.communicate(
                    input=result.stdout,
                    timeout=300
                )
                
                if fel_proc.returncode != 0:
                    return False, f"Failed at chunk {i+1}"
                    
                current_addr += 4 * 1024 * 1024
                progress = (i + 1) / len(chunks) * 100
                
                if progress_callback:
                    progress_callback(progress)
                    
                logger.info(f"Chunk {i+1}/{len(chunks)} written")
                
            # Limpiar chunks temporales
            for chunk_path in chunks:
                try:
                    os.remove(chunk_path)
                except:
                    pass
                    
            return True, f"Successfully wrote {file_size} bytes to 0x{address:x}"
            
        except subprocess.TimeoutExpired:
            return False, "Write operation timed out"
        except Exception as e:
            return False, f"Write error: {str(e)}"
            
    def _create_chunks(self, filepath: str, chunk_size: int) -> list:
        """Crea chunks temporales del archivo"""
        chunks = []
        chunk_num = 0
        
        try:
            with open(filepath, "rb") as f:
                while True:
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break
                        
                    chunk_path = f"/tmp/fel_chunk_{chunk_num}.bin"
                    with open(chunk_path, "wb") as chunk_file:
                        chunk_file.write(chunk_data)
                    chunks.append(chunk_path)
                    chunk_num += 1
                    
        except Exception as e:
            logger.error(f"Error creating chunks: {e}")
            # Limpiar chunks parciales
            for c in chunks:
                try:
                    os.remove(c)
                except:
                    pass
            raise
            
        return chunks
        
    def read_memory(self, address: int, length: int, output_file: str) -> Tuple[bool, str]:
        """Lee memoria del dispositivo y la guarda en archivo"""
        try:
            result = subprocess.run(
                ["sg", "sunxi-fel", "-c", 
                 f"sunxi-fel read 0x{address:x} 0x{length:x} {output_file}"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return True, f"Read {length} bytes to {output_file}"
            else:
                return False, f"Read failed: {result.stderr}"
                
        except Exception as e:
            return False, f"Read error: {str(e)}"
            
    def execute_address(self, address: int) -> Tuple[bool, str]:
        """Ejecuta código en una dirección de memoria"""
        try:
            result = subprocess.run(
                ["sg", "sunxi-fel", "-c", f"sunxi-fel exe 0x{address:x}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return True, f"Executed at 0x{address:x}"
            else:
                return False, f"Execute failed: {result.stderr}"
                
        except Exception as e:
            return False, f"Execute error: {str(e)}"
            
    def load_spl(self, spl_file: str) -> Tuple[bool, str]:
        """Carga y ejecuta un SPL (Secondary Program Loader)"""
        if not os.path.exists(spl_file):
            return False, f"SPL file not found: {spl_file}"
            
        try:
            result = subprocess.run(
                ["sg", "sunxi-fel", "-c", f"sunxi-fel spl {spl_file}"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return True, f"SPL loaded: {spl_file}"
            else:
                return False, f"SPL load failed: {result.stderr}"
                
        except Exception as e:
            return False, f"SPL error: {str(e)}"
            
    def write_with_progress(self, filepath: str, 
                           address: int = 0x40000000,
                           progress_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """
        Escribe archivo con barra de progreso.
        Método alternativo usando sunxi-fel write directo.
        """
        if not os.path.exists(filepath):
            return False, f"File not found: {filepath}"
            
        file_size = os.path.getsize(filepath)
        
        try:
            # Usar sunxi-fel write con pipe
            result = subprocess.run(
                ["dd", f"if={filepath}", "bs=4M"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            proc = subprocess.Popen(
                ["sg", "sunxi-fel", "-c", 
                 f"sunxi-fel write 0x{address:x} /dev/stdin"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = proc.communicate(
                input=result.stdout,
                timeout=600
            )
            
            if proc.returncode == 0:
                if progress_callback:
                    progress_callback(100)
                return True, f"Wrote {file_size} bytes"
            else:
                return False, stderr.decode()
                
        except subprocess.TimeoutExpired:
            return False, "Operation timed out"
        except Exception as e:
            return False, str(e)
