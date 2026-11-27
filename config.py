import os


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN CRÍTICA DEL SISTEMA
# ═══════════════════════════════════════════════════════════════════════════════

# 🚨 LÍMITES DE RECURSOS
MAX_REGISTROS = 200      # Máximo registros por carga (evita OOM)
BATCH_SIZE = 5           # Registros por lote (reduce memoria)
BATCH_DELAY = 3          # Segundos entre lotes (deja respirar al sistema)

# 🌐 CONFIGURACIÓN DEL FORMULARIO
FORM_URL = "https://survey.alchemer.com/s3/6972673/hospital-program-form"

# ⏱️ TIMEOUTS
SELENIUM_TIMEOUT = 20    # Segundos para esperar elementos
FORM_DELAY = 0.1         # Segundos entre formularios

# 🔧 CHROME OPTIONS
CHROME_OPTIONS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1920,1080",
    "--disable-extensions",
    "--disable-plugins",
    "--disable-images",  # Acelera carga
]

# 📁 PATHS
SCREENSHOTS_DIR = os.getenv("SCREENSHOTS_DIR", "screenshots")
EXCEL_DIR = os.getenv("EXCEL_DIR", "excel_files")
