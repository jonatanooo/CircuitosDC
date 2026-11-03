"""
Módulo 2: Motor Matemático con NumPy y SymPy (Núcleo de Resolución).

Recibe la matriz `A` y el vector `b` generados por el Módulo 1 y resuelve el
sistema de ecuaciones lineales $A \cdot X = B$ utilizando `numpy.linalg`.
Incluye validaciones de singularidad, número de condición y mapeo de resultados
a potenciales nodales y corrientes de fuentes de voltaje.
"""

from dataclasses import dataclass
from typing import Dict
import numpy as np

from modulo1_modelo.analizador_nodos import SistemaEcuacionesNodos


class ErrorCircuitoSingular(RuntimeError):
    """
    Excepción lanzada cuando la matriz A del circuito es singular o mal condicionada
    (por ejemplo: nodos flotantes sin camino a tierra, fuentes de voltaje en paralelo
    contradictorias o fuentes de corriente en serie incompatibles).
    """
    pass


@dataclass
class SolucionNodal:
    """
    Almacena el resultado numérico de la resolución de $A \cdot X = B$.

    Atributos:
        vector_x (np.ndarray): Vector solución 1D completo obtenido con `numpy.linalg.solve`.
        voltajes_nodos (Dict[int, float]): Diccionario `{id_nodo: voltaje_en_voltios}`
                                           incluyendo el nodo de tierra `{0: 0.0}`.
        corrientes_fuentes_v (Dict[str, float]): Diccionario `{nombre_fuente_v: corriente_A}`
                                                 con las corrientes incógnita de las fuentes de voltaje.
        residuo_maximo (float): Norma infinito del error residual $\|A \cdot x - b\|_\infty$
                                para verificar la exactitud numérica.
        numero_condicion (float): Número de condición $\kappa(A)$ de la matriz del sistema.
    """
    vector_x: np.ndarray
    voltajes_nodos: Dict[int, float]
    corrientes_fuentes_v: Dict[str, float]
    residuo_maximo: float
    numero_condicion: float


class MotorNumericoNumPy:
    """
    Núcleo numérico basado en `numpy.linalg` para resolver el sistema lineal $A \cdot X = B$.
    """

    UMBRAL_CONDICION: float = 1e14

    @classmethod
    def resolver(cls, sistema: SistemaEcuacionesNodos) -> SolucionNodal:
        """
        Resuelve el sistema matricial $A \cdot X = B$ empleando descomposición LU
        a través de `numpy.linalg.solve`.

        Parámetros:
            sistema (SistemaEcuacionesNodos): Estructura con `matriz_A`, `vector_b` y mapas de índices.

        Retorna:
            SolucionNodal: Objeto con el vector solución y los diccionarios de voltajes y corrientes.

        Lanza:
            ErrorCircuitoSingular: Si la matriz `A` no es invertible o su número de condición es infinito.
        """
        A = sistema.matriz_A
        b = sistema.vector_b

        if A.ndim != 2 or A.shape[0] != A.shape[1]:
            raise ValueError(f"La matriz A debe ser cuadrada, pero tiene forma {A.shape}.")
        if b.ndim != 1 or b.shape[0] != A.shape[0]:
            raise ValueError(
                f"Dimensiones incompatibles entre matriz A {A.shape} y vector b {b.shape}."
            )

        # Evaluar el número de condición de la matriz A
        num_cond = float(np.linalg.cond(A))
        if np.isinf(num_cond) or num_cond > cls.UMBRAL_CONDICION:
            raise ErrorCircuitoSingular(
                "El sistema de ecuaciones del circuito es singular o está extremadamente mal "
                f"condicionado (cond={num_cond:.2e}). Verifique que no existan subcircuitos "
                "flotantes sin referencia a tierra, lazos de fuentes de voltaje en paralelo "
                "o cortes de fuentes de corriente en serie."
            )

        try:
            vector_x = np.linalg.solve(A, b)
        except np.linalg.LinAlgError as exc:
            raise ErrorCircuitoSingular(
                f"Fallo en numpy.linalg.solve al resolver AX = B: {exc}"
            ) from exc

        # Cálculo del residuo numérico ||A*x - b||_inf
        residuo = A @ vector_x - b
        residuo_max = float(np.max(np.abs(residuo))) if residuo.size > 0 else 0.0

        # Mapear los voltajes nodales (incluyendo el nodo de referencia 0V)
        voltajes_nodos: Dict[int, float] = {0: 0.0}
        for id_nodo, idx in sistema.mapa_nodos_indice.items():
            voltajes_nodos[id_nodo] = float(vector_x[idx])

        # Mapear las corrientes incógnita de las fuentes de voltaje
        corrientes_fuentes_v: Dict[str, float] = {}
        for nombre_fv, idx in sistema.mapa_fuentes_v_indice.items():
            corrientes_fuentes_v[nombre_fv] = float(vector_x[idx])

        return SolucionNodal(
            vector_x=vector_x,
            voltajes_nodos=voltajes_nodos,
            corrientes_fuentes_v=corrientes_fuentes_v,
            residuo_maximo=residuo_max,
            numero_condicion=num_cond,
        )

