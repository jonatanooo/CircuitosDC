# Comparación del circuito de fase 1 con Qucs-S y ngspice

## Referencia

La comparación utiliza los valores transcritos en el documento proporcionado por el equipo, **Simulacion_QucsS_ngspice_Fase1.docx**. El documento describe una simulación DC en Qucs-S 26.1.1 con ngspice y una fuente de voltaje controlada por corriente (CCVS) de transresistencia 8 Ω. No se volvió a ejecutar Qucs-S como parte de esta comprobación.

En Qucs-S, el documento obtiene la corriente iφ y la potencia en la resistencia de 5 Ω a partir de los voltajes nodales. La columna de LTspice reproduce los valores que el documento atribuye a esa herramienta; no se ha verificado aquí una ejecución independiente de LTspice.

## Correspondencia de componentes

| Circuito | Qucs-S, según el documento | Simulador del proyecto |
|---|---|---|
| Fuente de 20 V | V20 | Vs |
| Resistencia superior izquierda de 2 Ω | R11 | R_2a |
| Resistencia vertical izquierda de 20 Ω | R10 | R_20 |
| Resistencia de 5 Ω, corriente iφ | R14 | R_5 |
| Resistencia vertical derecha de 10 Ω | R16 | R_10 |
| Resistencia superior derecha de 2 Ω | R15 | R_2b |
| Fuente dependiente 8·iφ | SRC1 | CCVS1 |

## Resultados principales

Los valores del simulador propio se comprobaron con la prueba `test_circuito_drag_drop.py` y con la prueba de la interfaz `tests/test_nodos_interfaz.py`. Las diferencias de la tabla están calculadas con los valores mostrados, sin interpretar el cero como una garantía de igualdad de precisión infinita.

| Magnitud | Teórico, según documento | Qucs-S + ngspice, según documento | LTspice, según documento | Simulador propio | Diferencia respecto a Qucs-S |
|---|---:|---:|---:|---:|---:|
| Nodo de referencia | 0 V | 0 V | — | 0 V | 0 V |
| Nodo izquierdo de 5 Ω (VA / V1) | 16 V | 16 V | 16 V | 16 V | 0 V |
| Nodo derecho de 5 Ω (VB / V2) | 10 V | 10 V | 10 V | 10 V | 0 V |
| Salida de la fuente dependiente (V3) | 9,6 V | 9,6 V | 9,6 V | 9,6 V | 0 V |
| Corriente de control iφ, de V1 a V2 | 1,2 A | 1,2 A calculados* | 1,2 A | 1,2 A | 0 A |
| Potencia disipada en 5 Ω | 7,2 W | 7,2 W calculados* | 7,2 W | 7,2 W | 0 W |

\* El documento de Qucs-S indica que estas magnitudes se calcularon a partir de los voltajes visualizados con DC Bias.

Para la potencia, usando 7,2 W como valor de referencia, el error porcentual con los valores mostrados es `|7,2 − 7,2| / 7,2 × 100 = 0 %`. No se calcula error relativo para GND, porque el valor de referencia es cero; en ese caso se informa la diferencia absoluta.

## Comprobaciones eléctricas y signos

- `iφ = (16 − 10) / 5 = 1,2 A` y `P = iφ² · 5 = 7,2 W`.
- `V_CCVS = 8 Ω · 1,2 A = 9,6 V`.
- En V1: `2 A = 0,8 A + 1,2 A`.
- En V2: `1,2 A = 1 A + 0,2 A`.
- La corriente de la fuente de 20 V aparece como −2 A cuando su referencia se toma desde el terminal positivo hacia tierra. El signo señala que la corriente real circula en sentido contrario; con esa convención la fuente entrega 40 W y su potencia aparece como −40 W.
- La fuente dependiente tiene una tensión de 9,6 V y una corriente de 0,2 A en el sentido positivo a negativo de sus terminales, por lo que absorbe 1,92 W. Junto a las resistencias, la potencia absorbida suma 40 W.

## Repetir la verificación

Desde la raíz del repositorio:

```powershell
python -m unittest test_circuito_drag_drop tests.test_nodos_interfaz
```

En el entorno virtual creado para este proyecto se puede sustituir `python` por `.\.venv\Scripts\python.exe`. Para revisar la interfaz, abrir la aplicación, restablecer el circuito de referencia y pulsar **Iniciar simulación**.

## Pendiente de validación

Conservar el documento y las capturas originales de Qucs-S junto a la entrega del equipo. Si se requiere evidencia reproducible entre herramientas, reunir los archivos de simulación y ejecutar de nuevo Qucs-S/ngspice y LTspice con las mismas referencias y polaridades. Comprobar cualquier diferencia con los valores sin redondear antes de concluir que es un error del motor.
