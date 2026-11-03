"""
Módulo 1: Analizador de Nodos y Construcción Matricial (Nodal / MNA).

Contiene el algoritmo encargado de recibir un objeto `Circuito`, aplicar la
Ley de Corrientes de Kirchhoff (LCK) mediante la técnica de estampado matricial
(Modified Nodal Analysis - MNA) y construir automáticamente la matriz del
sistema `A` y el vector de términos independientes `b`.

Soporta:
    - Resistencias
    - Fuentes de Corriente Independientes
    - Fuentes de Voltaje Independientes (a tierra o flotantes / supernodos)
    - Fuentes de Voltaje Controladas por Corriente (CCVS: V_ab = r * i_phi)
"""

from dataclasses import dataclass
from typing import Dict, List
import numpy as np

from modulo1_modelo.elementos import (
    Circuito,
    FuenteCorriente,
    FuenteVoltaje,
    FuenteVoltajeControladaCorriente,
    Nodo,
    Resistencia,
)


@dataclass
class SistemaEcuacionesNodos:
    """
    Estructura de datos que encapsula el sistema lineal A * x = b generado
    a partir de la topología del circuito mediante MNA.

    Atributos:
        matriz_A (np.ndarray): Matriz cuadrada de dimensión (N + M) x (N + M)
                               que contiene las conductancias y restricciones de voltaje.
        vector_b (np.ndarray): Vector columna/1D de longitud (N + M) con las
                               corrientes inyectadas y valores de fuentes de voltaje.
        etiquetas_incognitas (List[str]): Nombres simbólicos de las incógnitas en el
                                          vector `x` (ej. ['V_V1', 'V_V2', 'I_Vs']).
        mapa_nodos_indice (Dict[int, int]): Relaciona el `id_nodo` con su índice (0 a N-1)
                                            dentro del vector de incógnitas `x`.
        mapa_fuentes_v_indice (Dict[str, int]): Relaciona el nombre de cada fuente de voltaje
                                                (independiente o CCVS) con su índice (N a N+M-1)
                                                en el vector `x`.
    """
    matriz_A: np.ndarray
    vector_b: np.ndarray
    etiquetas_incognitas: List[str]
    mapa_nodos_indice: Dict[int, int]
    mapa_fuentes_v_indice: Dict[str, int]


class AnalizadorNodos:
    """
    Motor de formulación de ecuaciones de nodo mediante Análisis Nodal Modificado (MNA).

    Soporta:
        1. Análisis Nodal Clásico (resistencias y fuentes de corriente):
           A es la matriz de conductancias G (N x N) y b es el vector de corrientes I (N x 1).
        2. Análisis Nodal Modificado (MNA) con Fuentes de Voltaje Independientes y
           Fuentes de Voltaje Controladas por Corriente (CCVS):
           Extiende el sistema a dimensión (N + M) x (N + M) agregando las corrientes
           de las M fuentes de voltaje como incógnitas adicionales y estampando sus
           ecuaciones de restricción de potencial.
    """

    def __init__(self, circuito: Circuito) -> None:
        self.circuito: Circuito = circuito

    def validar_topologia(self) -> None:
        """
        Verifica que el circuito tenga al menos un nodo de referencia (GND=0),
        al menos un nodo incógnita y que no existan nodos completamente aislados.
        """
        nodos_incog = self.circuito.nodos_incognita
        if not nodos_incog:
            raise ValueError(
                "El circuito debe poseer al menos un nodo distinto de Tierra (GND=0)."
            )
        if not self.circuito.componentes:
            raise ValueError("El circuito no contiene componentes eléctricos conectados.")

        nodos_conectados = set()
        for comp in self.circuito.componentes:
            nodos_conectados.add(comp.nodo_a.id_nodo)
            nodos_conectados.add(comp.nodo_b.id_nodo)

        if 0 not in nodos_conectados:
            raise ValueError(
                "El nodo de referencia (GND, id_nodo=0) no está conectado a ningún componente."
            )

        for nodo in nodos_incog:
            if nodo.id_nodo not in nodos_conectados:
                raise ValueError(
                    f"El nodo '{nodo.nombre}' (id={nodo.id_nodo}) está aislado y no tiene conexiones."
                )

    def construir_sistema(self) -> SistemaEcuacionesNodos:
        """
        Ejecuta el algoritmo de estampado matricial (Matrix Stamping MNA) y devuelve
        el objeto `SistemaEcuacionesNodos` con la matriz `A`, el vector `b` y los
        metadatos de mapeo de variables.

        Para una fuente dependiente CCVS definida como:
            V(nodo_a) - V(nodo_b) = r * i_phi
        donde `i_phi` fluye por un componente de control desde `ctrl_a` hacia `ctrl_b`:
            - Si el elemento de control es una Resistencia R_c (conductancia G_c = 1/R_c):
              i_phi = G_c * (V(ctrl_a) - V(ctrl_b)), por lo que la ecuación de fila MNA es:
              V(nodo_a) - V(nodo_b) - r*G_c*V(ctrl_a) + r*G_c*V(ctrl_b) = 0
            - Si el elemento de control es una Fuente de Voltaje (cuya corriente I_ctrl ya
              forma parte del vector de incógnitas MNA):
              V(nodo_a) - V(nodo_b) - r*I_ctrl = 0
        """
        self.validar_topologia()

        nodos_activos: List[Nodo] = self.circuito.nodos_incognita
        fuentes_v_mna = self.circuito.todas_fuentes_voltaje_mna

        num_nodos = len(nodos_activos)
        num_fuentes_v = len(fuentes_v_mna)
        dim_total = num_nodos + num_fuentes_v

        # Mapas de indexación (id_nodo -> fila/columna 0..N-1)
        mapa_nodos: Dict[int, int] = {
            nodo.id_nodo: idx for idx, nodo in enumerate(nodos_activos)
        }
        # Mapa de fuentes de voltaje independientes y CCVS (nombre -> fila/columna N..N+M-1)
        mapa_fuentes_v: Dict[str, int] = {
            fv.nombre: (num_nodos + idx) for idx, fv in enumerate(fuentes_v_mna)
        }

        # Etiquetas simbólicas de las incógnitas del vector X
        etiquetas: List[str] = [f"V_{nodo.nombre}" for nodo in nodos_activos] + [
            f"I_{fv.nombre}" for fv in fuentes_v_mna
        ]

        # Inicializar Matriz A y Vector b con ceros en precisión float64
        matriz_A = np.zeros((dim_total, dim_total), dtype=np.float64)
        vector_b = np.zeros(dim_total, dtype=np.float64)

        # ---------------------------------------------------------------------
        # PASO 1: Estampado de Resistencias en la submatriz de conductancias G
        # ---------------------------------------------------------------------
        for res in self.circuito.resistencias:
            g = res.conductancia
            idx_a = mapa_nodos.get(res.nodo_a.id_nodo, None)
            idx_b = mapa_nodos.get(res.nodo_b.id_nodo, None)

            if idx_a is not None:
                matriz_A[idx_a, idx_a] += g
            if idx_b is not None:
                matriz_A[idx_b, idx_b] += g

            if idx_a is not None and idx_b is not None:
                matriz_A[idx_a, idx_b] -= g
                matriz_A[idx_b, idx_a] -= g

        # ---------------------------------------------------------------------
        # PASO 2: Estampado de Fuentes de Corriente en el vector b
        # Convención: Corriente que SALE del nodo_a (-) y ENTRA al nodo_b (+)
        # ---------------------------------------------------------------------
        for fc in self.circuito.fuentes_corriente:
            corriente = fc.valor
            idx_origen = mapa_nodos.get(fc.nodo_a.id_nodo, None)
            idx_destino = mapa_nodos.get(fc.nodo_b.id_nodo, None)

            if idx_origen is not None:
                vector_b[idx_origen] -= corriente
            if idx_destino is not None:
                vector_b[idx_destino] += corriente

        # ---------------------------------------------------------------------
        # PASO 3: Estampado de Fuentes de Voltaje Independientes y CCVS (MNA)
        # ---------------------------------------------------------------------
        for fv in fuentes_v_mna:
            idx_fv = mapa_fuentes_v[fv.nombre]
            idx_pos = mapa_nodos.get(fv.nodo_a.id_nodo, None)
            idx_neg = mapa_nodos.get(fv.nodo_b.id_nodo, None)

            # Aporte de la corriente incógnita I_fv en las ecuaciones LCK de sus nodos
            # y aporte de V_pos - V_neg en la fila de restricción idx_fv
            if idx_pos is not None:
                matriz_A[idx_pos, idx_fv] += 1.0
                matriz_A[idx_fv, idx_pos] += 1.0

            if idx_neg is not None:
                matriz_A[idx_neg, idx_fv] -= 1.0
                matriz_A[idx_fv, idx_neg] -= 1.0

            if isinstance(fv, FuenteVoltaje):
                # Fuente de voltaje independiente: V_pos - V_neg = V_nominal
                vector_b[idx_fv] = fv.valor

            elif isinstance(fv, FuenteVoltajeControladaCorriente):
                # Fuente CCVS dependiente: V_pos - V_neg - r * i_phi = 0
                r = fv.transresistencia
                comp_ctrl = fv.componente_control

                if isinstance(comp_ctrl, Resistencia):
                    # i_phi = G_ctrl * (V(ctrl_a) - V(ctrl_b))
                    g_ctrl = comp_ctrl.conductancia
                    idx_ca = mapa_nodos.get(comp_ctrl.nodo_a.id_nodo, None)
                    idx_cb = mapa_nodos.get(comp_ctrl.nodo_b.id_nodo, None)

                    if idx_ca is not None:
                        matriz_A[idx_fv, idx_ca] -= r * g_ctrl
                    if idx_cb is not None:
                        matriz_A[idx_fv, idx_cb] += r * g_ctrl
                    vector_b[idx_fv] = 0.0

                elif comp_ctrl.nombre in mapa_fuentes_v:
                    # i_phi es la corriente de otra fuente de voltaje en el vector X
                    idx_ctrl_i = mapa_fuentes_v[comp_ctrl.nombre]
                    matriz_A[idx_fv, idx_ctrl_i] -= r
                    vector_b[idx_fv] = 0.0

                elif isinstance(comp_ctrl, FuenteCorriente):
                    # i_phi es constante e igual al valor de la fuente de corriente
                    vector_b[idx_fv] = r * comp_ctrl.valor

                else:
                    raise TypeError(
                        f"Componente de control '{comp_ctrl.nombre}' no soportado para CCVS."
                    )

        return SistemaEcuacionesNodos(
            matriz_A=matriz_A,
            vector_b=vector_b,
            etiquetas_incognitas=etiquetas,
            mapa_nodos_indice=mapa_nodos,
            mapa_fuentes_v_indice=mapa_fuentes_v,
        )
