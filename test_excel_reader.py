import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

from excel_reader import ErrorArchivoExcel, leer_excel
from selenium_worker import procesar_excel_streaming


class ExcelReaderTests(unittest.TestCase):
    def _crear_excel(self, filas):
        archivo = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        archivo.close()
        pd.DataFrame(filas).to_excel(archivo.name, index=False)
        self.addCleanup(Path(archivo.name).unlink, missing_ok=True)
        return archivo.name

    def test_reporta_fila_invalida_y_conserva_la_siguiente(self):
        ruta = self._crear_excel([
            {
                "Nombre": "",
                "Apellido": "Rojas",
                "Número Celular": "123",
                "Zona": "DESCONOCIDA",
                "Es Primer Hijo": "quizás",
                "Fecha de Nacimiento": "no-es-fecha",
            },
            {
                "Nombre": "Camila",
                "Apellido": "Rojas",
                "Número Celular": 987654321,
                "Zona": "lima",
                "Es Primer Hijo": "sí",
                "Fecha de Nacimiento": datetime(2024, 1, 15),
            },
        ])

        registros = leer_excel(ruta)

        self.assertEqual(len(registros), 2)
        self.assertFalse(registros[0]["valido"])
        self.assertGreaterEqual(len(registros[0]["errores"]), 5)
        self.assertTrue(registros[1]["valido"])
        self.assertEqual(registros[1]["datos"]["Numero"], "987654321")
        self.assertEqual(registros[1]["datos"]["Zona"], "LIMA")
        self.assertEqual(registros[1]["datos"]["EsPrimerHijo"], "SI")

    def test_falla_el_archivo_si_falta_una_columna_requerida(self):
        ruta = self._crear_excel([{"Nombre": "Camila"}])

        with self.assertRaisesRegex(ErrorArchivoExcel, "Faltan columnas"):
            leer_excel(ruta)

    def test_conserva_correo_opcional_y_permite_celda_vacia(self):
        ruta = self._crear_excel([
            {
                "Nombre": "Camila",
                "Apellido": "Rojas",
                "Número Celular": "987654321",
                "Zona": "CUSCO",
                "Es Primer Hijo": "SI",
                "Fecha de Nacimiento": datetime(2024, 1, 15),
                "Correo": "camila@gmail.com",
            },
            {
                "Nombre": "Mateo",
                "Apellido": "Quispe",
                "Número Celular": "912345678",
                "Zona": "CUSCO",
                "Es Primer Hijo": "NO",
                "Fecha de Nacimiento": datetime(2024, 2, 10),
                "Correo": None,
            },
        ])

        registros = leer_excel(ruta)

        self.assertTrue(registros[0]["valido"])
        self.assertEqual(registros[0]["datos"]["Correo"], "camila@gmail.com")
        self.assertTrue(registros[1]["valido"])
        self.assertEqual(registros[1]["datos"]["Correo"], "")

    def test_reporta_correo_opcional_invalido(self):
        ruta = self._crear_excel([{
            "Nombre": "Camila",
            "Apellido": "Rojas",
            "Número Celular": "987654321",
            "Zona": "CUSCO",
            "Es Primer Hijo": "SI",
            "Fecha de Nacimiento": datetime(2024, 1, 15),
            "Correo": "correo-incompleto",
        }])

        registro = leer_excel(ruta)[0]

        self.assertFalse(registro["valido"])
        self.assertEqual(registro["errores"][0]["campo"], "Correo")


class StreamingTests(unittest.IsolatedAsyncioTestCase):
    async def test_emite_error_individual_campo_y_continua(self):
        invalido = {
            "fila": 2,
            "valido": False,
            "datos": {
                "Nombre": "",
                "Apellido": "Rojas",
                "Numero": "123",
                "Zona": "",
                "EsPrimerHijo": "NO",
                "FechaNacimiento": None,
            },
            "datos_recibidos": {"Nombre": None, "Número Celular": "123"},
            "errores": [{
                "campo": "Nombre",
                "mensaje": "El nombre es obligatorio",
                "valor": None,
            }],
        }
        valido = {
            "fila": 3,
            "valido": True,
            "datos": {
                "Nombre": "Camila",
                "Apellido": "Rojas",
                "Numero": "987654321",
                "Zona": "LIMA",
                "EsPrimerHijo": "SI",
                "FechaNacimiento": datetime(2024, 1, 15),
            },
            "datos_recibidos": {},
            "errores": [],
        }
        datos_formulario = {
            "codigo": "LIMVMJ02",
            "nombre": "Camila",
            "apellido": "Rojas",
            "esPrimerHijo": "SI",
            "fechaNacimiento": "01/15/2025",
            "sexo": "10127",
            "correo": "987654321@noemail.com",
            "numeroCelular": "987654321",
            "departamento": "Lima (departamento)",
            "consentimientos": ["10139", "10140", "10141"],
        }
        driver = Mock()

        def enviar(_driver, _registro, callback, _datos):
            callback({"campo": "nombre", "etiqueta": "Nombre", "valor": "Camila"})
            return {"success": True}

        with (
            patch("selenium_worker.leer_excel", return_value=[invalido, valido]),
            patch("selenium_worker.iniciar_driver", return_value=driver),
            patch(
                "selenium_worker.construir_datos_formulario",
                return_value=datos_formulario,
            ),
            patch("selenium_worker.enviar_formulario_con_driver", side_effect=enviar),
        ):
            eventos = [
                json.loads(evento)
                async for evento in procesar_excel_streaming("prueba.xlsx", True)
            ]

        resultados = [e for e in eventos if e["evento"] == "resultado"]
        self.assertEqual(len(resultados), 2)
        self.assertFalse(resultados[0]["success"])
        self.assertEqual(resultados[0]["etapa"], "validacion")
        self.assertTrue(resultados[1]["success"])
        self.assertTrue(any(e["evento"] == "campo" for e in eventos))
        self.assertEqual(eventos[-1]["evento"], "fin")
        self.assertEqual(eventos[-1]["exitosos"], 1)
        self.assertEqual(eventos[-1]["fallidos"], 1)


if __name__ == "__main__":
    unittest.main()
