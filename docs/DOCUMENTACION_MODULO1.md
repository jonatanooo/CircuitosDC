# Módulo 1: Modelo Eléctrico y Generación de Ecuaciones

**Integrante 1:** representar en Python los nodos, resistencias, fuentes y conexiones del circuito, y generar automáticamente las ecuaciones del análisis nodal (matriz A y vector b).

Archivos: [elementos.py](../modulo1_modelo/elementos.py) (clases del modelo) y [analizador_nodos.py](../modulo1_modelo/analizador_nodos.py) (estampado MNA).

---

## 1. El método de nodos en 3 ideas

1. **Tierra y conductancias.** Se elige un nodo de referencia GND (id_nodo = 0, con V0 = 0 V); los demás nodos tienen voltaje incógnita (V1, V2, ..., VN). Cada resistencia se expresa como conductancia G = 1/R, y la corriente que sale del nodo "a" hacia el nodo "b" es: I(a→b) = G · (Va − Vb) (Ley de Ohm).
2. **LCK por nodo.** En cada nodo, la suma de corrientes que salen por resistencias iguala la corriente neta que aportan las fuentes:
   (suma de G conectadas al nodo k) · Vk − (suma de G·Vj de los nodos vecinos j) = I_neta del nodo k
   El primer término va a la diagonal de A; los segundos, con signo menos, van fuera de la diagonal.
3. **Fuentes de voltaje → MNA.** La corriente de una fuente de voltaje no se puede escribir con conductancias, así que se agrega como incógnita extra (I_Vm) más una fila de restricción: Va − Vb = Vs. Si la fuente flota entre dos nodos, forma un **supernodo**. Lo mismo aplica a la fuente dependiente **CCVS**: Va − Vb = r · i_fi, donde i_fi es la corriente del componente de control (debe estar registrado en el mismo Circuito).

## 2. Del circuito a la matriz A · X = b

`AnalizadorNodos.construir_sistema()` recorre los componentes y "estampa" su aporte (técnica Matrix Stamping). Con N nodos y M fuentes de voltaje, el sistema es de (N+M) × (N+M):

- **G (N × N):** diagonal = suma de conductancias conectadas al nodo; fuera de la diagonal = −G entre nodos vecinos.
- **B y C (transpuesta de B):** +1 en el nodo del terminal positivo, −1 en el del negativo, por cada fuente de voltaje.
- **b:** corrientes de fuentes independientes que entran (+) o salen (−) de cada nodo, más los valores Vs en las filas de restricción. (Si un terminal es GND, su entrada se omite porque V0 = 0.)

| Componente | Aporte a A | Aporte a b |
| :--- | :--- | :--- |
| Resistencia G = 1/R (nodos a, b) | A[a,a] y A[b,b] suman G; A[a,b] y A[b,a] restan G | — |
| Fuente de corriente Is (de a hacia b) | — | b[a] resta Is; b[b] suma Is |
| Fuente de voltaje Vs (+ en a, − en b, índice k) | A[a,k] suma 1, A[b,k] resta 1 (y lo mismo en la fila k) | b[k] = Vs |
| CCVS r·i_fi | Igual que fuente de voltaje, más en la fila k: −r·Gc / +r·Gc en los nodos del control si el control es una resistencia Rc (Gc = 1/Rc); −r en la columna de I_ctrl si el control es otra fuente V | 0, o r·Is si el control es una fuente de corriente |

Sin fuentes de voltaje (M = 0) el sistema se reduce al nodal clásico G · v = i.

## 3. Clases (resumen)

- **Nodo**: punto de unión (id_nodo = 0 es GND automáticamente).
- **Resistencia** (valida R > 0, expone `conductancia`), **FuenteCorriente**, **FuenteVoltaje**, **FuenteVoltajeControladaCorriente** (CCVS con su `componente_control`).
- **Circuito**: registra nodos y componentes; fábricas `agregar_resistencia / agregar_fuente_corriente / agregar_fuente_voltaje / agregar_fuente_ccvs`; `resumen_topologia()` describe el circuito en texto.
- **AnalizadorNodos**: valida la topología y construye el sistema.
- **SistemaEcuacionesNodos**: guarda `matriz_A`, `vector_b`, `etiquetas_incognitas` y genera las ecuaciones en texto (`resumen_sistema()`), sin resolver.

## 4. Ejemplos de funcionamiento (verificados por ejecución)

**A. Nodal puro** — I1 = 4 A entra al N1; R1 = 2 ohm (N1–GND), R2 = 4 ohm (N1–N2), R3 = 2 ohm (N2–GND); I2 = 2 A sale de N2 a GND:

```python
from modulo1_modelo import Circuito, AnalizadorNodos
ckt = Circuito("Nodal puro")
ckt.agregar_fuente_corriente("I1", 0, 1, 4.0)
ckt.agregar_resistencia("R1", 1, 0, 2.0)
ckt.agregar_resistencia("R2", 1, 2, 4.0)
ckt.agregar_resistencia("R3", 2, 0, 2.0)
ckt.agregar_fuente_corriente("I2", 2, 0, 2.0)
sistema = AnalizadorNodos(ckt).construir_sistema()
print(sistema.resumen_sistema())
```

```text
Sistema MNA: 2 ecuaciones, incógnitas ['V_N1', 'V_N2']
Matriz A: [[0.75, -0.25], [-0.25, 0.75]]   Vector b: [4.0, -2.0]
E1: (0.75)·V_N1 + (-0.25)·V_N2 = 4
E2: (-0.25)·V_N1 + (0.75)·V_N2 = -2        →  V1 = 5 V, V2 = -1 V
```

**B. Supernodo** — fuente flotante V1 = 2 V (+ en N1, − en N2) con R1 = 2, R2 = 4, R3 = 10 ohm; I1 = 2 A entra a N1, I2 = 7 A sale de N2. La fila E3 es la restricción V1 − V2 = 2:

```text
Incógnitas ['V_N1', 'V_N2', 'I_V1']
A = [[0.6, -0.1, 1], [-0.1, 0.35, -1], [1, -1, 0]]   b = [2, -7, 2]
→  V1 = -6 V, V2 = -8 V
```

**C. Circuito de Fase 1 (con CCVS)** — el mismo de la Fase 1 y la interfaz: fuente de 20 V (+ en N_Vs, − en GND) en serie con 2 ohm hacia V1; 20 ohm (V1–GND); 5 ohm (V1–V2, rama de i_fi); 10 ohm (V2–GND); 2 ohm (V2–V3); CCVS de 8·i_fi (+ en V3, − en GND):

```python
ckt = Circuito("Fase 1 con CCVS")
for i, n in [(0, "GND"), (1, "V1"), (2, "V2"), (3, "V3"), (4, "N_Vs")]:
    ckt.obtener_o_crear_nodo(i, n)
ckt.agregar_fuente_voltaje("Vs_20V", 4, 0, 20.0)
ckt.agregar_resistencia("R_2ohm_serie", 4, 1, 2.0)
ckt.agregar_resistencia("R_20ohm", 1, 0, 20.0)
r5 = ckt.agregar_resistencia("R_5ohm", 1, 2, 5.0)
ckt.agregar_resistencia("R_10ohm", 2, 0, 10.0)
ckt.agregar_resistencia("R_2ohm_v2v3", 2, 3, 2.0)
ckt.agregar_fuente_ccvs("CCVS_8iphi", 3, 0, 8.0, r5)
print(AnalizadorNodos(ckt).construir_sistema().resumen_sistema())
```

```text
Incógnitas ['V_V1', 'V_V2', 'V_V3', 'V_N_Vs', 'I_Vs_20V', 'I_CCVS_8iphi']
A = [[0.75, -0.2, 0, -0.5, 0, 0], [-0.2, 0.8, -0.5, 0, 0, 0],
     [0, -0.5, 0.5, 0, 0, 1],   [-0.5, 0, 0, 0.5, 1, 0],
     [0, 0, 0, 1, 0, 0],        [-1.6, 1.6, 1, 0, 0, 0]]
b = [0, 0, 0, 0, 20, 0]
```

La última fila es la CCVS: como G de 5 ohm = 0.2 S, r·Gc = 1.6, o sea V3 − 1.6·(V1 − V2) = 0. Referencia: V1 = 16, V2 = 10, V3 = 9.6 V; i_fi = 1.2 A; P de 5 ohm = 7.2 W.

## 5. Límites del modelo

Solo DC permanente (sin capacitores ni inductores); dependientes solo tipo CCVS; este módulo **formula** el sistema A·x = b pero no lo resuelve (eso es del Módulo 2); un circuito sin camino a GND o con fuentes de voltaje en paralelo contradictorias da matriz singular, que se detecta al resolver.
