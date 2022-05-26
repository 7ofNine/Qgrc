# third-party modules
import logging
import datetime

from PyQt6 import QtGui, QtCore, QtWidgets
from PyQt6.QtCore import Qt

from ....core.connection import Connection as CoreConnection
from . import colors
from ...Constants import (
    CONNECTOR_ARROW_BASE,
    CONNECTOR_ARROW_HEIGHT,
    CONNECTOR_LINE_WIDTH,
)

log = logging.getLogger(__name__)

class Connection(CoreConnection, QtWidgets.QGraphicsPathItem):

    def __init__(self, parent, source, sink):
        log.debug("create Connection object")
        CoreConnection.__init__(self, parent, source, sink)
        QtWidgets.QGraphicsPathItem.__init__(self)

        self.source = source
        self.sink = sink
        
        #setup path objects
        self._line = QtGui.QPainterPath()
        self._arrowhead = QtGui.QPainterPath()
        self._path = QtGui.QPainterPath()
        
        #create the connection line
        self.update_connection_path()

        #self._line_width_factor = 1.0
        #self._color1 = self._color2 = None

        #self._current_port_rotations = self._current_coordinates = None

        #self._rel_points = None  # connection coordinates relative to sink/source
        #self._arrow_rotation = 0.0  # rotation of the arrow in radians
        #self._current_cr = None  # for what_is_selected() of curved line
        #self._line_path = None
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        parent.addItem(self)  
        #temporary
        #pathPen = QtGui.QPen()
        #pathPen.setColor(QtGui.QColor(0x61, 0x61, 0x61))
        #pathPen.setWidth(2)
        #self.setPen(pathPen)

    #create curved part of connection line
    def updateLine(self, path):

        self._line.clear()
        self._line.moveTo(self.startPoint)
        c1 = self.startPoint + QtCore.QPointF(200, 0)
        c2 = self.endPoint - QtCore.QPointF(200, 0)
        self._line.cubicTo(c1, c2, self.endPoint)
        path.addPath(self._line)
    
    # create connection path on flowgraph scene
    def update_connection_path(self):
        self._path.clear()
        self.update_endpoints()
        self.updateLine(self._path)
        self.update_arrowhead(self._path)
        self.setPath(self._path)
        
    # get colour according to state
    def get_connection_colour(self):
        
        if self.isSelected():
            return colors.HIGHLIGHT_COLOR
        elif not self.enabled:
            return colors.CONNECTION_DISABLED_COLOR
        elif not self.is_valid():
            return colors.CONNECTION_ERROR_COLOR
        else:
            return QtGui.QColor(0x61, 0x61, 0x61)

    
    # scene position of endpoints
    def update_endpoints(self):

        self.startPoint = self.source.getConnectionPoint()
        self.endPoint =self.sink.getConnectionPoint()

    # draw arrowhead at sink
    def update_arrowhead(self, path):

        self._arrowhead.clear()
        self._arrowhead.moveTo(self.endPoint)
        self._arrowhead.lineTo(self.endPoint + QtCore.QPointF(-CONNECTOR_ARROW_HEIGHT, -CONNECTOR_ARROW_BASE/2))    # this only allows sinks on the west/left side. needs extension for rotations
        self._arrowhead.lineTo(self.endPoint + QtCore.QPointF(-CONNECTOR_ARROW_HEIGHT, CONNECTOR_ARROW_BASE/2))     # TODO: enhance for rotation
        self._arrowhead.lineTo(self.endPoint)
        path.addPath(self._arrowhead)

    

    def paint(self, painter, option, widget):
        #ts = datetime.datetime.now().timestamp()
        log.debug("paint connection")

        self.update_connection_path()   # 
        #log.debug("paint Connection object")

        pen = QtGui.QPen()
        pen.setWidth(CONNECTOR_LINE_WIDTH)
        pen.setColor(self.get_connection_colour())
        
        painter.setPen(pen)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        painter.drawPath(self._line)    # draw line

        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)
        painter.setBrush(self.get_connection_colour())
        painter.drawPath(self._arrowhead) # draw arrowhead at sink   


    def mouseDoubleClickEvent(self, e):
        self.parent.connections.remove(self)
        self.parent.removeItem(self)

