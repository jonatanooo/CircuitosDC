# Simulador de Circuitos DC — Análisis por Nodos (MNA)

Simulador de circuitos eléctricos de corriente continua (DC) con **análisis nodal modificado (MNA)** y una primera implementación de **corrientes de lazos independientes (mallas)**. Está desarrollado en Python utilizando **NumPy** (resolución matricial), **SymPy** (representación simbólica/algebraica) y **PySide6** (interfaz gráfica de escritorio).

## Estructura del Proyecto y División de Trabajo

```text
CALCULADORA/
├── modulo1_modelo/                 # [INTEGRANTE 1] Modelo eléctrico y generación de ecuaciones
│   ├── __init__.py
│   ├── elementos.py                # Clases: Nodo, Componente, Resistencia, FuenteCorriente, FuenteVoltaje, Circuito
│   └── analizador_nodos.py         # Algoritmo MNA de estampado matricial (Matriz A y Vector b)
│
├── modulo2_motor/                  # [INTEGRANTE 2] Motor matemático con NumPy y SymPy
│   ├── __init__.py
│   ├── resolvedor_numpy.py         # Resolución lineal A*X = B con numpy.linalg.solve y diagnóstico numérico
│   ├── simbolico_sympy.py          # Ecuaciones simbólicas SymPy y cálculo de V, I, P por elemento + Tellegen
│   └── analizador_mallas.py        # Lazos independientes y restricciones de fuentes de corriente
│
├── interfaz_pyside6/               # Interfaz Gráfica de Usuario (Qt / PySide6)
│   ├── __init__.py
│   ├── componentes_graficos.py     # Componentes, terminales y cables gráficos
│   └── ventana_principal.py        # Ventana interactiva que conecta el Módulo 1 y el Módulo 2
│
├── tests/                          # Pruebas de validación e integración
│   ├── test_integracion_modulos.py  # Pruebas del modelo y motor
│   ├── test_nodos_interfaz.py      # Nodos, resultados y conectividad gráfica
│   └── test_flujo_interfaz.py      # Pruebas de interacción mediante eventos Qt
│
├── docs/                           # Documentación técnica detallada por integrante
│   ├── DOCUMENTACION_MODULO1.md    # Teoría nodal paso a paso, estampado matricial y ejemplos del Módulo 1
│   ├── DOCUMENTACION_MODULO2.md    # Explicación técnica de NumPy/SymPy y tests del Módulo 2
│   ├── DOCUMENTACION_MODULO3_GUI.md # Uso, capturas, pruebas y límites de la interfaz
│   └── capturas/                   # Evidencias de la interfaz
│
├── main.py                         # Punto de entrada principal (GUI o CLI)
└── requirements.txt                # Dependencias del proyecto
```

## Instalación y Ejecución

1. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Ejecutar las pruebas unitarias y demostración en consola (Validación de Módulos 1 y 2):**
   ```bash
   python -m unittest discover -s tests
   python -m unittest test_circuito_drag_drop
   ```

3. **Iniciar la interfaz gráfica PySide6:**
   ```bash
   python main.py
   ```
   *(O usar `python main.py --cli` para ejecutar directamente en modo terminal).*

Para conocer los controles, el circuito de ejemplo, las capturas y los tamaños de ventana comprobados, consulta la [documentación de la interfaz](docs/DOCUMENTACION_MODULO3_GUI.md).

Para comparar el circuito de fase 1 con los valores documentados en Qucs-S/ngspice, consulta la [tabla de validación](docs/COMPARACION_QUCSS_FASE1.md).

