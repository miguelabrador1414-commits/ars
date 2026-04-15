#!/bin/bash
# ============================================================================
# Allwinner Recovery Studio - Script de Instalación
# ============================================================================
# Autor: ARS Development Team
# Versión: 1.2.0
# ============================================================================

set -e

VERSION="1.2.0"
INSTALL_DIR="$HOME/.local/share/ars"
DESKTOP_FILE="$HOME/.local/share/applications/ars.desktop"
BIN_LINK="$HOME/.local/bin/ars"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                          ║${NC}"
echo -e "${BLUE}║${NC}       ${GREEN}Allwinner Recovery Studio v${VERSION}${NC} ${BLUE}                   ║${NC}"
echo -e "${BLUE}║${NC}              Sistema de Recuperación Profesional      ${BLUE}    ║${NC}"
echo -e "${BLUE}║${NC}                                                          ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Funciones
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_dependencies() {
    echo -e "\n${BLUE}▸ Verificando dependencias...${NC}"
    
    # Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        success "Python3 encontrado: $PYTHON_VERSION"
    else
        error "Python3 no encontrado. Instálalo primero."
        exit 1
    fi
    
    # pip
    if command -v pip3 &> /dev/null; then
        success "pip3 encontrado"
    else
        error "pip3 no encontrado"
        exit 1
    fi
    
    # sunxi-fel (opcional)
    if command -v sunxi-fel &> /dev/null; then
        FEL_VERSION=$(sunxi-fel ver 2>&1 | head -1)
        success "sunxi-fel encontrado: $FEL_VERSION"
    else
        warning "sunxi-fel no encontrado (necesario para FEL recovery)"
        info "Instala con: sudo apt install sunxi-fel-tools"
    fi
    
    # binwalk (opcional)
    if command -v binwalk &> /dev/null; then
        success "binwalk encontrado"
    else
        warning "binwalk no encontrado (necesario para análisis de firmware)"
        info "Instala con: sudo apt install binwalk"
    fi
}

install_python_deps() {
    echo -e "\n${BLUE}▸ Instalando dependencias de Python...${NC}"
    
    pip3 install --upgrade pip --quiet
    
    pip3 install customtkinter --quiet
    pip3 install pyserial --quiet
    pip3 install pyusb --quiet
    pip3 install requests --quiet
    
    success "Dependencias de Python instaladas"
}

create_directories() {
    echo -e "\n${BLUE}▸ Creando estructura de directorios...${NC}"
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$HOME/.local/bin"
    mkdir -p "$HOME/.local/share/applications"
    mkdir -p "$HOME/.local/share/ars/firmware"
    mkdir -p "$HOME/.local/share/ars/devices"
    mkdir -p "$HOME/.local/share/ars/logs"
    
    success "Directorios creados en $INSTALL_DIR"
}

copy_files() {
    echo -e "\n${BLUE}▸ Copiando archivos...${NC}"
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Copiar archivos del proyecto
    rsync -av --exclude='__pycache__' --exclude='*.pyc' \
          --exclude='.git' --exclude='tests' \
          "$SCRIPT_DIR/" "$INSTALL_DIR/" 2>/dev/null || \
    cp -r "$SCRIPT_DIR/"* "$INSTALL_DIR/" 2>/dev/null || true
    
    # Copiar individualmente si rsync falla
    for item in core ai db utils gui integrations; do
        if [ -d "$SCRIPT_DIR/$item" ]; then
            mkdir -p "$INSTALL_DIR/$item"
            cp -r "$SCRIPT_DIR/$item/"* "$INSTALL_DIR/$item/" 2>/dev/null || true
        fi
    done
    
    # Copiar archivos raíz
    for file in ars.py __init__.py requirements.txt; do
        if [ -f "$SCRIPT_DIR/$file" ]; then
            cp "$SCRIPT_DIR/$file" "$INSTALL_DIR/" 2>/dev/null || true
        fi
    done
    
    success "Archivos copiados"
}

create_launcher() {
    echo -e "\n${BLUE}▸ Creando lanzador...${NC}"
    
    # Crear script de ejecución
    cat > "$INSTALL_DIR/ars-runner.sh" << 'RUNNER_EOF'
#!/bin/bash
cd "$(dirname "$0")"
export PYTHONPATH="$(dirname "$0"):$PYTHONPATH"
python3 ars.py
RUNNER_EOF
    chmod +x "$INSTALL_DIR/ars-runner.sh"
    
    # Crear enlace simbólico
    ln -sf "$INSTALL_DIR/ars-runner.sh" "$BIN_LINK"
    
    # Crear archivo desktop
    cat > "$DESKTOP_FILE" << DESKTOP_EOF
[Desktop Entry]
Name=Allwinner Recovery Studio
Comment=Sistema profesional de recuperación de dispositivos Allwinner
Exec=$INSTALL_DIR/ars-runner.sh
Icon=$INSTALL_DIR/icon.png
Terminal=false
Type=Application
Categories=System;Utility;
Version=$VERSION
DESKTOP_EOF
    
    # Crear icono simple (placeholder)
    if [ ! -f "$INSTALL_DIR/icon.png" ]; then
        # Generar icono PNG simple con Python
        python3 << 'ICON_EOF' 2>/dev/null || true
import base64
icon_data = """iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlz
AAALEwAACxMBAJqcGAAAAW5JREFUWIXtl71uwzAMhe/+J+4NekG7S+3QDugB7YAO6IB2g9zQDuhY
uytdlC6S2E5sJ8WFJErs+8R2zjnHGPBfEf4H4D8CqioigqoKUFAV4gBVhSiE0iMKwfdQVRhjhDGG
oigQkc7vVVVVBEFAGAYkSUKSJMRxTBiGRFFEFEVkshlmMhmyWYAsSwjDkCAMCMOQMAz5+fMnP3/+
5NevX8RxTJ4XhGFInsfs7+/z7NkzdnZ2ODg4YHd3l+3tbba2tlhfX2dlZYXYb7K+vs7q6iqLi4ss
LS2xsLDA/Pw8s7OzLCwssLi4yOLiIouLi8RxTJ4XhGHAnz9/+PXrF79+/eL379/8/v2bMAzJ85ww
DMnznDAMyfOcMAzJ85wwDMnznDAMyfOcMAzJ85wwDMnznDAMyfOcMAzJ85wwDMnznDAMyfOcMAzJ
85wwDMnznDAMyfOcMAzJ85wwDMnznDAMyfOcMAzJ85wwDMnznDAMyfOcMAzJ85wwDMnznDAMyfOc
MAzJ85wwDMnznDAMyfOcMAzJ8wIAAAAASUVORK5CYII="""
try:
    with open("/tmp/ars_icon.png", "wb") as f:
        f.write(base64.b64decode(icon_data))
except:
    pass
ICON_EOF
    fi
    
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    
    success "Lanzador creado"
}

configure_ars() {
    echo -e "\n${BLUE}▸ Configurando ARS...${NC}"
    
    # Crear config inicial
    python3 << 'CONFIG_EOF'
import sys
import os
import json

config_dir = os.path.expanduser("~/.config/ars")
os.makedirs(config_dir, exist_ok=True)

config_file = os.path.join(config_dir, "config.json")

if not os.path.exists(config_file):
    default_config = {
        "ai": {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "api_key": ""
        },
        "serial": {
            "default_baudrate": 115200,
            "preferred_port": ""
        },
        "fel": {
            "write_method": "pipe",
            "chunk_size_mb": 4
        },
        "recovery": {
            "auto_interrupt_boot": True,
            "boot_timeout_seconds": 30
        },
        "ui": {
            "theme": "dark",
            "language": "es"
        }
    }
    
    with open(config_file, 'w') as f:
        json.dump(default_config, f, indent=2)

print("Config created")
CONFIG_EOF
    
    success "ARS configurado"
}

print_installation_summary() {
    echo -e "\n${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}                    ${GREEN}INSTALACIÓN COMPLETADA${NC}                   ${GREEN}║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BLUE}Directorio:${NC} $INSTALL_DIR"
    echo -e "  ${BLUE}Ejecutable:${NC} $BIN_LINK"
    echo -e "  ${BLUE}Menú:${NC} Aplicaciones > Sistema > Allwinner Recovery Studio"
    echo ""
    echo -e "  ${YELLOW}Para ejecutar:${NC}"
    echo -e "    • menuentry: Buscar 'Allwinner Recovery Studio' en el menú"
    echo -e "    • terminal:  ars"
    echo -e "    • directo:   python3 $INSTALL_DIR/ars.py"
    echo ""
    echo -e "  ${YELLOW}Configuración de IA:${NC}"
    echo -e "    1. Abre ARS"
    echo -e "    2. Ve a la pestaña '⚙️ Settings'"
    echo -e "    3. Ingresa tu Groq API Key (gratis en console.groq.com)"
    echo ""
    echo -e "  ${YELLOW}Requerimientos opcionales:${NC}"
    echo -e "    • sunxi-fel: sudo apt install sunxi-fel-tools"
    echo -e "    • binwalk:   sudo apt install binwalk"
    echo ""
}

# Main
main() {
    check_dependencies
    install_python_deps
    create_directories
    copy_files
    create_launcher
    configure_ars
    print_installation_summary
}

# Ejecutar
main "$@"
