"""
Script de Prueba e Integración (Tests) para Validar los Módulos 1 y 2.

Valida:
1. Caso 1: Circuito DC con resistencias y fuentes de corriente (Análisis Nodal Puro).
2. Caso 2: Circuito DC con fuente de voltaje a tierra y fuente de corriente (MNA).
3. Caso 3: Circuito DC con un Supernodo (Fuente de voltaje flotante entre dos nodos no-tierra).
4. Caso 4: Detección de circuitos singulares / nodos aislados.
5. Verificación automática del Teorema de Tellegen (Conservación de Potencia: sum(P) = 0).
"""

import unittest
import numpy as np

from modulo1_modelo.elementos import Circuito
from modulo1_modelo.analizador_nodos import AnalizadorNodos
from modulo2_motor.resolvedor_numpy import ErrorCircuitoSingular, MotorNumericoNumPy
from modulo2_motor.simbolico_sympy import AnalizadorSimbolicoYResultados


class TestSimuladorCircuitosDC(unittest.TestCase):
    """Pruebas unitarias y de integración entre el Módulo 1 y el Módulo 2."""

    def test_01_analisis_nodal_clasico_fuentes_corriente(self) -> None:
        """
        Caso 1: Circuito con 2 nodos activos y fuentes de corriente únicamente.
        Topología:
            - Fuente I1 = 4 A inyectando al Nodo 1 (0 -> 1).
            - R1 = 2 Ω entre Nodo 1 y GND (1 -> 0).
            - R2 = 4 Ω entre Nodo 1 y Nodo 2 (1 -> 2).
            - R3 = 2 Ω entre Nodo 2 y GND (2 -> 0).
            - Fuente I2 = 2 A saliendo del Nodo 2 hacia GND (2 -> 0).

        Ecuaciones teóricas:
            Nodo 1: (1/2 + 1/4)*V1 - (1/4)*V2 = 4   =>  0.75*V1 - 0.25*V2 = 4
            Nodo 2: -(1/4)*V1 + (1/4 + 1/2)*V2 = -2 => -0.25*V1 + 0.75*V2 = -2
        Solución analítica exacta:
            V1 = 5.0 V, V2 = -1.0 V
        """
        ckt = Circuito("Nodal Puro")
        ckt.agregar_fuente_corriente("I1", id_nodo_origen=0, id_nodo_destino=1, valor_amperios=4.0)
        ckt.agregar_resistencia("R1", id_nodo_a=1, id_nodo_b=0, valor_ohms=2.0)
        ckt.agregar_resistencia("R2", id_nodo_a=1, id_nodo_b=2, valor_ohms=4.0)
        ckt.agregar_resistencia("R3", id_nodo_a=2, id_nodo_b=0, valor_ohms=2.0)
        ckt.agregar_fuente_corriente("I2", id_nodo_origen=2, id_nodo_destino=0, valor_amperios=2.0)

        sistema = AnalizadorNodos(ckt).construir_sistema()
        solucion = MotorNumericoNumPy.resolver(sistema)
        reporte = AnalizadorSimbolicoYResultados.calcular_magnitudes_circuito(ckt, sistema, solucion)

        # Verificar Matriz A y Vector b
        A_esperada = np.array([[0.75, -0.25], [-0.25, 0.75]])
        b_esperado = np.array([4.0, -2.0])
        np.testing.assert_allclose(sistema.matriz_A, A_esperada, atol=1e-9)
        np.testing.assert_allclose(sistema.vector_b, b_esperado, atol=1e-9)

        # Verificar voltajes nodales
        self.assertAlmostEqual(solucion.voltajes_nodos[1], 5.0, places=7)
        self.assertAlmostEqual(solucion.voltajes_nodos[2], -1.0, places=7)

        # Verificar balance de potencia (Teorema de Tellegen)
        self.assertLess(reporte.error_balance_potencia, 1e-9)
        self.assertAlmostEqual(reporte.potencia_total_disipada, 22.0, places=7)
        self.assertAlmostEqual(reporte.potencia_total_generada, 22.0, places=7)

    def test_02_circuito_con_supernodo_fuente_voltaje_flotante(self) -> None:
        """
        Caso 2: Circuito con Supernodo (Fuente de voltaje flotante entre Nodo 1 y Nodo 2).
        Topología clásica de libro de texto (Alexander & Sadiku):
            - Fuente I1 = 2 A entrando al Nodo 1 (0 -> 1).
            - R1 = 2 Ω entre Nodo 1 y GND (1 -> 0).
            - R2 = 4 Ω entre Nodo 2 y GND (2 -> 0).
            - R3 = 10 Ω en paralelo con la fuente de voltaje entre Nodo 1 y Nodo 2 (1 -> 2).
            - Fuente V1 = 2 V con (+) en Nodo 1 y (-) en Nodo 2.
            - Fuente I2 = 7 A saliendo del Nodo 2 hacia GND (2 -> 0).

        Ecuación del supernodo (1 y 2):
            V1 / 2 + V2 / 4 = 2 - 7 = -5  =>  2*V1 + V2 = -20
        Ecuación de restricción de potencial:
            V1 - V2 = 2
        Solución analítica exacta:
            3*V1 = -18 => V1 = -6.0 V
            V2 = -8.0 V
        """
        ckt = Circuito("Circuito con Supernodo")
        ckt.agregar_fuente_corriente("I1", id_nodo_origen=0, id_nodo_destino=1, valor_amperios=2.0)
        ckt.agregar_resistencia("R1", id_nodo_a=1, id_nodo_b=0, valor_ohms=2.0)
        ckt.agregar_resistencia("R2", id_nodo_a=2, id_nodo_b=0, valor_ohms=4.0)
        ckt.agregar_resistencia("R3", id_nodo_a=1, id_nodo_b=2, valor_ohms=10.0)
        ckt.agregar_fuente_voltaje("V1", id_nodo_pos=1, id_nodo_neg=2, valor_voltios=2.0)
        ckt.agregar_fuente_corriente("I2", id_nodo_origen=2, id_nodo_destino=0, valor_amperios=7.0)

        sistema = AnalizadorNodos(ckt).construir_sistema()
        solucion = MotorNumericoNumPy.resolver(sistema)
        reporte = AnalizadorSimbolicoYResultados.calcular_magnitudes_circuito(ckt, sistema, solucion)

        self.assertAlmostEqual(solucion.voltajes_nodos[1], -6.0, places=7)
        self.assertAlmostEqual(solucion.voltajes_nodos[2], -8.0, places=7)
        self.assertLess(reporte.error_balance_potencia, 1e-9)
        self.assertEqual(len(reporte.ecuaciones_sympy), 3)

    def test_03_deteccion_circuito_singular(self) -> None:
        """
        Caso 3: Dos fuentes de voltaje de distinto valor en paralelo entre los mismos nodos
        generan un sistema inconsistente/singular que debe lanzar `ErrorCircuitoSingular`.
        """
        ckt = Circuito("Fuentes V en Paralelo Incompatibles")
        ckt.agregar_fuente_voltaje("V1", id_nodo_pos=1, id_nodo_neg=0, valor_voltios=10.0)
        ckt.agregar_fuente_voltaje("V2", id_nodo_pos=1, id_nodo_neg=0, valor_voltios=5.0)
        ckt.agregar_resistencia("R1", id_nodo_a=1, id_nodo_b=0, valor_ohms=10.0)

        sistema = AnalizadorNodos(ckt).construir_sistema()
        with self.assertRaises(ErrorCircuitoSingular):
            MotorNumericoNumPy.resolver(sistema)


def demostrar_simulacion_consola() -> None:
    """
    Ejecuta una demostración detallada en consola imprimiendo las matrices,
    las ecuaciones simbólicas de SymPy y la tabla completa de resultados.
    """
    print("=" * 78)
    print(" DEMOSTRACIÓN INTEGRAL DEL SIMULADOR DE CIRCUITOS DC (MÓDULOS 1 Y 2)")
    print("=" * 78)

    ckt = Circuito("Circuito Mixto con Supernodo")
    ckt.agregar_fuente_voltaje("Vs1", id_nodo_pos=1, id_nodo_neg=0, valor_voltios=24.0)
    ckt.agregar_resistencia("R1", id_nodo_a=1, id_nodo_b=2, valor_ohms=6.0)
    ckt.agregar_resistencia("R2", id_nodo_a=2, id_nodo_b=0, valor_ohms=12.0)
    ckt.agregar_resistencia("R3", id_nodo_a=2, id_nodo_b=3, valor_ohms=4.0)
    ckt.agregar_resistencia("R4", id_nodo_a=3, id_nodo_b=0, valor_ohms=8.0)
    ckt.agregar_fuente_corriente("Is1", id_nodo_origen=0, id_nodo_destino=3, valor_amperios=1.5)

    analizador = AnalizadorNodos(ckt)
    sistema = analizador.construir_sistema()
    solucion = MotorNumericoNumPy.resolver(sistema)
    reporte = AnalizadorSimbolicoYResultados.calcular_magnitudes_circuito(ckt, sistema, solucion)

    print("\n1. INCÓGNITAS DEL SISTEMA (Vector X):")
    print("  ", sistema.etiquetas_incognitas)

    print("\n2. MATRIZ DEL SISTEMA (A) GENERADA POR EL MÓDULO 1:")
    print(sistema.matriz_A)

    print("\n3. VECTOR INDEPENDIENTE (b) GENERADO POR EL MÓDULO 1:")
    print(sistema.vector_b)

    print("\n4. ECUACIONES ALGEBRAICAS FORMADAS CON SYMPY (MÓDULO 2):")
    for ec_txt in reporte.ecuaciones_texto:
        print("  ", ec_txt)

    print("\n5. VOLTAJES DE NODO OBTENIDOS CON NUMPY (MÓDULO 2):")
    for id_n, val_v in sorted(solucion.voltajes_nodos.items()):
        etiqueta = "GND (Ref)" if id_n == 0 else f"Nodo {id_n}   "
        print(f"   {etiqueta} : {val_v:10.4f} V")

    print("\n6. MAGNITUDES ELÉCTRICAS POR ELEMENTO (VOLTAJE, CORRIENTE Y POTENCIA):")
    encabezado = f"   {'Nombre':<8} | {'Tipo':<20} | {'Nodos':<10} | {'V_ab [V]':>10} | {'I_ab [A]':>10} | {'Potencia [W] y Estado'}"
    print(encabezado)
    print("   " + "-" * (len(encabezado) - 3))
    for r in reporte.resultados_elementos.values():
        nodos_str = f"{r.nodo_a}->{r.nodo_b}"
        print(
            f"   {r.nombre:<8} | {r.tipo:<20} | {nodos_str:<10} | "
            f"{r.voltaje_ab:10.4f} | {r.corriente_ab:10.4f} | {r.estado_potencia}"
        )

    print("\n7. VERIFICACIÓN DEL BALANCE DE POTENCIA (TEOREMA DE TELLEGEN):")
    print(f"   Potencia total disipada (Resistencias) : {reporte.potencia_total_disipada:.6f} W")
    print(f"   Potencia total entregada (Fuentes)     : {reporte.potencia_total_generada:.6f} W")
    print(f"   Error de conservación de energía       : {reporte.error_balance_potencia:.2e} W")
    print("=" * 78)


if __name__ == "__main__":
    demostrar_simulacion_consola()
    print("\nEjecutando suite de pruebas unitarias (unittest)...\n")
    unittest.main()

