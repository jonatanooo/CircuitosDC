# Simulador de Circuitos DC — Análisis por Nodos (MNA)

Primera versión del simulador de circuitos eléctricos de corriente continua (DC) enfocado en el **Método de Nodos y Análisis Nodal Modificado (MNA)**, desarrollado en Python utilizando **NumPy** (resolución matricial), **SymPy** (representación simbólica/algebraica) y **PySide6** (interfaz gráfica de escritorio).

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
│   └── simbolico_sympy.py          # Ecuaciones simbólicas SymPy y cálculo de V, I, P por elemento + Tellegen
│
├── interfaz_pyside6/               # Interfaz Gráfica de Usuario (Qt / PySide6)
│   ├── __init__.py
│   └── ventana_principal.py        # Ventana interactiva que conecta el Módulo 1 y el Módulo 2
│
├── tests/                          # Pruebas de validación e integración
│   └── test_integracion_modulos.py # Suite unittest + demostración completa en consola
│
├── docs/                           # Documentación técnica detallada por integrante
│   ├── DOCUMENTACION_MODULO1.md    # Teoría nodal paso a paso, estampado matricial y ejemplos del Módulo 1
│   └── DOCUMENTACION_MODULO2.md    # Explicación técnica de NumPy/SymPy, balance de potencia y tests del Módulo 2
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
   python tests/test_integracion_modulos.py
   ```

3. **Iniciar la interfaz gráfica PySide6:**
   ```bash
   python main.py
   ```
   *(O usar `python main.py --cli` para ejecutar directamente en modo terminal).*

