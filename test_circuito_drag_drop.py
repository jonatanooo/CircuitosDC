"""
Script de Prueba de Validación e Integración: `test_circuito_drag_drop.py`

Ensambla programáticamente por nodos el circuito de prueba con Fuente de Voltaje
Controlada por Corriente (CCVS) y valida el motor de Análisis Nodal Modificado (MNA)
y los cálculos de potencia:

Topología del Circuito a Validar:
    - Nodo de Referencia (Tierra, id=0): 0 V.
    - Rama 1: Fuente de voltaje independiente de 20 V (+ en Nodo auxiliar N_Vs id=4,
              - a Tierra id=0) en serie con una resistencia de 2 Ω conectada entre
              N_Vs (id=4) y el Nodo V1 (id=1).
    - Rama 2: Resistencia de 20 Ω conectada entre el Nodo V1 (id=1) y Tierra (id=0).
    - Rama 3: Resistencia de 5 Ω conectada entre el Nodo V1 (id=1) y el Nodo V2 (id=2).
              Por esta rama fluye la corriente de control i_φ (de V1 hacia V2).
    - Rama 4: Resistencia de 10 Ω conectada entre el Nodo V2 (id=2) y Tierra (id=0).
    - Rama 5: Resistencia de 2 Ω conectada entre el Nodo V2 (id=2) y el Nodo V3 (id=3).
    - Rama 6: Fuente de voltaje dependiente (CCVS) conectada entre el Nodo V3 (id=3,
              terminal positivo) y Tierra (id=0, terminal negativo), con valor 8 * i_φ.

Solución Analítica Exacta Esperada:
    - V1 = 16.0000 V
    - V2 = 10.0000 V
    - V3 =  9.6000 V
    - i_φ = (V1 - V2) / 5 Ω = (16 - 10) / 5 = 1.2000 A
    - Potencia disipada en la resistencia de 5 Ω:
      P_5Ω = (V1 - V2) * i_φ = (i_φ)^2 * 5 Ω = (1.2 A)^2 * 5 Ω = 7.2000 W
"""

import unittest
from typing import Tuple

from modulo1_modelo import AnalizadorNodos, Circuito, SistemaEcuacionesNodos
from modulo2_motor import (
    AnalizadorSimbolicoYResultados,
    MotorNumericoNumPy,
    ReporteSimulacion,
    SolucionNodal,
)


def construir_y_resolver_circuito_ccvs() -> Tuple[
    Circuito, SistemaEcuacionesNodos, SolucionNodal, ReporteSimulacion
]:
    """
    Ensambla programáticamente el circuito de 6 ramas con fuente dependiente CCVS
    y ejecuta el pipeline completo de los Módulos 1 y 2.
    """
    ckt = Circuito("Circuito de Validación MNA con CCVS (8 * i_phi)")

    # Definir explícitamente los nodos del circuito
    ckt.obtener_o_crear_nodo(0, "GND")   # Nodo de referencia (0 V)
    ckt.obtener_o_crear_nodo(1, "V1")    # Nodo principal V1
    ckt.obtener_o_crear_nodo(2, "V2")    # Nodo principal V2
    ckt.obtener_o_crear_nodo(3, "V3")    # Nodo principal V3
    ckt.obtener_o_crear_nodo(4, "N_Vs")  # Nodo entre la fuente de 20V y la resistencia de 2Ω en serie

    # -------------------------------------------------------------------------
    # Rama 1: Fuente independiente de 20 V (+ en N_Vs, - en GND) en serie con
    #         resistencia de 2 Ω conectada al Nodo V1
    # -------------------------------------------------------------------------
    ckt.agregar_fuente_voltaje("Vs_20V", id_nodo_pos=4, id_nodo_neg=0, valor_voltios=20.0)
    ckt.agregar_resistencia("R_2ohm_serie", id_nodo_a=4, id_nodo_b=1, valor_ohms=2.0)

    # -------------------------------------------------------------------------
    # Rama 2: Resistencia de 20 Ω entre el Nodo V1 y Tierra (0)
    # -------------------------------------------------------------------------
    ckt.agregar_resistencia("R_20ohm", id_nodo_a=1, id_nodo_b=0, valor_ohms=20.0)

    # -------------------------------------------------------------------------
    # Rama 3: Resistencia de 5 Ω entre el Nodo V1 y el Nodo V2
    #         La corriente de control i_φ se define fluyendo de V1 (nodo_a=1) a V2 (nodo_b=2)
    # -------------------------------------------------------------------------
    r_5ohm = ckt.agregar_resistencia("R_5ohm", id_nodo_a=1, id_nodo_b=2, valor_ohms=5.0)

    # -------------------------------------------------------------------------
    # Rama 4: Resistencia de 10 Ω entre el Nodo V2 y Tierra (0)
    # -------------------------------------------------------------------------
    ckt.agregar_resistencia("R_10ohm", id_nodo_a=2, id_nodo_b=0, valor_ohms=10.0)

    # -------------------------------------------------------------------------
    # Rama 5: Resistencia de 2 Ω entre el Nodo V2 y el Nodo V3
    # -------------------------------------------------------------------------
    ckt.agregar_resistencia("R_2ohm_v2v3", id_nodo_a=2, id_nodo_b=3, valor_ohms=2.0)

    # -------------------------------------------------------------------------
    # Rama 6: Fuente de voltaje dependiente (CCVS) entre el Nodo V3 (+) y Tierra (-),
    #         cuyo valor es 8 * i_φ (controlada por la corriente en R_5ohm)
    # -------------------------------------------------------------------------
    ckt.agregar_fuente_ccvs(
        nombre="CCVS_8iphi",
        id_nodo_pos=3,
        id_nodo_neg=0,
        transresistencia=8.0,
        componente_o_nombre_control=r_5ohm,
    )

    # Construir matriz A y vector b mediante Análisis Nodal Modificado (MNA)
    analizador = AnalizadorNodos(ckt)
    sistema = analizador.construir_sistema()

    # Resolver numéricamente A * x = b con NumPy
    solucion = MotorNumericoNumPy.resolver(sistema)

    # Generar ecuaciones simbólicas con SymPy y calcular V, I, P por elemento
    reporte = AnalizadorSimbolicoYResultados.calcular_magnitudes_circuito(
        ckt, sistema, solucion
    )

    return ckt, sistema, solucion, reporte


def ejecutar_reporte_validacion() -> None:
    """
    Ejecuta la simulación del circuito de validación e imprime en consola
    los voltajes nodales V1, V2, V3, la corriente de control i_φ y la potencia
    disipada en la resistencia de 5 Ω.
    """
    ckt, sistema, solucion, reporte = construir_y_resolver_circuito_ccvs()

    v1 = solucion.voltajes_nodos[1]
    v2 = solucion.voltajes_nodos[2]
    v3 = solucion.voltajes_nodos[3]
    res_5ohm = reporte.resultados_elementos["R_5ohm"]
    i_phi = res_5ohm.corriente_ab
    potencia_5ohm = res_5ohm.potencia_w

    print("=" * 80)
    print(" VALIDACIÓN DEL MOTOR MNA CON FUENTE DEPENDIENTE CCVS (8 * i_φ)")
    print("=" * 80)

    print("\n1. ECUACIONES GENERADAS POR EL MOTOR SIMBÓLICO (SymPy):")
    for ec_str in reporte.ecuaciones_texto:
        print(f"   {ec_str}")

    print("\n2. MATRIZ DEL SISTEMA MNA (A) Y VECTOR INDEPENDIENTE (b):")
    print("   Incógnitas x =", sistema.etiquetas_incognitas)
    print("   Matriz A:\n", sistema.matriz_A)
    print("   Vector b:\n", sistema.vector_b)

    print("\n3. VOLTAJES DE NODO RESUELTOS (NumPy):")
    print(f"   V_GND (Referencia) = {solucion.voltajes_nodos[0]:8.4f} V")
    print(f"   V1                 = {v1:8.4f} V")
    print(f"   V2                 = {v2:8.4f} V")
    print(f"   V3                 = {v3:8.4f} V")

    print("\n4. CORRIENTE DE CONTROL (i_φ de V1 a V2 por la resistencia de 5 Ω):")
    print(f"   i_φ = (V1 - V2) / 5 Ω = ({v1:.2f} V - {v2:.2f} V) / 5 Ω = {i_phi:.4f} A")

    print("\n5. TABLA COMPLETA DE MAGNITUDES POR COMPONENTE:")
    encabezado = (
        f"   {'Elemento':<14} | {'Tipo':<25} | {'Nodos':<11} | "
        f"{'V_ab [V]':>9} | {'I_ab [A]':>9} | {'Potencia [W]'}"
    )
    print(encabezado)
    print("   " + "-" * (len(encabezado) - 3))
    for r in reporte.resultados_elementos.values():
        nodos_txt = f"{r.nodo_a}->{r.nodo_b}"
        print(
            f"   {r.nombre:<14} | {r.tipo:<25} | {nodos_txt:<11} | "
            f"{r.voltaje_ab:9.4f} | {r.corriente_ab:9.4f} | {r.estado_potencia}"
        )

    print("\n" + "=" * 80)
    print(" RESULTADO OBJETIVO FINAL — POTENCIA DISIPADA EN LA RESISTENCIA DE 5 Ω:")
    print(f"   Voltaje en R_5Ω (V1 - V2) : {res_5ohm.voltaje_ab:.4f} V")
    print(f"   Corriente i_φ (V1 -> V2)  : {i_phi:.4f} A")
    print(f"   Potencia disipada P_5Ω    : {potencia_5ohm:.4f} W")
    print("=" * 80)


class TestCircuitoDragDropCCVS(unittest.TestCase):
    """Pruebas automatizadas para verificar la exactitud matemática del circuito con CCVS."""

    def test_resolucion_voltajes_corriente_y_potencia_5ohm(self) -> None:
        _, _, solucion, reporte = construir_y_resolver_circuito_ccvs()

        # Verificar voltajes nodales V1 = 16 V, V2 = 10 V, V3 = 9.6 V
        self.assertAlmostEqual(solucion.voltajes_nodos[1], 16.0, places=6)
        self.assertAlmostEqual(solucion.voltajes_nodos[2], 10.0, places=6)
        self.assertAlmostEqual(solucion.voltajes_nodos[3], 9.6, places=6)

        # Verificar corriente de control i_φ = 1.2 A
        res_5ohm = reporte.resultados_elementos["R_5ohm"]
        self.assertAlmostEqual(res_5ohm.corriente_ab, 1.2, places=6)
        self.assertAlmostEqual(res_5ohm.voltaje_ab, 6.0, places=6)

        # Verificar potencia disipada en la resistencia de 5 Ω: P = 7.2 W
        self.assertAlmostEqual(res_5ohm.potencia_w, 7.2, places=6)

        # Verificar que el balance global de potencia (Teorema de Tellegen) se cumple
        self.assertLess(reporte.error_balance_potencia, 1e-9)


if __name__ == "__main__":
    ejecutar_reporte_validacion()
    print("\nEjecutando verificación automatizada (unittest)...\n")
    unittest.main()

