import json
import os
import asyncio
import time
from excel_reader import ErrorArchivoExcel, leer_excel
from email_utils import generar_correo
from form_validation import escribir_y_validar_correo, validar_correo_cargado
from utils import generar_fecha_lima, formatear_fecha_selva
from config import (
    MAX_REGISTROS, BATCH_SIZE, BATCH_DELAY, FORM_URL,
    SELENIUM_TIMEOUT, FORM_DELAY, CHROME_OPTIONS, SCREENSHOTS_DIR
)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

CODIGOS_POR_ZONA = {
    "LIMA": "LIMVMJ02",
    "LIMA 2": "LIMVMJ02",
    "LIMA 3": "LIMVMJ03",
    "LIMA 4": "LIMVMJ04",
    "LIMA 6": "LIMVMJ06",
    "CUSCO": "CUSVMJ",
    "CHICLAYO": "CIXVMJ",
    "AREQUIPA": "AQPVMJ",
    "TRUJILLO 1": "TRUVMJ",
    "TRUJILLO 2": "TRUVMJ2",
    "HUANCAYO": "HCYOVMJ",
    "ICA": "ICAVMJ",
    "MADRE DE DIOS": "MDVMJ",
    "SELVA": "SELVMJ",
}

DEPARTAMENTOS_POR_ZONA = {
    "LIMA": "Lima (departamento)",
    "LIMA 2": "Lima (departamento)",
    "LIMA 3": "Lima (departamento)",
    "LIMA 4": "Lima (departamento)",
    "LIMA 6": "Lima (departamento)",
    "CUSCO": "Cusco",
    "CHICLAYO": "Lambayeque",
    "AREQUIPA": "Arequipa",
    "TRUJILLO 1": "La Libertad",
    "TRUJILLO 2": "La Libertad",
    "HUANCAYO": "Junín",
    "ICA": "Ica",
    "MADRE DE DIOS": "Madre de Dios",
    "SELVA": "Amazonas",
}

ZONAS_LIMA = {"LIMA", "LIMA 2", "LIMA 3", "LIMA 4", "LIMA 6"}


def _nombre_completo(registro, fila=None):
    nombre = f"{registro.get('Nombre', '')} {registro.get('Apellido', '')}".strip()
    return nombre or (f"Fila {fila}" if fila else "Registro sin nombre")


def construir_datos_formulario(registro):
    """Calcula una sola vez los valores exactos que se mostrarán y enviarán."""
    zona = registro["Zona"]
    es_primer_hijo = "SI" if zona in ZONAS_LIMA else registro["EsPrimerHijo"]
    fecha = (
        generar_fecha_lima()
        if zona in ZONAS_LIMA
        else formatear_fecha_selva(registro["FechaNacimiento"])
    )

    return {
        "codigo": CODIGOS_POR_ZONA[zona],
        "nombre": registro["Nombre"],
        "apellido": registro["Apellido"],
        "esPrimerHijo": es_primer_hijo,
        "fechaNacimiento": fecha,
        "sexo": "10127",
        "correo": generar_correo(registro["Numero"]),
        "numeroCelular": registro["Numero"],
        "departamento": DEPARTAMENTOS_POR_ZONA[zona],
        "consentimientos": ["10139", "10140", "10141"],
    }


def _reportar_campo(callback, campo, etiqueta, valor):
    if callback:
        callback({"campo": campo, "etiqueta": etiqueta, "valor": valor})


# ─────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────

def iniciar_driver(headless=False):
    options = webdriver.ChromeOptions()
    is_docker = os.path.exists("/.dockerenv")

    if is_docker:
        options.add_argument("--headless=new")
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
    else:
        if headless:
            options.add_argument("--headless")
        service = Service()

    # Aplicar opciones optimizadas
    for option in CHROME_OPTIONS:
        options.add_argument(option)

    return webdriver.Chrome(service=service, options=options)


# ─────────────────────────────────────────────
# Envío de formulario
# ─────────────────────────────────────────────

def enviar_formulario_con_driver(
    driver,
    registro,
    on_campo=None,
    datos_formulario=None,
):
    """Envía un formulario usando un driver existente"""
    try:
        zona = str(registro.get("Zona", "")).strip().upper()
        datos = datos_formulario or construir_datos_formulario(registro)

        driver.get(FORM_URL)

        WebDriverWait(driver, SELENIUM_TIMEOUT).until(
            EC.presence_of_element_located((By.NAME, "sgE-6972673-1-74"))
        )

        # Código
        driver.find_element(By.NAME, "sgE-6972673-1-74").send_keys(datos["codigo"])
        _reportar_campo(on_campo, "codigo", "Código", datos["codigo"])

        # Datos personales
        driver.find_element(By.NAME, "sgE-6972673-1-50").send_keys(datos["nombre"])
        _reportar_campo(on_campo, "nombre", "Nombre", datos["nombre"])
        driver.find_element(By.NAME, "sgE-6972673-1-51").send_keys(datos["apellido"])
        _reportar_campo(on_campo, "apellido", "Apellido", datos["apellido"])

        # Zona / fecha
        if zona in ZONAS_LIMA:
            driver.find_element(
                By.CSS_SELECTOR, 'label[for="sgE-6972673-1-77-10128"]'
            ).click()
        else:
            if datos["esPrimerHijo"] == "SI":
                driver.find_element(
                    By.CSS_SELECTOR, 'label[for="sgE-6972673-1-77-10128"]'
                ).click()
            else:
                driver.find_element(
                    By.CSS_SELECTOR, 'label[for="sgE-6972673-1-77-10129"]'
                ).click()
        _reportar_campo(
            on_campo,
            "esPrimerHijo",
            "Es primer hijo",
            datos["esPrimerHijo"],
        )

        driver.find_element(By.NAME, "sgE-6972673-1-52").send_keys(
            datos["fechaNacimiento"]
        )
        _reportar_campo(
            on_campo,
            "fechaNacimiento",
            "Fecha de nacimiento",
            datos["fechaNacimiento"],
        )

        # Sexo
        Select(
            driver.find_element(By.NAME, "sgE-6972673-1-76")
        ).select_by_value(datos["sexo"])
        _reportar_campo(on_campo, "sexo", "Sexo", datos["sexo"])

        # Contacto
        correo = escribir_y_validar_correo(driver, registro["Numero"])
        _reportar_campo(on_campo, "correo", "Correo", correo)
        driver.find_element(By.NAME, "sgE-6972673-1-54").send_keys(
            datos["numeroCelular"]
        )
        _reportar_campo(
            on_campo,
            "numeroCelular",
            "Número celular",
            datos["numeroCelular"],
        )

        # Departamento
        Select(
            driver.find_element(By.NAME, "sgE-6972673-1-64")
        ).select_by_visible_text(datos["departamento"])
        _reportar_campo(
            on_campo,
            "departamento",
            "Departamento",
            datos["departamento"],
        )

        # Checkboxes
        driver.find_element(
            By.CSS_SELECTOR, 'label[for="sgE-6972673-1-86-10139"]'
        ).click()
        driver.find_element(
            By.CSS_SELECTOR, 'label[for="sgE-6972673-1-86-10140"]'
        ).click()
        driver.find_element(
            By.CSS_SELECTOR, 'label[for="sgE-6972673-1-86-10141"]'
        ).click()
        _reportar_campo(
            on_campo,
            "consentimientos",
            "Consentimientos",
            datos["consentimientos"],
        )

        # Segundo control después de que el campo perdió el foco y antes del submit.
        validar_correo_cargado(driver, correo)

        # Submit robusto
        submit_btn = WebDriverWait(driver, SELENIUM_TIMEOUT).until(
            EC.element_to_be_clickable((By.ID, "sg_SubmitButton"))
        )

        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});",
            submit_btn
        )
        time.sleep(0.5)

        try:
            submit_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", submit_btn)

        WebDriverWait(driver, SELENIUM_TIMEOUT).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//h2[contains(text(), 'Thank You!')]")
            )
        )

        return {"success": True}

    except Exception as e:
        try:
            os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
            driver.save_screenshot(
                f"{SCREENSHOTS_DIR}/error_{int(time.time() * 1000)}.png"
            )
        except Exception:
            pass

        return {"success": False, "error": str(e)}


def enviar_formulario(registro, headless=False):
    """Función legacy - mantener compatibilidad"""
    driver = iniciar_driver(headless)
    try:
        return enviar_formulario_con_driver(driver, registro)
    finally:
        driver.quit()


# ─────────────────────────────────────────────
# Streaming
# ─────────────────────────────────────────────

async def procesar_excel_streaming(path, headless=False):
    try:
        registros = leer_excel(path)
    except ErrorArchivoExcel as exc:
        yield json.dumps({
            "evento": "error",
            "mensaje": str(exc),
        }, ensure_ascii=False)
        return
    except Exception as exc:
        yield json.dumps({
            "evento": "error",
            "mensaje": f"No se pudo validar el archivo: {exc}",
        }, ensure_ascii=False)
        return

    total = len(registros)

    # 🚨 LÍMITE CRÍTICO
    if total > MAX_REGISTROS:
        yield json.dumps({
            "evento": "error",
            "mensaje": f"Máximo {MAX_REGISTROS} registros por carga. Archivo tiene {total} registros."
        }, ensure_ascii=False)
        return

    total_validos = sum(1 for registro in registros if registro["valido"])
    yield json.dumps({
        "evento": "inicio",
        "total": total,
        "validos": total_validos,
        "invalidos": total - total_validos,
    }, ensure_ascii=False)

    exitosos = 0
    fallidos = 0

    # 🔄 PROCESAMIENTO POR LOTES
    for batch_start in range(0, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total)
        batch = registros[batch_start:batch_end]

        yield json.dumps({
            "evento": "batch_inicio",
            "lote": f"{batch_start + 1}-{batch_end} de {total}"
        }, ensure_ascii=False)

        # 🎯 UN DRIVER POR LOTE. No se abre Chrome si todas las filas del
        # lote fallaron la validación de consistencia.
        driver = None
        error_driver = None
        try:
            if any(item["valido"] for item in batch):
                driver = iniciar_driver(headless)
        except Exception as exc:
            error_driver = str(exc)

        try:
            for i, item in enumerate(batch):
                index_global = batch_start + i + 1
                fila = item["fila"]
                registro = item["datos"]
                nombre = _nombre_completo(registro, fila)

                yield json.dumps({
                    "evento": "procesando",
                    "index": index_global,
                    "fila": fila,
                    "nombre": nombre,
                    "etapa": "validacion" if not item["valido"] else "llenado",
                    "datos": (
                        item["datos_recibidos"]
                        if not item["valido"]
                        else registro
                    ),
                }, ensure_ascii=False, default=str)

                if not item["valido"]:
                    fallidos += 1
                    mensaje = "; ".join(
                        f"{error['campo']}: {error['mensaje']}"
                        for error in item["errores"]
                    )
                    yield json.dumps({
                        "evento": "resultado",
                        "index": index_global,
                        "fila": fila,
                        "nombre": nombre,
                        "success": False,
                        "etapa": "validacion",
                        "error": mensaje,
                        "errores": item["errores"],
                        "datos": item["datos_recibidos"],
                    }, ensure_ascii=False, default=str)
                    continue

                try:
                    datos_formulario = construir_datos_formulario(registro)
                except Exception as exc:
                    fallidos += 1
                    yield json.dumps({
                        "evento": "resultado",
                        "index": index_global,
                        "fila": fila,
                        "nombre": nombre,
                        "success": False,
                        "etapa": "preparacion",
                        "error": f"No se pudieron preparar los datos: {exc}",
                        "datos": registro,
                    }, ensure_ascii=False, default=str)
                    continue

                # Este segundo evento contiene exactamente lo que se intentará
                # colocar en el formulario, incluidos los valores derivados.
                yield json.dumps({
                    "evento": "registro_preparado",
                    "index": index_global,
                    "fila": fila,
                    "nombre": nombre,
                    "datos": datos_formulario,
                }, ensure_ascii=False)

                if error_driver:
                    fallidos += 1
                    yield json.dumps({
                        "evento": "resultado",
                        "index": index_global,
                        "fila": fila,
                        "nombre": nombre,
                        "success": False,
                        "etapa": "navegador",
                        "error": f"No se pudo iniciar el navegador: {error_driver}",
                        "datos": datos_formulario,
                    }, ensure_ascii=False)
                    continue

                cola_campos = asyncio.Queue()
                loop = asyncio.get_running_loop()

                def reportar_desde_driver(campo):
                    loop.call_soon_threadsafe(cola_campos.put_nowait, campo)

                tarea = asyncio.create_task(asyncio.to_thread(
                    enviar_formulario_con_driver,
                    driver,
                    registro,
                    reportar_desde_driver,
                    datos_formulario,
                ))

                # Se drena la cola mientras Selenium trabaja para que el front
                # vea cada campo a medida que se completa, no al final.
                while True:
                    if tarea.done() and cola_campos.empty():
                        break
                    try:
                        campo = await asyncio.wait_for(
                            cola_campos.get(),
                            timeout=0.1,
                        )
                    except asyncio.TimeoutError:
                        continue

                    yield json.dumps({
                        "evento": "campo",
                        "index": index_global,
                        "fila": fila,
                        "nombre": nombre,
                        **campo,
                    }, ensure_ascii=False)

                resultado = await tarea
                if resultado["success"]:
                    exitosos += 1
                else:
                    fallidos += 1

                yield json.dumps({
                    "evento": "resultado",
                    "index": index_global,
                    "fila": fila,
                    "nombre": nombre,
                    "etapa": "envio",
                    "datos": datos_formulario,
                    **resultado
                }, ensure_ascii=False)

                await asyncio.sleep(FORM_DELAY)

        except Exception as e:
            yield json.dumps({
                "evento": "error_batch",
                "mensaje": f"Error en lote {batch_start + 1}-{batch_end}: {str(e)}"
            }, ensure_ascii=False)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        # 💤 DESCANSO ENTRE LOTES
        hay_validos_despues = any(
            item["valido"] for item in registros[batch_end:]
        )
        if driver and batch_end < total and hay_validos_despues:
            yield json.dumps({
                "evento": "batch_pausa",
                "mensaje": f"Pausa {BATCH_DELAY}s antes del siguiente lote..."
            }, ensure_ascii=False)
            await asyncio.sleep(BATCH_DELAY)

    yield json.dumps({
        "evento": "fin",
        "total": total,
        "exitosos": exitosos,
        "fallidos": fallidos,
    }, ensure_ascii=False)
