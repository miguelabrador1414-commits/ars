"""
Plugin System - Sistema de plugins para ARS

Permite extender la funcionalidad de ARS mediante plugins.

Estructura de un plugin:
```
plugins/
└── mi_plugin/
    ├── __init__.py
    ├── plugin.json
    └── main.py
```

plugin.json:
{
    "name": "Mi Plugin",
    "version": "1.0.0",
    "author": "Autor",
    "description": "Descripción del plugin",
    "socs": ["h616", "rk3588"],
    "entry_point": "main:MiPlugin"
}
"""

import os
import sys
import importlib
import importlib.util
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import zipfile
import tempfile

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo:
    """Información del plugin"""
    name: str
    version: str
    author: str
    description: str
    socs: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = ""
    path: str = ""
    enabled: bool = True
    loaded: bool = False


@dataclass
class PluginHook:
    """Hook de plugin"""
    name: str
    callback: Callable
    priority: int = 0


class BasePlugin(ABC):
    """Clase base para plugins"""
    
    name: str = "BasePlugin"
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    socs: List[str] = []
    
    def __init__(self, app=None):
        self.app = app
        self.enabled = True
        self._hooks: Dict[str, List[PluginHook]] = {}
        
    @abstractmethod
    def on_load(self):
        """Se llama cuando el plugin se carga"""
        pass
        
    @abstractmethod
    def on_unload(self):
        """Se llama cuando el plugin se descarga"""
        pass
        
    def register_hook(self, hook_name: str, callback: Callable, priority: int = 0):
        """Registra un hook"""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(PluginHook(hook_name, callback, priority))
        
    def unregister_hook(self, hook_name: str, callback: Callable):
        """Desregistra un hook"""
        if hook_name in self._hooks:
            self._hooks[hook_name] = [
                h for h in self._hooks[hook_name] if h.callback != callback
            ]
            
    def call_hooks(self, hook_name: str, *args, **kwargs):
        """Llama a todos los hooks de un tipo"""
        if hook_name not in self._hooks:
            return []
            
        results = []
        for hook in sorted(self._hooks[hook_name], key=lambda h: h.priority):
            try:
                result = hook.callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook error in {self.name}.{hook_name}: {e}")
                
        return results


class PluginManager:
    """Gestor de plugins"""
    
    HOOKS = [
        "device_connected",
        "device_disconnected",
        "bootlog_received",
        "recovery_start",
        "recovery_complete",
        "recovery_error",
        "serial_data",
        "fel_write",
        "ui_tab_created",
        "menu_created",
        "toolbar_created",
        "settings_loaded",
    ]
    
    def __init__(self, plugins_dir: str = None):
        if plugins_dir is None:
            plugins_dir = Path.home() / ".local" / "share" / "ars" / "plugins"
            
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_info: Dict[str, PluginInfo] = {}
        self.hooks: Dict[str, List[Callable]] = {h: [] for h in self.HOOKS}
        
        self._discover_plugins()
        
    def _discover_plugins(self):
        """Descubre plugins en el directorio"""
        for item in self.plugins_dir.iterdir():
            if item.is_dir() and (item / "plugin.json").exists():
                try:
                    self._load_plugin_info(item)
                except Exception as e:
                    logger.error(f"Error discovering plugin {item}: {e}")
                    
    def _load_plugin_info(self, plugin_path: Path):
        """Carga información del plugin"""
        info_file = plugin_path / "plugin.json"
        info = json.loads(info_file.read_text())
        
        plugin_info = PluginInfo(
            name=info.get("name", plugin_path.name),
            version=info.get("version", "1.0.0"),
            author=info.get("author", "Unknown"),
            description=info.get("description", ""),
            socs=info.get("socs", []),
            dependencies=info.get("dependencies", []),
            entry_point=info.get("entry_point", "main:Plugin"),
            path=str(plugin_path)
        )
        
        self.plugin_info[plugin_info.name] = plugin_info
        logger.info(f"Discovered plugin: {plugin_info.name} v{plugin_info.version}")
        
    def load_plugin(self, name: str, app=None) -> bool:
        """Carga un plugin"""
        if name in self.plugins:
            logger.info(f"Plugin {name} already loaded")
            return True
            
        if name not in self.plugin_info:
            logger.error(f"Plugin {name} not found")
            return False
            
        info = self.plugin_info[name]
        
        if not info.enabled:
            logger.info(f"Plugin {name} is disabled")
            return False
            
        try:
            spec = importlib.util.spec_from_file_location(
                name,
                Path(info.path) / "__init__.py"
            )
            
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[name] = module
                spec.loader.exec_module(module)
                
                entry_parts = info.entry_point.split(":")
                if len(entry_parts) == 2:
                    class_name = entry_parts[1]
                    if hasattr(module, class_name):
                        plugin_class = getattr(module, class_name)
                        plugin = plugin_class(app)
                        plugin.on_load()
                        
                        self.plugins[name] = plugin
                        info.loaded = True
                        
                        self._register_plugin_hooks(plugin)
                        
                        logger.info(f"Loaded plugin: {name}")
                        return True
                        
        except Exception as e:
            logger.error(f"Error loading plugin {name}: {e}")
            
        return False
        
    def _register_plugin_hooks(self, plugin: BasePlugin):
        """Registra los hooks de un plugin"""
        for hook_name, hooks in plugin._hooks.items():
            if hook_name in self.hooks:
                for hook in hooks:
                    self.hooks[hook_name].append(hook.callback)
                    
    def unload_plugin(self, name: str) -> bool:
        """Descarga un plugin"""
        if name not in self.plugins:
            return False
            
        plugin = self.plugins[name]
        
        try:
            plugin.on_unload()
            
            for hook_name, callbacks in plugin._hooks.items():
                if hook_name in self.hooks:
                    for callback in callbacks:
                        if callback in self.hooks[hook_name]:
                            self.hooks[hook_name].remove(callback)
                            
            del self.plugins[name]
            self.plugin_info[name].loaded = False
            
            logger.info(f"Unloaded plugin: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error unloading plugin {name}: {e}")
            return False
            
    def enable_plugin(self, name: str):
        """Habilita un plugin"""
        if name in self.plugin_info:
            self.plugin_info[name].enabled = True
            
    def disable_plugin(self, name: str):
        """Deshabilita un plugin"""
        if name in self.plugin_info:
            self.plugin_info[name].enabled = False
            if name in self.plugins:
                self.unload_plugin(name)
                
    def load_all(self, app=None):
        """Carga todos los plugins habilitados"""
        for name, info in self.plugin_info.items():
            if info.enabled and not info.loaded:
                self.load_plugin(name, app)
                
    def call_hook(self, hook_name: str, *args, **kwargs):
        """Llama a todos los hooks de un tipo"""
        if hook_name not in self.hooks:
            return []
            
        results = []
        for callback in self.hooks[hook_name]:
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Hook error in {hook_name}: {e}")
                
        return results
        
    def list_plugins(self) -> List[PluginInfo]:
        """Lista todos los plugins"""
        return list(self.plugin_info.values())
        
    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Obtiene instancia de plugin"""
        return self.plugins.get(name)
        
    def install_plugin(self, plugin_path: str) -> Tuple[bool, str]:
        """
        Instala un plugin desde archivo zip.
        
        Returns:
            Tuple de (éxito, mensaje)
        """
        try:
            plugin_path = Path(plugin_path)
            
            if not plugin_path.exists():
                return False, "Archivo no encontrado"
                
            if plugin_path.suffix == ".zip":
                return self._install_from_zip(plugin_path)
            elif plugin_path.is_dir():
                return self._install_from_directory(plugin_path)
            else:
                return False, "Formato no soportado"
                
        except Exception as e:
            return False, str(e)
            
    def _install_from_zip(self, zip_path: Path) -> Tuple[bool, str]:
        """Instala plugin desde zip"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(temp_dir)
                
            items = list(temp_dir.iterdir())
            if len(items) == 1 and items[0].is_dir():
                plugin_dir = items[0]
            else:
                plugin_dir = temp_dir / "plugin"
                
            if not (plugin_dir / "plugin.json").exists():
                return False, "plugin.json no encontrado"
                
            plugin_name = json.loads((plugin_dir / "plugin.json").read_text()).get("name", "plugin")
            dest_dir = self.plugins_dir / plugin_name
            
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
                
            shutil.copytree(plugin_dir, dest_dir)
            
            self._load_plugin_info(dest_dir)
            
            return True, f"Plugin '{plugin_name}' instalado"
            
        finally:
            shutil.rmtree(temp_dir)
            
    def _install_from_directory(self, dir_path: Path) -> Tuple[bool, str]:
        """Instala plugin desde directorio"""
        if not (dir_path / "plugin.json").exists():
            return False, "plugin.json no encontrado"
            
        plugin_name = json.loads((dir_path / "plugin.json").read_text()).get("name", "plugin")
        dest_dir = self.plugins_dir / plugin_name
        
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
            
        shutil.copytree(dir_path, dest_dir)
        
        self._load_plugin_info(dest_dir)
        
        return True, f"Plugin '{plugin_name}' instalado"
        
    def uninstall_plugin(self, name: str) -> bool:
        """Desinstala un plugin"""
        if name in self.plugins:
            self.unload_plugin(name)
            
        if name in self.plugin_info:
            plugin_path = Path(self.plugin_info[name].path)
            if plugin_path.exists():
                shutil.rmtree(plugin_path)
            del self.plugin_info[name]
            return True
            
        return False


class PluginTemplate:
    """Template para crear nuevos plugins"""
    
    @staticmethod
    def create_plugin(name: str, description: str, socs: List[str], output_dir: str):
        """Crea la estructura de un nuevo plugin"""
        output_dir = Path(output_dir) / name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        plugin_json = {
            "name": name,
            "version": "1.0.0",
            "author": "Your Name",
            "description": description,
            "socs": socs,
            "dependencies": [],
            "entry_point": "main:Plugin"
        }
        
        (output_dir / "plugin.json").write_text(json.dumps(plugin_json, indent=2))
        
        main_py = f'''"""
{name} - Plugin para ARS
{description}
"""

from plugins.base import BasePlugin


class Plugin(BasePlugin):
    """Plugin {name}"""
    
    name = "{name}"
    version = "1.0.0"
    description = "{description}"
    author = "Your Name"
    socs = {socs}
    
    def on_load(self):
        """Se llama cuando el plugin se carga"""
        print(f"Plugin {{self.name}} cargado")
        
        # Registrar hooks
        # self.register_hook("bootlog_received", self.on_bootlog)
        # self.register_hook("device_connected", self.on_device_connected)
        
    def on_unload(self):
        """Se llama cuando el plugin se descarga"""
        print(f"Plugin {{self.name}} descargado")
        
    # def on_bootlog(self, bootlog):
    #     """Procesa bootlog"""
    #     return bootlog
    #     
    # def on_device_connected(self, device_info):
    #     """Se llama cuando se conecta un dispositivo"""
    #     return device_info
'''
        
        (output_dir / "__init__.py").write_text(main_py)
        
        readme = f'''# {name}

{description}

## Instalación

1. Copia la carpeta `{name}` a `~/.local/share/ars/plugins/`
2. Reinicia ARS
3. El plugin aparecerá en Settings > Plugins

## Configuración

[Agregar instrucciones de configuración]

## SOCs Soportados

{", ".join(socs)}

## Autor

Tu Nombre
'''
        
        (output_dir / "README.md").write_text(readme)
        
        return str(output_dir)
