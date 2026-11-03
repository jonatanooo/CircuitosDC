# Documentación Técnica — Módulo 2: Motor Matemático con NumPy y SymPy

**Responsabilidad del Integrante 2:** Resolución numérica de sistemas de ecuaciones lineales ($A \cdot X = B$) mediante `numpy.linalg`, generación de la representación simbólica/algebraica del sistema con `SymPy`, y posprocesamiento eléctrico (cálculo de voltaje, corriente, potencia disipada/generada por elemento y verificación del Teorema de Tellegen).

---

## 1. Proceso Matemático y Uso Técnico de NumPy (`resolvedor_numpy.py`)

El núcleo de cálculo numérico reside en la clase [`MotorNumericoNumPy`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo2_motor/resolvedor_numpy.py#L44-L107), la cual recibe el objeto [`SistemaEcuacionesNodos`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo1_modelo/analizador_nodos.py#L22-L44) generado por el Módulo 1 y resuelve la ecuación matricial:

$$A \cdot X = b$$

### 1.1 ¿Por qué usar `numpy.linalg.solve(A, b)` en lugar de invertir la matriz ($A^{-1} b$)?
En ingeniería de simulación de circuitos (como SPICE), **nunca** se calcula explícitamente la matriz inversa `np.linalg.inv(A) @ b` por dos razones fundamentales:
1. **Eficiencia Computacional:** `numpy.linalg.solve` utiliza la subrutina ` _gesv` de **LAPACK** basada en **Factorización LU con pivoteo parcial** ($P \cdot A = L \cdot U$), requiriendo $\frac{2}{3}n^3$ operaciones en punto flotante, frente a las $2n^3$ operaciones necesarias para invertir la matriz explícitamente.
2. **Estabilidad Numérica:** Resolver sistemas triangulares mediante sustitución hacia adelante y hacia atrás sobre los factores $L$ y $U$ acumula mucho menor error de redondeo en aritmética IEEE 754 de 64 bits (`float64`) que multiplicar por $A^{-1}$.

### 1.2 Análisis de Condicionamiento y Detección de Circuitos Singulares
Antes de invocar a `solve`, el motor evalúa el **número de condición** de la matriz $A$:
$$\kappa(A) = \|A\| \cdot \|A^{-1}\| \quad \longrightarrow \quad \text{calculado vía } \texttt{np.linalg.cond(A)}$$

Si $\kappa(A) = \infty$ o supera el umbral $\kappa(A) > 10^{14}$, el motor lanza la excepción personalizada [`ErrorCircuitoSingular`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo2_motor/resolvedor_numpy.py#L16-L23). Eléctricamente, esto identifica topologías inválidas tales como:
* Subcircuitos o nodos flotantes sin camino conductivo a tierra.
* Dos fuentes de voltaje ideales en paralelo con voltajes distintos (contradicción de la Ley de Voltajes de Kirchhoff).
* Dos fuentes de corriente ideales en serie con corrientes distintas (contradicción de la Ley de Corrientes de Kirchhoff).

### 1.3 Verificación del Residuo Numérico
Una vez obtenido el vector solución $X$, se verifica la exactitud de la solución calculando la norma infinito del vector residual:
$$r_{\max} = \|A \cdot X - b\|_\infty = \max_i |(A \cdot X)_i - b_i|$$
Para circuitos bien condicionados, este valor se sitúa en el orden del épsilon de la máquina ($\sim 10^{-15}$).

---

## 2. Representación Algebraica y Cálculo de Magnitudes con SymPy (`simbolico_sympy.py`)

La clase [`AnalizadorSimbolicoYResultados`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo2_motor/simbolico_sympy.py#L64-L185) cumple dos propósitos esenciales:

### 2.1 Construcción de Ecuaciones Simbólicas con `SymPy`
En el método [`generar_representacion_sympy`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo2_motor/simbolico_sympy.py#L70-L120):
1. Se transforma cada etiqueta de incógnita (`'V_N1'`, `'V_N2'`, `'I_V1'`, etc.) en un objeto algebraico `sympy.Symbol`.
2. Se convierten los arreglos de NumPy `matriz_A` y `vector_b` en matrices simbólicas `sympy.Matrix`.
3. Se ejecuta el producto matricial simbólico $A_{\text{sym}} \cdot X_{\text{sym}}$, obteniendo las combinaciones lineales exactas de cada fila.
4. Cada fila $k$ se empaqueta en una igualdad formal `sympy.Eq(lhs, rhs)` tras limpiar coeficientes con `sympy.nsimplify`.
5. Se exportan tanto cadenas en texto plano (`sympy.sstr`) como expresiones en formato **LaTeX** (`sympy.latex`) listas para mostrarse en reportes o en la interfaz gráfica PySide6.

### 2.2 Cálculo de Voltaje, Corriente y Potencia por Elemento
Con los potenciales nodales $V_1, V_2, \dots, V_N$ (y $V_0 = 0\text{ V}$) obtenidos en [`SolucionNodal`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo2_motor/resolvedor_numpy.py#L26-L41), para cada elemento conectado entre `nodo_a` y `nodo_b` se aplica la **Convención Pasiva de Signos**:

1. **Voltaje entre terminales ($V_{ab}$):**
   $$V_{ab} = V(\text{nodo\_a}) - V(\text{nodo\_b}) \quad [\text{V}]$$
2. **Corriente del elemento ($I_{ab}$, entrando por `nodo_a` y saliendo por `nodo_b`):**
   * **En una [`Resistencia`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo1_modelo/elementos.py#L80-L108):**
     $$I_{ab} = \frac{V_{ab}}{R} \quad [\text{A}]$$
   * **En una [`FuenteCorriente`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo1_modelo/elementos.py#L111-L130):**
     $$I_{ab} = I_{\text{nominal}} \quad [\text{A}]$$
   * **En una [`FuenteVoltaje`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo1_modelo/elementos.py#L133-L157):**
     $$I_{ab} = I_{V_m} \quad (\text{extraída directamente del vector solución } X \text{ del MNA})$$
3. **Potencia Eléctrica ($P$):**
   $$P = V_{ab} \cdot I_{ab} \quad [\text{W}]$$
   * Si $P > 0$: El componente **absorbe o disipa** potencia (comportamiento pasivo/resistivo).
   * Si $P < 0$: El componente **genera o entrega** potencia al circuito (comportamiento activo de fuente).

### 2.3 Validación mediante el Teorema de Tellegen (Conservación de la Energía)
En todo circuito eléctrico que cumple las Leyes de Kirchhoff, la suma algebraica de las potencias instantáneas de todos sus elementos es idénticamente cero:
$$\sum_{k=1}^{K} P_k = 0 \quad \Longleftrightarrow \quad \sum P_{\text{disipada}} = \sum P_{\text{generada}}$$
El objeto [`ReporteSimulacion`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo2_motor/simbolico_sympy.py#L49-L61) calcula `error_balance_potencia = |potencia_total_disipada - potencia_total_generada|`, garantizando matemáticamente la coherencia de los resultados.

---

## 3. Script de Prueba e Integración de Ambos Módulos

El archivo [test_integracion_modulos.py](file:///c:/Users/Imprenta/Desktop/CALCULADORA/tests/test_integracion_modulos.py) integra y valida el Módulo 1 y el Módulo 2 conjuntamente mediante tres pruebas automatizadas con `unittest` y una demostración detallada en consola.

### Fragmento del Script de Prueba Conjunta

```python
from modulo1_modelo import Circuito, AnalizadorNodos
from modulo2_motor import MotorNumericoNumPy, AnalizadorSimbolicoYResultados

# 1. Definir circuito mixto con fuente de voltaje (MNA), resistencias y fuente de corriente
ckt = Circuito("Circuito Mixto de Validación")
ckt.agregar_fuente_voltaje("Vs1", id_nodo_pos=1, id_nodo_neg=0, valor_voltios=24.0)
ckt.agregar_resistencia("R1", id_nodo_a=1, id_nodo_b=2, valor_ohms=6.0)
ckt.agregar_resistencia("R2", id_nodo_a=2, id_nodo_b=0, valor_ohms=12.0)
ckt.agregar_resistencia("R3", id_nodo_a=2, id_nodo_b=3, valor_ohms=4.0)
ckt.agregar_resistencia("R4", id_nodo_a=3, id_nodo_b=0, valor_ohms=8.0)
ckt.agregar_fuente_corriente("Is1", id_nodo_origen=0, id_nodo_destino=3, valor_amperios=1.5)

# 2. Módulo 1: Construir matriz A y vector b
sistema = AnalizadorNodos(ckt).construir_sistema()

# 3. Módulo 2 (NumPy): Resolver A * X = b
solucion = MotorNumericoNumPy.resolver(sistema)

# 4. Módulo 2 (SymPy + Posprocesamiento): Generar ecuaciones y potencias por elemento
reporte = AnalizadorSimbolicoYResultados.calcular_magnitudes_circuito(ckt, sistema, solucion)

for ec in reporte.ecuaciones_texto:
    print(ec)

for nombre, elem in reporte.resultados_elementos.items():
    print(f"{nombre}: V={elem.voltaje_ab:.2f} V, I={elem.corriente_ab:.2f} A -> {elem.estado_potencia}")
```

### Resultados Obtenidos en la Prueba de Integración

1. **Ecuaciones simbólicas generadas por SymPy:**
   * $\text{Ecuación 1: } I_{Vs1} + 0.1667\,V_{N1} - 0.1667\,V_{N2} = 0$
   * $\text{Ecuación 2: } -0.1667\,V_{N1} + 0.5\,V_{N2} - 0.25\,V_{N3} = 0$
   * $\text{Ecuación 3: } -0.25\,V_{N2} + 0.375\,V_{N3} = 1.5$
   * $\text{Ecuación 4: } 1.0\,V_{N1} = 24.0$
2. **Potenciales de Nodo resueltos con `numpy.linalg.solve`:**
   * $V_{\text{GND}} = 0.0000\text{ V}$
   * $V_{N1} = 24.0000\text{ V}$
   * $V_{N2} = 15.0000\text{ V}$
   * $V_{N3} = 14.0000\text{ V}$
3. **Magnitudes por Componente y Balance de Potencia:**
   * `Vs1` ($24\text{ V}$): $V_{ab} = 24.00\text{ V}$, $I_{ab} = -1.50\text{ A}$, $P = -36.00\text{ W}$ (**Genera $36.00\text{ W}$**)
   * `Is1` ($1.5\text{ A}$): $V_{ab} = -14.00\text{ V}$, $I_{ab} = 1.50\text{ A}$, $P = -21.00\text{ W}$ (**Genera $21.00\text{ W}$**)
   * `R1` ($6\,\Omega$): $V_{ab} = 9.00\text{ V}$, $I_{ab} = 1.50\text{ A}$, $P = +13.50\text{ W}$ (**Disipa $13.50\text{ W}$**)
   * `R2` ($12\,\Omega$): $V_{ab} = 15.00\text{ V}$, $I_{ab} = 1.25\text{ A}$, $P = +18.75\text{ W}$ (**Disipa $18.75\text{ W}$**)
   * `R3` ($4\,\Omega$): $V_{ab} = 1.00\text{ V}$, $I_{ab} = 0.25\text{ A}$, $P = +0.25\text{ W}$ (**Disipa $0.25\text{ W}$**)
   * `R4` ($8\,\Omega$): $V_{ab} = 14.00\text{ V}$, $I_{ab} = 1.75\text{ A}$, $P = +24.50\text{ W}$ (**Disipa $24.50\text{ W}$**)
   * **Balance Total:** $\sum P_{\text{disipada}} = 57.0000\text{ W} = \sum P_{\text{generada}} = 57.0000\text{ W}$ (Error $= 0.00\text{ W}$).

