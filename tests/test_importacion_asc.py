"""Importación de LTspice y visualización del punto de operación."""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QTextEdit
from interfaz_pyside6.importador_asc import ErrorImportacionASC, importar_asc
from interfaz_pyside6.ventana_principal import VentanaSimuladorDC


class TestImportacionASC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.w = VentanaSimuladorDC()

    def tearDown(self):
        self.w.close()

    def test_archivo_fase1_y_limpieza_al_detener(self):
        ruta = Path(__file__).parent / "fixtures" / "fase1_ltspice.asc"
        datos = importar_asc(ruta)
        self.w._restaurar_estado(datos)
        self.w._alternar_simulacion()
        self.assertTrue(self.w._analisis_exitoso)
        self.assertEqual(self.w.tabla_nodos.rowCount(), 6)
        self.assertAlmostEqual(self.w._corrientes_calculadas["V2"], 1.2)
        self.assertAlmostEqual(self.w._corrientes_calculadas["R2"], 1.2)
        variables = {self.w.tabla_variables.item(i, 0).text(): self.w.tabla_variables.item(i, 1).text()
                     for i in range(self.w.tabla_variables.rowCount())}
        self.assertEqual(variables["P(R2)"], "7,2")
        self.assertEqual(variables["V(N5)"], "9,6")
        self.assertIn("correcto", self.w._dialogo_estado.findChild(QTextEdit).toPlainText())
        self.w._alternar_simulacion()
        self.assertEqual(self.w.tabla_variables.rowCount(), 0)
        self.assertEqual(self.w.tabla_nodos.rowCount(), 0)
        self.assertEqual(self.w.tabla_lecturas.rowCount(), 0)
        self.assertFalse(self.w._dialogo_estado.isVisible())

    def test_simbolo_no_soportado_se_rechaza(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "circuito.asc"
            ruta.write_text("Version 4\nSYMBOL cap 0 0 R0\nSYMATTR InstName C1\nSYMATTR Value 1u\n", encoding="utf-8")
            with self.assertRaisesRegex(ErrorImportacionASC, "no compatible"):
                importar_asc(ruta)

    def test_error_se_muestra_con_descripcion(self):
        self.w.escena_circuito.eliminar_componente("GND")
        self.w._alternar_simulacion()
        self.assertFalse(self.w._analisis_exitoso)
        texto = self.w._dialogo_estado.findChild(QTextEdit).toPlainText()
        self.assertIn("error", texto)
        self.assertIn("Tierra", texto)

    def test_archivo_fase1_tambien_se_resuelve_con_mallas(self):
        ruta = Path(__file__).parent / "fixtures" / "fase1_ltspice.asc"
        self.w._restaurar_estado(importar_asc(ruta))
        self.w.btn_mallas.click()
        self.w._alternar_simulacion()
        self.assertTrue(self.w._analisis_exitoso)
        self.assertAlmostEqual(self.w._corrientes_calculadas["R2"], 1.2)
        self.assertTrue(self.w.tabla_matriz_a.horizontalHeaderItem(0).text().startswith("I_lazo_"))
        self.assertIn("mallas", self.w._dialogo_estado.findChild(QTextEdit).toPlainText())
        self.w.btn_nodos.click()
        self.assertFalse(self.w._simulando)
        self.assertEqual(self.w.tabla_matriz_a.rowCount(), 0)


if __name__ == "__main__":
    unittest.main()
