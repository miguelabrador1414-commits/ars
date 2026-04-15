# Allwinner Recovery Studio (ARS)

![Version](https://img.shields.io/badge/version-1.3.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

**Sistema profesional de recuperación de dispositivos Allwinner y otros SOCs ARM**

---

## 📋 Descripción

ARS es una herramienta que automatiza la recuperación de TV Boxes, SBCs y dispositivos ARM. Diseñado para usuarios sin conocimiento técnico profundo.

### Características principales

- 🔧 **Recovery automático** via Serial Console
- ⚡ **FEL Recovery** para dispositivos completamente muertos
- 🤖 **IA integrada** (Groq) para diagnóstico inteligente
- 📦 **Análisis de firmware** con binwalk
- 🔍 **Base de errores** con 13+ problemas documentados
- 🌍 **Multi-SOC**: Allwinner, Rockchip, Amlogic, MediaTek

---

## 🚀 Instalación

### Requisitos

- Python 3.8+
- Linux (Debian/Ubuntu)
- Cable CH340 USB-TTL (serial)
- Cable USB OTG (FEL mode)

### Pasos

```bash
# Clonar repositorio
git clone https://github.com/YOUR_USER/ars.git
cd ars

# Dar permisos
chmod +x install.sh

# Instalar
./install.sh

# Ejecutar
python3 ars.py
```

---

## 📱 SOCs Soportados

| Fabricante | Modelos |
|------------|---------|
| **Allwinner** | H616, H313, H618, H3, A64 |
| **Rockchip** | RK3588, RK3399 |
| **Amlogic** | S905X4, S905X3, S912 |
| **MediaTek** | MT8581 |
| **Novatek** | NT96678 |

---

## 🖥️ Interfaz

```
┌─────────────────────────────────────────────────────────┐
│  🎯 Allwinner Recovery Studio v1.3.0                    │
├─────────┬───────────────────────────────────────────────┤
│ 📱 SOC │  📋 Bootlog    📦 Firmware   🤖 IA          │
│        │  🔧 Recovery   ⚡ FEL       🔧 Errores       │
├─────────┴───────────────────────────────────────────────┤
│                                                           │
│  Bootlog Console                                          │
│  ───────────────────────────────────────────────────────  │
│  [    1.234] sunxi-mmc 4020000.sdmmc: error            │
│  [    5.456] FATAL: kernel panic                        │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## 🔧 Uso Rápido

### 1. Recovery Automático (Recomendado)

1. Conectar cable CH340 al TV Box
2. Abrir puerto serial (115200 baud)
3. Ir a pestaña "🔧 Auto Recovery"
4. Encender dispositivo
5. Click "🚀 INICIAR RECUPERACIÓN"

### 2. FEL Recovery (Dispositivos Muertos)

1. Mantener botón FEL + conectar USB
2. Ir a pestaña "⚡ FEL Recovery"
3. Detectar dispositivo
4. Seleccionar firmware
5. Escribir a RAM

---

## 🤖 IA Integrada

Configura Groq para diagnóstico automático:

1. Obtén API key gratis en [console.groq.com](https://console.groq.com)
2. Abre ARS → Pestaña "⚙️ Settings"
3. Ingresa tu API key

Modelos disponibles:
- `llama-3.3-70b-versatile` (recomendado)
- `llama-3.1-8b-instant`
- `mixtral-8x7b-32768`

---

## 📂 Estructura del Proyecto

```
ars/
├── ars.py              # Lanzador
├── install.sh           # Instalador
├── requirements.txt     # Dependencias
├── core/                # Módulos core
├── ai/                  # Sistema de IA
├── db/                  # Bases de datos
├── gui/                 # Interfaz gráfica
├── utils/               # Herramientas
├── plugins/             # Sistema de plugins
└── integrations/        # Integraciones externas
```

---

## 📜 Licencia

Este proyecto está bajo licencia **MIT**. Ver [LICENSE](LICENSE) para más detalles.

---

## 🤝 Contribuir

1. Fork el repositorio
2. Crea tu branch (`git checkout -b feature/nueva-funcion`)
3. Commit tus cambios (`git commit -am 'Agrega feature'`)
4. Push al branch (`git push origin feature/nueva-funcion`)
5. Crea un Pull Request

---

## ⚠️ Disclaimer

**USO BAJO TU PROPIO RIESGO.** Este software puede dañar dispositivos si se usa incorrectamente. Siempre verifica el firmware antes de flashear.

---

## 📞 Soporte

- 📖 Documentación: [Wiki](https://github.com/YOUR_USER/ars/wiki)
- 🐛 Issues: [GitHub Issues](https://github.com/YOUR_USER/ars/issues)

---

**¡Buena suerte con tus recuperaciones! 🎯**
