"""Comparación de fase 1 y selección visual de resultados."""
import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidget
from PySide6.QtTest import QTest

from interfaz_pyside6.importador_asc import importar_asc
from interfaz_pyside6.ventana_principal import VentanaSimuladorDC


class TestComparacionResultados(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.w = VentanaSimuladorDC()
        self.w.show()
        self.app.processEvents()

    def tearDown(self):
        self.w.close()

    def test_comparar_y_voltajes_en_cables(self):
        self.assertFalse(self.w.btn_comparar.isEnabled())
        self.assertFalse(self.w._accion_comparar.isVisible())
        self.w._alternar_simulacion()
        self.assertTrue(self.w.btn_comparar.isEnabled())
        self.assertTrue(self.w._accion_comparar.isVisible())
        filas, modificados = self.w._comparacion_actual
        self.assertFalse(modificados)
        self.assertEqual(len(filas), 5)
        for _, referencia, obtenido, _ in filas:
            self.assertAlmostEqual(referencia, obtenido)
        self.assertTrue(all(c.voltaje_nodo is not None for c in self.w.escena_circuito.cables_graficos))
        self.w._mostrar_comparacion()
        tabla = self.w._dialogo_comparacion.findChild(QTableWidget)
        self.assertEqual([tabla.item(i, 3).text() for i in range(5)], ["0,0000 %"] * 5)
        self.w._alternar_simulacion()
        self.assertFalse(self.w.btn_comparar.isEnabled())
        self.assertFalse(self.w._accion_comparar.isVisible())
        self.assertTrue(all(c.voltaje_nodo is None for c in self.w.escena_circuito.cables_graficos))

    def test_referencia_ltspice_y_parametros_cambiados(self):
        ruta = Path(__file__).parent / "fixtures" / "fase1_ltspice.asc"
        self.w._restaurar_estado(importar_asc(ruta))
        self.w._alternar_simulacion()
        filas, modificados = self.w._comparacion_actual
        self.assertFalse(modificados)
        self.assertAlmostEqual(filas[3][2], 1.2)
        self.w._alternar_simulacion()
        self.w._sincronizar_seleccion("R2")
        self.w.input_valor_prop.setText("6")
        self.w._slot_aplicar_valor_propiedad()
        self.w._alternar_simulacion()
        filas, modificados = self.w._comparacion_actual
        self.assertTrue(modificados)
        self.assertNotAlmostEqual(filas[3][1], filas[3][2])

    def test_seleccion_de_componentes_y_nodos(self):
        self.w._alternar_simulacion()
        tabla = self.w.tabla_variables
        fila = next(i for i in range(tabla.rowCount()) if tabla.item(i, 0).text() == "I(R_5)")
        self.w._dialogo_estado.close()
        tabla.scrollToItem(tabla.item(fila, 0))
        self.app.processEvents()
        QTest.mouseClick(tabla.viewport(), Qt.MouseButton.LeftButton,
                         pos=tabla.visualItemRect(tabla.item(fila, 0)).center())
        self.assertTrue(self.w.escena_circuito.componentes_graficos["R_5"].isSelected())
        fila = next(i for i in range(tabla.rowCount()) if tabla.item(i, 0).text() == "V(V1)")
        self.w._seleccionar_variable_resultado(fila, 0)
        cables = self.w.escena_circuito.cables_graficos
        self.assertTrue(any(c.resaltado_nodo for c in cables))
        self.assertTrue(all(c.terminal_origen.etiqueta_nodo == "V1" for c in cables if c.resaltado_nodo))
        self.w._sincronizar_seleccion("R_5")
        self.assertFalse(any(c.resaltado_nodo for c in cables))


if __name__ == "__main__":
    unittest.main()
