# Documentación Técnica — Módulo 1: Modelo Eléctrico y Generación de Ecuaciones

**Responsabilidad del Integrante 1:** Diseño orientado a objetos de los elementos del circuito DC, representación de la topología nodal y formulación automática de la matriz del sistema ($A$) y el vector independiente ($b$) mediante el Método de Nodos y Análisis Nodal Modificado (MNA).

---

## 1. Fundamento Teórico: El Método de Nodos Paso a Paso

El **Análisis por Nodos** se fundamenta en la aplicación sistemática de la **Ley de Corrientes de Kirchhoff (LCK)** junto con la **Ley de Ohm** expresada en términos de conductancias ($G = \frac{1}{R}$). Las incógnitas primarias del sistema son los **potenciales eléctricos nodales** medidos respecto a un nodo de referencia común.

### Paso 1: Identificación de Nodos y Selección de Tierra (GND)
En un circuito con $N + 1$ nodos de interconexión:
1. Se elige un nodo de referencia llamado **Tierra (GND)**, identificado en nuestro modelo con `id_nodo = 0`, cuyo potencial se fija por definición en:
   $$V_0 = 0\text{ V}$$
2. Los $N$ nodos restantes ($1, 2, \dots, N$) poseen potenciales incógnita $V_1, V_2, \dots, V_N$.

### Paso 2: Expresión de Corrientes de Rama mediante Conductancias
Para cualquier resistencia $R_{ab}$ conectada entre el nodo $a$ y el nodo $b$, su conductancia es:
$$G_{ab} = \frac{1}{R_{ab}} \quad [\text{Siemens, S}]$$
La corriente que abandona el nodo $a$ hacia el nodo $b$ a través del resistor está dada por la Ley de Ohm:
$$I_{a \to b} = \frac{V_a - V_b}{R_{ab}} = G_{ab}(V_a - V_b)$$

### Paso 3: Aplicación de la LCK en cada Nodo Activo
La Ley de Corrientes de Kirchhoff establece que en cualquier nodo $k$:
$$\sum I_{\text{salientes por ramas resistivas}} = \sum I_{\text{fuentes que entran}} - \sum I_{\text{fuentes que salen}}$$
Agrupando los términos que multiplican a cada potencial nodal $V_j$:
$$\left(\sum_{j \neq k} G_{kj}\right) V_k - \sum_{j \neq k} G_{kj} V_j = I_{\text{neta}, k}$$

### Paso 4: Tratamiento de Fuentes de Voltaje y Supernodos (Extensión MNA)
Cuando el circuito contiene $M$ **fuentes de voltaje independientes** (ya sea conectadas a tierra o flotantes entre dos nodos formando un **supernodo**), la corriente que circula por cada fuente de voltaje $V_{s,m}$ no puede expresarse directamente en función de conductancias.

Para automatizar este proceso computacionalmente sin necesidad de inspección manual, se emplea el **Análisis Nodal Modificado (MNA)**:
1. Se introduce la corriente $I_{V_m}$ (que entra por el terminal positivo $a$ y sale por el terminal negativo $b$ de la fuente $m$) como una **incógnita adicional** en el vector $X$.
2. En la ecuación de LCK del nodo positivo $a$, se suma $+I_{V_m}$ (corriente saliente del nodo hacia la fuente); en la del nodo negativo $b$, se resta $-I_{V_m}$.
3. Se añade una **ecuación de restricción de potencial** en la fila $N + m$:
   $$V_a - V_b = V_{s,m}$$

---

## 2. Traducción de la Topología a la Representación Matricial ($A \cdot X = b$)

El algoritmo implementado en [`AnalizadorNodos.construir_sistema`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo1_modelo/analizador_nodos.py#L90-L195) ensambla el sistema lineal mediante la técnica de **Estampado Matricial (Matrix Stamping)**.

Para un circuito con $N$ nodos incógnita y $M$ fuentes de voltaje independientes, el sistema tiene dimensión $(N + M) \times (N + M)$ y se divide en cuatro bloques:

$$
\underbrace{
\begin{bmatrix}
G_{N \times N} & B_{N \times M} \\
C_{M \times N} & D_{M \times M}
\end{bmatrix}
}_{A}
\underbrace{
\begin{bmatrix}
\mathbf{v}_{N \times 1} \\
\mathbf{j}_{M \times 1}
\end{bmatrix}
}_{X}
=
\underbrace{
\begin{bmatrix}
\mathbf{i}_{N \times 1} \\
\mathbf{e}_{M \times 1}
\end{bmatrix}
}_{b}
$$

Donde:
* **$G \in \mathbb{R}^{N \times N}$ (Matriz de Conductancias):**
  * **Elementos diagonales ($G_{ii}$):** Suma de todas las conductancias conectadas directamente al nodo $i$.
  * **Elementos fuera de la diagonal ($G_{ij}$, con $i \neq j$):** Negativo de la suma de conductancias conectadas directamente entre el nodo $i$ y el nodo $j$ ($-G_{ij}$).
* **$B \in \mathbb{R}^{N \times M}$ y $C = B^T \in \mathbb{R}^{M \times N}$ (Incidencia de Fuentes de Voltaje):** Contienen $+1$ en el índice del nodo conectado al terminal positivo ($+$), $-1$ en el índice del nodo conectado al terminal negativo ($-$), y $0$ en el resto.
* **$D \in \mathbb{R}^{M \times M}$:** Matriz de ceros ($0$) para fuentes independientes ideales.
* **$\mathbf{i} \in \mathbb{R}^{N \times 1}$:** Suma algebraica de corrientes de fuentes independientes que entran ($+$) o salen ($-$) de cada nodo.
* **$\mathbf{e} \in \mathbb{R}^{M \times 1}$:** Valores en voltios de las $M$ fuentes de voltaje.

> [!NOTE]
> **Caso particular sin fuentes de voltaje ($M = 0$):** Cuando el circuito solo tiene resistencias y fuentes de corriente, los bloques $B, C, D, \mathbf{j}, \mathbf{e}$ desaparecen automáticamente, quedando el sistema clásico $G \cdot \mathbf{v} = \mathbf{i}$ de dimensión $N \times N$.

### Reglas de Estampado por Elemento

| Componente | Conectado entre | Contribución a la Matriz $A$ | Contribución al Vector $b$ |
| :--- | :--- | :--- | :--- |
| **Resistencia** ($G = 1/R$) | Nodo $a$ y Nodo $b$ | $A[a,a] \mathrel{+}= G$, $A[b,b] \mathrel{+}= G$<br>$A[a,b] \mathrel{-}= G$, $A[b,a] \mathrel{-}= G$ | Ninguna |
| **Fuente de Corriente** ($I_s$) | Sale de $a \to$ Entra a $b$ | Ninguna | $b[a] \mathrel{-}= I_s$<br>$b[b] \mathrel{+}= I_s$ |
| **Fuente de Voltaje** ($V_s$, índice $k$) | Terminal $(+) = a$, $(-) = b$ | $A[a,k] \mathrel{+}= 1$, $A[b,k] \mathrel{-}= 1$<br>$A[k,a] \mathrel{+}= 1$, $A[k,b] \mathrel{-}= 1$ | $b[k] = V_s$ |

*(Nota: Si $a = 0$ o $b = 0$, las entradas correspondientes al nodo de tierra se omiten porque $V_0 = 0\text{ V}$).*

---

## 3. Arquitectura de Clases del Módulo 1

El código se estructura en dos archivos dentro de `modulo1_modelo/`:

1. [elementos.py](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo1_modelo/elementos.py):
   * [`Nodo`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo1_modelo/elementos.py#L14-L35): Dataclass inmutable que identifica cada punto de unión (`id_nodo=0` es automáticamente `GND`).
   * [`Componente`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo1_modelo/elementos.py#L38-L77): Clase abstracta base para dipolos eléctricos (`nodo_a`, `nodo_b`, `valor`), con validación contra cortocircuitos sobre el mismo nodo.
   * [`Resistencia`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo1_modelo/elementos.py#L80-L108): Valida $R > 0\,\Omega$ y expone la propiedad calculada `conductancia` ($G = 1/R$).
   * [`FuenteCorriente`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo1_modelo/elementos.py#L111-L130) y [`FuenteVoltaje`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo1_modelo/elementos.py#L133-L157): Clases para fuentes DC independientes.
   * [`Circuito`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo1_modelo/elementos.py#L160-L250): Contenedor que registra nodos y componentes con métodos de fábrica (`agregar_resistencia`, `agregar_fuente_corriente`, `agregar_fuente_voltaje`).
2. [analizador_nodos.py](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo1_modelo/analizador_nodos.py):
   * [`SistemaEcuacionesNodos`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo1_modelo/analizador_nodos.py#L22-L44): Contenedor del resultado con `matriz_A`, `vector_b`, `etiquetas_incognitas` y diccionarios de mapeo.
   * [`AnalizadorNodos`](file:///c:/Users/Imprenta/Desktop/CALCULADORA/modulo1_modelo/analizador_nodos.py#L47-L195): Valida la conectividad del grafo eléctrico y ejecuta el algoritmo de estampado.

---

## 4. Ejemplo de Uso del Código (Módulo 1)

```python
from modulo1_modelo import Circuito, AnalizadorNodos

# 1. Instanciar el circuito (el nodo 0 = GND se crea automáticamente)
circuito = Circuito("Ejemplo Divisor y Fuente de Corriente")

# 2. Agregar componentes conectando entre IDs de nodo
# Fuente de corriente I1 de 4 A que fluye desde Tierra (0) hacia el Nodo 1
circuito.agregar_fuente_corriente("I1", id_nodo_origen=0, id_nodo_destino=1, valor_amperios=4.0)

# Resistencias R1 (2 Ω entre Nodo 1 y GND), R2 (4 Ω entre Nodo 1 y 2), R3 (2 Ω entre Nodo 2 y GND)
circuito.agregar_resistencia("R1", id_nodo_a=1, id_nodo_b=0, valor_ohms=2.0)
circuito.agregar_resistencia("R2", id_nodo_a=1, id_nodo_b=2, valor_ohms=4.0)
circuito.agregar_resistencia("R3", id_nodo_a=2, id_nodo_b=0, valor_ohms=2.0)

# Fuente de corriente I2 de 2 A que sale del Nodo 2 hacia Tierra (0)
circuito.agregar_fuente_corriente("I2", id_nodo_origen=2, id_nodo_destino=0, valor_amperios=2.0)

# 3. Construir automáticamente la matriz A y el vector b
analizador = AnalizadorNodos(circuito)
sistema = analizador.construir_sistema()

print("Incógnitas:", sistema.etiquetas_incognitas)
# Salida: ['V_N1', 'V_N2']

print("Matriz de Conductancias A:\n", sistema.matriz_A)
# Salida:
# [[ 0.75 -0.25]
#  [-0.25  0.75]]

print("Vector de Corrientes b:\n", sistema.vector_b)
# Salida: [ 4. -2.]
```

