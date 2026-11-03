"""
Módulo 2: Representación Simbólica con SymPy y Cálculo de Magnitudes por Elemento.

Utiliza `SymPy` para construir una representación algebraica y visual exacta
de las ecuaciones nodales ($A \cdot X = B$), y calcula a partir de los voltajes
de nodo obtenidos el voltaje ($V$), la corriente ($I$) y la potencia ($P$)
disipada o generada por cada elemento del circuito (incluyendo fuentes dependientes
CCVS), verificando además el Balance de Potencia (Teorema de Tellegen).
"""

from dataclasses import dataclass
from typing import Dict, List
import sympy as sp

from modulo1_modelo.analizador_nodos import SistemaEcuacionesNodos
from modulo1_modelo.elementos import (
    Circuito,
    Componente,
    FuenteCorriente,
    FuenteVoltaje,
    FuenteVoltajeControladaCorriente,
    Resistencia,
)
from modulo2_motor.resolvedor_numpy import SolucionNodal


@dataclass
class ResultadoElemento:
    """
    Almacena las variables eléctricas calculadas para un componente específico.

    Convención pasiva de signos:
        - `voltaje_ab`: $V_{ab} = V(\text{nodo\_a}) - V(\text{nodo\_b})$ en Voltios [V].
        - `corriente_ab`: Corriente $I_{ab}$ que entra por `nodo_a` y sale por `nodo_b` en Amperios [A].
        - `potencia_w`: $P = V_{ab} \cdot I_{ab}$ en Vatios [W].
            * Si $P > 0$: El elemento ABSORBE / DISIPA potencia (ej. resistencias).
            * Si $P < 0$: El elemento ENTREGA / GENERA potencia activa al circuito (ej. fuentes).
    """
    nombre: str
    tipo: str
    nodo_a: str
    nodo_b: str
    valor_nominal: float
    unidad_nominal: str
    voltaje_ab: float
    corriente_ab: float
    potencia_w: float

    @property
    def estado_potencia(self) -> str:
        """Indica textualmente si el componente disipa/absorbe, genera o es neutro."""
        if abs(self.potencia_w) < 1e-12:
            return "Neutra (0 W)"
        elif self.potencia_w > 0:
            return f"Absorbe / Disipa ({self.potencia_w:.4f} W)"
        else:
            return f"Genera / Entrega ({abs(self.potencia_w):.4f} W)"


@dataclass
class ReporteSimulacion:
    """
    Agrupa la representación algebraica de SymPy, la solución nodal y el desglose
    completo de voltajes, corrientes y potencias por elemento.
    """
    ecuaciones_sympy: List[sp.Eq]
    matriz_A_sympy: sp.Matrix
    vector_X_sympy: sp.Matrix
    vector_b_sympy: sp.Matrix
    ecuaciones_texto: List[str]
    ecuaciones_latex: List[str]
    resultados_elementos: Dict[str, ResultadoElemento]
    potencia_total_disipada: float
    potencia_total_generada: float
    error_balance_potencia: float


class AnalizadorSimbolicoYResultados:
    """
    Genera las expresiones algebraicas del sistema mediante `SymPy` y calcula
    las magnitudes eléctricas de todos los elementos del circuito.
    """

    @staticmethod
    def generar_representacion_sympy(
        sistema: SistemaEcuacionesNodos, decimales: int = 4
    ) -> tuple[List[sp.Eq], sp.Matrix, sp.Matrix, sp.Matrix, List[str], List[str]]:
        """
        Construye las matrices simbólicas $A$, $X$, $B$ y la lista de ecuaciones
        algebraicas `sp.Eq` usando SymPy.
        """
        simbolos_x = [sp.Symbol(etiqueta) for etiqueta in sistema.etiquetas_incognitas]
        vector_X_sym = sp.Matrix(simbolos_x)

        filas_A = [
            [round(float(val), decimales) for val in fila]
            for fila in sistema.matriz_A
        ]
        valores_b = [round(float(val), decimales) for val in sistema.vector_b]

        matriz_A_sym = sp.Matrix(filas_A)
        vector_b_sym = sp.Matrix(valores_b)

        producto_AX = matriz_A_sym * vector_X_sym

        ecuaciones_eq: List[sp.Eq] = []
        ecuaciones_txt: List[str] = []
        ecuaciones_tex: List[str] = []

        for idx in range(len(simbolos_x)):
            expr_izq = sp.nsimplify(producto_AX[idx], rational=False, tolerance=1e-8)
            expr_der = sp.nsimplify(vector_b_sym[idx], rational=False, tolerance=1e-8)
            ec = sp.Eq(expr_izq, expr_der)
            ecuaciones_eq.append(ec)
            ecuaciones_txt.append(f"Ecuación {idx + 1}: {sp.sstr(expr_izq)} = {sp.sstr(expr_der)}")
            ecuaciones_tex.append(sp.latex(ec))

        return (
            ecuaciones_eq,
            matriz_A_sym,
            vector_X_sym,
            vector_b_sym,
            ecuaciones_txt,
            ecuaciones_tex,
        )

    @classmethod
    def calcular_magnitudes_circuito(
        cls,
        circuito: Circuito,
        sistema: SistemaEcuacionesNodos,
        solucion: SolucionNodal,
    ) -> ReporteSimulacion:
        """
        A partir de la solución nodal de NumPy, calcula el voltaje, corriente y
        potencia para cada componente del circuito y genera la representación de SymPy.
        """
        (
            ecs_sympy,
            mat_A_sym,
            vec_X_sym,
            vec_b_sym,
            ecs_txt,
            ecs_latex,
        ) = cls.generar_representacion_sympy(sistema)

        resultados: Dict[str, ResultadoElemento] = {}
        pot_absorbida = 0.0
        pot_entregada = 0.0

        v_nodos = solucion.voltajes_nodos
        i_fuentes_v = solucion.corrientes_fuentes_v

        for comp in circuito.componentes:
            va = v_nodos[comp.nodo_a.id_nodo]
            vb = v_nodos[comp.nodo_b.id_nodo]
            v_ab = va - vb

            if isinstance(comp, Resistencia):
                # Ley de Ohm: corriente de nodo_a hacia nodo_b
                i_ab = v_ab / comp.valor
            elif isinstance(comp, FuenteCorriente):
                # La corriente nominal de la fuente fluye de nodo_a a nodo_b
                i_ab = comp.valor
            elif isinstance(comp, (FuenteVoltaje, FuenteVoltajeControladaCorriente)):
                # En el estampado MNA, la incógnita I_fv entra por el terminal positivo (nodo_a)
                # y sale por el terminal negativo (nodo_b), coincidiendo con I_ab pasiva
                i_ab = i_fuentes_v[comp.nombre]
            else:
                raise TypeError(f"Tipo de componente no soportado: {type(comp)}")

            potencia = v_ab * i_ab
            if potencia > 0:
                pot_absorbida += potencia
            else:
                pot_entregada += abs(potencia)

            resultados[comp.nombre] = ResultadoElemento(
                nombre=comp.nombre,
                tipo=comp.tipo,
                nodo_a=comp.nodo_a.nombre,
                nodo_b=comp.nodo_b.nombre,
                valor_nominal=comp.valor,
                unidad_nominal=comp.unidad,
                voltaje_ab=v_ab,
                corriente_ab=i_ab,
                potencia_w=potencia,
            )

        # Por conservación de la energía (Teorema de Tellegen), sum(P) = 0
        error_balance = abs(pot_absorbida - pot_entregada)

        return ReporteSimulacion(
            ecuaciones_sympy=ecs_sympy,
            matriz_A_sympy=mat_A_sym,
            vector_X_sympy=vec_X_sym,
            vector_b_sympy=vec_b_sym,
            ecuaciones_texto=ecs_txt,
            ecuaciones_latex=ecs_latex,
            resultados_elementos=resultados,
            potencia_total_disipada=pot_absorbida,
            potencia_total_generada=pot_entregada,
            error_balance_potencia=error_balance,
        )
