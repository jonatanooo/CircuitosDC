"""
Módulo 3: Componentes Gráficos Interactivos (QGraphicsItem), Cables y Drag & Drop.

Implementa:
    1. `BotonPaletaDrag`: Botón de paleta que inicia operaciones `QDrag` con `QMimeData`
       para arrastrar y soltar componentes hacia el lienzo.
    2. `TerminalGraficoItem`: Punto de conexión interactivo en los extremos de cada
       componente que permite trazar cables y propagar identificadores de nodo.
    3. `CableGraficoItem`: Línea de interconexión dinámica entre dos terminales que
       se actualiza en tiempo real cuando los componentes se mueven, permite ser
       seleccionada/eliminada y muestra la etiqueta visual del nodo eléctrico.
    4. `ComponenteGraficoItem`: Subclase directa de `QGraphicsItem` con las banderas
       `ItemIsMovable`, `ItemIsSelectable` e `ItemSendsGeometryChanges` habilitadas,
       menú contextual de clic derecho para eliminar el componente, y renderizado de
       Resistencias, Fuentes Independientes (V e I), Fuentes Dependientes CCVS y Tierra.
"""

from typing import List, Optional

from PySide6.QtCore import QMimeData, QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QDrag,
    QFont,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QMenu,
    QPushButton,
    QStyleOptionGraphicsItem,
    QWidget,
)

MIME_TYPE_COMPONENTE = "application/x-simulador-dc-componente"


class BotonPaletaDrag(QPushButton):
    """
    Botón de la barra lateral izquierda que soporta Arrastrar y Soltar (Drag & Drop).
    Al hacer clic y arrastrar, empaqueta el `tipo_componente` en un objeto `QMimeData`
    e inicia un `QDrag` hacia el `QGraphicsView` / `QGraphicsScene`.
    """

    def __init__(
        self,
        texto: str,
        tipo_componente: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(texto, parent)
        self.tipo_componente: str = tipo_componente
        self._pos_inicio_drag: Optional[QPoint] = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pos_inicio_drag = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._pos_inicio_drag is None:
            return
        distancia = (event.pos() - self._pos_inicio_drag).manhattanLength()
        if distancia < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData(MIME_TYPE_COMPONENTE, self.tipo_componente.encode("utf-8"))
        mime_data.setText(self.tipo_componente)
        drag.setMimeData(mime_data)

        pixmap = QPixmap(150, 42)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(231, 240, 233, 235)))
        painter.setPen(QPen(QColor("#2E6F46"), 1.5))
        painter.drawRoundedRect(1, 1, 148, 40, 7, 7)
        painter.setPen(QColor("#1E3A28"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(
            pixmap.rect(), Qt.AlignmentFlag.AlignCenter, f"+ {self.tipo_componente}"
        )
        painter.end()

        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(75, 21))
        drag.exec(Qt.DropAction.CopyAction)


class TerminalGraficoItem(QGraphicsEllipseItem):
    """
    Representa un pin/terminal de conexión eléctrica perteneciente a un `ComponenteGraficoItem`.
    Permite iniciar y finalizar el trazado de cables (`CableGraficoItem`) para definir nodos.
    """

    RADIO = 5.5

    def __init__(
        self,
        componente_padre: "ComponenteGraficoItem",
        nombre_terminal: str,
        pos_relativa: QPointF,
        id_nodo_inicial: int = 1,
        etiqueta_nodo: str = "N1",
    ) -> None:
        super().__init__(
            -self.RADIO,
            -self.RADIO,
            self.RADIO * 2,
            self.RADIO * 2,
            parent=componente_padre,
        )
        self.componente_padre: "ComponenteGraficoItem" = componente_padre
        self.nombre_terminal: str = nombre_terminal  # 'A' (+) o 'B' (-)
        self.id_nodo: int = id_nodo_inicial
        self.etiqueta_nodo: str = etiqueta_nodo
        self.cables_conectados: List["CableGraficoItem"] = []

        self.setPos(pos_relativa)
        self.setAcceptHoverEvents(True)
        self.setZValue(10)
        self._actualizar_estilo(resaltado=False)

    def _actualizar_estilo(self, resaltado: bool) -> None:
        if resaltado:
            self.setBrush(QBrush(QColor("#2E6F46")))
            self.setPen(QPen(QColor("#FFFFFF"), 1.5))
            self.setScale(1.3)
        else:
            color_relleno = QColor("#1E3A28") if self.id_nodo == 0 else QColor("#5C6460")
            self.setBrush(QBrush(color_relleno))
            self.setPen(QPen(QColor("#FFFFFF"), 1.2))
            self.setScale(1.0)

    def hoverEnterEvent(self, event) -> None:
        self._actualizar_estilo(resaltado=True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._actualizar_estilo(resaltado=False)
        super().hoverLeaveEvent(event)

    def pos_escena(self) -> QPointF:
        """Retorna la posición absoluta del centro del terminal en coordenadas del QGraphicsScene."""
        return self.scenePos()

    def agregar_cable(self, cable: "CableGraficoItem") -> None:
        if cable not in self.cables_conectados:
            self.cables_conectados.append(cable)

    def remover_cable(self, cable: "CableGraficoItem") -> None:
        if cable in self.cables_conectados:
            self.cables_conectados.remove(cable)

    def actualizar_cables(self) -> None:
        for cable in list(self.cables_conectados):
            cable.actualizar_geometria()


class CableGraficoItem(QGraphicsLineItem):
    """
    Representa un conductor ideal (cable) que une dos `TerminalGraficoItem` en el
    `QGraphicsScene`, definiendo visual y eléctricamente un nodo compartido.
    """

    def __init__(
        self,
        terminal_origen: TerminalGraficoItem,
        terminal_destino: TerminalGraficoItem,
        etiqueta_nodo: str = "",
    ) -> None:
        super().__init__()
        self.terminal_origen: TerminalGraficoItem = terminal_origen
        self.terminal_destino: TerminalGraficoItem = terminal_destino
        self.etiqueta_nodo: str = etiqueta_nodo or terminal_origen.etiqueta_nodo

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        pen = QPen(QColor("#49504C"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        self.setPen(pen)
        self.setZValue(1)

        self.terminal_origen.agregar_cable(self)
        self.terminal_destino.agregar_cable(self)
        self.actualizar_geometria()

    def desconectar_de_terminales(self) -> None:
        """Desvincula este cable de sus dos terminales."""
        self.terminal_origen.remover_cable(self)
        self.terminal_destino.remover_cable(self)

    def actualizar_geometria(self) -> None:
        """Actualiza los extremos de la línea según la posición actual de ambos terminales."""
        p1 = self.terminal_origen.pos_escena()
        p2 = self.terminal_destino.pos_escena()
        self.setLine(p1.x(), p1.y(), p2.x(), p2.y())
        self.update()

    def contextMenuEvent(self, event) -> None:
        """Permite eliminar un cable haciendo clic derecho sobre él."""
        menu = QMenu()
        accion_eliminar = menu.addAction(f"Eliminar cable ({self.etiqueta_nodo})")
        accion_elegida = menu.exec(event.screenPos())
        if accion_elegida == accion_eliminar and self.scene():
            escena = self.scene()
            if hasattr(escena, "eliminar_cable"):
                escena.eliminar_cable(self)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.isSelected():
            self.setPen(QPen(QColor("#D9534F"), 2.8, Qt.PenStyle.SolidLine))
        else:
            self.setPen(QPen(QColor("#49504C"), 2.2, Qt.PenStyle.SolidLine))
        super().paint(painter, option, widget)

        if self.etiqueta_nodo:
            linea = self.line()
            punto_medio = linea.center()
            painter.save()
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            rect_badge = QRectF(punto_medio.x() - 18, punto_medio.y() - 18, 36, 15)
            painter.setPen(QPen(QColor("#DCE1DD"), 1.0))
            painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
            painter.drawRoundedRect(rect_badge, 4, 4)
            painter.setPen(
                QColor("#2E6F46") if self.etiqueta_nodo != "GND" else QColor("#495057")
            )
            painter.drawText(rect_badge, Qt.AlignmentFlag.AlignCenter, self.etiqueta_nodo)
            painter.restore()


class ComponenteGraficoItem(QGraphicsItem):
    """
    Elemento gráfico interactivo para representar componentes del circuito DC en el
    `QGraphicsScene`.

    Hereda directamente de `QGraphicsItem` y habilita:
        - `ItemIsMovable`: Permite al usuario arrastrar y reposicionar el componente en el lienzo.
        - `ItemIsSelectable`: Permite seleccionarlo para editar sus propiedades o eliminarlo.
        - `ItemSendsGeometryChanges`: Notifica cambios de posición para actualizar los cables conectados.
    """

    ANCHO_BASE = 110.0
    ALTO_BASE = 76.0

    def __init__(
        self,
        id_ref: str,
        tipo_catalogo: str,
        valor_str: str,
        unidad_simbolo: str,
        pos_inicial: QPointF = QPointF(100, 100),
        orientacion: str = "H",
        nodo_a_id: int = 1,
        nodo_b_id: int = 0,
        etiqueta_nodo_a: str = "V1",
        etiqueta_nodo_b: str = "GND",
        componente_control_ref: str = "",
    ) -> None:
        super().__init__()
        self.id_ref: str = id_ref
        self.tipo_catalogo: str = tipo_catalogo
        self.valor_str: str = valor_str
        self.unidad_simbolo: str = unidad_simbolo
        self.orientacion: str = orientacion
        self.componente_control_ref: str = componente_control_ref

        self.voltaje_lectura: str = "0,000 V"
        self.corriente_lectura: str = "0,000 mA"
        self.potencia_lectura: str = "0,000 W"

        # Habilitar banderas requeridas de QGraphicsItem
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setZValue(5)

        if self.orientacion == "H":
            pos_a = QPointF(-46.0, 0.0)
            pos_b = QPointF(46.0, 0.0)
        else:
            pos_a = QPointF(0.0, -46.0)
            pos_b = QPointF(0.0, 46.0)

        self.terminal_a = TerminalGraficoItem(
            self, "A", pos_a, nodo_a_id, etiqueta_nodo_a
        )
        self.terminal_b = TerminalGraficoItem(
            self, "B", pos_b, nodo_b_id, etiqueta_nodo_b
        )

        if self.tipo_catalogo == "TIERRA":
            self.terminal_a.setPos(QPointF(0.0, -20.0))
            self.terminal_a.id_nodo = 0
            self.terminal_a.etiqueta_nodo = "GND"
            self.terminal_b.setVisible(False)

        self.setPos(pos_inicial)

    @property
    def nombre_tipo_legible(self) -> str:
        mapa = {
            "RESISTENCIA": "Resistencia",
            "FUENTE_VOLTAJE": "Fuente de voltaje",
            "FUENTE_CORRIENTE": "Fuente de corriente",
            "FUENTE_CCVS": "Fuente CCVS (Dependiente)",
            "TIERRA": "Tierra (Referencia 0 V)",
        }
        return mapa.get(self.tipo_catalogo, "Componente")

    @property
    def etiqueta_propiedad_valor(self) -> str:
        mapa = {
            "RESISTENCIA": "Valor de resistencia",
            "FUENTE_VOLTAJE": "Valor de voltaje",
            "FUENTE_CORRIENTE": "Valor de corriente",
            "FUENTE_CCVS": f"Ganancia r (control: {self.componente_control_ref or 'i_φ'})",
            "TIERRA": "Potencial de referencia",
        }
        return mapa.get(self.tipo_catalogo, "Valor nominal")

    def obtener_todos_los_cables(self) -> List[CableGraficoItem]:
        """Retorna todos los cables conectados tanto al terminal A como al terminal B."""
        cables = list(self.terminal_a.cables_conectados)
        for c in self.terminal_b.cables_conectados:
            if c not in cables:
                cables.append(c)
        return cables

    def boundingRect(self) -> QRectF:
        return QRectF(
            -self.ANCHO_BASE / 2.0,
            -self.ALTO_BASE / 2.0,
            self.ANCHO_BASE,
            self.ALTO_BASE,
        )

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.terminal_a.actualizar_cables()
            self.terminal_b.actualizar_cables()
        return super().itemChange(change, value)

    def contextMenuEvent(self, event) -> None:
        """Menú contextual al hacer clic derecho sobre el componente en el lienzo."""
        self.setSelected(True)
        menu = QMenu()
        accion_eliminar = menu.addAction(f"Eliminar componente '{self.id_ref}'")
        accion_rotar = menu.addAction("Rotar orientación (H / V)")
        accion_elegida = menu.exec(event.screenPos())

        if accion_elegida == accion_eliminar and self.scene():
            escena = self.scene()
            if hasattr(escena, "eliminar_componente"):
                escena.eliminar_componente(self.id_ref)
        elif accion_elegida == accion_rotar:
            self.alternar_orientacion()

    def alternar_orientacion(self) -> None:
        if self.tipo_catalogo == "TIERRA":
            return
        self.orientacion = "V" if self.orientacion == "H" else "H"
        if self.orientacion == "H":
            self.terminal_a.setPos(QPointF(-46.0, 0.0))
            self.terminal_b.setPos(QPointF(46.0, 0.0))
        else:
            self.terminal_a.setPos(QPointF(0.0, -46.0))
            self.terminal_b.setPos(QPointF(0.0, 46.0))
        self.terminal_a.actualizar_cables()
        self.terminal_b.actualizar_cables()
        self.update()

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.isSelected():
            pen_sel = QPen(QColor("#8FB99D"), 1.6)
            brush_sel = QBrush(QColor(225, 239, 229, 195))
            painter.setPen(pen_sel)
            painter.setBrush(brush_sel)
            painter.drawRoundedRect(self.boundingRect().adjusted(4, 4, -4, -4), 8, 8)

        pen_linea = QPen(QColor("#49504C"), 2.0)
        brush_cuerpo = QBrush(QColor("#FFFFFF"))
        painter.setPen(pen_linea)
        painter.setBrush(brush_cuerpo)

        if self.tipo_catalogo == "TIERRA":
            painter.drawLine(QPointF(0, -20), QPointF(0, 0))
            painter.drawLine(QPointF(-14, 0), QPointF(14, 0))
            painter.drawLine(QPointF(-9, 6), QPointF(9, 6))
            painter.drawLine(QPointF(-4, 12), QPointF(4, 12))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            painter.setPen(QColor("#5C6460"))
            painter.drawText(
                QRectF(-25, 14, 50, 16), Qt.AlignmentFlag.AlignCenter, "GND (0V)"
            )
            return

        if self.orientacion == "H":
            painter.drawLine(QPointF(-46, 0), QPointF(-26, 0))
            painter.drawLine(QPointF(26, 0), QPointF(46, 0))
        else:
            painter.drawLine(QPointF(0, -46), QPointF(0, -26))
            painter.drawLine(QPointF(0, 26), QPointF(0, 46))

        if self.tipo_catalogo == "RESISTENCIA":
            if self.orientacion == "H":
                painter.drawRect(QRectF(-26, -10, 52, 20))
            else:
                painter.drawRect(QRectF(-10, -26, 20, 52))

        elif self.tipo_catalogo == "FUENTE_VOLTAJE":
            painter.drawEllipse(QPointF(0, 0), 24, 24)
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            if self.orientacion == "H":
                painter.drawText(QRectF(-20, -10, 16, 20), Qt.AlignmentFlag.AlignCenter, "+")
                painter.drawText(QRectF(4, -10, 16, 20), Qt.AlignmentFlag.AlignCenter, "−")
            else:
                painter.drawText(QRectF(-10, -21, 20, 18), Qt.AlignmentFlag.AlignCenter, "+")
                painter.drawText(QRectF(-10, 3, 20, 18), Qt.AlignmentFlag.AlignCenter, "−")

        elif self.tipo_catalogo == "FUENTE_CORRIENTE":
            painter.drawEllipse(QPointF(0, 0), 24, 24)
            if self.orientacion == "H":
                painter.drawLine(QPointF(-12, 0), QPointF(12, 0))
                painter.drawLine(QPointF(5, -5), QPointF(12, 0))
                painter.drawLine(QPointF(5, 5), QPointF(12, 0))
            else:
                painter.drawLine(QPointF(0, 12), QPointF(0, -12))
                painter.drawLine(QPointF(-5, -5), QPointF(0, -12))
                painter.drawLine(QPointF(5, -5), QPointF(0, -12))

        elif self.tipo_catalogo == "FUENTE_CCVS":
            rombo = QPolygonF(
                [
                    QPointF(0.0, -25.0),
                    QPointF(25.0, 0.0),
                    QPointF(0.0, 25.0),
                    QPointF(-25.0, 0.0),
                ]
            )
            painter.setBrush(QBrush(QColor("#F4FAF6")))
            painter.drawPolygon(rombo)
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            if self.orientacion == "H":
                painter.drawText(QRectF(-18, -9, 14, 18), Qt.AlignmentFlag.AlignCenter, "+")
                painter.drawText(QRectF(4, -9, 14, 18), Qt.AlignmentFlag.AlignCenter, "−")
            else:
                painter.drawText(QRectF(-9, -19, 18, 16), Qt.AlignmentFlag.AlignCenter, "+")
                painter.drawText(QRectF(-9, 3, 18, 16), Qt.AlignmentFlag.AlignCenter, "−")

        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#212529"))
        if self.orientacion == "H":
            painter.drawText(
                QRectF(-45, -34, 90, 18), Qt.AlignmentFlag.AlignCenter, self.id_ref
            )
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#5C6460"))
            painter.drawText(
                QRectF(-50, 14, 100, 18),
                Qt.AlignmentFlag.AlignCenter,
                f"{self.valor_str} {self.unidad_simbolo}",
            )
        else:
            painter.drawText(
                QRectF(26, -18, 48, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self.id_ref,
            )
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#5C6460"))
            painter.drawText(
                QRectF(26, 0, 56, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{self.valor_str} {self.unidad_simbolo}",
            )
