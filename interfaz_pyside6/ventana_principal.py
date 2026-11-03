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
from typing import Dict, List, Optional, Set

from PySide6.QtCore import QLineF, QPointF, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QKeySequence,
    QPainter,
    QPen,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFrame,
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
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
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
from modulo1_modelo import AnalizadorNodos, Circuito
from modulo2_motor import (
    AnalizadorSimbolicoYResultados,
    ErrorCircuitoSingular,
    MotorNumericoNumPy,
)


# =============================================================================
# HOJA DE ESTILOS GLOBAL (QSS)
# =============================================================================

ESTILO_QSS = """
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
    background-color: #555E58;
    color: #FFFFFF;
    border: none;
    border-radius: 7px;
    padding: 7px 24px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton#BotonAnalizar:hover {
    background-color: #434B46;
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
}
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
    componente_soltado = Signal(object)
    conexion_creada = Signal(object)
    elemento_eliminado = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setSceneRect(0, 0, 880, 360)
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

        # Asignar id_nodo a cada grupo conexo (si contiene un componente TIERRA -> nodo 0)
        siguiente_id_aislado = 50
        for grupo in grupos:
            tiene_tierra = any(
                t.componente_padre.tipo_catalogo == "TIERRA" for t in grupo
            )
            if tiene_tierra:
                id_asignado = 0
                etiqueta_asignada = "GND"
            else:
                # Conservar el id_nodo no nulo existente si el grupo proviene de un nodo válido
                ids_existentes = [t.id_nodo for t in grupo if t.id_nodo > 0]
                etiquetas_existentes = [
                    t.etiqueta_nodo for t in grupo if t.etiqueta_nodo and t.etiqueta_nodo != "GND"
                ]
                if ids_existentes and len(grupo) > 1:
                    id_asignado = ids_existentes[0]
                    etiqueta_asignada = (
                        etiquetas_existentes[0] if etiquetas_existentes else f"V{id_asignado}"
                    )
                else:
                    id_asignado = siguiente_id_aislado
                    etiqueta_asignada = f"N_abierto_{siguiente_id_aislado}"
                    siguiente_id_aislado += 1

            for t in grupo:
                t.id_nodo = id_asignado
                t.etiqueta_nodo = etiqueta_asignada
                for c in t.cables_conectados:
                    c.etiqueta_nodo = etiqueta_asignada
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
        self.setWindowTitle(
            "Simulador de Circuitos DC — Análisis Nodal Modificado (MNA) y Drag & Drop (PySide6)"
        )
        self.resize(1420, 920)
        self.setStyleSheet(ESTILO_QSS)

        self._id_actual: str = "R_5"
        self._items_arbol_por_id: Dict[str, QTreeWidgetItem] = {}

        self._construir_barra_menu()
        self._construir_barra_herramientas()
        self._construir_cuerpo_principal()

        # Atajo de teclado global (Supr / Delete) para eliminar el elemento seleccionado
        self.atajo_eliminar = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        self.atajo_eliminar.activated.connect(self._slot_eliminar_componente_actual)

        # Cargar el circuito de validación con CCVS en el lienzo interactivo
        self._cargar_circuito_validacion_ccvs()

    def _construir_barra_menu(self) -> None:
        barra_menu: QMenuBar = self.menuBar()
        for nombre_menu in ("Archivo", "Editar", "Vista", "Análisis", "Ayuda"):
            menu = barra_menu.addMenu(nombre_menu)
            if nombre_menu == "Editar":
                accion_elim = QAction("Eliminar componente seleccionado (Supr)", self)
                accion_elim.triggered.connect(self._slot_eliminar_componente_actual)
                menu.addAction(accion_elim)
            else:
                menu.addAction(QAction(f"Opciones de {nombre_menu}", self))

    def _construir_barra_herramientas(self) -> None:
        toolbar = QToolBar("Barra de Acciones Principal")
        toolbar.setObjectName("BarraSuperior")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        self.btn_nuevo = QPushButton("+ Nuevo")
        self.btn_abrir = QPushButton("Abrir")
        self.btn_guardar = QPushButton("Guardar")
        for btn in (self.btn_nuevo, self.btn_abrir, self.btn_guardar):
            btn.setProperty("class", "BotonToolbar")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            toolbar.addWidget(btn)

        self.btn_nuevo.clicked.connect(self._slot_limpiar_lienzo)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #E2E6E3; margin: 0 10px;")
        toolbar.addWidget(sep)

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

        # Botón en barra superior para eliminar el elemento seleccionado
        self.btn_eliminar_toolbar = QPushButton("Eliminar seleccionado")
        self.btn_eliminar_toolbar.setProperty("class", "BotonEliminar")
        self.btn_eliminar_toolbar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eliminar_toolbar.clicked.connect(self._slot_eliminar_componente_actual)
        toolbar.addWidget(self.btn_eliminar_toolbar)

        self.btn_restablecer = QPushButton("Restablecer")
        self.btn_restablecer.setProperty("class", "BotonToolbar")
        self.btn_restablecer.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_restablecer.clicked.connect(self._cargar_circuito_validacion_ccvs)
        toolbar.addWidget(self.btn_restablecer)

        self.btn_analizar = QPushButton("Analizar circuito")
        self.btn_analizar.setObjectName("BotonAnalizar")
        self.btn_analizar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analizar.clicked.connect(self._slot_analizar_circuito)
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

        lbl_circuito = QLabel("CIRCUITO ABIERTO")
        lbl_circuito.setProperty("class", "TituloSeccion")
        layout.addWidget(lbl_circuito)

        self.arbol_circuito = QTreeWidget()
        self.arbol_circuito.setObjectName("ArbolCircuito")
        self.arbol_circuito.setHeaderHidden(True)
        self.arbol_circuito.setColumnCount(2)
        self.arbol_circuito.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.arbol_circuito.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.arbol_circuito.itemClicked.connect(self._slot_item_arbol_clic)
        layout.addWidget(self.arbol_circuito, stretch=1)

        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setStyleSheet("color: #EAECE9;")
        layout.addWidget(linea)

        lbl_insertar = QLabel("INSERTAR COMPONENTE (DRAG & DROP)")
        lbl_insertar.setProperty("class", "TituloSeccion")
        layout.addWidget(lbl_insertar)

        lbl_instruccion_dd = QLabel("Arrastra un componente hacia el lienzo:")
        lbl_instruccion_dd.setStyleSheet("color: #6C757D; font-size: 11px;")
        layout.addWidget(lbl_instruccion_dd)

        definicion_paleta = [
            ("∿  Resistencia\n     R · Ohmios (Ω)", "RESISTENCIA", True),
            ("⊕  Fuente de voltaje\n     V · Independiente (V)", "FUENTE_VOLTAJE", False),
            ("⊙  Fuente de corriente\n     I · Independiente (A)", "FUENTE_CORRIENTE", False),
            ("◇  Fuente dependiente CCVS\n     V = r · i_φ (Controlada)", "FUENTE_CCVS", False),
            ("⏚  Tierra\n     GND · Referencia 0 V", "TIERRA", False),
        ]

        for texto_btn, tipo_cat, es_destacado in definicion_paleta:
            btn_drag = BotonPaletaDrag(texto_btn, tipo_cat, self)
            btn_drag.setProperty(
                "class", "BotonInsertarActivo" if es_destacado else "BotonInsertar"
            )
            layout.addWidget(btn_drag)

        lbl_tip_cable = QLabel(
            "Tip: Arrastra entre pines para unir con cables. Usa clic derecho o 'Supr' para eliminar."
        )
        lbl_tip_cable.setWordWrap(True)
        lbl_tip_cable.setStyleSheet(
            "color: #6C757D; font-size: 11px; margin-top: 4px;"
        )
        layout.addWidget(lbl_tip_cable)

        return panel

    def _crear_panel_central(self) -> QWidget:
        contenedor = QWidget()
        layout = QVBoxLayout(contenedor)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        self.splitter_central_vertical = QSplitter(Qt.Orientation.Vertical)
        self.splitter_central_vertical.setHandleWidth(6)

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

        fila_cabecera = QHBoxLayout()
        col_titulos = QVBoxLayout()
        col_titulos.setSpacing(2)

        lbl_titulo = QLabel("espacio de trabajo (Drag & Drop interactivo)")
        lbl_titulo.setStyleSheet("font-size: 16px; font-weight: 700; color: #212529;")
        lbl_subtitulo = QLabel(
            "Selecciona cualquier elemento para editar o eliminar (clic derecho, botón Eliminar o tecla Supr)."
        )
        lbl_subtitulo.setStyleSheet("font-size: 12px; color: #6C757D;")

        col_titulos.addWidget(lbl_titulo)
        col_titulos.addWidget(lbl_subtitulo)
        fila_cabecera.addLayout(col_titulos)
        fila_cabecera.addStretch()

        self.lbl_badge_estado = QLabel("• Análisis completo")
        self.lbl_badge_estado.setObjectName("BadgeEstado")
        fila_cabecera.addWidget(self.lbl_badge_estado)
        layout.addLayout(fila_cabecera)

        marco_canvas = QFrame()
        marco_canvas.setProperty("class", "PanelBlanco")
        layout_canvas = QVBoxLayout(marco_canvas)
        layout_canvas.setContentsMargins(10, 6, 10, 6)
        layout_canvas.setSpacing(0)

        fila_info_sup = QHBoxLayout()
        fila_info_sup.addStretch()
        self.lbl_conteo_topologia = QLabel("4 nodos activos · 7 componentes")
        self.lbl_conteo_topologia.setStyleSheet("color: #868E96; font-size: 11px;")
        fila_info_sup.addWidget(self.lbl_conteo_topologia)
        layout_canvas.addLayout(fila_info_sup)

        self.escena_circuito = EscenaEsquematicoDC(self)
        self.escena_circuito.componente_seleccionado.connect(self._sincronizar_seleccion)
        self.escena_circuito.componente_soltado.connect(
            self._slot_componente_soltado_en_escena
        )
        self.escena_circuito.conexion_creada.connect(self._slot_conexion_cable_creada)
        self.escena_circuito.elemento_eliminado.connect(
            self._slot_elemento_eliminado_en_escena
        )

        self.vista_circuito = VistaEsquematicoDC(self.escena_circuito, self)
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
        lbl_sub_metodo = QLabel("Análisis Nodal Modificado (MNA con CCVS)")
        lbl_sub_metodo.setStyleSheet(
            "font-size: 12px; color: #6C757D; margin-left: 10px;"
        )

        fila_top.addWidget(lbl_res)
        fila_top.addWidget(lbl_sub_metodo)
        fila_top.addStretch()
        layout.addLayout(fila_top)

        fila_metricas_tabla = QHBoxLayout()
        fila_metricas_tabla.setSpacing(16)

        col_voltajes = QVBoxLayout()
        col_voltajes.setSpacing(8)

        lbl_vnodo = QLabel("VOLTAJES DE NODO Y CORRIENTE DE CONTROL")
        lbl_vnodo.setProperty("class", "TituloSeccion")
        col_voltajes.addWidget(lbl_vnodo)

        fila_tarjetas_v = QHBoxLayout()
        fila_tarjetas_v.setSpacing(8)

        self.lbl_val_v1 = QLabel("16,00")
        self.lbl_val_v2 = QLabel("10,00")
        self.lbl_val_v3 = QLabel("9,60")

        fila_tarjetas_v.addWidget(
            self._crear_tarjeta_voltaje_nodo("Nodo V1", self.lbl_val_v1, "V")
        )
        fila_tarjetas_v.addWidget(
            self._crear_tarjeta_voltaje_nodo("Nodo V2", self.lbl_val_v2, "V")
        )
        fila_tarjetas_v.addWidget(
            self._crear_tarjeta_voltaje_nodo("Nodo V3", self.lbl_val_v3, "V")
        )
        col_voltajes.addLayout(fila_tarjetas_v)

        tarjeta_destacada = QFrame()
        tarjeta_destacada.setObjectName("TarjetaCorrienteTotal")
        layout_dest = QHBoxLayout(tarjeta_destacada)
        layout_dest.setContentsMargins(12, 8, 14, 8)
        self.lbl_resumen_iphi = QLabel(
            "i_φ (V1→V2) = 1,20 A  |  Potencia en R_5 (5 Ω):"
        )
        self.lbl_resumen_iphi.setStyleSheet(
            "color: #2C332E; font-size: 12px; font-weight: 600;"
        )
        self.lbl_potencia_5ohm = QLabel("7,200 W")
        self.lbl_potencia_5ohm.setStyleSheet(
            "color: #1E3A28; font-size: 19px; font-weight: 700;"
        )
        layout_dest.addWidget(self.lbl_resumen_iphi)
        layout_dest.addStretch()
        layout_dest.addWidget(self.lbl_potencia_5ohm)
        col_voltajes.addWidget(tarjeta_destacada)

        fila_metricas_tabla.addLayout(col_voltajes, stretch=4)

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
        self.tabla_lecturas.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.tabla_lecturas.cellClicked.connect(self._slot_fila_tabla_clic)

        col_tabla.addWidget(self.tabla_lecturas)
        fila_metricas_tabla.addLayout(col_tabla, stretch=5)
        layout.addLayout(fila_metricas_tabla)

        fila_inferior = QHBoxLayout()
        fila_inferior.setSpacing(14)

        self.caja_ecuaciones = QTextEdit()
        self.caja_ecuaciones.setReadOnly(True)
        self.caja_ecuaciones.setFrameShape(QFrame.Shape.NoFrame)

        self.caja_matriz = QTextEdit()
        self.caja_matriz.setReadOnly(True)
        self.caja_matriz.setFrameShape(QFrame.Shape.NoFrame)

        fila_inferior.addWidget(
            self._envolver_en_tarjeta(
                "Ecuaciones (SymPy MNA)",
                "Método de Nodos Modificado · GND = 0 V",
                self.caja_ecuaciones,
            ),
            stretch=1,
        )
        fila_inferior.addWidget(
            self._envolver_en_tarjeta(
                "Matriz del sistema (NumPy)",
                "A · x = b",
                self.caja_matriz,
            ),
            stretch=1,
        )
        layout.addLayout(fila_inferior, stretch=1)

        return panel_res

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
        self.chk_ref_n0.setChecked(True)
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
        self.lbl_valor_voltaje_prop = QLabel("6,000 V")
        self.lbl_valor_voltaje_prop.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_valor_voltaje_prop.setStyleSheet("font-weight: 700; color: #212529;")

        self.lbl_titulo_corriente_prop = QLabel("Corriente V1 → V2")
        self.lbl_titulo_corriente_prop.setStyleSheet("color: #6C757D; font-size: 12px;")
        self.lbl_valor_corriente_prop = QLabel("1,200 A")
        self.lbl_valor_corriente_prop.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_valor_corriente_prop.setStyleSheet("font-weight: 700; color: #212529;")

        lbl_tit_pot = QLabel("Potencia calculada")
        lbl_tit_pot.setStyleSheet("color: #6C757D; font-size: 12px;")
        self.lbl_valor_potencia_prop = QLabel("7,200 W")
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
        self.escena_circuito.clear()
        self.escena_circuito.componentes_graficos.clear()
        self.escena_circuito.cables_graficos.clear()

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

        self._reconstruir_arbol_lateral()
        self._slot_analizar_circuito()
        self._sincronizar_seleccion("R_5")

    # =========================================================================
    # GESTIÓN DE ELIMINACIÓN DE COMPONENTES Y VENTANAS DE ERROR
    # =========================================================================

    def _actualizar_badge_estado(self, texto: str, es_error: bool = False) -> None:
        self.lbl_badge_estado.setText(texto)
        if es_error:
            self.lbl_badge_estado.setStyleSheet(
                "background-color: #F8D7DA; color: #842029; border: 1px solid #F5C2C7; "
                "border-radius: 11px; padding: 3px 12px; font-size: 11px; font-weight: 700;"
            )
        else:
            self.lbl_badge_estado.setStyleSheet("")

    def _mostrar_ventana_error_calculo(self, titulo: str, detalle: str) -> None:
        """
        Muestra una ventana emergente modal (`QMessageBox`) indicando claramente
        el error ocurrido al intentar analizar el circuito.
        """
        self._actualizar_badge_estado("• Error en el cálculo", es_error=True)
        cuadro_error = QMessageBox(self)
        cuadro_error.setIcon(QMessageBox.Icon.Critical)
        cuadro_error.setWindowTitle("Error al Analizar el Circuito")
        cuadro_error.setText(f"<b>{titulo}</b>")
        cuadro_error.setInformativeText(detalle)
        cuadro_error.setStandardButtons(QMessageBox.StandardButton.Ok)
        cuadro_error.exec()

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
        self.escena_circuito.clear()
        self.escena_circuito.componentes_graficos.clear()
        self.escena_circuito.cables_graficos.clear()
        self.arbol_circuito.clear()
        self.tabla_lecturas.setRowCount(0)
        self.caja_ecuaciones.clear()
        self.caja_matriz.clear()
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

        raiz = QTreeWidgetItem(self.arbol_circuito, ["circuito-mna-ccvs", ""])
        raiz.setFont(0, QFont("Segoe UI", 10, QFont.Weight.DemiBold))

        rama_comp = QTreeWidgetItem(raiz, ["Componentes", ""])
        nodos_vistos = set()

        for id_c, item in self.escena_circuito.componentes_graficos.items():
            if item.tipo_catalogo == "TIERRA":
                continue
            nod_a = item.terminal_a.etiqueta_nodo
            nod_b = item.terminal_b.etiqueta_nodo
            nodos_vistos.add(nod_a)
            nodos_vistos.add(nod_b)

            fila_arbol = QTreeWidgetItem(
                rama_comp, [id_c, f"{item.valor_str} {item.unidad_simbolo}"]
            )
            fila_arbol.setTextAlignment(
                1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            fila_arbol.setForeground(1, QBrush(QColor("#6C757D")))
            fila_arbol.setData(0, Qt.ItemDataRole.UserRole, id_c)
            self._items_arbol_por_id[id_c] = fila_arbol

        rama_nodos = QTreeWidgetItem(raiz, ["Nodos", ""])
        texto_nodos = " · ".join(sorted(nodos_vistos)) if nodos_vistos else "GND"
        item_nodos = QTreeWidgetItem(rama_nodos, [texto_nodos, ""])
        item_nodos.setForeground(0, QBrush(QColor("#6C757D")))

        self.arbol_circuito.expandAll()
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

        self._id_actual = id_comp
        comp_item = self.escena_circuito.componentes_graficos[id_comp]

        self.lbl_badge_elemento.setText(comp_item.id_ref)
        self.lbl_tipo_elemento.setText(comp_item.nombre_tipo_legible)
        etq_a = comp_item.terminal_a.etiqueta_nodo
        etq_b = comp_item.terminal_b.etiqueta_nodo
        self.lbl_nodos_entre.setText(f"Entre {etq_a} y {etq_b}")
        self.lbl_etiqueta_valor.setText(comp_item.etiqueta_propiedad_valor)
        self.input_valor_prop.setText(comp_item.valor_str)
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

    def _slot_aplicar_valor_propiedad(self) -> None:
        if self._id_actual not in self.escena_circuito.componentes_graficos:
            return
        comp_item = self.escena_circuito.componentes_graficos[self._id_actual]
        texto = self.input_valor_prop.text().strip().replace(",", ".")
        try:
            val = float(texto)
            if comp_item.tipo_catalogo == "RESISTENCIA" and val <= 0:
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

        comp_item.valor_str = str(int(val)) if val.is_integer() else f"{val:.2f}"
        comp_item.update()
        self._reconstruir_arbol_lateral()
        self._actualizar_badge_estado("• Pendiente de analizar")

    def _slot_analizar_circuito(self) -> None:
        """
        Valida las conexiones de los componentes en el lienzo, construye el modelo
        eléctrico (Módulo 1), resuelve el sistema MNA (Módulo 2) y, si ocurre
        cualquier error topológico o numérico, despliega una ventana emergente de error.
        """
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

        # 4. Actualizar tarjetas de Voltajes de Nodo V1, V2, V3
        v1 = solucion.voltajes_nodos.get(1, 0.0)
        v2 = solucion.voltajes_nodos.get(2, 0.0)
        v3 = solucion.voltajes_nodos.get(3, 0.0)
        self.lbl_val_v1.setText(f"{v1:.2f}".replace(".", ","))
        self.lbl_val_v2.setText(f"{v2:.2f}".replace(".", ","))
        self.lbl_val_v3.setText(f"{v3:.2f}".replace(".", ","))

        if "R_5" in reporte.resultados_elementos:
            res_r5 = reporte.resultados_elementos["R_5"]
            self.lbl_resumen_iphi.setText(
                f"i_φ (V1→V2) = {res_r5.corriente_ab:.2f} A  |  Potencia disipada en R_5 (5 Ω):"
            )
            self.lbl_potencia_5ohm.setText(
                f"{res_r5.potencia_w:.3f} W".replace(".", ",")
            )
        else:
            self.lbl_resumen_iphi.setText(
                f"Potencia total disipada en el circuito:"
            )
            self.lbl_potencia_5ohm.setText(
                f"{reporte.potencia_total_disipada:.3f} W".replace(".", ",")
            )

        # 5. Actualizar tabla de lecturas por componente
        elementos_lista = list(reporte.resultados_elementos.values())
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

            self.tabla_lecturas.setItem(fila, 0, QTableWidgetItem(r_el.nombre))
            self.tabla_lecturas.setItem(
                fila, 1, QTableWidgetItem(f"{r_el.nodo_a} → {r_el.nodo_b}")
            )
            self.tabla_lecturas.setItem(fila, 2, QTableWidgetItem(v_str))
            self.tabla_lecturas.setItem(fila, 3, QTableWidgetItem(i_str))
            self.tabla_lecturas.setItem(fila, 4, QTableWidgetItem(p_str))
            self.tabla_lecturas.setRowHeight(fila, 28)

        # 6. Actualizar visores de Ecuaciones (SymPy) y Matriz del sistema (NumPy)
        self.caja_ecuaciones.setPlainText("\n".join(reporte.ecuaciones_texto))
        texto_matriz = (
            f"Incógnitas x = {sistema.etiquetas_incognitas}\n\n"
            f"Matriz A:\n{sistema.matriz_A}\n\n"
            f"Vector b:\n{sistema.vector_b}\n\n"
            f"Solución x:\n{solucion.vector_x}"
        )
        self.caja_matriz.setPlainText(texto_matriz)

        self._actualizar_badge_estado("• Análisis completo", es_error=False)
        if self._id_actual:
            self._sincronizar_seleccion(self._id_actual)


def ejecutar_app() -> None:
    app = QApplication(sys.argv)
    ventana = VentanaSimuladorDC()
    ventana.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    ejecutar_app()
