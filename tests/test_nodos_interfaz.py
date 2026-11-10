"""Regresiones de conectividad y etiquetas del circuito gráfico."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF

from interfaz_pyside6.ventana_principal import VentanaSimuladorDC


class TestNodosInterfaz(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.ventana = VentanaSimuladorDC()
        self.escena = self.ventana.escena_circuito

    def tearDown(self):
        self.ventana.close()

    def test_etiquetas_de_circuito_cargado_y_restaurado(self):
        esperadas = {"N_Vs", "V1", "V2", "V3", "GND"}
        self.assertEqual({c.etiqueta_nodo for c in self.escena.cables_graficos}, esperadas)
        self.ventana._restaurar_estado(self.ventana._estado_circuito())
        self.assertEqual({c.etiqueta_nodo for c in self.escena.cables_graficos}, esperadas)

    def test_resultados_se_generan_al_simular_y_se_invalidan_al_editar(self):
        self.assertEqual(self.ventana.tabla_nodos.rowCount(), 0)
        self.assertEqual(self.ventana.tabla_lecturas.rowCount(), 0)
        self.assertEqual(self.ventana.lbl_valor_voltaje_prop.text(), "—")
        self.ventana._alternar_simulacion()
        tabla = self.ventana.tabla_nodos
        valores = {tabla.item(fila, 0).text(): tabla.item(fila, 1).text()
                   for fila in range(tabla.rowCount())}
        self.assertEqual(valores, {"GND": "0,000 V", "N_Vs": "20,000 V",
                                   "V1": "16,000 V", "V2": "10,000 V", "V3": "9,600 V"})
        self.ventana.input_valor_prop.setText("6")
        self.ventana._slot_aplicar_valor_propiedad()
        self.assertEqual(tabla.rowCount(), 0)
        self.assertEqual(self.ventana.tabla_lecturas.rowCount(), 0)
        self.assertEqual(self.ventana.lbl_valor_voltaje_prop.text(), "—")

    def test_separar_nodo_no_mantiene_ids_iguales(self):
        cable = next(c for c in self.escena.cables_graficos
                     if c.terminal_origen.componente_padre.id_ref == "R_20"
                     and c.terminal_destino.componente_padre.id_ref == "R_5")
        self.escena.eliminar_cable(cable)
        self.escena.recalcular_nodos_desde_cables()
        componentes = self.escena.componentes_graficos
        self.assertNotEqual(componentes["R_20"].terminal_a.id_nodo,
                            componentes["R_5"].terminal_a.id_nodo)
        self.ventana._deshacer()
        self.ventana._alternar_simulacion()
        self.assertAlmostEqual(self.ventana._corrientes_calculadas["R_5"], 1.2)

    def test_resultados_incluyen_nodo_adicional(self):
        componentes = self.escena.componentes_graficos
        cable = next(c for c in self.escena.cables_graficos
                     if c.terminal_origen.componente_padre.id_ref == "R_5"
                     and c.terminal_destino.componente_padre.id_ref == "R_10")
        self.escena.eliminar_cable(cable)
        resistencia = self.escena.instanciar_componente_por_drop("RESISTENCIA", QPointF(470, 85))
        self.escena.conectar_terminales_con_cable(componentes["R_5"].terminal_b, resistencia.terminal_a)
        self.escena.conectar_terminales_con_cable(resistencia.terminal_b, componentes["R_10"].terminal_a)
        self.ventana._alternar_simulacion()
        self.assertTrue(self.ventana._analisis_exitoso)
        self.assertEqual(self.ventana.tabla_nodos.rowCount(), 6)
        self.assertIsNone(self.ventana._comparacion_actual)

    def test_matriz_muestra_coeficientes_solucion_y_se_limpia(self):
        self.assertEqual(self.ventana.tabla_matriz_a.rowCount(), 0)
        self.ventana._alternar_simulacion()
        matriz = self.ventana.tabla_matriz_a
        solucion = self.ventana.tabla_vector_x
        termino = self.ventana.tabla_vector_b
        self.assertEqual((matriz.rowCount(), matriz.columnCount()), (6, 6))
        self.assertEqual(matriz.horizontalHeaderItem(0).text(), "V_V1")
        self.assertAlmostEqual(float(matriz.item(0, 0).text().replace(",", ".")), 0.75)
        self.assertEqual(solucion.item(0, 0).text(), "V_V1")
        self.assertAlmostEqual(float(solucion.item(0, 1).text().replace(",", ".")), 16)
        self.assertAlmostEqual(float(termino.item(0, 0).text().replace(",", ".")), 0)
        self.ventana._alternar_simulacion()
        self.assertEqual(matriz.rowCount(), 0)
        self.assertEqual(solucion.rowCount(), 0)


if __name__ == "__main__":
    unittest.main()
