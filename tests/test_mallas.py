"""Comparación del análisis de lazos con la solución nodal independiente."""
import unittest
import numpy as np
from modulo1_modelo import AnalizadorNodos, Circuito
from modulo2_motor.analizador_mallas import AnalizadorMallas
from modulo2_motor import MotorNumericoNumPy, AnalizadorSimbolicoYResultados, ErrorCircuitoSingular
from test_circuito_drag_drop import construir_y_resolver_circuito_ccvs


class TestAnalisisMallas(unittest.TestCase):
    def comprobar(self, circuito):
        sn = AnalizadorNodos(circuito).construir_sistema()
        nodal = MotorNumericoNumPy.resolver(sn)
        sm, mallas = AnalizadorMallas(circuito).resolver()
        self.assertEqual(set(nodal.voltajes_nodos), set(mallas.voltajes_nodos))
        for nodo in nodal.voltajes_nodos:
            self.assertAlmostEqual(nodal.voltajes_nodos[nodo], mallas.voltajes_nodos[nodo], places=7)
        for fuente in nodal.corrientes_fuentes_v:
            self.assertAlmostEqual(nodal.corrientes_fuentes_v[fuente], mallas.corrientes_fuentes_v[fuente], places=7)
        reporte = AnalizadorSimbolicoYResultados.calcular_magnitudes_circuito(circuito, sm, mallas)
        self.assertLess(reporte.error_balance_potencia, 1e-8)
        np.testing.assert_allclose(sm.matriz_A @ mallas.vector_x, sm.vector_b, atol=1e-9)
        return sm, mallas, reporte

    def test_circuito_fase1_ccvs(self):
        circuito, _, _, _ = construir_y_resolver_circuito_ccvs()
        sm, sol, reporte = self.comprobar(circuito)
        self.assertEqual(len(sm.etiquetas_incognitas), 3)
        self.assertAlmostEqual(sol.voltajes_nodos[1], 16)
        self.assertAlmostEqual(reporte.resultados_elementos['R_5ohm'].potencia_w, 7.2)

    def test_supermalla_fuentes_corriente(self):
        c = Circuito('Supermalla')
        c.agregar_fuente_corriente('I1', 0, 1, 4)
        c.agregar_resistencia('R1', 1, 0, 2)
        c.agregar_resistencia('R2', 1, 2, 4)
        c.agregar_resistencia('R3', 2, 0, 2)
        c.agregar_fuente_corriente('I2', 2, 0, 2)
        sm, sol, _ = self.comprobar(c)
        self.assertTrue(any(s.startswith('V_I') for s in sm.etiquetas_incognitas))
        self.assertAlmostEqual(sol.voltajes_nodos[1], 5)
        self.assertAlmostEqual(sol.voltajes_nodos[2], -1)

    def test_fuente_flotante(self):
        c = Circuito('Fuente flotante')
        c.agregar_fuente_corriente('I1', 0, 1, 2)
        c.agregar_resistencia('R1', 1, 0, 2)
        c.agregar_resistencia('R2', 2, 0, 4)
        c.agregar_resistencia('R3', 1, 2, 10)
        c.agregar_fuente_voltaje('V1', 1, 2, 2)
        c.agregar_fuente_corriente('I2', 2, 0, 7)
        _, sol, _ = self.comprobar(c)
        self.assertAlmostEqual(sol.voltajes_nodos[1], -6)
        self.assertAlmostEqual(sol.voltajes_nodos[2], -8)

    def test_circuito_singular(self):
        c = Circuito('Fuentes incompatibles')
        c.agregar_fuente_voltaje('V1', 1, 0, 10)
        c.agregar_fuente_voltaje('V2', 1, 0, 5)
        c.agregar_resistencia('R1', 1, 0, 10)
        with self.assertRaises(ErrorCircuitoSingular):
            AnalizadorMallas(c).resolver()

    def test_lazos_sin_gnd(self):
        c = Circuito('Flotante')
        c.agregar_resistencia('R1', 1, 2, 10)
        c.agregar_fuente_voltaje('V1', 1, 2, 5)
        with self.assertRaisesRegex(ValueError, 'GND'):
            AnalizadorMallas(c).resolver()

if __name__ == '__main__':
    unittest.main()
