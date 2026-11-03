"""
Punto de Entrada Principal del Simulador de Circuitos DC por Nodos.

Uso:
    - `python main.py`          : Inicia la interfaz gráfica PySide6 (si está instalada)
                                  o ejecuta la demostración en consola como alternativa.
    - `python main.py --cli`    : Ejecuta la demostración en consola y las pruebas de validación.
"""

import sys


def main() -> None:
    if "--cli" in sys.argv:
        from tests.test_integracion_modulos import demostrar_simulacion_consola
        demostrar_simulacion_consola()
        return

    try:
        from interfaz_pyside6.ventana_principal import ejecutar_app
        ejecutar_app()
    except ImportError:
        print(
            "Aviso: PySide6 no se encontró en el entorno actual. "
            "Ejecutando demostración completa en modo consola (--cli):\n"
        )
        from tests.test_integracion_modulos import demostrar_simulacion_consola
        demostrar_simulacion_consola()


if __name__ == "__main__":
    main()

