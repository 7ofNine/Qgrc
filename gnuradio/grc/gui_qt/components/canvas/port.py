"""
Copyright 2007, 2008, 2009 Free Software Foundation, Inc.
This file is part of GNU Radio

SPDX-License-Identifier: GPL-2.0-or-later

"""
import logging
import datetime

import math

from PyQt6 import QtGui, QtCore, QtWidgets
from PyQt6.QtCore import Qt

from . import colors
from ... import Constants
from ....core.utils.descriptors import nop_write
from ....core.ports import Port as CorePort

log = logging.getLogger(__name__)
class Port(QtWidgets.QGraphicsItem, CorePort):
    """The graphical port."""

    @classmethod
    def make_cls_with_base(cls, super_cls):
        name = super_cls.__name__
        bases = (super_cls,) + cls.__bases__[:-1]
        namespace = cls.__dict__.copy()
        return type(name, bases, namespace)

    def __init__(self, parent, direction, **n):
        """
        Port constructor.
        """
        #log.debug("port({}): construct {} port".format(parent.key, direction))

        self._parent = parent
        super(self.__class__, self).__init__(parent, direction, **n)
        QtWidgets.QGraphicsItem.__init__(self)
        self.create_shapes()

        #self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges)  # still a problem unknown how to solve it with sink connection point

        self._border_color = self._bg_color = colors.BLOCK_ENABLED_COLOR
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemStacksBehindParent)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

    #def itemChange(self, change, value):    # temporary disabled gets invoked when setFlag above is called and fails ! in calling up the hierarchy?
    #    if self._dir == "sink":
    #        self.connection_point = self.scenePos() + QtCore.QPointF(0.0, self.height / 2.0)
    #    else:
    #        self.connection_point = self.scenePos() + QtCore.QPointF(15.0, self.height / 2.0)
    #    for conn in self.connections():
    #        conn.updateLine()
    #    return QtWidgets.QGraphicsLineItem.itemChange(self, change, value)

    def create_shapes(self):
        """Create new areas and labels for the port."""
        #log.debug("port({}), {}: create shapes".format(self.parent.key, self.name))
        
        self.height = 15.0 #currently font height +3
        fm = QtGui.QFontMetrics(QtGui.QFont('Helvetica', 8))
        self.width = max(15.0, fm.horizontalAdvance(self.name) * 1.5)
        log.debug("port name: {}".format(self.name))
        if self._dir == "sink":
            self.connection_point = QtCore.QPointF(-self.width/2 + 2, self.height / 2.0)                       # determine connection point for port
        else:
            self.connection_point = QtCore.QPointF(self.width, self.height / 2.0)
        #log.debug("port height = {}, width = {}".format(self.height, self.width))
        #log.debug("port {} direction {} connection point{}".format(self.name, self._dir, self.connection_point))

        self.text_rectangle = {"sink":QtCore.QRectF(-max(0, self.width - 15), 0, self.width, 15), "source":QtCore.QRectF(0, 0, self.width, 15)}  # define text rectangle

    def create_labels(self, cr=None):
        """Create the labels for the socket."""
        #log.debug("port: create labels: NOP ")
        pass


    def create_shapes_and_labels(self):
        #log.debug("port({}): create_shapes_and_labels ".format(self.parent.key))
        if not self.parentItem():                   # that is already done earlier after port creation. remove
            self.setParentItem(self.parent_block)
        #self.create_shapes()   # moved to paint?
        self._update_colors()

    def _update_colors(self):
        """
        Get the color that represents this port's type.
        Codes differ for ports where the vec length is 1 or greater than 1.
        Returns:
            a QColor object.
        """
        #log.debug("port: update colors")
        if not self.parent.enabled:
            #self._font_color[-1] = 0.4
            color = colors.BLOCK_DISABLED_COLOR
        elif self.domain == Constants.GR_MESSAGE_DOMAIN:
            color = colors.PORT_TYPE_TO_COLOR.get('message')
        else:
            #self._font_color[-1] = 1.0
            color = colors.PORT_TYPE_TO_COLOR.get(self.dtype) or colors.PORT_TYPE_TO_COLOR.get('')
            if self.vlen > 1:
                dark = (0, 0, 30 / 255.0, 50 / 255.0, 70 / 255.0)[min(4, self.vlen)]
                #color = tuple(max(c - dark, 0) for c in color)
        self._bg_color = color
        self._border_color = color

        #self._border_color = tuple(max(c - 0.3, 0) for c in color)

    def boundingRect(self):
        #log.debug('br{} bounding'.format(ts))
        
        return self.text_rectangle[self._dir]

    def getConnectionPoint(self):
        #log.debug("port{}: get connection point".format(self.parent.key))
        #log.debug("block {} position on scene: {}".format(self.parent.key, str(self.parent.pos())))
        #log.debug("block {} height = {}, width = {}".format(self.parent.key,self.parent.height, self.parent.width))
        temp = self.mapToScene(self.connection_point)
        #log.debug("port({}): connection point position on scene: {}".format(self.parent.key, str(temp)))
        #log.debug("port({}): size. height = {}, width = {}".format(self.parent.key,self.height, self.width))
        return temp
        #return self.mapToScene(self.connection_point)

    def paint(self, painter, option, widget):
        """
        Draw the port with a label.
        """
        #log.debug(f"port: paint port {self.parent.key}")
        if self.hidden:
            return
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        pen = QtGui.QPen(self._border_color)
        painter.setPen(pen)
        painter.setBrush(QtGui.QBrush(self._bg_color))

        painter.drawRect(self.text_rectangle[self._dir])

        painter.setPen(QtGui.QPen(QtCore.Qt.PenStyle.SolidLine))
        font = QtGui.QFont('Helvetica', 8)
        painter.setFont(font)
        
        # would using a graphicstextitem avoid all these rotations?? (except for 2 values, where it has to be mirrored by 180)
        painter.save()

        self.rotate_painter(painter, self.text_rectangle[self._dir])

        painter.drawText(self.text_rectangle[self._dir], Qt.AlignmentFlag.AlignCenter, self.name)   # write port name

        painter.restore()

    def rotate_painter(self, painter, rectangle):

        painter.translate(rectangle.center())
            
        rotation_modulus = self.parent.rotation()%360.0
        if rotation_modulus in {90.0, 180.0}:                                                  
            painter.setTransform(QtGui.QTransform().rotate(180.0), combine = True)
    
        painter.translate(- rectangle.center())
