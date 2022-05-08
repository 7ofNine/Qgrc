# third-party modules
import logging

from PyQt6 import QtGui, QtCore, QtWidgets
from PyQt6.QtCore import Qt

from ....core.Connection import Connection as CoreConnection
from . import colors
from ...Constants import (
    CONNECTOR_ARROW_BASE,
    CONNECTOR_ARROW_HEIGHT
)

log = logging.getLogger(__name__)

class Connection(CoreConnection, QtWidgets.QGraphicsPathItem):

    def __init__(self, parent, source, sink):
        CoreConnection.__init__(self, parent, source, sink)
        QtWidgets.QGraphicsItem.__init__(self)
        log.debug("create Connection object")
        parent.addItem(self)

        self.source = source
        self.sink = sink

        #self._line = QtCore.QLineF(source.scenePos(), sink.scenePos())
        self._line = QtGui.QPainterPath()
        self._arrowhead = QtGui.QPainterPath()
        self._path = QtGui.QPainterPath()
        self.updateLine()

        #self._line_width_factor = 1.0
        #self._color1 = self._color2 = None

        #self._current_port_rotations = self._current_coordinates = None

        #self._rel_points = None  # connection coordinates relative to sink/source
        #self._arrow_rotation = 0.0  # rotation of the arrow in radians
        #self._current_cr = None  # for what_is_selected() of curved line
        #self._line_path = None
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

        #temporary
        #pathPen = QtGui.QPen()
        #pathPen.setColor(QtGui.QColor(0x61, 0x61, 0x61))
        #pathPen.setWidth(2)
        #self.setPen(pathPen)

    def updateLine(self):
        self.startPoint = self.source.getConnectionPoint()
        self.endPoint =self.sink.getConnectionPoint()
        self._line.clear()
        self._line.moveTo(self.startPoint)
        c1 = self.startPoint + QtCore.QPointF(200, 0)
        c2 = self.endPoint - QtCore.QPointF(200, 0)
        self._line.cubicTo(c1, c2, self.endPoint)

        self._arrowhead.clear()
        self._arrowhead.moveTo(self.endPoint)
        self._arrowhead.lineTo(self.endPoint + QtCore.QPointF(-CONNECTOR_ARROW_HEIGHT, -CONNECTOR_ARROW_BASE/2))
        self._arrowhead.lineTo(self.endPoint + QtCore.QPointF(-CONNECTOR_ARROW_HEIGHT, CONNECTOR_ARROW_BASE/2))
        self._arrowhead.lineTo(self.endPoint)

        self._path.clear()
        self._path.addPath(self._line)
        self._path.addPath(self._arrowhead)
        self.setPath(self._path)

    def paint(self, painter, option, widget):

        log.debug("paint Connection object")
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        pen = QtGui.QPen()
        if self.isSelected():
            pen.setColor(colors.HIGHLIGHT_COLOR)
        elif not self.enabled:
            pen.setColor(colors.CONNECTION_DISABLED_COLOR)
        elif not self.is_valid():
            pen.setColor(colors.CONNECTION_ERROR_COLOR)
        else:
            pen.setColor(QtGui.QColor(0x61, 0x61, 0x61))

        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawPath(self._path)

        if self.isSelected():
            painter.setBrush(colors.HIGHLIGHT_COLOR)
        elif not self.enabled:
            painter.setBrush(colors.CONNECTION_DISABLED_COLOR)
        elif not self.is_valid():
            painter.setBrush(colors.CONNECTION_ERROR_COLOR)
        else:
            painter.setBrush(QtGui.QColor(0x61, 0x61, 0x61))

        painter.drawPath(self._arrowhead)

    def mouseDoubleClickEvent(self, e):
        self.parent.connections.remove(self)
        self.parent.removeItem(self)

