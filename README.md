# 🏥 Sistema de Automatización de Formularios Hospitalarios

Este proyecto es una aplicación backend que automatiza el llenado de formularios web para un programa hospitalario, procesando datos desde archivos Excel y enviándolos mediante Selenium WebDriver.

## Backend independiente

Esta carpeta es desplegable por sí sola: no necesita `frontend/`, Nginx ni los
archivos de la raíz del repositorio. Desde `backend/` ejecuta:

```bash
cp .env.example .env
docker compose up --build -d
```

El servicio queda disponible en `http://localhost:8000`. Para comprobarlo:

```bash
curl http://localhost:8000/health
```

Para detenerlo:

```bash
docker compose down
```

Si la plataforma construye directamente el `Dockerfile`, configura el directorio
raíz del servicio como `backend`. El contenedor acepta la variable `PORT` que
inyectan plataformas como Render o Railway. Usa un solo proceso/réplica porque
la aplicación permite un único trabajo de Selenium a la vez.

## Despliegue automático en CentOS

El workflow `.github/workflows/deploy.yml` ejecuta las pruebas, publica la
imagen en GHCR y despliega por SSH cuando se actualiza `main`.

### Preparar el servidor una sola vez

```bash
sudo bash deploy/bootstrap-centos.sh USUARIO_SSH
```

Después, cierra la sesión SSH y vuelve a entrar para aplicar el grupo `docker`.
El DNS tipo `A` del dominio debe apuntar a la IP pública del servidor y los
puertos `80` y `443` deben estar abiertos. Caddy obtendrá y renovará el
certificado automáticamente.

### Secretos del environment `production` en GitHub

| Secreto | Valor |
| --- | --- |
| `SERVER_HOST` | IP o hostname SSH del servidor |
| `SERVER_USER` | Usuario SSH con acceso a Docker |
| `SERVER_PORT` | Puerto SSH, normalmente `22` |
| `SERVER_SSH_KEY` | Llave privada SSH de despliegue |
| `SERVER_KNOWN_HOSTS` | Resultado de `ssh-keyscan -H SERVIDOR` |
| `DOMAIN` | Dominio público, por ejemplo `api.example.com` |
| `ACME_EMAIL` | Correo para avisos del certificado |
| `GHCR_USERNAME` | Usuario de GitHub que descargará la imagen |
| `GHCR_TOKEN` | PAT classic con permiso `read:packages` |
| `CORS_ORIGINS` | Dominio del frontend; opcional, default `*` |

Si faltan secretos, el pipeline ejecuta pruebas y publica la imagen, pero omite
el despliegue. Después de agregarlos, ejecuta manualmente `Backend CI/CD` desde
la pestaña Actions.

## 📋 Descripción

El sistema permite cargar archivos Excel con información de pacientes y automáticamente completa formularios web en el sitio de Alchemer. Está diseñado para manejar dos zonas diferentes (Lima y Selva) con lógicas específicas para cada una.

## 🚀 Características

- **API REST** con FastAPI para cargar archivos Excel
- **Procesamiento en tiempo real** con streaming de resultados
- **Automatización web** usando Selenium WebDriver
- **Soporte para múltiples zonas** (Lima y Selva)
- **Modo headless** configurable para ejecución en segundo plano
- **CORS habilitado** para integración con frontend

## 🛠️ Tecnologías

- **FastAPI** - Framework web moderno y rápido
- **Selenium** - Automatización de navegador web
- **Pandas** - Procesamiento de datos Excel
- **Uvicorn** - Servidor ASGI
- **ChromeDriver** - Driver para automatización de Chrome

## 📁 Estructura del Proyecto

```
backend/
├── chromeDriver/           # Driver de Chrome para Selenium
├── excel_files/           # Archivos Excel de entrada
├── main.py               # Aplicación principal FastAPI
├── selenium_worker.py    # Lógica de automatización web
├── excel_reader.py       # Lectura y procesamiento de Excel
├── utils.py             # Funciones utilitarias
└── requirements.txt     # Dependencias del proyecto
```

## 📊 Formato de Datos Excel

El archivo Excel debe contener las siguientes columnas:

| Columna | Descripción |
|---------|-------------|
| Nombre | Nombre del paciente |
| Apellido | Apellido del paciente |
| Número Celular | Número de teléfono |
| Zona | LIMA o SELVA |
| Es Primer Hijo | SI o NO |
| Fecha de Nacimiento | Fecha en formato Excel |

## 🔧 Instalación

1. **Clonar el repositorio**
```bash
git clone <url-del-repositorio>
cd backend
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Configurar ChromeDriver**
   - Asegúrate de que ChromeDriver esté en la carpeta `chromeDriver/`
   - Actualiza la ruta en `selenium_worker.py` si es necesario

## ▶️ Uso

1. **Iniciar el servidor**
```bash
uvicorn main:app --reload
```

2. **Cargar archivo Excel**
```bash
curl -X POST "http://localhost:8000/upload/" \
  -F "file=@archivo.xlsx" \
  -F "headless=true"
```

3. **Ver resultados en tiempo real**
   - La API devuelve un stream de eventos con el progreso
   - Cada registro procesado se reporta individualmente

## 🎯 Funcionalidades por Zona

### Zonas Lima
- `LIMA` y `LIMA 2`: código `LIMVMJ02`
- `LIMA 3`: código `LIMVMJ03`
- `LIMA 4`: código `LIMVMJ04`
- `LIMA 6`: código `LIMVMJ06`
- Departamento: `Lima (departamento)`
- Fecha: generada aleatoriamente en 2025
- Siempre marca la opcion equivalente a "Es primer hijo"

### Otras zonas configuradas
- `CUSCO`: código `CUSVMJ`, departamento `Cusco`
- `CHICLAYO`: código `CIXVMJ`, departamento `Lambayeque`
- `AREQUIPA`: código `AQPVMJ`, departamento `Arequipa`
- `TRUJILLO 1`: código `TRUVMJ`, departamento `La Libertad`
- `TRUJILLO 2`: código `TRUVMJ2`, departamento `La Libertad`
- `HUANCAYO`: código `HCYOVMJ`, departamento `Junín`
- `ICA`: código `ICAVMJ`, departamento `Ica`
- `MADRE DE DIOS`: código `MDVMJ`, departamento `Madre de Dios`
- `SELVA`: código `SELVMJ`, departamento `Amazonas`
- Otras zonas: fallback a código `SELVMJ` y departamento `Amazonas`
- Para zonas no Lima, la fecha usa `Fecha de Nacimiento` y respeta `Es Primer Hijo`

## 📡 API Endpoints

### GET `/health`

Health check del servicio. Devuelve `status` y si existe un procesamiento activo.

### GET `/docs`

Documentación interactiva OpenAPI generada por FastAPI.

### GET `/openapi.json`

Especificación OpenAPI de la API.

### POST `/stop`

Solicita detener el procesamiento activo. El backend termina de forma segura el
registro actual, cierra Selenium, elimina el archivo temporal y libera el lock.

### POST `/upload/`
Carga un archivo Excel y procesa los registros.

**Parámetros:**
- `file`: Archivo Excel (multipart/form-data)
- `headless`: Boolean para modo headless (opcional, default: true)

**Respuesta:** Stream de eventos con progreso en tiempo real

## ⚙️ Configuración

- **URL del formulario**: Configurada en `FORM_URL` en `selenium_worker.py`
- **Ruta ChromeDriver**: Configurada en `CHROME_DRIVER_PATH`
- **CORS**: Habilitado para todos los orígenes

## 🔍 Monitoreo

El sistema proporciona feedback en tiempo real:
- Total de registros a procesar
- Progreso individual por registro
- Estado de éxito/error para cada envío

## 🚨 Consideraciones

- Requiere Chrome instalado en el sistema
- ChromeDriver debe coincidir con la versión de Chrome
- Los archivos Excel se guardan temporalmente en `excel_files/`
- El sistema genera correos ficticios usando el formato `{numero}@noemail.com`

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request
