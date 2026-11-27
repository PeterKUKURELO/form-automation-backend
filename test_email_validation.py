import unittest
from unittest.mock import Mock

from form_validation import (
    CAMPO_CORREO,
    escribir_y_validar_correo,
    validar_correo_cargado,
)
from email_utils import generar_correo


class GenerarCorreoTests(unittest.TestCase):
    def test_genera_correo_completo(self):
        self.assertEqual(generar_correo("987654321"), "987654321@noemail.com")

    def test_limpia_espacios_del_numero(self):
        self.assertEqual(generar_correo(" 987654321 "), "987654321@noemail.com")

    def test_rechaza_numero_vacio(self):
        with self.assertRaises(ValueError):
            generar_correo("   ")


class ValidacionNavegadorTests(unittest.TestCase):
    def test_acepta_el_correo_completo(self):
        campo = Mock()
        campo.get_attribute.return_value = "987654321@noemail.com"
        driver = Mock()
        driver.find_element.return_value = campo

        validar_correo_cargado(driver, "987654321@noemail.com")

        driver.find_element.assert_called_once_with("name", CAMPO_CORREO)

    def test_rechaza_el_correo_sin_com(self):
        campo = Mock()
        campo.get_attribute.return_value = "987654321@noemail"
        driver = Mock()
        driver.find_element.return_value = campo

        with self.assertRaisesRegex(ValueError, "correo quedó incompleto"):
            validar_correo_cargado(driver, "987654321@noemail.com")

    def test_corrige_el_valor_si_send_keys_lo_deja_incompleto(self):
        campo = Mock()
        campo.get_attribute.side_effect = [
            "987654321@noemail",
            "987654321@noemail.com",
        ]
        driver = Mock()
        driver.find_element.return_value = campo

        correo = escribir_y_validar_correo(driver, "987654321")

        self.assertEqual(correo, "987654321@noemail.com")
        driver.execute_script.assert_called_once()


if __name__ == "__main__":
    unittest.main()
