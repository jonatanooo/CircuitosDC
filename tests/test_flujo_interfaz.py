"""Pruebas del flujo de edición mediante widgets y eventos de Qt."""

import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData, QPointF, Qt, QTimer
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit

from interfaz_pyside6.componentes_graficos import MIME_TYPE_COMPONENTE
from interfaz_pyside6.ventana_principal import VentanaSimuladorDC


class TestFlujoInterfaz(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.w = VentanaSimuladorDC()
        self.w.resize(1420, 920)
        self.w.show()
        self.app.processEvents()

    def tearDown(self):
        self.w.close()
        self.app.processEvents()

    def _soltar(self, tipo, posicion):
        vista = self.w.vista_circuito
        punto = vista.mapFromScene(posicion)
        mime = QMimeData()
        mime.setData(MIME_TYPE_COMPONENTE, tipo.encode())
        argumentos = (Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton,
                      Qt.KeyboardModifier.NoModifier)
        entrada = QDragEnterEvent(punto, *argumentos)
        movimiento = QDragMoveEvent(punto, *argumentos)
        soltar = QDropEvent(QPointF(punto), *argumentos)
        for evento in (entrada, movimiento, soltar):
            QApplication.sendEvent(vista.viewport(), evento)
        self.assertTrue(soltar.isAccepted())
        self.app.processEvents()

    def _conectar(self, origen, destino):
        vista = self.w.vista_circuito
        p1 = vista.mapFromScene(origen.scenePos())
        p2 = vista.mapFromScene(destino.scenePos())
        QTest.mousePress(vista.viewport(), Qt.MouseButton.LeftButton, pos=p1)
        QTest.mouseMove(vista.viewport(), p2, delay=10)
        QTest.mouseRelease(vista.viewport(), Qt.MouseButton.LeftButton, pos=p2)
        self.app.processEvents()

    def test_construir_conectar_guardar_y_abrir(self):
        self.w._slot_limpiar_lienzo()
        self.w.vista_circuito.centerOn(440, 180)
        self.app.processEvents()
        self._soltar("FUENTE_VOLTAJE", QPointF(260, 140))
        self._soltar("RESISTENCIA", QPointF(440, 140))
        self._soltar("TIERRA", QPointF(550, 230))
        elementos = list(self.w.escena_circuito.componentes_graficos.values())
        fuente, resistencia, tierra = elementos
        self._conectar(fuente.terminal_a, resistencia.terminal_a)
        self._conectar(resistencia.terminal_b, fuente.terminal_b)
        self._conectar(fuente.terminal_b, tierra.terminal_a)
        self.assertEqual(len(self.w.escena_circuito.cables_graficos), 3)
        self.w._alternar_simulacion()
        self.assertTrue(self.w._analisis_exitoso)
        self.assertAlmostEqual(self.w._corrientes_calculadas[resistencia.id_ref], 1.2)
        with tempfile.TemporaryDirectory() as carpeta:
            archivo = os.path.join(carpeta, "prueba.json")
            with patch("interfaz_pyside6.ventana_principal.QFileDialog.getSaveFileName",
                       return_value=(archivo, "")):
                self.w._guardar_circuito()
            self.w._slot_limpiar_lienzo()
            with patch("interfaz_pyside6.ventana_principal.QFileDialog.getOpenFileName",
                       return_value=(archivo, "")):
                self.w._abrir_circuito()
            self.assertEqual(len(self.w.escena_circuito.cables_graficos), 3)
            self.assertEqual(self.w.tabla_nodos.rowCount(), 0)
            self.w._alternar_simulacion()
            self.assertTrue(self.w._analisis_exitoso)
            self.assertAlmostEqual(self.w._corrientes_calculadas[resistencia.id_ref], 1.2)

    def test_editar_unidades_y_deshacer(self):
        def completar_dialogo():
            dialogo = self.app.activeModalWidget()
            campos = dialogo.findChildren(QLineEdit)
            campos[0].setText("R_control")
            campos[1].setText("0.005")
            dialogo.findChild(QComboBox).setCurrentText("kΩ")
            dialogo.accept()

        QTimer.singleShot(50, completar_dialogo)
        item = self.w.escena_circuito.componentes_graficos["R_5"]
        punto = self.w.vista_circuito.mapFromScene(item.scenePos())
        QTest.mouseDClick(self.w.vista_circuito.viewport(), Qt.MouseButton.LeftButton, pos=punto)
        componentes = self.w.escena_circuito.componentes_graficos
        self.assertEqual(float(componentes["R_control"].valor_str), 5.0)
        self.assertEqual(componentes["CCVS1"].componente_control_ref, "R_control")
        self.w.activateWindow()
        self.w.vista_circuito.setFocus()
        self.app.processEvents()
        QTest.keyClick(self.w.vista_circuito, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        self.assertIn("R_5", componentes)
        self.assertEqual(componentes["CCVS1"].componente_control_ref, "R_5")

    def test_validar_terminal_abierto_y_valor(self):
        errores = []
        self.w._mostrar_ventana_error_calculo = lambda titulo, detalle: errores.append((titulo, detalle))
        cable = self.w.escena_circuito.cables_graficos[0]
        self.w.escena_circuito.eliminar_cable(cable)
        self.w._alternar_simulacion()
        self.assertFalse(self.w._analisis_exitoso)
        self.assertIn("desconectado", errores[-1][1])
        self.w._sincronizar_seleccion("R_5")
        self.w.input_valor_prop.setText("0")
        self.w._slot_aplicar_valor_propiedad()
        self.assertIn("mayor que cero", errores[-1][1])

    def test_indicador_y_validacion_de_tierra(self):
        errores = []
        self.w._mostrar_ventana_error_calculo = lambda titulo, detalle: errores.append((titulo, detalle))
        self.assertTrue(self.w.chk_ref_n0.isChecked())
        self.w.escena_circuito.eliminar_componente("GND")
        self.assertFalse(self.w.chk_ref_n0.isChecked())
        self.w._alternar_simulacion()
        self.assertFalse(self.w._analisis_exitoso)
        self.assertIn("Tierra", errores[-1][1])

    def test_seleccionar_mover_componente_y_deshacer(self):
        vista = self.w.vista_circuito
        resistencia = self.w.escena_circuito.componentes_graficos["R_5"]
        inicio = QPointF(resistencia.pos())
        punto = vista.mapFromScene(resistencia.scenePos())
        QTest.mouseClick(vista.viewport(), Qt.MouseButton.LeftButton, pos=punto)
        self.assertEqual(self.w._id_actual, "R_5")
        QTest.mousePress(vista.viewport(), Qt.MouseButton.LeftButton, pos=punto)
        QTest.mouseMove(vista.viewport(), punto + type(punto)(30, 20), delay=20)
        QTest.mouseRelease(vista.viewport(), Qt.MouseButton.LeftButton,
                           pos=punto + type(punto)(30, 20))
        self.assertNotEqual(resistencia.pos(), inicio)
        self.assertEqual(resistencia.terminal_a.cables_conectados[0].line().p2(),
                         resistencia.terminal_a.scenePos())
        self.w._deshacer()
        self.assertEqual(self.w.escena_circuito.componentes_graficos["R_5"].pos(), inicio)

    def test_zoom_mano_y_tamanos(self):
        vista = self.w.vista_circuito
        self.w.slider_zoom.setValue(150)
        self.assertAlmostEqual(vista.transform().m11(), 1.5)
        vista.establecer_modo_mano(True)
        h, v = vista.horizontalScrollBar(), vista.verticalScrollBar()
        antes = (h.value(), v.value())
        origen = vista.viewport().rect().center()
        destino = origen + type(origen)(40, 30)
        QTest.mousePress(vista.viewport(), Qt.MouseButton.LeftButton, pos=origen)
        QTest.mouseMove(vista.viewport(), destino, delay=10)
        QTest.mouseRelease(vista.viewport(), Qt.MouseButton.LeftButton, pos=destino)
        self.assertNotEqual(h.value(), antes[0])
        self.assertNotEqual(v.value(), antes[1])
        for ancho, alto in ((1420, 920), (1280, 720), (1024, 768)):
            self.w.resize(ancho, alto)
            self.app.processEvents()
            self.assertGreater(vista.width(), 0)
            self.assertGreater(self.w.tabla_nodos.height(), 0)


if __name__ == "__main__":
    unittest.main()
