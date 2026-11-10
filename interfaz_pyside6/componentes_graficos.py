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
    QFontMetricsF,
    QPainter,
    QPainterPath,
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
        self.voltaje_nodo: Optional[float] = None
        self.resaltado_nodo = False

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

    def boundingRect(self) -> QRectF:
        # La etiqueta se dibuja fuera de la línea; Qt debe repintar esa zona también.
        margen = max(20.0, self._ancho_etiqueta() / 2 + 2)
        return super().boundingRect().adjusted(-margen, -22, margen, 4)

    def _ancho_etiqueta(self) -> float:
        return max(36.0, QFontMetricsF(QFont("Segoe UI", 8, QFont.Weight.Bold)).horizontalAdvance(self._texto_etiqueta()) + 14)

    def _texto_etiqueta(self) -> str:
        if self.voltaje_nodo is None:
            return self.etiqueta_nodo
        return f"{self.etiqueta_nodo} · {self.voltaje_nodo:.4g} V".replace('.', ',')

    def establecer_voltaje(self, voltaje: Optional[float]) -> None:
        if self.voltaje_nodo != voltaje:
            self.prepareGeometryChange()
            self.voltaje_nodo = voltaje
            self.update()

    def establecer_etiqueta(self, texto: str) -> None:
        if texto != self.etiqueta_nodo:
            self.prepareGeometryChange()
            self.etiqueta_nodo = texto
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
        color = QColor("#087b68") if self.resaltado_nodo else (QColor("#D9534F") if self.isSelected() else QColor("#49504C"))
        painter.setPen(QPen(color, 4.0 if self.resaltado_nodo else (2.8 if self.isSelected() else 2.2),
                            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(self.line())

        if self.etiqueta_nodo:
            linea = self.line()
            punto_medio = linea.center()
            painter.save()
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            ancho = self._ancho_etiqueta()
            rect_badge = QRectF(punto_medio.x() - ancho / 2, punto_medio.y() - 19, ancho, 17)
            painter.setPen(QPen(QColor("#DCE1DD"), 1.0))
            painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
            painter.drawRoundedRect(rect_badge, 4, 4)
            painter.setPen(
                QColor("#2E6F46") if self.etiqueta_nodo != "GND" else QColor("#495057")
            )
            painter.drawText(rect_badge, Qt.AlignmentFlag.AlignCenter, self._texto_etiqueta())
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
        self.factor_unidad: float = 1.0
        self.orientacion: str = orientacion
        self.componente_control_ref: str = componente_control_ref

        self.voltaje_lectura: str = "—"
        self.corriente_lectura: str = "—"
        self.potencia_lectura: str = "—"
        self.corriente_animacion = 0.0
        self.fase_animacion = 0.0

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
        ancho = self._ancho_etiquetas()
        if self.orientacion == "H":
            margen = max(55.0, ancho / 2 + 4)
            return QRectF(-margen, -52, 2 * margen, 104)
        return QRectF(-55, -52, 87 + ancho, 104)

    def _ancho_etiquetas(self) -> float:
        nombre = QFontMetricsF(QFont("Segoe UI", 9, QFont.Weight.Bold)).horizontalAdvance(self.id_ref)
        valor = QFontMetricsF(QFont("Segoe UI", 8)).horizontalAdvance(
            f"{float(self.valor_str) / self.factor_unidad:g} {self.unidad_simbolo}"
        )
        return max(55.0, nombre, valor) + 8

    def shape(self) -> QPainterPath:
        forma = QPainterPath()
        forma.addRect(QRectF(-30, -30, 60, 60))
        return forma

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

    def mouseDoubleClickEvent(self, event) -> None:
        if self.scene() and hasattr(self.scene(), "componente_doble_clic"):
            self.scene().componente_doble_clic.emit(self.id_ref)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.scene() and hasattr(self.scene(), "antes_de_cambio"):
            self.scene().antes_de_cambio.emit()
        super().mousePressEvent(event)

    def alternar_orientacion(self) -> None:
        if self.tipo_catalogo == "TIERRA":
            return
        if self.scene() and hasattr(self.scene(), "antes_de_cambio"):
            self.scene().antes_de_cambio.emit()
        self.prepareGeometryChange()
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
            painter.drawRoundedRect(QRectF(-51, -34, 102, 68), 8, 8)

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
                painter.drawLine(QPointF(0, -12), QPointF(0, 12))
                painter.drawLine(QPointF(-5, 5), QPointF(0, 12))
                painter.drawLine(QPointF(5, 5), QPointF(0, 12))

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
        ancho_etiqueta = self._ancho_etiquetas()
        if self.orientacion == "H":
            painter.drawText(
                QRectF(-ancho_etiqueta / 2, -34, ancho_etiqueta, 18), Qt.AlignmentFlag.AlignCenter, self.id_ref
            )
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#5C6460"))
            painter.drawText(
                QRectF(-ancho_etiqueta / 2, 14, ancho_etiqueta, 18),
                Qt.AlignmentFlag.AlignCenter,
                f"{float(self.valor_str) / self.factor_unidad:g} {self.unidad_simbolo}",
            )
        else:
            painter.drawText(
                QRectF(32, -18, ancho_etiqueta, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self.id_ref,
            )
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#5C6460"))
            painter.drawText(
                QRectF(32, 0, ancho_etiqueta, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{float(self.valor_str) / self.factor_unidad:g} {self.unidad_simbolo}",
            )

        # Marcador esquemático: el sentido sigue el signo de la corriente calculada.
        if abs(self.corriente_animacion) > 1e-12:
            avance = self.fase_animacion if self.corriente_animacion > 0 else 1 - self.fase_animacion
            painter.setPen(QPen(QColor("#087b68"), 1.8))
            painter.setBrush(QColor("#087b68"))
            sentido = 1 if self.corriente_animacion > 0 else -1
            if self.orientacion == "H":
                x = -40 + 80 * avance
                painter.drawLine(QPointF(x - 5 * sentido, 12), QPointF(x + 5 * sentido, 12))
                painter.drawPolygon(QPolygonF([QPointF(x + 6 * sentido, 12), QPointF(x + 1 * sentido, 8), QPointF(x + 1 * sentido, 16)]))
            else:
                y = -40 + 80 * avance
                painter.drawLine(QPointF(-15, y - 5 * sentido), QPointF(-15, y + 5 * sentido))
                painter.drawPolygon(QPolygonF([QPointF(-15, y + 6 * sentido), QPointF(-19, y + sentido), QPointF(-11, y + sentido)]))
