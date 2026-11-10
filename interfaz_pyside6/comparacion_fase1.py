"""Comparación con los valores de referencia de Qucs-S para la fase 1."""
from itertools import permutations
from math import isclose

from modulo1_modelo.elementos import Resistencia, FuenteVoltaje


def comparar_fase1(circuito, solucion, reporte):
    """Identifica la topología de fase 1 sin depender de etiquetas de componentes.

    Acepta la resistencia de control directamente o un sensor de 0 V en serie,
    como en el archivo LTspice suministrado. Devuelve None para otras topologías.
    """
    resistencias = circuito.resistencias
    if len(resistencias) != 5 or len(circuito.fuentes_ccvs) != 1 or circuito.fuentes_corriente:
        return None
    fuente_h = circuito.fuentes_ccvs[0]
    control = fuente_h.componente_control
    sensores = []
    if isinstance(control, FuenteVoltaje):
        if not isclose(control.valor, 0.0, abs_tol=1e-12):
            return None
        sensores = [control]
    elif not isinstance(control, Resistencia):
        return None
    fuentes = [f for f in circuito.fuentes_voltaje if f not in sensores]
    if len(fuentes) != 1 or len(circuito.fuentes_voltaje) != 1 + len(sensores):
        return None
    fuente = fuentes[0]
    if fuente.nodo_b.id_nodo != 0 or fuente_h.nodo_b.id_nodo != 0:
        return None
    salida_fuente = fuente.nodo_a.id_nodo
    salida_dependiente = fuente_h.nodo_a.id_nodo
    def par(c):
        return {c.nodo_a.id_nodo, c.nodo_b.id_nodo}
    def otro(c, nodo):
        extremos = par(c)
        return next(iter(extremos - {nodo})) if nodo in extremos and len(extremos) == 2 else None
    for entrada, centro, deriv_izq, deriv_der, derecha in permutations(resistencias):
        a = otro(entrada, salida_fuente)
        b = otro(derecha, salida_dependiente)
        if a is None or b is None or len({0, salida_fuente, salida_dependiente, a, b}) != 5:
            continue
        if par(deriv_izq) != {a, 0} or par(deriv_der) != {b, 0}:
            continue
        if sensores:
            sensor = sensores[0]
            intermedio = otro(centro, a)
            if intermedio is None or par(sensor) != {intermedio, b}:
                continue
            # El sensor debe estar en serie, sin ramas conectadas en el nodo intermedio.
            if sum(intermedio in par(c) for c in circuito.componentes) != 2:
                continue
        elif control is not centro or par(centro) != {a, b}:
            continue
        valores = solucion.voltajes_nodos
        corriente = (valores[a] - valores[b]) / centro.valor
        potencia = reporte.resultados_elementos[centro.nombre].potencia_w
        resultado = [
            ("Nodo izquierdo de 5 Ω", 16.0, valores[a], "V"),
            ("Nodo derecho de 5 Ω", 10.0, valores[b], "V"),
            ("Fuente dependiente", 9.6, valores[salida_dependiente], "V"),
            ("Corriente iφ", 1.2, corriente, "A"),
            ("Potencia en 5 Ω", 7.2, potencia, "W"),
        ]
        configuracion = (fuente.valor, entrada.valor, centro.valor, deriv_izq.valor,
                         deriv_der.valor, derecha.valor, fuente_h.valor)
        original = (20, 2, 5, 20, 10, 2, 8)
        modificados = any(not isclose(x, y, rel_tol=1e-9, abs_tol=1e-9)
                           for x, y in zip(configuracion, original))
        # Un control invertido también implica una configuración distinta.
        if sensores:
            modificados |= control.nodo_a.id_nodo != intermedio or control.nodo_b.id_nodo != b
        else:
            modificados |= control.nodo_a.id_nodo != a or control.nodo_b.id_nodo != b
        return resultado, modificados
    return None
