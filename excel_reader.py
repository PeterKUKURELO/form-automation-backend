import math
import re
from datetime import datetime

import pandas as pd

from email_utils import PATRON_CORREO


COLUMNAS_REQUERIDAS = (
    "Nombre",
    "Apellido",
    "Número Celular",
    "Zona",
    "Es Primer Hijo",
    "Fecha de Nacimiento",
)

ZONAS_VALIDAS = {
    "LIMA",
    "LIMA 2",
    "LIMA 3",
    "LIMA 4",
    "LIMA 6",
    "CUSCO",
    "CHICLAYO",
    "AREQUIPA",
    "TRUJILLO 1",
    "TRUJILLO 2",
    "HUANCAYO",
    "ICA",
    "MADRE DE DIOS",
    "SELVA",
}

PATRON_CELULAR = re.compile(r"^\d{9}$")


class ErrorArchivoExcel(ValueError):
    """Error que impide interpretar el archivo completo."""


def _esta_vacio(valor):
    try:
        return valor is None or bool(pd.isna(valor))
    except (TypeError, ValueError):
        return False


def _texto(valor):
    return "" if _esta_vacio(valor) else str(valor).strip()


def _celular(valor):
    if _esta_vacio(valor):
        return ""

    # Excel suele convertir un celular numérico en float. Se evita exponer el
    # sufijo artificial `.0`, sin modificar valores que realmente no son enteros.
    if isinstance(valor, float) and math.isfinite(valor) and valor.is_integer():
        return str(int(valor))
    if isinstance(valor, int):
        return str(valor)
    return str(valor).strip()


def _valor_serializable(valor):
    if _esta_vacio(valor):
        return None
    if isinstance(valor, (pd.Timestamp, datetime)):
        return valor.isoformat()
    if hasattr(valor, "item"):
        try:
            return valor.item()
        except (TypeError, ValueError):
            pass
    return valor


def _agregar_error(errores, campo, mensaje, valor):
    errores.append({
        "campo": campo,
        "mensaje": mensaje,
        "valor": _valor_serializable(valor),
    })


def validar_fila(row, numero_fila):
    """Normaliza una fila y devuelve sus errores sin detener las demás."""
    nombre = _texto(row["Nombre"])
    apellido = _texto(row["Apellido"])
    numero = _celular(row["Número Celular"])
    zona = _texto(row["Zona"]).upper()
    es_primer_hijo = _texto(row["Es Primer Hijo"]).upper().replace("Í", "I")
    correo = _texto(row.get("Correo"))
    fecha_original = row["Fecha de Nacimiento"]
    fecha = pd.to_datetime(fecha_original, errors="coerce")

    errores = []
    if not nombre:
        _agregar_error(errores, "Nombre", "El nombre es obligatorio", row["Nombre"])
    if not apellido:
        _agregar_error(
            errores,
            "Apellido",
            "El apellido es obligatorio",
            row["Apellido"],
        )
    if not numero:
        _agregar_error(
            errores,
            "Número Celular",
            "El número celular es obligatorio",
            row["Número Celular"],
        )
    elif not PATRON_CELULAR.fullmatch(numero):
        _agregar_error(
            errores,
            "Número Celular",
            "El número celular debe contener exactamente 9 dígitos",
            row["Número Celular"],
        )
    if not zona:
        _agregar_error(errores, "Zona", "La zona es obligatoria", row["Zona"])
    elif zona not in ZONAS_VALIDAS:
        _agregar_error(
            errores,
            "Zona",
            f"Zona no reconocida: {zona}",
            row["Zona"],
        )
    if es_primer_hijo not in {"SI", "NO"}:
        _agregar_error(
            errores,
            "Es Primer Hijo",
            "El valor debe ser SI o NO",
            row["Es Primer Hijo"],
        )
    if correo and not PATRON_CORREO.fullmatch(correo):
        _agregar_error(
            errores,
            "Correo",
            "El correo no tiene un formato válido",
            row.get("Correo"),
        )
    if pd.isna(fecha):
        _agregar_error(
            errores,
            "Fecha de Nacimiento",
            "La fecha de nacimiento es obligatoria y debe ser válida",
            fecha_original,
        )

    datos = {
        "Nombre": nombre,
        "Apellido": apellido,
        "Numero": numero,
        "Zona": zona,
        "EsPrimerHijo": es_primer_hijo,
        "Correo": correo,
        "FechaNacimiento": None if pd.isna(fecha) else fecha.to_pydatetime(),
    }
    datos_recibidos = {
        columna: _valor_serializable(row[columna])
        for columna in COLUMNAS_REQUERIDAS
    }
    if "Correo" in row.index:
        datos_recibidos["Correo"] = _valor_serializable(row["Correo"])

    return {
        "fila": numero_fila,
        "valido": not errores,
        "datos": datos,
        "datos_recibidos": datos_recibidos,
        "errores": errores,
    }


def leer_excel(ruta):
    """Lee el archivo y conserva tanto filas válidas como inválidas."""
    try:
        df = pd.read_excel(ruta, dtype=object)
    except Exception as exc:
        raise ErrorArchivoExcel(f"No se pudo leer el archivo Excel: {exc}") from exc

    faltantes = [
        columna
        for columna in COLUMNAS_REQUERIDAS
        if columna not in df.columns
    ]
    if faltantes:
        raise ErrorArchivoExcel(
            "Faltan columnas requeridas: " + ", ".join(faltantes)
        )

    return [
        validar_fila(row, numero_fila=indice + 2)
        for indice, (_, row) in enumerate(df.iterrows())
    ]
