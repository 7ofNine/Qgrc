# Copyright 2014-2022 Free Software Foundation, Inc.
# This file is part of GNU Radio
#
# GNU Radio Companion is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# GNU Radio Companion is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

import logging


from PyQt6 import QtGui, QtCore, QtWidgets


log = logging.getLogger(__name__)

class RubberBand(QtWidgets.QGraphicsLineItem):

    def __init__(self, event):
        log.debug('create Rubberband')
        super(RubberBand, self).__init__()

        self.setLine(QtCore.QLineF(event.scenePos(), event.scenePos()))
        linePen = QtGui.QPen(QtCore.Qt.PenStyle.DotLine)
        linePen.setColor(QtGui.QColor(255,0,0)) #temporary
        self.setPen(linePen)

    def update(self, event):
        log.debug(f"update end point: {str(event.scenePos())})")
        newLine = QtCore.QLineF(self.line().p1(), event.scenePos())
        self.setLine(newLine) #trigger scene update
