"""
Módulo 3: Interfaz Gráfica de Usuario (GUI) en PySide6 con Drag & Drop,
Eliminación de Componentes/Cables, Ventanas de Error de Cálculo y Soporte CCVS.

Incorpora:
    1. Paleta de componentes con soporte "Arrastrar y Soltar" (`BotonPaletaDrag` -> `QDrag` / `QMimeData`).
    2. Lienzo interactivo (`VistaEsquematicoDC` + `EscenaEsquematicoDC`) con `ComponenteGraficoItem`
       (`ItemIsMovable`, `ItemIsSelectable`) y trazado de cables (`CableGraficoItem`).
    3. Eliminación de componentes y cables mediante:
       - Botón "Eliminar componente" en el Panel Derecho de Propiedades y en la Barra Superior.
       - Menú contextual de clic derecho sobre cualquier componente o cable en el lienzo.
       - Teclas rápidas `Supr` (`Delete`) o `Backspace`.
    4. Detección de errores topológicos y matemáticos (terminales abiertos tras eliminar un
       componente, falta de referencia a tierra, eliminación de rama de control de una CCVS o
       matriz singular MNA) mostrando una ventana modal de error (`QMessageBox.critical`).
"""

import sys
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Set

from PySide6.QtCore import QLineF, QPointF, Qt, Signal, QTimer
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QIcon,
    QKeySequence,
    QPainter,
    QPen,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QFileDialog,
    QGraphicsLineItem,
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QScrollArea,
    QSlider,
    QToolBox,
    QToolButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from interfaz_pyside6.componentes_graficos import (
    MIME_TYPE_COMPONENTE,
    BotonPaletaDrag,
    CableGraficoItem,
    ComponenteGraficoItem,
    TerminalGraficoItem,
)
from interfaz_pyside6.importador_asc import importar_asc
from interfaz_pyside6.comparacion_fase1 import comparar_fase1
from modulo1_modelo import AnalizadorNodos, Circuito
from modulo2_motor import (
    AnalizadorSimbolicoYResultados,
    ErrorCircuitoSingular,
    MotorNumericoNumPy,
)
from modulo2_motor.analizador_mallas import AnalizadorMallas


# =============================================================================
# HOJA DE ESTILOS GLOBAL (QSS)
# =============================================================================

ESTILO_QSS = """
QWidget { color: #1d3835; font-family: "Segoe UI"; }
QDialog, QMessageBox { background-color: #f5faf8; color: #1d3835; }
QLineEdit, QComboBox { background-color: #ffffff; color: #1d3835; border: 1px solid #bcd4ce; border-radius: 6px; padding: 7px; selection-background-color: #bce4db; selection-color: #173c36; }
QComboBox QAbstractItemView { background-color: #ffffff; color: #1d3835; selection-background-color: #d9eee9; selection-color: #173c36; }
QToolBox, QToolBox > QWidget, QToolBox > QWidget > QWidget { background-color: #f4faf8; color: #1d3835; border: 0; }
QToolBox::tab { min-height: 32px; padding: 6px 10px; }
QStatusBar { background-color: #edf6f3; color: #345d54; }
QTextEdit, QTreeWidget, QTableWidget { color: #172b3a; background-color: #ffffff; }
QMenu { background-color: #ffffff; color: #172b3a; }
QMenu::item { padding: 8px 32px 8px 18px; }
QMenu::item:selected { background-color: #dcefeb; color: #123c38; }
QPushButton { color: #172b3a; background-color: #f4f8f8; border: 1px solid #cbdcda; border-radius: 6px; padding: 6px 10px; }
QPushButton:hover { background-color: #dcefeb; }
QPushButton:checked { background-color: #bce4db; color: #123c38; border: 1px solid #48a691; }
QToolBox::tab { background: #edf4f3; color: #284942; border: 1px solid #d5e3e0; border-radius: 5px; padding: 8px; font-weight: 600; }
QToolBox::tab:selected { background: #d9eee9; color: #15584c; }
QSlider::groove:horizontal { height: 5px; background: #d5e3e0; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #15947f; border-radius: 2px; }
QSlider::handle:horizontal { background: #087c6c; width: 14px; margin: -5px 0; border-radius: 7px; }
QMainWindow, QWidget#FondoPrincipal {
    background-color: #F8F9F8;
    color: #212529;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}
QMenuBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #EAECE9;
    padding: 4px 12px;
    color: #495057;
}
QToolBar#BarraSuperior {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E6E3;
    padding: 8px 16px;
    spacing: 8px;
}
QPushButton.BotonToolbar {
    background-color: #FFFFFF;
    border: 1px solid #DCE1DD;
    border-radius: 6px;
    padding: 6px 14px;
    color: #2C332E;
    font-weight: 500;
}
QPushButton.BotonToolbar:hover {
    background-color: #F1F5F2;
}
QPushButton.BotonEliminar {
    background-color: #FFF5F5;
    border: 1px solid #F1AEB5;
    border-radius: 6px;
    padding: 6px 14px;
    color: #B02A37;
    font-weight: 600;
}
QPushButton.BotonEliminar:hover {
    background-color: #F8D7DA;
    border: 1px solid #EA868F;
}
QFrame#ContenedorSegmentado {
    background-color: #EEF1EE;
    border: 1px solid #DCE1DD;
    border-radius: 7px;
    padding: 2px;
}
QPushButton.BotonSegmento {
    background-color: transparent;
    border: none;
    border-radius: 5px;
    padding: 5px 16px;
    color: #5C6660;
    font-weight: 600;
}
QPushButton.BotonSegmento:checked {
    background-color: #FFFFFF;
    color: #212529;
    border: 1px solid #DCE1DD;
}
QPushButton#BotonAnalizar {
    background-color: #147b69;
    color: #FFFFFF;
    border: none;
    border-radius: 7px;
    padding: 7px 24px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton#BotonAnalizar:hover {
    background-color: #0d6657;
}
QFrame.PanelBlanco {
    background-color: #FFFFFF;
    border: 1px solid #E4E8E5;
    border-radius: 8px;
}
QFrame.PanelLateral {
    background-color: #FFFFFF;
    border: 1px solid #E4E8E5;
}
QLabel.TituloSeccion {
    color: #6C757D;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.6px;
}
QTreeWidget#ArbolCircuito {
    border: none;
    background-color: transparent;
    font-size: 12px;
    outline: 0;
    color: #172b3a;
}
QTreeWidget#ArbolCircuito::item {
    padding: 4px 6px;
    border-radius: 5px;
}
QTreeWidget#ArbolCircuito::item:selected {
    background-color: #E7F0E9;
    color: #1E3A28;
    font-weight: 600;
}
QPushButton.BotonInsertar {
    background-color: #FFFFFF;
    border: 1px solid #E6EBE7;
    border-radius: 7px;
    padding: 7px 10px;
    text-align: left;
    color: #2B302C;
}
QPushButton.BotonInsertar:hover {
    background-color: #F3F7F4;
    border: 1px solid #C8DDD0;
}
QPushButton.BotonInsertarActivo {
    background-color: #E7F0E9;
    border: 1px solid #9EC5AB;
    border-radius: 7px;
    padding: 7px 10px;
    text-align: left;
    color: #1E3A28;
    font-weight: 600;
}
QLabel#BadgeEstado {
    background-color: #E6F2EA;
    color: #2E6F46;
    border: 1px solid #C6E2CF;
    border-radius: 11px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#BadgeElemento {
    background-color: #EEF2EF;
    color: #495057;
    border: 1px solid #DCE1DD;
    border-radius: 5px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 700;
}
QFrame.TarjetaMetrica {
    background-color: #FBFCFB;
    border: 1px solid #E5E9E6;
    border-radius: 8px;
}
QFrame#TarjetaCorrienteTotal {
    background-color: #EAEFEC;
    border: 1px solid #D5E0D8;
    border-radius: 8px;
}
QTableWidget#TablaLecturas {
    background-color: #FFFFFF;
    border: none;
    gridline-color: #EFF2F0;
    selection-background-color: #E7F0E9;
    selection-color: #1E3A28;
    outline: 0;
    color: #172b3a;
}
QTableWidget#TablaLecturas::item:hover { background-color: #e7f4ef; color: #164d41; }
QTableWidget#TablaLecturas::item:selected { background-color: #cce9df; color: #123f35; }
QHeaderView::section {
    background-color: #FFFFFF;
    color: #7A827C;
    font-size: 11px;
    font-weight: 600;
    border: none;
    border-bottom: 1px solid #E5E9E6;
    padding: 6px 8px;
    text-align: left;
}
QLineEdit#InputValorPropiedad {
    background-color: #FFFFFF;
    border: 1px solid #D6DBD7;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    font-weight: 600;
    color: #212529;
}
QDialog, QMessageBox { background-color: #f5faf8; color: #1d3835; }
QDialog QLabel, QMessageBox QLabel { color: #1d3835; background: transparent; }
QDialog QLineEdit, QDialog QComboBox { background: #ffffff; color: #1d3835; border: 1px solid #bcd4ce; border-radius: 6px; padding: 7px; }
QToolButton#Categoria { background: #e8f3ef; color: #28554a; border: 1px solid #cfdfda; border-radius: 6px; text-align: left; padding: 8px; font-weight: 600; }
QToolButton#Categoria:hover { background: #d9eee6; }
QTabWidget::pane { border: 1px solid #d6e6e1; border-radius: 6px; background: #ffffff; }
QTabBar::tab { background: #edf6f3; color: #31584f; padding: 7px 14px; margin-right: 3px; border-top-left-radius: 5px; border-top-right-radius: 5px; }
QTabBar::tab:selected { background: #d7eee7; color: #165749; font-weight: 600; }
QScrollArea { border: none; background: #ffffff; }
QScrollArea > QWidget > QWidget { background: #ffffff; }
QAbstractScrollArea::corner { background: #ffffff; border: none; }
QScrollBar:vertical { background: #f5faf8; width: 7px; border: none; }
QScrollBar:horizontal { background: #f5faf8; height: 7px; border: none; }
QScrollBar::handle:vertical, QScrollBar::handle:horizontal { background: #a8c9bf; border-radius: 3px; min-height: 24px; min-width: 24px; }
QScrollBar::handle:hover { background: #6fa99a; }
QScrollBar::add-page, QScrollBar::sub-page { background: #f5faf8; border: none; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QPushButton#BotonAnalizar { background: #147b69; color: white; }
QPushButton#BotonAnalizar:hover { background: #0d6657; }
"""


# =============================================================================
# ESCENA Y VISTA GRÁFICA CON SOPORTE DRAG & DROP, CABLES Y ELIMINACIÓN
# =============================================================================

class EscenaEsquematicoDC(QGraphicsScene):
    """
    Escena interactiva (`QGraphicsScene`) que gestiona:
        - Objetos `ComponenteGraficoItem` movibles y seleccionables.
        - Trazado interactivo de `CableGraficoItem` entre terminales (`TerminalGraficoItem`).
        - Recepción de componentes arrastrados desde la paleta (`dropEvent`).
        - Eliminación segura de componentes y sus cables asociados (`eliminar_componente`,
          `eliminar_cable`, `eliminar_seleccionados`).
    """

    componente_seleccionado = Signal(str)
    antes_de_cambio = Signal()
    componente_doble_clic = Signal(str)
    componente_soltado = Signal(object)
    conexion_creada = Signal(object)
    elemento_eliminado = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setSceneRect(-1200, -900, 3280, 2160)
        self.componentes_graficos: Dict[str, ComponenteGraficoItem] = {}
        self.cables_graficos: List[CableGraficoItem] = []

        self._terminal_inicio_cable: Optional[TerminalGraficoItem] = None
        self._linea_temporal_cable: Optional[QGraphicsLineItem] = None
        self._contador_nuevos: int = 1
        self._contador_nodos_auto: int = 5

        self.selectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self) -> None:
        for item in self.selectedItems():
            if isinstance(item, ComponenteGraficoItem):
                self.componente_seleccionado.emit(item.id_ref)
                break

    def registrar_componente_grafico(self, comp_item: ComponenteGraficoItem) -> None:
        self.componentes_graficos[comp_item.id_ref] = comp_item
        self.addItem(comp_item)

    def eliminar_cable(self, cable: CableGraficoItem) -> None:
        """Desconecta un cable de sus dos terminales y lo remueve de la escena."""
        self.antes_de_cambio.emit()
        if cable in self.cables_graficos:
            self.cables_graficos.remove(cable)
        cable.desconectar_de_terminales()
        if cable.scene() is self:
            self.removeItem(cable)
        self.elemento_eliminado.emit(f"Cable ({cable.etiqueta_nodo})")

    def eliminar_componente(self, id_ref: str) -> bool:
        """
        Elimina el componente `id_ref` del lienzo junto con todos los cables
        conectados a sus terminales A y B.
        """
        if id_ref not in self.componentes_graficos:
            return False

        self.antes_de_cambio.emit()

        comp_item = self.componentes_graficos.pop(id_ref)

        # Eliminar primero todos los cables conectados a este componente
        for cable in comp_item.obtener_todos_los_cables():
            if cable in self.cables_graficos:
                self.cables_graficos.remove(cable)
            cable.desconectar_de_terminales()
            if cable.scene() is self:
                self.removeItem(cable)

        if comp_item.scene() is self:
            self.removeItem(comp_item)

        self.elemento_eliminado.emit(id_ref)
        return True

    def eliminar_seleccionados(self) -> bool:
        """Elimina cualquier componente o cable actualmente seleccionado en el lienzo."""
        seleccionados = list(self.selectedItems())
        if not seleccionados:
            return False

        hubo_eliminacion = False
        for item in seleccionados:
            if isinstance(item, ComponenteGraficoItem):
                if self.eliminar_componente(item.id_ref):
                    hubo_eliminacion = True
            elif isinstance(item, CableGraficoItem):
                self.eliminar_cable(item)
                hubo_eliminacion = True
        return hubo_eliminacion

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.eliminar_seleccionados():
                event.accept()
                return
        super().keyPressEvent(event)

    def conectar_terminales_con_cable(
        self,
        term_a: TerminalGraficoItem,
        term_b: TerminalGraficoItem,
        id_nodo: Optional[int] = None,
        etiqueta_nodo: str = "",
    ) -> Optional[CableGraficoItem]:
        """Crea un `CableGraficoItem` entre `term_a` y `term_b`, unificando su nodo eléctrico."""
        if term_a is term_b or term_a.componente_padre is term_b.componente_padre:
            return None

        self.antes_de_cambio.emit()

        if id_nodo is not None:
            nodo_final = id_nodo
            etiqueta_final = etiqueta_nodo or ("GND" if nodo_final == 0 else f"V{nodo_final}")
        elif term_a.id_nodo == 0 or term_b.id_nodo == 0:
            nodo_final = 0
            etiqueta_final = "GND"
        else:
            nodo_final = term_a.id_nodo
            etiqueta_final = etiqueta_nodo or term_a.etiqueta_nodo

        term_a.id_nodo = nodo_final
        term_b.id_nodo = nodo_final
        term_a.etiqueta_nodo = etiqueta_final
        term_b.etiqueta_nodo = etiqueta_final

        cable = CableGraficoItem(term_a, term_b, etiqueta_final)
        self.cables_graficos.append(cable)
        self.addItem(cable)
        self.conexion_creada.emit(cable)
        return cable

    def recalcular_nodos_desde_cables(self) -> None:
        """
        Analiza los grupos conexos de terminales unidos por objetos `CableGraficoItem`
        para actualizar dinámicamente los identificadores de nodo tras agregar o
        eliminar cables/componentes.
        """
        todos_terminales: List[TerminalGraficoItem] = []
        for comp in self.componentes_graficos.values():
            todos_terminales.append(comp.terminal_a)
            if comp.tipo_catalogo != "TIERRA":
                todos_terminales.append(comp.terminal_b)

        visitados: Set[TerminalGraficoItem] = set()
        grupos: List[List[TerminalGraficoItem]] = []

        for term in todos_terminales:
            if term in visitados:
                continue
            # Búsqueda en anchura (BFS) sobre los cables conectados
            cola = [term]
            grupo_actual: List[TerminalGraficoItem] = []
            visitados.add(term)
            while cola:
                actual = cola.pop(0)
                grupo_actual.append(actual)
                for cable in actual.cables_conectados:
                    vecino = (
                        cable.terminal_destino
                        if cable.terminal_origen is actual
                        else cable.terminal_origen
                    )
                    if vecino not in visitados:
                        visitados.add(vecino)
                        cola.append(vecino)
            grupos.append(grupo_actual)

        # Cada grupo físico recibe un ID distinto. Los nombres temporales de
        # terminales abiertos no deben heredarse al conectar el grupo.
        reservados = {t.id_nodo for grupo in grupos if len(grupo) > 1 for t in grupo
                      if t.id_nodo > 0 and t.etiqueta_nodo and
                      not t.etiqueta_nodo.startswith("N_abierto_")}
        usados = set()
        siguiente_id = 1
        for grupo in grupos:
            tiene_tierra = any(
                t.componente_padre.tipo_catalogo == "TIERRA" for t in grupo
            )
            if tiene_tierra:
                id_asignado = 0
                etiqueta_asignada = "GND"
            else:
                candidatos = [t for t in grupo if t.id_nodo > 0 and t.id_nodo not in usados
                              and t.etiqueta_nodo and t.etiqueta_nodo != "GND"
                              and not t.etiqueta_nodo.startswith("N_abierto_")]
                if len(grupo) > 1 and candidatos:
                    id_asignado = candidatos[0].id_nodo
                    etiqueta_asignada = candidatos[0].etiqueta_nodo
                else:
                    while siguiente_id in usados or siguiente_id in reservados:
                        siguiente_id += 1
                    id_asignado = siguiente_id
                    siguiente_id += 1
                    etiqueta_asignada = (f"V{id_asignado}" if len(grupo) > 1
                                         else f"N_abierto_{id_asignado}")
                usados.add(id_asignado)

            for t in grupo:
                t.id_nodo = id_asignado
                t.etiqueta_nodo = etiqueta_asignada
                for c in t.cables_conectados:
                    c.establecer_etiqueta(etiqueta_asignada)
                    c.update()

    # -------------------------------------------------------------------------
    # Eventos de Ratón para Trazado de Líneas (Cables) entre Terminales
    # -------------------------------------------------------------------------
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            pos_escena = event.scenePos()
            for item in self.items(pos_escena):
                if isinstance(item, TerminalGraficoItem):
                    self._terminal_inicio_cable = item
                    p_ini = item.pos_escena()
                    self._linea_temporal_cable = QGraphicsLineItem(
                        QLineF(p_ini, pos_escena)
                    )
                    pen_temp = QPen(QColor("#2E6F46"), 2.0, Qt.PenStyle.DashLine)
                    self._linea_temporal_cable.setPen(pen_temp)
                    self._linea_temporal_cable.setZValue(20)
                    self.addItem(self._linea_temporal_cable)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._linea_temporal_cable is not None and self._terminal_inicio_cable is not None:
            p_ini = self._terminal_inicio_cable.pos_escena()
            self._linea_temporal_cable.setLine(QLineF(p_ini, event.scenePos()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._linea_temporal_cable is not None and self._terminal_inicio_cable is not None:
            self.removeItem(self._linea_temporal_cable)
            self._linea_temporal_cable = None

            pos_fin = event.scenePos()
            for item in self.items(pos_fin):
                if (
                    isinstance(item, TerminalGraficoItem)
                    and item is not self._terminal_inicio_cable
                ):
                    self.conectar_terminales_con_cable(self._terminal_inicio_cable, item)
                    break

            self._terminal_inicio_cable = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # -------------------------------------------------------------------------
    # Eventos Drag & Drop en la Escena
    # -------------------------------------------------------------------------
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(MIME_TYPE_COMPONENTE) or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(MIME_TYPE_COMPONENTE) or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        mime = event.mimeData()
        if mime.hasFormat(MIME_TYPE_COMPONENTE):
            tipo = bytes(mime.data(MIME_TYPE_COMPONENTE)).decode("utf-8")
        elif mime.hasText():
            tipo = mime.text()
        else:
            return

        pos_drop = event.scenePos()
        self.antes_de_cambio.emit()
        nuevo_item = self.instanciar_componente_por_drop(tipo, pos_drop)
        if nuevo_item is not None:
            self.clearSelection()
            nuevo_item.setSelected(True)
            self.componente_soltado.emit(nuevo_item)
        event.acceptProposedAction()

    def instanciar_componente_por_drop(
        self, tipo_catalogo: str, posicion: QPointF
    ) -> Optional[ComponenteGraficoItem]:
        prefijos = {
            "RESISTENCIA": ("R", "10", "Ω"),
            "FUENTE_VOLTAJE": ("V", "12", "V"),
            "FUENTE_CORRIENTE": ("I", "1", "A"),
            "FUENTE_CCVS": ("CCVS", "8", "·i_φ"),
            "TIERRA": ("GND", "0", "V"),
        }
        if tipo_catalogo not in prefijos:
            return None

        pref, val_def, uni_def = prefijos[tipo_catalogo]
        while f"{pref}{self._contador_nuevos}" in self.componentes_graficos:
            self._contador_nuevos += 1
        id_nuevo = f"{pref}{self._contador_nuevos}"
        self._contador_nuevos += 1

        nodo_a = self._contador_nodos_auto
        nodo_b = self._contador_nodos_auto + 1
        self._contador_nodos_auto += 2

        comp_ctrl_def = "R_5" if "R_5" in self.componentes_graficos else ""
        nuevo = ComponenteGraficoItem(
            id_ref=id_nuevo,
            tipo_catalogo=tipo_catalogo,
            valor_str=val_def,
            unidad_simbolo=uni_def,
            pos_inicial=posicion,
            orientacion="H" if tipo_catalogo == "RESISTENCIA" else "V",
            nodo_a_id=0 if tipo_catalogo == "TIERRA" else nodo_a,
            nodo_b_id=0 if tipo_catalogo == "TIERRA" else nodo_b,
            etiqueta_nodo_a="GND" if tipo_catalogo == "TIERRA" else f"N{nodo_a}",
            etiqueta_nodo_b="GND" if tipo_catalogo == "TIERRA" else f"N{nodo_b}",
            componente_control_ref=comp_ctrl_def,
        )
        self.registrar_componente_grafico(nuevo)
        return nuevo


class VistaEsquematicoDC(QGraphicsView):
    """
    Vista (`QGraphicsView`) configurada con `setAcceptDrops(True)` y suavizado
    Antialiasing para alojar el lienzo de circuito interactivo.
    """

    def __init__(
        self, escena: EscenaEsquematicoDC, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(escena, parent)
        self.setAcceptDrops(True)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing
        )
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setBackgroundBrush(QBrush(QColor("#FFFFFF")))
        # El desplazamiento del lienzo se hace con la mano; mantiene el área limpia.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.centerOn(440, 180)
        self._modo_mano = False
        self._inicio_arrastre = None

    def establecer_modo_mano(self, activo: bool) -> None:
        self._modo_mano = activo
        self.setDragMode(
            QGraphicsView.DragMode.ScrollHandDrag if activo
            else QGraphicsView.DragMode.RubberBandDrag
        )
        self.viewport().setCursor(
            Qt.CursorShape.OpenHandCursor if activo else Qt.CursorShape.ArrowCursor
        )

    def mousePressEvent(self, event) -> None:
        if self._modo_mano and event.button() == Qt.MouseButton.LeftButton:
            self._inicio_arrastre = event.position().toPoint()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._modo_mano and self._inicio_arrastre is not None:
            posicion = event.position().toPoint()
            desplazamiento = posicion - self._inicio_arrastre
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - desplazamiento.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - desplazamiento.y())
            self._inicio_arrastre = posicion
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._modo_mano and self._inicio_arrastre is not None and event.button() == Qt.MouseButton.LeftButton:
            self._inicio_arrastre = None
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def establecer_zoom(self, porcentaje: int) -> None:
        self.resetTransform()
        escala = porcentaje / 100.0
        self.scale(escala, escala)


# =============================================================================
# VENTANA PRINCIPAL (QMainWindow)
# =============================================================================

class VentanaSimuladorDC(QMainWindow):
    """
    Ventana principal del Simulador de Circuitos DC (PySide6).
    Integra Drag & Drop de componentes, cableado interactivo entre terminales,
    opción de eliminar componentes/cables y diálogo modal de errores de cálculo.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Simulador de Circuitos DC — Fase 3")
        self.setWindowIcon(QIcon(str(Path(__file__).resolve().parent.parent / "assets" / "icono_circuito.ico")))
        self.resize(1420, 920)
        self.setStyleSheet(ESTILO_QSS)

        self._id_actual: str = "R_5"
        self._items_arbol_por_id: Dict[str, QTreeWidgetItem] = {}
        self._historial = []
        self._registrar_historial = False
        self._simulando = False
        self._fase_animacion = 0.0
        self._temporizador_animacion = QTimer(self)
        self._temporizador_animacion.setInterval(50)
        self._temporizador_animacion.timeout.connect(self._avanzar_animacion)

        self._construir_barra_menu()
        self._construir_barra_herramientas()
        self._construir_cuerpo_principal()

        # Atajo de teclado global (Supr / Delete) para eliminar el elemento seleccionado
        self.atajo_eliminar = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        self.atajo_eliminar.activated.connect(self._slot_eliminar_componente_actual)

        # Cargar el circuito de validación con CCVS en el lienzo interactivo
        self._cargar_circuito_validacion_ccvs()
        self._registrar_historial = True

    def _construir_barra_menu(self) -> None:
        barra_menu: QMenuBar = self.menuBar()
        for nombre_menu in ("Archivo", "Editar", "Vista", "Análisis", "Ayuda"):
            menu = barra_menu.addMenu(nombre_menu)
            if nombre_menu == "Archivo":
                for texto, funcion in (("Nuevo", self._slot_limpiar_lienzo),
                                       ("Abrir…", self._abrir_circuito),
                                       ("Guardar como…", self._guardar_circuito)):
                    accion = QAction(texto, self)
                    accion.triggered.connect(funcion)
                    menu.addAction(accion)
            elif nombre_menu == "Editar":
                deshacer = QAction("Deshacer", self)
                deshacer.setShortcut(QKeySequence.StandardKey.Undo)
                deshacer.triggered.connect(self._deshacer)
                menu.addAction(deshacer)
                accion_elim = QAction("Eliminar componente seleccionado (Supr)", self)
                accion_elim.triggered.connect(self._slot_eliminar_componente_actual)
                menu.addAction(accion_elim)
            else:
                menu.setEnabled(False)

    def _construir_barra_herramientas(self) -> None:
        toolbar = QToolBar("Barra de Acciones Principal")
        toolbar.setObjectName("BarraSuperior")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        lbl_metodo = QLabel("Método de análisis")
        lbl_metodo.setStyleSheet("color: #6C757D; font-size: 12px; margin-right: 6px;")
        toolbar.addWidget(lbl_metodo)

        frame_segmentado = QFrame()
        frame_segmentado.setObjectName("ContenedorSegmentado")
        layout_seg = QHBoxLayout(frame_segmentado)
        layout_seg.setContentsMargins(2, 2, 2, 2)
        layout_seg.setSpacing(2)

        self.btn_nodos = QPushButton("Nodos (MNA)")
        self.btn_nodos.setCheckable(True)
        self.btn_nodos.setChecked(True)
        self.btn_nodos.setProperty("class", "BotonSegmento")

        self.btn_mallas = QPushButton("Mallas")
        self.btn_mallas.setCheckable(True)
        self.btn_mallas.setProperty("class", "BotonSegmento")
        self.btn_mallas.setToolTip("Corrientes de lazos independientes, con supermallas para fuentes de corriente")
        self.btn_mallas.toggled.connect(self._cambiar_metodo)

        grupo_metodo = QButtonGroup(self)
        grupo_metodo.setExclusive(True)
        grupo_metodo.addButton(self.btn_nodos)
        grupo_metodo.addButton(self.btn_mallas)

        layout_seg.addWidget(self.btn_nodos)
        layout_seg.addWidget(self.btn_mallas)
        toolbar.addWidget(frame_segmentado)

        espaciador = QWidget()
        espaciador.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        toolbar.addWidget(espaciador)

        self.btn_comparar = QPushButton("Comparar resultados")
        self.btn_comparar.setProperty("class", "BotonToolbar")
        self.btn_comparar.setEnabled(False)
        self.btn_comparar.setToolTip("Comparar el circuito de fase 1 con Qucs-S/ngspice")
        self.btn_comparar.clicked.connect(self._mostrar_comparacion)
        self._accion_comparar = toolbar.addWidget(self.btn_comparar)
        self._accion_comparar.setVisible(False)

        self.btn_restablecer = QPushButton("Restablecer")
        self.btn_restablecer.setProperty("class", "BotonToolbar")
        self.btn_restablecer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restablecer.clicked.connect(self._restablecer_circuito)
        toolbar.addWidget(self.btn_restablecer)

        self.btn_analizar = QPushButton("Iniciar simulación")
        self.btn_analizar.setObjectName("BotonAnalizar")
        self.btn_analizar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analizar.clicked.connect(self._alternar_simulacion)
        toolbar.addWidget(self.btn_analizar)

    def _construir_cuerpo_principal(self) -> None:
        contenedor_raiz = QWidget()
        contenedor_raiz.setObjectName("FondoPrincipal")
        self.setCentralWidget(contenedor_raiz)

        layout_raiz = QHBoxLayout(contenedor_raiz)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)

        self.splitter_horizontal = QSplitter(Qt.Orientation.Horizontal)
        self.splitter_horizontal.setHandleWidth(1)
        self.splitter_horizontal.setStyleSheet(
            "QSplitter::handle { background-color: #E2E6E3; }"
        )

        panel_izquierdo = self._crear_panel_izquierdo()
        panel_central = self._crear_panel_central()
        panel_derecho = self._crear_panel_derecho()

        self.splitter_horizontal.addWidget(panel_izquierdo)
        self.splitter_horizontal.addWidget(panel_central)
        self.splitter_horizontal.addWidget(panel_derecho)

        self.splitter_horizontal.setSizes([240, 910, 270])
        self.splitter_horizontal.setStretchFactor(0, 0)
        self.splitter_horizontal.setStretchFactor(1, 1)
        self.splitter_horizontal.setStretchFactor(2, 0)

        layout_raiz.addWidget(self.splitter_horizontal)

    def _crear_panel_izquierdo(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("class", "PanelLateral")
        panel.setMinimumWidth(220)
        panel.setMaximumWidth(280)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        seccion_circuito = QWidget()
        seccion_circuito.setMinimumHeight(0)
        seccion_circuito.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Ignored)
        layout_circuito = QVBoxLayout(seccion_circuito)
        layout_circuito.setContentsMargins(0, 0, 0, 0)
        layout_circuito.setSpacing(8)
        lbl_circuito = QLabel("CIRCUITO ABIERTO")
        lbl_circuito.setProperty("class", "TituloSeccion")
        layout_circuito.addWidget(lbl_circuito)

        self.arbol_circuito = QTreeWidget()
        self.arbol_circuito.setObjectName("ArbolCircuito")
        self.arbol_circuito.setHeaderHidden(True)
        self.arbol_circuito.setColumnCount(2)
        self.arbol_circuito.setIndentation(14)
        self.arbol_circuito.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.arbol_circuito.header().setStretchLastSection(False)
        self.arbol_circuito.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.arbol_circuito.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Fixed
        )
        self.arbol_circuito.header().resizeSection(1, 70)
        self.arbol_circuito.itemClicked.connect(self._slot_item_arbol_clic)
        layout_circuito.addWidget(self.arbol_circuito, stretch=1)
        layout.addWidget(seccion_circuito, stretch=1)

        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setStyleSheet("color: #EAECE9;")
        layout.addWidget(linea)

        seccion_componentes = QWidget()
        seccion_componentes.setMinimumHeight(0)
        seccion_componentes.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Ignored)
        layout_componentes = QVBoxLayout(seccion_componentes)
        layout_componentes.setContentsMargins(0, 0, 0, 0)
        layout_componentes.setSpacing(8)
        lbl_insertar = QLabel("COMPONENTES")
        lbl_insertar.setProperty("class", "TituloSeccion")
        layout_componentes.addWidget(lbl_insertar)

        self.scroll_componentes = QScrollArea()
        self.scroll_componentes.setWidgetResizable(True)
        self.scroll_componentes.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_componentes.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        contenido_paleta = QWidget()
        layout_paleta = QVBoxLayout(contenido_paleta)
        layout_paleta.setContentsMargins(0, 0, 2, 0)
        layout_paleta.setSpacing(6)
        self.scroll_componentes.setWidget(contenido_paleta)
        layout_componentes.addWidget(self.scroll_componentes, stretch=1)
        layout.addWidget(seccion_componentes, stretch=1)

        grupos = [
            ("Fuentes independientes", [("⊕   Voltaje", "FUENTE_VOLTAJE"), ("⊙   Corriente", "FUENTE_CORRIENTE")]),
            ("Resistivos", [("∿   Resistencia", "RESISTENCIA")]),
            ("Fuentes controladas", [("◇   CCVS", "FUENTE_CCVS")]),
            ("Referencia", [("⏚   Tierra", "TIERRA")]),
        ]
        for nombre, componentes in grupos:
            boton_grupo = QToolButton()
            boton_grupo.setObjectName("Categoria")
            boton_grupo.setText(nombre)
            boton_grupo.setCheckable(True)
            boton_grupo.setArrowType(Qt.ArrowType.RightArrow)
            boton_grupo.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            boton_grupo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            contenido = QWidget()
            contenido.setStyleSheet("background-color: #f4faf8; border-radius: 6px;")
            columna = QVBoxLayout(contenido)
            columna.setContentsMargins(7, 6, 7, 6)
            columna.setSpacing(6)
            for texto, tipo in componentes:
                boton = BotonPaletaDrag(texto, tipo, self)
                boton.setProperty("class", "BotonInsertar")
                boton.setMinimumHeight(36)
                columna.addWidget(boton)
            contenido.setVisible(False)
            boton_grupo.toggled.connect(contenido.setVisible)
            boton_grupo.toggled.connect(lambda abierto, b=boton_grupo: b.setArrowType(Qt.ArrowType.DownArrow if abierto else Qt.ArrowType.RightArrow))
            layout_paleta.addWidget(boton_grupo)
            layout_paleta.addWidget(contenido)
        layout_paleta.addStretch()

        return panel

    def _crear_panel_central(self) -> QWidget:
        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        self.splitter_central_vertical = QSplitter(Qt.Orientation.Vertical)
        self.splitter_central_vertical.setHandleWidth(4)
        self.splitter_central_vertical.setStyleSheet(
            "QSplitter::handle { background: #f5faf8; } "
            "QSplitter::handle:hover { background: #b9d9cf; }"
        )

        widget_espacio_trabajo = self._crear_seccion_espacio_trabajo()
        widget_resultados = self._crear_seccion_resultados()

        self.splitter_central_vertical.addWidget(widget_espacio_trabajo)
        self.splitter_central_vertical.addWidget(widget_resultados)
        self.splitter_central_vertical.setSizes([430, 440])

        layout.addWidget(self.splitter_central_vertical)
        return contenedor

    def _crear_seccion_espacio_trabajo(self) -> QWidget:
        seccion = QWidget()
        layout = QVBoxLayout(seccion)
        layout.setContentsMargins(4, 0, 4, 4)
        layout.setSpacing(6)

        marco_canvas = QFrame()
        marco_canvas.setProperty("class", "PanelBlanco")
        layout_canvas = QVBoxLayout(marco_canvas)
        layout_canvas.setContentsMargins(10, 6, 10, 6)
        layout_canvas.setSpacing(0)

        fila_info_sup = QHBoxLayout()
        fila_info_sup.setSpacing(10)
        self.btn_modo_seleccion = QPushButton("↖  Seleccionar")
        self.btn_modo_mano = QPushButton("✋  Mano")
        self.btn_modo_seleccion.setToolTip("Seleccionar, mover componentes y conectar terminales")
        self.btn_modo_mano.setToolTip("Arrastrar para desplazar el lienzo")
        grupo_modos = QButtonGroup(self)
        grupo_modos.setExclusive(True)
        for boton in (self.btn_modo_seleccion, self.btn_modo_mano):
            boton.setCheckable(True)
            grupo_modos.addButton(boton)
            fila_info_sup.addWidget(boton)
        self.btn_modo_seleccion.setChecked(True)
        fila_info_sup.addSpacing(12)
        fila_info_sup.addWidget(QLabel("Zoom"))
        self.slider_zoom = QSlider(Qt.Orientation.Horizontal)
        self.slider_zoom.setRange(25, 200)
        self.slider_zoom.setValue(100)
        self.slider_zoom.setFixedWidth(120)
        self.slider_zoom.setToolTip("Ajustar zoom del circuito")
        fila_info_sup.addWidget(self.slider_zoom)
        self.lbl_zoom = QLabel("100 %")
        self.lbl_zoom.setMinimumWidth(45)
        fila_info_sup.addWidget(self.lbl_zoom)
        fila_info_sup.addStretch()
        self.lbl_conteo_topologia = QLabel("4 nodos activos · 7 componentes")
        self.lbl_conteo_topologia.setStyleSheet("color: #868E96; font-size: 11px;")
        fila_info_sup.addWidget(self.lbl_conteo_topologia)
        layout_canvas.addLayout(fila_info_sup)

        self.escena_circuito = EscenaEsquematicoDC(self)
        self.escena_circuito.antes_de_cambio.connect(self._guardar_punto_deshacer)
        self.escena_circuito.componente_seleccionado.connect(self._sincronizar_seleccion)
        self.escena_circuito.componente_doble_clic.connect(self._editar_componente)
        self.escena_circuito.componente_soltado.connect(
            self._slot_componente_soltado_en_escena
        )
        self.escena_circuito.conexion_creada.connect(self._slot_conexion_cable_creada)
        self.escena_circuito.elemento_eliminado.connect(
            self._slot_elemento_eliminado_en_escena
        )

        self.vista_circuito = VistaEsquematicoDC(self.escena_circuito, self)
        self.btn_modo_seleccion.clicked.connect(
            lambda: self.vista_circuito.establecer_modo_mano(False)
        )
        self.btn_modo_mano.clicked.connect(
            lambda: self.vista_circuito.establecer_modo_mano(True)
        )
        self.slider_zoom.valueChanged.connect(self.vista_circuito.establecer_zoom)
        self.slider_zoom.valueChanged.connect(lambda valor: self.lbl_zoom.setText(f"{valor} %"))
        layout_canvas.addWidget(self.vista_circuito, stretch=1)

        layout.addWidget(marco_canvas, stretch=1)
        return seccion

    def _crear_seccion_resultados(self) -> QFrame:
        panel_res = QFrame()
        panel_res.setProperty("class", "PanelBlanco")
        layout = QVBoxLayout(panel_res)
        layout.setContentsMargins(16, 10, 16, 12)
        layout.setSpacing(10)

        fila_top = QHBoxLayout()
        lbl_res = QLabel("Resultados")
        lbl_res.setStyleSheet("font-size: 15px; font-weight: 700; color: #212529;")
        self.lbl_estado_resultados = QLabel("Ejecuta la simulación para ver resultados")
        self.lbl_estado_resultados.setStyleSheet("color: #59756d; font-size: 12px;")
        fila_top.addWidget(lbl_res)
        fila_top.addStretch()
        fila_top.addWidget(self.lbl_estado_resultados)
        layout.addLayout(fila_top)

        fila_metricas_tabla = QHBoxLayout()
        fila_metricas_tabla.setSpacing(16)

        col_voltajes = QVBoxLayout()
        col_voltajes.setSpacing(6)
        titulo_nodos = QLabel("Voltajes por nodo")
        titulo_nodos.setProperty("class", "TituloSeccion")
        col_voltajes.addWidget(titulo_nodos)
        self.tabla_nodos = QTableWidget(0, 2)
        self.tabla_nodos.setObjectName("TablaLecturas")
        self.tabla_nodos.setHorizontalHeaderLabels(["Nodo", "Voltaje"])
        self.tabla_nodos.verticalHeader().setVisible(False)
        self.tabla_nodos.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_nodos.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.tabla_nodos.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_nodos.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla_nodos.setMouseTracking(True)
        self.tabla_nodos.cellClicked.connect(self._seleccionar_nodo_resultado)
        self.tabla_nodos.setShowGrid(False)
        self.tabla_nodos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        col_voltajes.addWidget(self.tabla_nodos)
        fila_metricas_tabla.addLayout(col_voltajes, stretch=2)

        col_tabla = QVBoxLayout()
        col_tabla.setSpacing(6)

        lbl_lecturas = QLabel(
            "LECTURAS POR COMPONENTE (VOLTAJE, CORRIENTE Y POTENCIA)"
        )
        lbl_lecturas.setProperty("class", "TituloSeccion")
        col_tabla.addWidget(lbl_lecturas)

        self.tabla_lecturas = QTableWidget(0, 5)
        self.tabla_lecturas.setObjectName("TablaLecturas")
        self.tabla_lecturas.setHorizontalHeaderLabels(
            ["Componente", "Terminales", "Voltaje", "Corriente", "Potencia"]
        )
        self.tabla_lecturas.verticalHeader().setVisible(False)
        self.tabla_lecturas.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_lecturas.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.tabla_lecturas.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.tabla_lecturas.setShowGrid(False)
        self.tabla_lecturas.setMouseTracking(True)
        self.tabla_lecturas.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.tabla_lecturas.cellClicked.connect(self._slot_fila_tabla_clic)

        col_tabla.addWidget(self.tabla_lecturas)
        fila_metricas_tabla.addLayout(col_tabla, stretch=3)
        panel_detalles = QWidget()
        panel_detalles.setLayout(fila_metricas_tabla)
        self.tabla_variables = QTableWidget(0, 3)
        self.tabla_variables.setObjectName("TablaLecturas")
        self.tabla_variables.setHorizontalHeaderLabels(["Variable", "Valor", "Unidad"])
        self.tabla_variables.verticalHeader().setVisible(False)
        self.tabla_variables.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla_variables.setShowGrid(False)
        self.tabla_variables.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla_variables.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla_variables.setMouseTracking(True)
        self.tabla_variables.cellClicked.connect(self._seleccionar_variable_resultado)
        self.tabla_variables.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.pestanas_resultados = QTabWidget()
        self.pestanas_resultados.addTab(self.tabla_variables, "Punto de operación")
        self.pestanas_resultados.addTab(panel_detalles, "Detalle por elemento")
        layout.addWidget(self.pestanas_resultados, stretch=2)

        self.caja_ecuaciones = QTextEdit()
        self.caja_ecuaciones.setReadOnly(True)
        self.caja_ecuaciones.setPlaceholderText("Sin resultados todavía")
        self.caja_ecuaciones.setFrameShape(QFrame.Shape.NoFrame)

        panel_matriz = QWidget()
        layout_matriz = QVBoxLayout(panel_matriz)
        layout_matriz.setContentsMargins(12, 10, 12, 12)
        layout_matriz.setSpacing(8)
        titulo_matriz = QLabel("Sistema de ecuaciones   A · x = b")
        titulo_matriz.setStyleSheet("font-size: 15px; font-weight: 700; color: #173f37;")
        layout_matriz.addWidget(titulo_matriz)
        self.lbl_estado_matriz = QLabel("Inicia la simulación para visualizar la matriz y los vectores.")
        self.lbl_estado_matriz.setStyleSheet("color: #59756d; font-size: 12px;")
        layout_matriz.addWidget(self.lbl_estado_matriz)
        fila_matriz = QHBoxLayout()
        fila_matriz.setSpacing(12)
        self.tabla_matriz_a = self._crear_tabla_matriz()
        self.tabla_matriz_a.horizontalHeader().setStretchLastSection(False)
        self.tabla_matriz_a.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_vector_x = self._crear_tabla_matriz()
        self.tabla_vector_b = self._crear_tabla_matriz()
        self.tabla_vector_x.verticalHeader().setVisible(False)
        self.tabla_vector_b.verticalHeader().setVisible(False)
        for titulo, tabla, proporcion in (("A · Coeficientes", self.tabla_matriz_a, 6),
                                         ("x · Solución", self.tabla_vector_x, 3),
                                         ("b · Términos", self.tabla_vector_b, 2)):
            columna = QVBoxLayout()
            encabezado = QLabel(titulo)
            encabezado.setStyleSheet("font-weight: 700; color: #315c52;")
            columna.addWidget(encabezado)
            columna.addWidget(tabla)
            fila_matriz.addLayout(columna, proporcion)
        layout_matriz.addLayout(fila_matriz, 1)
        for tabla in (self.tabla_vector_x, self.tabla_vector_b):
            self.tabla_matriz_a.verticalScrollBar().valueChanged.connect(tabla.verticalScrollBar().setValue)
            tabla.verticalScrollBar().valueChanged.connect(self.tabla_matriz_a.verticalScrollBar().setValue)

        self.pestanas_resultados.addTab(
            self._envolver_en_tarjeta(
                "Ecuaciones del sistema (SymPy)",
                "Sistema generado por el método seleccionado",
                self.caja_ecuaciones,
            ),
            "Ecuaciones",
        )
        self.pestanas_resultados.addTab(panel_matriz, "Matriz del sistema")

        return panel_res

    @staticmethod
    def _celda_centrada(texto: str) -> QTableWidgetItem:
        celda = QTableWidgetItem(texto)
        celda.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        celda.setToolTip(texto)
        return celda

    @staticmethod
    def _crear_tabla_matriz() -> QTableWidget:
        tabla = QTableWidget()
        tabla.setObjectName("TablaLecturas")
        tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabla.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        tabla.setAlternatingRowColors(True)
        tabla.setStyleSheet(
            "QTableWidget { background: #ffffff; alternate-background-color: #f3faf7; gridline-color: #dcebe5; color: #173f37; border: 1px solid #dcebe5; border-radius: 5px; }"
            "QHeaderView { background: #f5faf8; }"
            "QHeaderView::section { background: #f5faf8; color: #45665e; border: none; padding: 5px; }"
            "QTableCornerButton::section { background: #f5faf8; border: none; }"
        )
        tabla.verticalHeader().setDefaultSectionSize(32)
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        tabla.horizontalHeader().setStretchLastSection(True)
        return tabla

    def _limpiar_matriz(self) -> None:
        for tabla in (self.tabla_matriz_a, self.tabla_vector_x, self.tabla_vector_b):
            tabla.clear()
            tabla.setRowCount(0)
            tabla.setColumnCount(0)
        self.lbl_estado_matriz.setText("Inicia la simulación para visualizar la matriz y los vectores.")

    def _mostrar_matriz(self, sistema, solucion) -> None:
        etiquetas = sistema.etiquetas_incognitas
        cantidad = len(etiquetas)
        for tabla, columnas in ((self.tabla_matriz_a, cantidad), (self.tabla_vector_x, 2), (self.tabla_vector_b, 1)):
            tabla.clear()
            tabla.setRowCount(cantidad)
            tabla.setColumnCount(columnas)
        self.tabla_matriz_a.setHorizontalHeaderLabels(etiquetas)
        self.tabla_matriz_a.setVerticalHeaderLabels([f"E{i + 1}" for i in range(cantidad)])
        self.tabla_vector_x.setHorizontalHeaderLabels(["Incógnita", "Valor"])
        self.tabla_vector_b.setHorizontalHeaderLabels(["Valor"])
        def numero(valor):
            return f"{float(valor):.6g}".replace(".", ",")
        def agregar(tabla, fila, columna, valor):
            celda = self._celda_centrada(numero(valor))
            celda.setToolTip(f"Valor completo: {float(valor):.15g}")
            if float(valor) == 0:
                celda.setForeground(QBrush(QColor("#8aa39b")))
            tabla.setItem(fila, columna, celda)
        for fila in range(cantidad):
            for columna in range(cantidad):
                agregar(self.tabla_matriz_a, fila, columna, sistema.matriz_A[fila, columna])
            self.tabla_vector_x.setItem(fila, 0, self._celda_centrada(etiquetas[fila]))
            agregar(self.tabla_vector_x, fila, 1, solucion.vector_x[fila])
            agregar(self.tabla_vector_b, fila, 0, sistema.vector_b[fila])
        self.lbl_estado_matriz.setText("Las filas E1, E2… son ecuaciones; las columnas de A y las filas de x siguen el orden de las incógnitas.")

    def _crear_tarjeta_voltaje_nodo(
        self, subtitulo: str, lbl_valor: QLabel, unidad: str
    ) -> QFrame:
        card = QFrame()
        card.setProperty("class", "TarjetaMetrica")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)

        lbl_sub = QLabel(subtitulo)
        lbl_sub.setStyleSheet("color: #6C757D; font-size: 11px;")
        lay.addWidget(lbl_sub)

        fila_val = QHBoxLayout()
        lbl_valor.setStyleSheet("color: #212529; font-size: 20px; font-weight: 700;")
        lbl_u = QLabel(unidad)
        lbl_u.setStyleSheet("color: #6C757D; font-size: 12px; margin-top: 4px;")
        fila_val.addWidget(lbl_valor)
        fila_val.addWidget(lbl_u)
        fila_val.addStretch()
        lay.addLayout(fila_val)
        return card

    def _envolver_en_tarjeta(
        self, titulo: str, subtitulo: str, widget_contenido: QWidget
    ) -> QFrame:
        card = QFrame()
        card.setProperty("class", "TarjetaMetrica")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)
        lbl_t = QLabel(titulo)
        lbl_t.setStyleSheet("font-size: 13px; font-weight: 700; color: #212529;")
        lbl_s = QLabel(subtitulo)
        lbl_s.setStyleSheet("font-size: 11px; color: #6C757D;")
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_s)
        lay.addWidget(widget_contenido)
        return card

    def _crear_panel_derecho(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("class", "PanelLateral")
        panel.setMinimumWidth(245)
        panel.setMaximumWidth(300)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        fila_cab = QHBoxLayout()
        lbl_prop = QLabel("PROPIEDADES")
        lbl_prop.setProperty("class", "TituloSeccion")
        self.lbl_badge_elemento = QLabel("R_5")
        self.lbl_badge_elemento.setObjectName("BadgeElemento")
        fila_cab.addWidget(lbl_prop)
        fila_cab.addStretch()
        fila_cab.addWidget(self.lbl_badge_elemento)
        layout.addLayout(fila_cab)

        self.lbl_tipo_elemento = QLabel("Resistencia")
        self.lbl_tipo_elemento.setStyleSheet(
            "font-size: 17px; font-weight: 700; color: #212529;"
        )
        self.lbl_nodos_entre = QLabel("Entre V1 y V2")
        self.lbl_nodos_entre.setStyleSheet(
            "font-size: 12px; color: #6C757D; margin-bottom: 4px;"
        )
        layout.addWidget(self.lbl_tipo_elemento)
        layout.addWidget(self.lbl_nodos_entre)

        self.lbl_etiqueta_valor = QLabel("Valor de resistencia")
        self.lbl_etiqueta_valor.setStyleSheet("font-size: 12px; color: #495057;")
        layout.addWidget(self.lbl_etiqueta_valor)

        fila_input = QHBoxLayout()
        fila_input.setSpacing(6)
        self.input_valor_prop = QLineEdit("5")
        self.input_valor_prop.setObjectName("InputValorPropiedad")
        self.lbl_simbolo_unidad = QLabel("Ω")
        self.lbl_simbolo_unidad.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_simbolo_unidad.setFixedSize(44, 34)
        self.lbl_simbolo_unidad.setStyleSheet(
            "background-color: #F4F6F4; border: 1px solid #D6DBD7; "
            "border-radius: 6px; font-weight: 600; color: #495057;"
        )
        fila_input.addWidget(self.input_valor_prop, stretch=1)
        fila_input.addWidget(self.lbl_simbolo_unidad)
        layout.addLayout(fila_input)

        self.btn_aplicar_valor = QPushButton("Aplicar valor")
        self.btn_aplicar_valor.setProperty("class", "BotonToolbar")
        self.btn_aplicar_valor.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_aplicar_valor.clicked.connect(self._slot_aplicar_valor_propiedad)
        layout.addWidget(self.btn_aplicar_valor)

        # Botón para eliminar el componente seleccionado desde el panel de propiedades
        self.btn_eliminar_prop = QPushButton("Eliminar componente")
        self.btn_eliminar_prop.setProperty("class", "BotonEliminar")
        self.btn_eliminar_prop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eliminar_prop.clicked.connect(self._slot_eliminar_componente_actual)
        layout.addWidget(self.btn_eliminar_prop)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("color: #EAECE9; margin: 4px 0;")
        layout.addWidget(sep1)

        grid_term = QGridLayout()
        grid_term.setVerticalSpacing(8)
        lbl_ti = QLabel("Terminal inicial (+)")
        lbl_ti.setStyleSheet("color: #6C757D; font-size: 12px;")
        self.lbl_val_terminal_ini = QLabel("V1")
        self.lbl_val_terminal_ini.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_val_terminal_ini.setStyleSheet("font-weight: 600; color: #212529;")

        lbl_tf = QLabel("Terminal final (−)")
        lbl_tf.setStyleSheet("color: #6C757D; font-size: 12px;")
        self.lbl_val_terminal_fin = QLabel("V2")
        self.lbl_val_terminal_fin.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_val_terminal_fin.setStyleSheet("font-weight: 600; color: #212529;")

        grid_term.addWidget(lbl_ti, 0, 0)
        grid_term.addWidget(self.lbl_val_terminal_ini, 0, 1)
        grid_term.addWidget(lbl_tf, 1, 0)
        grid_term.addWidget(self.lbl_val_terminal_fin, 1, 1)
        layout.addLayout(grid_term)

        self.chk_ref_n0 = QCheckBox("Referencia GND (0 V) definida")
        self.chk_ref_n0.setEnabled(False)
        self.chk_ref_n0.setStyleSheet(
            "color: #495057; font-size: 12px; margin-top: 4px;"
        )
        layout.addWidget(self.chk_ref_n0)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #EAECE9; margin: 4px 0;")
        layout.addWidget(sep2)

        grid_lec = QGridLayout()
        grid_lec.setVerticalSpacing(8)

        self.lbl_titulo_voltaje_prop = QLabel("Voltaje V1 - V2")
        self.lbl_titulo_voltaje_prop.setStyleSheet("color: #6C757D; font-size: 12px;")
        self.lbl_valor_voltaje_prop = QLabel("—")
        self.lbl_valor_voltaje_prop.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_valor_voltaje_prop.setStyleSheet("font-weight: 700; color: #212529;")

        self.lbl_titulo_corriente_prop = QLabel("Corriente V1 → V2")
        self.lbl_titulo_corriente_prop.setStyleSheet("color: #6C757D; font-size: 12px;")
        self.lbl_valor_corriente_prop = QLabel("—")
        self.lbl_valor_corriente_prop.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_valor_corriente_prop.setStyleSheet("font-weight: 700; color: #212529;")

        lbl_tit_pot = QLabel("Potencia calculada")
        lbl_tit_pot.setStyleSheet("color: #6C757D; font-size: 12px;")
        self.lbl_valor_potencia_prop = QLabel("—")
        self.lbl_valor_potencia_prop.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_valor_potencia_prop.setStyleSheet("font-weight: 700; color: #1E3A28;")

        grid_lec.addWidget(self.lbl_titulo_voltaje_prop, 0, 0)
        grid_lec.addWidget(self.lbl_valor_voltaje_prop, 0, 1)
        grid_lec.addWidget(self.lbl_titulo_corriente_prop, 1, 0)
        grid_lec.addWidget(self.lbl_valor_corriente_prop, 1, 1)
        grid_lec.addWidget(lbl_tit_pot, 2, 0)
        grid_lec.addWidget(self.lbl_valor_potencia_prop, 2, 1)
        layout.addLayout(grid_lec)

        layout.addStretch()
        return panel

    # =========================================================================
    # ENSAMBLAJE DEL CIRCUITO DE PRUEBA CON CCVS EN EL LIENZO INTERACTIVO
    # =========================================================================

    def _cargar_circuito_validacion_ccvs(self) -> None:
        self._guardar_punto_deshacer()
        self.escena_circuito.blockSignals(True)
        self.escena_circuito.clear()
        self.escena_circuito.componentes_graficos.clear()
        self.escena_circuito.cables_graficos.clear()
        self.escena_circuito.blockSignals(False)

        vs = ComponenteGraficoItem(
            "Vs", "FUENTE_VOLTAJE", "20", "V", QPointF(95, 200), "V", 4, 0, "N_Vs", "GND"
        )
        r_2a = ComponenteGraficoItem(
            "R_2a", "RESISTENCIA", "2", "Ω", QPointF(185, 85), "H", 4, 1, "N_Vs", "V1"
        )
        r_20 = ComponenteGraficoItem(
            "R_20", "RESISTENCIA", "20", "Ω", QPointF(280, 200), "V", 1, 0, "V1", "GND"
        )
        r_5 = ComponenteGraficoItem(
            "R_5", "RESISTENCIA", "5", "Ω", QPointF(400, 85), "H", 1, 2, "V1", "V2"
        )
        r_10 = ComponenteGraficoItem(
            "R_10", "RESISTENCIA", "10", "Ω", QPointF(520, 200), "V", 2, 0, "V2", "GND"
        )
        r_2b = ComponenteGraficoItem(
            "R_2b", "RESISTENCIA", "2", "Ω", QPointF(635, 85), "H", 2, 3, "V2", "V3"
        )
        ccvs1 = ComponenteGraficoItem(
            "CCVS1",
            "FUENTE_CCVS",
            "8",
            "·i_φ",
            QPointF(755, 200),
            "V",
            3,
            0,
            "V3",
            "GND",
            componente_control_ref="R_5",
        )
        gnd_item = ComponenteGraficoItem(
            "GND", "TIERRA", "0", "V", QPointF(425, 315), "V", 0, 0, "GND", "GND"
        )

        for item in (vs, r_2a, r_20, r_5, r_10, r_2b, ccvs1, gnd_item):
            self.escena_circuito.registrar_componente_grafico(item)

        self.escena_circuito.blockSignals(True)
        self.escena_circuito.conectar_terminales_con_cable(
            vs.terminal_a, r_2a.terminal_a, 4, "N_Vs"
        )
        self.escena_circuito.conectar_terminales_con_cable(
            r_2a.terminal_b, r_20.terminal_a, 1, "V1"
        )
        self.escena_circuito.conectar_terminales_con_cable(
            r_20.terminal_a, r_5.terminal_a, 1, "V1"
        )
        self.escena_circuito.conectar_terminales_con_cable(
            r_5.terminal_b, r_10.terminal_a, 2, "V2"
        )
        self.escena_circuito.conectar_terminales_con_cable(
            r_10.terminal_a, r_2b.terminal_a, 2, "V2"
        )
        self.escena_circuito.conectar_terminales_con_cable(
            r_2b.terminal_b, ccvs1.terminal_a, 3, "V3"
        )

        self.escena_circuito.conectar_terminales_con_cable(
            vs.terminal_b, r_20.terminal_b, 0, "GND"
        )
        self.escena_circuito.conectar_terminales_con_cable(
            r_20.terminal_b, r_10.terminal_b, 0, "GND"
        )
        self.escena_circuito.conectar_terminales_con_cable(
            r_10.terminal_b, ccvs1.terminal_b, 0, "GND"
        )
        self.escena_circuito.conectar_terminales_con_cable(
            r_20.terminal_b, gnd_item.terminal_a, 0, "GND"
        )
        self.escena_circuito.blockSignals(False)

        self._reconstruir_arbol_lateral()
        self._limpiar_resultados()
        self._sincronizar_seleccion("R_5")

    # =========================================================================
    # GESTIÓN DE ELIMINACIÓN DE COMPONENTES Y VENTANAS DE ERROR
    # =========================================================================

    def _detener_animacion(self) -> None:
        self._temporizador_animacion.stop()
        if hasattr(self, "_dialogo_estado"):
            self._dialogo_estado.close()
        self._simulando = False
        self._comparacion_actual = None
        if hasattr(self, "btn_comparar"):
            self.btn_comparar.setEnabled(False)
            self._accion_comparar.setVisible(False)
        if hasattr(self, "_dialogo_comparacion"):
            self._dialogo_comparacion.close()
        if hasattr(self, "btn_analizar"):
            self.btn_analizar.setText("Iniciar simulación")
        self._corrientes_calculadas = {}
        if hasattr(self, "escena_circuito"):
            for cable in self.escena_circuito.cables_graficos:
                cable.establecer_voltaje(None)
                cable.resaltado_nodo = False
                cable.update()
            for item in self.escena_circuito.componentes_graficos.values():
                item.corriente_animacion = 0.0
                item.update()

    def _restablecer_circuito(self) -> None:
        self._guardar_punto_deshacer()
        anterior = self._registrar_historial
        self._registrar_historial = False
        try:
            self._detener_animacion()
            self._cargar_circuito_validacion_ccvs()
        finally:
            self.escena_circuito.blockSignals(False)
            self._registrar_historial = anterior

    def _alternar_simulacion(self) -> None:
        if self._simulando:
            self._detener_animacion()
            self._limpiar_resultados()
            self.statusBar().showMessage("Simulación detenida", 4000)
            return
        self._slot_analizar_circuito()
        if self._analisis_exitoso:
            self._simulando = True
            self.btn_analizar.setText("Detener simulación")
            self.btn_comparar.setEnabled(True)
            self._accion_comparar.setVisible(True)
            self._alternar_animacion(True)
            self.statusBar().showMessage("Simulación activa: las flechas indican la dirección de corriente", 5000)
            self._mostrar_estado_simulacion(True, "El punto de operación DC se calculó correctamente. Consulta las variables y los detalles en Resultados.")

    def _cambiar_metodo(self, activo: bool) -> None:
        if hasattr(self, "tabla_nodos"):
            metodo = "mallas" if activo else "nodos"
            self._actualizar_badge_estado(f"Método de {metodo} seleccionado. Inicia la simulación.")

    def _mostrar_comparacion(self) -> None:
        if not self._simulando:
            return
        if self._comparacion_actual is None:
            QMessageBox.information(self, "Comparar resultados", "La referencia de Qucs-S corresponde al circuito de fase 1. El circuito actual tiene otra topología o configuración de control y no se puede comparar automáticamente.")
            return
        filas, modificados = self._comparacion_actual
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Comparar resultados — Qucs-S/ngspice (Fase 1)")
        dialogo.resize(780, 360)
        layout = QVBoxLayout(dialogo)
        aviso = QLabel("Referencia: Qucs-S/ngspice (Fase 1) · Error = |simulado − referencia| / |referencia| × 100")
        aviso.setWordWrap(True)
        layout.addWidget(aviso)
        if modificados:
            advertencia = QLabel("Los valores o el sentido de control difieren de la configuración de fase 1; los porcentajes comparan circuitos con parámetros distintos.")
            advertencia.setWordWrap(True)
            advertencia.setStyleSheet("color: #9a5c10; font-weight: 600;")
            layout.addWidget(advertencia)
        tabla = QTableWidget(len(filas), 4)
        tabla.setObjectName("TablaLecturas")
        tabla.setHorizontalHeaderLabels(["Magnitud", "Qucs-S/ngspice", "Simulador", "Error"])
        tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tabla.verticalHeader().setVisible(False)
        tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabla.setShowGrid(False)
        for fila, (nombre, referencia, obtenido, unidad) in enumerate(filas):
            error = abs(obtenido - referencia) / abs(referencia) * 100 if referencia else None
            # Se evita mostrar ruido de coma flotante como un error significativo.
            if error is not None and error < 1e-10:
                error = 0.0
            valores = (nombre, f"{referencia:.6g} {unidad}", f"{obtenido:.6g} {unidad}",
                       f"{error:.4f} %" if error is not None else "No definido")
            for columna, valor in enumerate(valores):
                tabla.setItem(fila, columna, self._celda_centrada(valor.replace('.', ',')))
        layout.addWidget(tabla)
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(dialogo.close)
        layout.addWidget(cerrar, alignment=Qt.AlignmentFlag.AlignRight)
        self._dialogo_comparacion = dialogo
        dialogo.show()

    def _estado_circuito(self) -> dict:
        componentes = []
        for item in self.escena_circuito.componentes_graficos.values():
            componentes.append({"id": item.id_ref, "tipo": item.tipo_catalogo,
                "valor": item.valor_str, "unidad": item.unidad_simbolo, "factor": item.factor_unidad,
                "x": item.pos().x(), "y": item.pos().y(), "orientacion": item.orientacion,
                "control": item.componente_control_ref,
                "nodo_a": item.terminal_a.id_nodo, "nodo_b": item.terminal_b.id_nodo,
                "etiqueta_a": item.terminal_a.etiqueta_nodo, "etiqueta_b": item.terminal_b.etiqueta_nodo})
        cables = [{"origen": c.terminal_origen.componente_padre.id_ref,
                   "pin_origen": c.terminal_origen.nombre_terminal,
                   "destino": c.terminal_destino.componente_padre.id_ref,
                   "pin_destino": c.terminal_destino.nombre_terminal}
                  for c in self.escena_circuito.cables_graficos]
        return {"version": 1, "componentes": componentes, "cables": cables}

    def _guardar_punto_deshacer(self) -> None:
        if self._registrar_historial and hasattr(self, "escena_circuito"):
            estado = self._estado_circuito()
            if not self._historial or self._historial[-1] != estado:
                self._historial.append(estado)
                self._historial = self._historial[-50:]

    def _deshacer(self) -> None:
        actual = self._estado_circuito()
        while self._historial and self._historial[-1] == actual:
            self._historial.pop()
        if self._historial:
            estado = self._historial.pop()
            self._restaurar_estado(estado)
            self.statusBar().showMessage("Cambio deshecho", 4000)

    def _guardar_circuito(self) -> None:
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar circuito", "circuito.json", "Circuito JSON (*.json)")
        if not ruta:
            return
        try:
            with open(ruta, "w", encoding="utf-8") as archivo:
                json.dump(self._estado_circuito(), archivo, ensure_ascii=False, indent=2)
        except OSError as exc:
            QMessageBox.warning(self, "No se pudo guardar", str(exc))

    def _abrir_circuito(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(self, "Abrir circuito", "", "Circuitos (*.json *.asc);;Circuito JSON (*.json);;LTspice (*.asc)")
        if not ruta:
            return
        try:
            if Path(ruta).suffix.lower() == ".asc":
                datos = importar_asc(ruta)
            else:
                with open(ruta, encoding="utf-8") as archivo:
                    datos = json.load(archivo)
            self._restaurar_estado(datos, guardar=True)
            if Path(ruta).suffix.lower() == ".asc":
                self.statusBar().showMessage("Esquema LTspice importado; las conexiones se redibujaron. Guarda como JSON para editarlo.", 10000)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, "No se pudo abrir", str(exc))

    def _restaurar_estado(self, datos: dict, guardar: bool = False) -> None:
        if datos["version"] != 1 or not isinstance(datos["componentes"], list) or not isinstance(datos["cables"], list):
            raise ValueError("Formato de circuito no compatible")
        nuevos = {}
        for d in datos["componentes"]:
            if d["tipo"] not in ("RESISTENCIA", "FUENTE_VOLTAJE", "FUENTE_CORRIENTE", "FUENTE_CCVS", "TIERRA") or not d["id"] or d["id"] in nuevos:
                raise ValueError("Componente inválido o etiqueta repetida")
            if not all(math.isfinite(float(v)) for v in (d["valor"], d["x"], d["y"], d["factor"])) or float(d["factor"]) <= 0 or d["orientacion"] not in ("H", "V"):
                raise ValueError("Propiedades inválidas")
            item = ComponenteGraficoItem(d["id"], d["tipo"], d["valor"], d["unidad"], QPointF(d["x"], d["y"]), d["orientacion"], d["nodo_a"], d["nodo_b"], d["etiqueta_a"], d["etiqueta_b"], d["control"])
            item.factor_unidad = float(d["factor"])
            nuevos[item.id_ref] = item
        for c in datos["cables"]:
            if c["origen"] not in nuevos or c["destino"] not in nuevos or c["pin_origen"] not in ("A", "B") or c["pin_destino"] not in ("A", "B"):
                raise ValueError("Conexión inválida")
        if guardar:
            self._guardar_punto_deshacer()
        anterior = self._registrar_historial
        self._registrar_historial = False
        try:
            self._slot_limpiar_lienzo()
            for item in nuevos.values():
                self.escena_circuito.registrar_componente_grafico(item)
            self.escena_circuito.blockSignals(True)
            for c in datos["cables"]:
                a = getattr(nuevos[c["origen"]], "terminal_" + c["pin_origen"].lower())
                b = getattr(nuevos[c["destino"]], "terminal_" + c["pin_destino"].lower())
                self.escena_circuito.conectar_terminales_con_cable(a, b)
            self.escena_circuito.blockSignals(False)
            self.escena_circuito.recalcular_nodos_desde_cables()
            self._reconstruir_arbol_lateral()
            if nuevos:
                self._sincronizar_seleccion(next(iter(nuevos)))
        finally:
            self.escena_circuito.blockSignals(False)
            self._registrar_historial = anterior

    def _alternar_animacion(self, activa: bool) -> None:
        if activa and hasattr(self, "_corrientes_calculadas") and self._corrientes_calculadas:
            for nombre, corriente in self._corrientes_calculadas.items():
                item = self.escena_circuito.componentes_graficos.get(nombre)
                if item:
                    item.corriente_animacion = corriente
            self._temporizador_animacion.start()
        else:
            self._temporizador_animacion.stop()
            if hasattr(self, "escena_circuito"):
                for item in self.escena_circuito.componentes_graficos.values():
                    item.corriente_animacion = 0.0
                    item.update()

    def _avanzar_animacion(self) -> None:
        self._fase_animacion = (self._fase_animacion + 0.015) % 1.0
        for item in self.escena_circuito.componentes_graficos.values():
            if item.corriente_animacion:
                item.fase_animacion = self._fase_animacion
                item.update()

    def _editar_componente(self, nombre: str) -> None:
        item = self.escena_circuito.componentes_graficos.get(nombre)
        if not item or item.tipo_catalogo == "TIERRA":
            return
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Editar componente")
        formulario = QFormLayout(dialogo)
        etiqueta = QLineEdit(item.id_ref)
        valor = QLineEdit(f"{float(item.valor_str) / item.factor_unidad:g}")
        unidad = QComboBox()
        unidades = {
            "RESISTENCIA": [("Ω", 1), ("kΩ", 1e3), ("MΩ", 1e6)],
            "FUENTE_VOLTAJE": [("V", 1), ("mV", 1e-3), ("kV", 1e3)],
            "FUENTE_CORRIENTE": [("A", 1), ("mA", 1e-3), ("µA", 1e-6)],
            "FUENTE_CCVS": [("Ω", 1), ("kΩ", 1e3), ("MΩ", 1e6)],
        }
        for texto, factor in unidades[item.tipo_catalogo]:
            unidad.addItem(texto, factor)
        indice = unidad.findData(item.factor_unidad)
        unidad.setCurrentIndex(max(indice, 0))
        formulario.addRow("Etiqueta", etiqueta)
        formulario.addRow("Valor", valor)
        formulario.addRow("Unidad", unidad)
        control = None
        if item.tipo_catalogo == "FUENTE_CCVS":
            control = QComboBox()
            for otro in self.escena_circuito.componentes_graficos.values():
                if otro.tipo_catalogo in ("RESISTENCIA", "FUENTE_VOLTAJE", "FUENTE_CORRIENTE", "FUENTE_CCVS") and otro is not item:
                    control.addItem(otro.id_ref)
            control.setCurrentText(item.componente_control_ref)
            formulario.addRow("Corriente de control", control)
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        botones.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(dialogo.accept)
        botones.rejected.connect(dialogo.reject)
        formulario.addRow(botones)
        while dialogo.exec() == QDialog.DialogCode.Accepted:
            nuevo = etiqueta.text().strip()
            try:
                numero = float(valor.text().strip().replace(",", "."))
                if not nuevo or (nuevo != nombre and nuevo in self.escena_circuito.componentes_graficos):
                    raise ValueError("La etiqueta debe ser única y no puede estar vacía.")
                if not math.isfinite(numero) or (item.tipo_catalogo == "RESISTENCIA" and numero <= 0):
                    raise ValueError("Introduce un valor finito; la resistencia debe ser mayor que cero.")
                if control is not None and not control.currentText():
                    raise ValueError("Selecciona un componente de control.")
            except ValueError as exc:
                QMessageBox.warning(dialogo, "Datos inválidos", str(exc))
                continue
            self._guardar_punto_deshacer()
            item.prepareGeometryChange()
            if nuevo != nombre:
                del self.escena_circuito.componentes_graficos[nombre]
                item.id_ref = nuevo
                self.escena_circuito.componentes_graficos[nuevo] = item
                for otro in self.escena_circuito.componentes_graficos.values():
                    if otro.componente_control_ref == nombre:
                        otro.componente_control_ref = nuevo
            item.factor_unidad = float(unidad.currentData())
            item.unidad_simbolo = unidad.currentText()
            item.valor_str = str(numero * item.factor_unidad)
            if control is not None:
                item.componente_control_ref = control.currentText()
            item.update()
            self._reconstruir_arbol_lateral()
            self._sincronizar_seleccion(nuevo)
            self._actualizar_badge_estado("Pendiente de analizar")
            break

    def _actualizar_badge_estado(self, texto: str, es_error: bool = False) -> None:
        # Los mensajes se reservan para la barra de estado, sin ocupar el lienzo.
        self.statusBar().showMessage(texto.lstrip("• "), 5000)
        if "Análisis completo" not in texto:
            self._detener_animacion()
            self._limpiar_resultados()

    def _limpiar_resultados(self) -> None:
        self.tabla_nodos.setRowCount(0)
        self.tabla_lecturas.setRowCount(0)
        self.tabla_variables.setRowCount(0)
        self.caja_ecuaciones.clear()
        self._limpiar_matriz()
        self.lbl_estado_resultados.setText("Ejecuta la simulación para ver resultados")
        for item in self.escena_circuito.componentes_graficos.values():
            item.voltaje_lectura = "—"
            item.corriente_lectura = "—"
            item.potencia_lectura = "—"
        self.lbl_valor_voltaje_prop.setText("—")
        self.lbl_valor_corriente_prop.setText("—")
        self.lbl_valor_potencia_prop.setText("—")

    def _mostrar_ventana_error_calculo(self, titulo: str, detalle: str) -> None:
        """
        Muestra una ventana emergente modal (`QMessageBox`) indicando claramente
        el error ocurrido al intentar analizar el circuito.
        """
        self._actualizar_badge_estado("• Error en el cálculo", es_error=True)
        self._mostrar_estado_simulacion(False, f"{titulo}\n\n{detalle}")

    def _mostrar_estado_simulacion(self, correcto: bool, detalle: str) -> None:
        if hasattr(self, "_dialogo_estado"):
            self._dialogo_estado.close()
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Estado de simulación")
        dialogo.resize(520, 270)
        contenido = QVBoxLayout(dialogo)
        titulo = QLabel("Simulación completada" if correcto else "No se pudo completar")
        titulo.setStyleSheet("font-size: 16px; font-weight: 700; color: " + ("#147b69" if correcto else "#b02a37") + ";")
        contenido.addWidget(titulo)
        consola = QTextEdit()
        consola.setReadOnly(True)
        metodo = "lazos independientes (mallas)" if self.btn_mallas.isChecked() else "nodos (MNA)"
        consola.setPlainText(f"Análisis DC: {metodo}\nEstado: " + ("correcto" if correcto else "error") + "\n\n" + detalle)
        contenido.addWidget(consola)
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(dialogo.close)
        contenido.addWidget(cerrar, alignment=Qt.AlignmentFlag.AlignRight)
        self._dialogo_estado = dialogo
        dialogo.show()

    def _slot_eliminar_componente_actual(self) -> None:
        """
        Elimina el componente o cable seleccionado actualmente en el lienzo
        o el componente activo en el panel de propiedades.
        """
        if self.escena_circuito.eliminar_seleccionados():
            return

        if self._id_actual and self._id_actual in self.escena_circuito.componentes_graficos:
            self.escena_circuito.eliminar_componente(self._id_actual)
        else:
            QMessageBox.information(
                self,
                "Eliminar componente",
                "Selecciona primero un componente o cable en el lienzo o en el árbol izquierdo para eliminarlo.",
            )

    def _slot_elemento_eliminado_en_escena(self, id_eliminado: str) -> None:
        """Se ejecuta automáticamente cuando se elimina un componente o cable de la escena."""
        self.escena_circuito.recalcular_nodos_desde_cables()
        self._reconstruir_arbol_lateral()
        self._actualizar_badge_estado(
            f"• '{id_eliminado}' eliminado (Pulsa Analizar)", es_error=False
        )

        # Seleccionar otro componente disponible o limpiar el panel derecho
        restantes = [
            k
            for k, v in self.escena_circuito.componentes_graficos.items()
            if v.tipo_catalogo != "TIERRA"
        ]
        if restantes:
            self._sincronizar_seleccion(restantes[0])
        else:
            self._id_actual = ""
            self.lbl_badge_elemento.setText("—")
            self.lbl_tipo_elemento.setText("Sin selección")
            self.lbl_nodos_entre.setText("Ningún componente seleccionado")
            self.input_valor_prop.clear()

    def _slot_limpiar_lienzo(self) -> None:
        self._guardar_punto_deshacer()
        self.escena_circuito.blockSignals(True)
        self.escena_circuito.clear()
        self.escena_circuito.componentes_graficos.clear()
        self.escena_circuito.cables_graficos.clear()
        self.escena_circuito.blockSignals(False)
        self.arbol_circuito.clear()
        self.chk_ref_n0.setChecked(False)
        self.tabla_lecturas.setRowCount(0)
        self.caja_ecuaciones.clear()
        self._limpiar_matriz()
        self._actualizar_badge_estado("• Lienzo vacío (Arrastra componentes)")

    def _slot_componente_soltado_en_escena(self, comp_item: ComponenteGraficoItem) -> None:
        self._reconstruir_arbol_lateral()
        self._sincronizar_seleccion(comp_item.id_ref)
        self._actualizar_badge_estado("• Componente agregado (Une sus pines)")

    def _slot_conexion_cable_creada(self, cable: CableGraficoItem) -> None:
        self.escena_circuito.recalcular_nodos_desde_cables()
        self._reconstruir_arbol_lateral()
        self._actualizar_badge_estado("• Nodo conectado (Pulsa Analizar)")

    def _reconstruir_arbol_lateral(self) -> None:
        self.arbol_circuito.clear()
        self._items_arbol_por_id.clear()

        rama_comp = QTreeWidgetItem(self.arbol_circuito, ["Componentes", ""])
        rama_comp.setFont(0, QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        rama_comp.setForeground(0, QBrush(QColor("#1d3835")))
        nodos_vistos = set()

        for id_c, item in self.escena_circuito.componentes_graficos.items():
            if item.tipo_catalogo == "TIERRA":
                continue
            nod_a = item.terminal_a.etiqueta_nodo
            nod_b = item.terminal_b.etiqueta_nodo
            nodos_vistos.add(nod_a)
            nodos_vistos.add(nod_b)

            fila_arbol = QTreeWidgetItem(
                rama_comp, [id_c, f"{float(item.valor_str) / item.factor_unidad:g} {item.unidad_simbolo}"]
            )
            fila_arbol.setTextAlignment(
                1, Qt.AlignmentFlag.AlignCenter
            )
            fila_arbol.setForeground(1, QBrush(QColor("#6C757D")))
            fila_arbol.setForeground(0, QBrush(QColor("#1d3835")))
            fila_arbol.setToolTip(0, id_c)
            fila_arbol.setToolTip(1, fila_arbol.text(1))
            fila_arbol.setData(0, Qt.ItemDataRole.UserRole, id_c)
            self._items_arbol_por_id[id_c] = fila_arbol

        rama_nodos = QTreeWidgetItem(self.arbol_circuito, ["Nodos", ""])
        rama_nodos.setFont(0, QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        rama_nodos.setForeground(0, QBrush(QColor("#1d3835")))
        for nodo in sorted(nodos_vistos or {"GND"}):
            item_nodo = QTreeWidgetItem(rama_nodos, [nodo, ""])
            item_nodo.setForeground(0, QBrush(QColor("#536d67")))
            item_nodo.setToolTip(0, nodo)

        self.arbol_circuito.expandAll()
        self.chk_ref_n0.setChecked(any(
            item.tipo_catalogo == "TIERRA" and item.terminal_a.cables_conectados
            for item in self.escena_circuito.componentes_graficos.values()
        ))
        num_c = len(self._items_arbol_por_id)
        self.lbl_conteo_topologia.setText(
            f"{len(nodos_vistos)} nodos · {num_c} componentes"
        )

    # =========================================================================
    # SINCRONIZACIÓN DE SELECCIÓN Y RESOLUCIÓN MATEMÁTICA MNA CON VALIDACIÓN
    # =========================================================================

    def _sincronizar_seleccion(self, id_comp: str) -> None:
        if id_comp not in self.escena_circuito.componentes_graficos:
            return

        for cable in self.escena_circuito.cables_graficos:
            if cable.resaltado_nodo:
                cable.resaltado_nodo = False
                cable.update()

        self._id_actual = id_comp
        comp_item = self.escena_circuito.componentes_graficos[id_comp]
        self.input_valor_prop.setEnabled(True)
        self.btn_aplicar_valor.setEnabled(True)
        self.btn_eliminar_prop.setEnabled(True)

        self.lbl_badge_elemento.setText(comp_item.id_ref)
        self.lbl_tipo_elemento.setText(comp_item.nombre_tipo_legible)
        etq_a = comp_item.terminal_a.etiqueta_nodo
        etq_b = comp_item.terminal_b.etiqueta_nodo
        self.lbl_nodos_entre.setText(f"Entre {etq_a} y {etq_b}")
        self.lbl_etiqueta_valor.setText(comp_item.etiqueta_propiedad_valor)
        self.input_valor_prop.setText(f"{float(comp_item.valor_str) / comp_item.factor_unidad:g}")
        self.lbl_simbolo_unidad.setText(comp_item.unidad_simbolo)
        self.lbl_val_terminal_ini.setText(etq_a)
        self.lbl_val_terminal_fin.setText(etq_b)
        self.lbl_titulo_voltaje_prop.setText(f"Voltaje {etq_a} - {etq_b}")
        self.lbl_valor_voltaje_prop.setText(comp_item.voltaje_lectura)
        self.lbl_titulo_corriente_prop.setText(f"Corriente {etq_a} → {etq_b}")
        self.lbl_valor_corriente_prop.setText(comp_item.corriente_lectura)
        self.lbl_valor_potencia_prop.setText(comp_item.potencia_lectura)

        if id_comp in self._items_arbol_por_id:
            self.arbol_circuito.setCurrentItem(self._items_arbol_por_id[id_comp])

        self.escena_circuito.blockSignals(True)
        for k, it in self.escena_circuito.componentes_graficos.items():
            it.setSelected(k == id_comp)
        self.escena_circuito.blockSignals(False)

    def _slot_item_arbol_clic(self, item: QTreeWidgetItem, col: int) -> None:
        id_c = item.data(0, Qt.ItemDataRole.UserRole)
        if id_c:
            self._sincronizar_seleccion(id_c)

    def _slot_fila_tabla_clic(self, fila: int, col: int) -> None:
        it = self.tabla_lecturas.item(fila, 0)
        if it:
            self._sincronizar_seleccion(it.text())
            item = self.escena_circuito.componentes_graficos.get(it.text())
            if item:
                self.vista_circuito.ensureVisible(item, 40, 40)

    def _resaltar_nodo(self, id_nodo: int) -> None:
        self._id_actual = ""
        self.lbl_badge_elemento.setText("Nodo")
        self.lbl_tipo_elemento.setText("Nodo seleccionado")
        self.lbl_nodos_entre.setText("Conexiones resaltadas en el lienzo")
        self.input_valor_prop.clear()
        self.input_valor_prop.setEnabled(False)
        self.btn_aplicar_valor.setEnabled(False)
        self.btn_eliminar_prop.setEnabled(False)
        self.lbl_val_terminal_ini.setText("—")
        self.lbl_val_terminal_fin.setText("—")
        self.lbl_valor_voltaje_prop.setText("—")
        self.lbl_valor_corriente_prop.setText("—")
        self.lbl_valor_potencia_prop.setText("—")
        self.escena_circuito.blockSignals(True)
        self.escena_circuito.clearSelection()
        self.escena_circuito.blockSignals(False)
        primer_cable = None
        for cable in self.escena_circuito.cables_graficos:
            cable.resaltado_nodo = cable.terminal_origen.id_nodo == id_nodo
            if cable.resaltado_nodo and primer_cable is None:
                primer_cable = cable
            cable.update()
        if primer_cable:
            self.vista_circuito.ensureVisible(primer_cable, 40, 40)

    def _seleccionar_nodo_resultado(self, fila: int, columna: int) -> None:
        celda = self.tabla_nodos.item(fila, 0)
        if celda:
            id_nodo = celda.data(Qt.ItemDataRole.UserRole)
            if id_nodo is not None:
                self._resaltar_nodo(id_nodo)

    def _seleccionar_variable_resultado(self, fila: int, columna: int) -> None:
        celda = self.tabla_variables.item(fila, 0)
        if not celda:
            return
        destino = celda.data(Qt.ItemDataRole.UserRole)
        if not destino:
            return
        if destino[0] == "nodo":
            self._resaltar_nodo(destino[1])
        elif destino[0] == "componente":
            self._sincronizar_seleccion(destino[1])
            item = self.escena_circuito.componentes_graficos.get(destino[1])
            if item:
                self.vista_circuito.ensureVisible(item, 40, 40)

    def _slot_aplicar_valor_propiedad(self) -> None:
        if self._id_actual not in self.escena_circuito.componentes_graficos:
            return
        comp_item = self.escena_circuito.componentes_graficos[self._id_actual]
        texto = self.input_valor_prop.text().strip().replace(",", ".")
        try:
            val = float(texto)
            if not math.isfinite(val) or (comp_item.tipo_catalogo == "RESISTENCIA" and val <= 0):
                raise ValueError(
                    f"La resistencia '{comp_item.id_ref}' debe tener un valor estrictamente mayor que cero (> 0 Ω)."
                )
        except ValueError as exc:
            self._mostrar_ventana_error_calculo(
                "Valor de Componente Inválido",
                str(exc)
                if "resistencia" in str(exc)
                else f"El valor '{self.input_valor_prop.text()}' no es un número válido.",
            )
            return

        self._guardar_punto_deshacer()
        comp_item.prepareGeometryChange()
        comp_item.valor_str = str(val * comp_item.factor_unidad)
        comp_item.update()
        self._reconstruir_arbol_lateral()
        self._actualizar_badge_estado("• Pendiente de analizar")

    def _slot_analizar_circuito(self) -> None:
        """
        Valida las conexiones de los componentes en el lienzo, construye el modelo
        eléctrico (Módulo 1), resuelve el sistema MNA (Módulo 2) y, si ocurre
        cualquier error topológico o numérico, despliega una ventana emergente de error.
        """
        self._analisis_exitoso = False
        try:
            # 0. Recalcular conectividad de nodos a partir de los cables actuales
            self.escena_circuito.recalcular_nodos_desde_cables()
            self._reconstruir_arbol_lateral()

            componentes_activos = [
                it
                for it in self.escena_circuito.componentes_graficos.values()
                if it.tipo_catalogo != "TIERRA"
            ]
            if not componentes_activos:
                raise ValueError(
                    "No hay componentes eléctricos en el lienzo. Arrastra componentes "
                    "desde la paleta izquierda antes de analizar."
                )

            # Verificar que exista al menos una referencia de Tierra conectada
            tiene_tierra_conectada = any(
                it.terminal_a.id_nodo == 0 or it.terminal_b.id_nodo == 0
                for it in componentes_activos
            )
            if not tiene_tierra_conectada:
                raise ValueError(
                    "El circuito no posee conexión al nodo de referencia Tierra (GND = 0 V). "
                    "Asegúrate de que exista un componente Tierra conectado mediante cables."
                )

            # Verificar que ningún componente tenga terminales abiertos / desconectados
            for item in componentes_activos:
                if len(item.terminal_a.cables_conectados) == 0:
                    raise ValueError(
                        f"El terminal inicial (+) del componente '{item.id_ref}' "
                        f"({item.nombre_tipo_legible}) está desconectado (circuito abierto). "
                        "Conéctalo con un cable o elimina el componente."
                    )
                if len(item.terminal_b.cables_conectados) == 0:
                    raise ValueError(
                        f"El terminal final (−) del componente '{item.id_ref}' "
                        f"({item.nombre_tipo_legible}) está desconectado (circuito abierto). "
                        "Conéctalo con un cable o elimina el componente."
                    )

            ckt = Circuito("Circuito Lienzo MNA")
            pendientes_ccvs: List[ComponenteGraficoItem] = []

            # 1. Instanciar resistencias y fuentes independientes
            for item in componentes_activos:
                na_id = item.terminal_a.id_nodo
                nb_id = item.terminal_b.id_nodo
                ckt.obtener_o_crear_nodo(na_id, item.terminal_a.etiqueta_nodo)
                ckt.obtener_o_crear_nodo(nb_id, item.terminal_b.etiqueta_nodo)

                val_num = float(item.valor_str.replace(",", "."))

                if item.tipo_catalogo == "RESISTENCIA":
                    ckt.agregar_resistencia(item.id_ref, na_id, nb_id, val_num)
                elif item.tipo_catalogo == "FUENTE_VOLTAJE":
                    ckt.agregar_fuente_voltaje(item.id_ref, na_id, nb_id, val_num)
                elif item.tipo_catalogo == "FUENTE_CORRIENTE":
                    ckt.agregar_fuente_corriente(item.id_ref, na_id, nb_id, val_num)
                elif item.tipo_catalogo == "FUENTE_CCVS":
                    pendientes_ccvs.append(item)

            # 2. Instanciar fuentes dependientes CCVS verificando que su elemento de control exista
            for item_ccvs in pendientes_ccvs:
                na_id = item_ccvs.terminal_a.id_nodo
                nb_id = item_ccvs.terminal_b.id_nodo
                ganancia_r = float(item_ccvs.valor_str.replace(",", "."))
                ref_ctrl = item_ccvs.componente_control_ref or "R_5"

                if ref_ctrl not in self.escena_circuito.componentes_graficos:
                    raise KeyError(
                        f"La fuente dependiente '{item_ccvs.id_ref}' depende de la corriente "
                        f"i_φ en '{ref_ctrl}', pero el componente '{ref_ctrl}' fue eliminado "
                        "del circuito."
                    )
                ckt.agregar_fuente_ccvs(
                    item_ccvs.id_ref, na_id, nb_id, ganancia_r, ref_ctrl
                )

            # 3. Construir sistema MNA y resolver con NumPy y SymPy
            if self.btn_mallas.isChecked():
                sistema, solucion = AnalizadorMallas(ckt).resolver()
            else:
                sistema = AnalizadorNodos(ckt).construir_sistema()
                solucion = MotorNumericoNumPy.resolver(sistema)
            reporte = AnalizadorSimbolicoYResultados.calcular_magnitudes_circuito(
                ckt, sistema, solucion
            )

        except ErrorCircuitoSingular as exc:
            self._mostrar_ventana_error_calculo(
                "Error Matemático: Matriz Singular o Circuito Incompatible",
                str(exc),
            )
            return
        except KeyError as exc:
            self._mostrar_ventana_error_calculo(
                "Error de Dependencia (Fuente Controlada CCVS)",
                str(exc).strip("\"'"),
            )
            return
        except ValueError as exc:
            self._mostrar_ventana_error_calculo(
                "Error de Topología o Conexión en el Circuito",
                str(exc),
            )
            return
        except Exception as exc:
            self._mostrar_ventana_error_calculo(
                "Error Inesperado durante el Cálculo",
                f"Ocurrió un problema al resolver el circuito:\n{exc}",
            )
            return

        # Mostrar todos los nodos resueltos, incluida la referencia y los auxiliares.
        nombres_nodos = {n.id_nodo: n.nombre for n in ckt.nodos}
        nodos_resueltos = sorted(solucion.voltajes_nodos.items())
        self.tabla_nodos.setRowCount(len(nodos_resueltos))
        for fila, (id_nodo, voltaje) in enumerate(nodos_resueltos):
            nombre = nombres_nodos.get(id_nodo, f"N{id_nodo}")
            celda_nodo = self._celda_centrada(nombre)
            celda_nodo.setData(Qt.ItemDataRole.UserRole, id_nodo)
            self.tabla_nodos.setItem(fila, 0, celda_nodo)
            self.tabla_nodos.setItem(fila, 1, self._celda_centrada(f"{voltaje:.3f} V".replace(".", ",")))
        self.lbl_estado_resultados.setText("Resultados de la última simulación")

        # 5. Actualizar tabla de lecturas por componente
        elementos_lista = list(reporte.resultados_elementos.values())
        variables = [(f"V({nombres_nodos.get(n, f'N{n}')})", v, "V", ("nodo", n)) for n, v in nodos_resueltos]
        for resultado in elementos_lista:
            variables.extend([(f"I({resultado.nombre})", resultado.corriente_ab, "A", ("componente", resultado.nombre)),
                              (f"P({resultado.nombre})", resultado.potencia_w, "W", ("componente", resultado.nombre))])
        self.tabla_variables.setRowCount(len(variables))
        for fila_variable, (nombre_variable, valor_variable, unidad_variable, destino) in enumerate(variables):
            for columna, texto in enumerate((nombre_variable, f"{valor_variable:.6g}".replace(".", ","), unidad_variable)):
                celda = self._celda_centrada(texto)
                if columna == 0:
                    celda.setData(Qt.ItemDataRole.UserRole, destino)
                self.tabla_variables.setItem(fila_variable, columna, celda)
        self.tabla_lecturas.setRowCount(len(elementos_lista))

        for fila, r_el in enumerate(elementos_lista):
            v_str = f"{r_el.voltaje_ab:.3f} V".replace(".", ",")
            i_str = f"{r_el.corriente_ab:.3f} A".replace(".", ",")
            p_str = f"{r_el.potencia_w:.3f} W".replace(".", ",")

            if r_el.nombre in self.escena_circuito.componentes_graficos:
                g_item = self.escena_circuito.componentes_graficos[r_el.nombre]
                g_item.voltaje_lectura = v_str
                g_item.corriente_lectura = i_str
                g_item.potencia_lectura = p_str

            self.tabla_lecturas.setItem(fila, 0, self._celda_centrada(r_el.nombre))
            self.tabla_lecturas.setItem(
                fila, 1, self._celda_centrada(f"{r_el.nodo_a} → {r_el.nodo_b}")
            )
            self.tabla_lecturas.setItem(fila, 2, self._celda_centrada(v_str))
            self.tabla_lecturas.setItem(fila, 3, self._celda_centrada(i_str))
            self.tabla_lecturas.setItem(fila, 4, self._celda_centrada(p_str))
            self.tabla_lecturas.setRowHeight(fila, 28)

        # 6. Actualizar visores de Ecuaciones (SymPy) y Matriz del sistema (NumPy)
        self.caja_ecuaciones.setPlainText("\n".join(reporte.ecuaciones_texto))
        self._mostrar_matriz(sistema, solucion)

        self._actualizar_badge_estado("• Análisis completo", es_error=False)
        self._corrientes_calculadas = {r.nombre: r.corriente_ab for r in elementos_lista}
        self._comparacion_actual = comparar_fase1(ckt, solucion, reporte)
        for cable in self.escena_circuito.cables_graficos:
            cable.establecer_voltaje(solucion.voltajes_nodos.get(cable.terminal_origen.id_nodo))
        self._analisis_exitoso = True
        if self._id_actual:
            self._sincronizar_seleccion(self._id_actual)


def ejecutar_app() -> None:
    if sys.platform == "win32":
        # Identifica la aplicación en la barra de tareas en lugar de agruparla con Python.
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("CircuitosDC.Simulador.Fase3")
        except (AttributeError, OSError):
            pass
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent.parent / "assets" / "icono_circuito.ico")))
    ventana = VentanaSimuladorDC()
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    ejecutar_app()
