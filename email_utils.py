import re


DOMINIO_CORREO = "noemail.com"
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def generar_correo(numero):
    numero_limpio = str(numero).strip()

    if not numero_limpio or numero_limpio.lower() == "nan":
        raise ValueError("No se puede generar el correo: el número está vacío")

    correo = f"{numero_limpio}@{DOMINIO_CORREO}"
    if not PATRON_CORREO.fullmatch(correo) or not correo.endswith(".com"):
        raise ValueError("No se pudo generar un correo válido y completo")

    return correo


def resolver_correo(numero, correo_recibido=None):
    """Usa el correo recibido o genera uno cuando la celda está vacía."""
    correo = "" if correo_recibido is None else str(correo_recibido).strip()
    if not correo or correo.lower() == "nan":
        return generar_correo(numero)

    if not PATRON_CORREO.fullmatch(correo):
        raise ValueError("El correo recibido no tiene un formato válido")

    return correo
