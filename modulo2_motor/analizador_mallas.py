"""Análisis DC mediante corrientes de lazos independientes y supermallas.

Los lazos se generan con un árbol generador. Este método algebraico de
corrientes de lazo también funciona con una base independiente que no sea el
conjunto de caras mínimas del dibujo. Las fuentes de corriente imponen una
restricción y añaden su voltaje como incógnita (supermalla generalizada).
"""
from collections import deque
import numpy as np

from modulo1_modelo.analizador_nodos import SistemaEcuacionesNodos
from modulo1_modelo.elementos import Resistencia, FuenteVoltaje, FuenteCorriente, FuenteVoltajeControladaCorriente
from modulo2_motor.resolvedor_numpy import ErrorCircuitoSingular, MotorNumericoNumPy


class AnalizadorMallas:
    def __init__(self, circuito):
        self.circuito = circuito

    def resolver(self):
        componentes = self.circuito.componentes
        if not componentes:
            raise ValueError('No hay componentes para analizar.')
        nodos = {n.id_nodo for n in self.circuito.nodos}
        padre = {n: n for n in nodos}
        def raiz(n):
            while padre[n] != n:
                padre[n] = padre[padre[n]]
                n = padre[n]
            return n
        arbol = {n: [] for n in nodos}
        cuerdas = []
        for indice, comp in enumerate(componentes):
            a, b = comp.nodo_a.id_nodo, comp.nodo_b.id_nodo
            ra, rb = raiz(a), raiz(b)
            if ra != rb:
                padre[rb] = ra
                arbol[a].append((b, indice, 1))
                arbol[b].append((a, indice, -1))
            else:
                cuerdas.append(indice)
        if any(raiz(n) != raiz(0) for n in nodos):
            raise ValueError('El circuito contiene nodos desconectados de la referencia GND.')
        if not cuerdas:
            raise ValueError('El circuito no contiene lazos cerrados para el análisis de mallas.')
        B = np.zeros((len(cuerdas), len(componentes)))
        for lazo, indice in enumerate(cuerdas):
            comp = componentes[indice]
            inicio, fin = comp.nodo_b.id_nodo, comp.nodo_a.id_nodo
            B[lazo, indice] = 1.0
            pendientes = deque([inicio])
            anterior = {inicio: None}
            while pendientes and fin not in anterior:
                actual = pendientes.popleft()
                for vecino, rama, sentido in arbol[actual]:
                    if vecino not in anterior:
                        anterior[vecino] = (actual, rama, sentido)
                        pendientes.append(vecino)
            actual = fin
            while actual != inicio:
                previo, rama, sentido = anterior[actual]
                B[lazo, rama] = sentido
                actual = previo
        fuentes_i = [i for i, c in enumerate(componentes) if isinstance(c, FuenteCorriente)]
        n_lazos, n_fuentes = len(cuerdas), len(fuentes_i)
        matriz = np.zeros((n_lazos + n_fuentes, n_lazos + n_fuentes))
        vector = np.zeros(n_lazos + n_fuentes)
        indices = {c.nombre: i for i, c in enumerate(componentes)}
        for j, comp in enumerate(componentes):
            rama_lazos = B[:, j]
            if isinstance(comp, Resistencia):
                matriz[:n_lazos, :n_lazos] += comp.valor * np.outer(rama_lazos, rama_lazos)
            elif isinstance(comp, FuenteVoltaje):
                vector[:n_lazos] -= rama_lazos * comp.valor
            elif isinstance(comp, FuenteVoltajeControladaCorriente):
                nombre = comp.componente_control.nombre
                if nombre not in indices or componentes[indices[nombre]] is not comp.componente_control:
                    raise ValueError(f"La fuente '{comp.nombre}' tiene un control que no pertenece al circuito.")
                matriz[:n_lazos, :n_lazos] += comp.valor * np.outer(rama_lazos, B[:, indices[nombre]])
            elif not isinstance(comp, FuenteCorriente):
                raise ValueError(f"Componente no soportado por mallas: {comp.nombre}")
        for k, indice in enumerate(fuentes_i):
            matriz[:n_lazos, n_lazos + k] = B[:, indice]
            matriz[n_lazos + k, :n_lazos] = B[:, indice]
            vector[n_lazos + k] = componentes[indice].valor
        etiquetas = [f'I_lazo_{i + 1}' for i in range(n_lazos)] + [f'V_{componentes[i].nombre}' for i in fuentes_i]
        sistema = SistemaEcuacionesNodos(matriz, vector, etiquetas, {}, {})
        solucion = MotorNumericoNumPy.resolver(sistema)
        corrientes = B.T @ solucion.vector_x[:n_lazos]
        voltajes_ramas = np.zeros(len(componentes))
        por_fuente_i = {indice: k for k, indice in enumerate(fuentes_i)}
        for j, comp in enumerate(componentes):
            if isinstance(comp, Resistencia):
                voltajes_ramas[j] = comp.valor * corrientes[j]
            elif isinstance(comp, FuenteVoltaje):
                voltajes_ramas[j] = comp.valor
            elif isinstance(comp, FuenteVoltajeControladaCorriente):
                voltajes_ramas[j] = comp.valor * corrientes[indices[comp.componente_control.nombre]]
            else:
                voltajes_ramas[j] = solucion.vector_x[n_lazos + por_fuente_i[j]]
        voltajes = {0: 0.0}
        relaciones = {n: [] for n in nodos}
        for j, comp in enumerate(componentes):
            a,b = comp.nodo_a.id_nodo, comp.nodo_b.id_nodo
            relaciones[a].append((b, -voltajes_ramas[j]))
            relaciones[b].append((a, voltajes_ramas[j]))
        pendientes = deque([0])
        while pendientes:
            nodo = pendientes.popleft()
            for vecino, diferencia in relaciones[nodo]:
                valor = voltajes[nodo] + diferencia
                if vecino not in voltajes:
                    voltajes[vecino] = valor
                    pendientes.append(vecino)
                elif not np.isclose(voltajes[vecino], valor, atol=1e-8, rtol=1e-8):
                    raise ErrorCircuitoSingular('Las tensiones calculadas en los lazos no son coherentes.')
        solucion.voltajes_nodos = voltajes
        solucion.corrientes_fuentes_v = {
            c.nombre: float(corrientes[i]) for i, c in enumerate(componentes)
            if isinstance(c, (FuenteVoltaje, FuenteVoltajeControladaCorriente))
        }
        return sistema, solucion
