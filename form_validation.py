from email_utils import generar_correo


CAMPO_CORREO = "sgE-6972673-1-53"


def escribir_y_validar_correo(driver, numero):
    """Escribe el correo y comprueba el valor real conservado por el navegador."""
    correo_esperado = generar_correo(numero)
    campo = driver.find_element("name", CAMPO_CORREO)

    campo.clear()
    campo.send_keys(correo_esperado)
    correo_cargado = (campo.get_attribute("value") or "").strip()

    # Si algún evento del formulario o del navegador alteró el texto, se asigna
    # mediante el setter nativo y se notifican los mismos eventos de un usuario.
    if correo_cargado != correo_esperado:
        driver.execute_script(
            """
            const campo = arguments[0];
            const valor = arguments[1];
            const setter = Object.getOwnPropertyDescriptor(
                HTMLInputElement.prototype,
                'value'
            ).set;
            setter.call(campo, valor);
            campo.dispatchEvent(new Event('input', { bubbles: true }));
            campo.dispatchEvent(new Event('change', { bubbles: true }));
            """,
            campo,
            correo_esperado,
        )

    validar_correo_cargado(driver, correo_esperado)
    return correo_esperado


def validar_correo_cargado(driver, correo_esperado):
    """Impide enviar si el campo perdió una parte del correo, incluido `.com`."""
    campo = driver.find_element("name", CAMPO_CORREO)
    correo_cargado = (campo.get_attribute("value") or "").strip()

    if correo_cargado != correo_esperado or not correo_cargado.endswith(".com"):
        raise ValueError(
            "El correo quedó incompleto en el formulario "
            f"(esperado={len(correo_esperado)} caracteres, "
            f"cargado={len(correo_cargado)} caracteres)"
        )
