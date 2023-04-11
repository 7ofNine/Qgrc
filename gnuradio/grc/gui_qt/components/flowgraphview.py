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

# Third-party modules
import logging
import datetime;

from PyQt6 import QtGui, QtCore, QtWidgets
from PyQt6.QtCore import Qt

from .. import base
from .canvas import FlowgraphScene 


log = logging.getLogger(__name__)

DEFAULT_MAX_X = 1280   # how does this relate to the FlowgraphScene ?
DEFAULT_MAX_Y = 1024


class FlowgraphView(QtWidgets.QGraphicsView, base.Component): # added base.Component so it can see platform
    def __init__(self, parent, filename=None):
        super(FlowgraphView, self).__init__()
        self.setParent(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)

        self.flowgraphScene = FlowgraphScene()
        self.scalefactor = 1.0

        #if filename is not None:
        #    self.readFile(filename)
        #else:
        self.initEmpty()

        self.setScene(self.flowgraphScene) # set scene in GraphicsView
        
        self.setBackgroundBrush(QtGui.QBrush(Qt.GlobalColor.white))

        self.isPanning    = False
        self.mousePressed = False
        


        '''
        QGraphicsView.__init__(self, flow_graph, parent)
        self._flow_graph = flow_graph

        self.setFrameShape(QFrame.NoFrame)
        self.setRenderHints(QPainter.Antialiasing |
                            QPainter.SmoothPixmapTransform)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setSceneRect(0, 0, self.width(), self.height())

        self._dragged_block = None

        #ToDo: Better put this in Block()
        #self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        #self.addActions(parent.main_window.menuEdit.actions())
        '''


    def createActions(self, actions):
        log.debug("Creating actions")

        '''
        # File Actions
        actions['save'] = Action(Icons("document-save"), _("save"), self,
                                shortcut=Keys.New, statusTip=_("save-tooltip"))

        actions['clear'] = Action(Icons("document-close"), _("clear"), self,
                                         shortcut=Keys.Open, statusTip=_("clear-tooltip"))
        '''

    def createMenus(self, actions, menus):
        log.debug("Creating menus")

    def createToolbars(self, actions, toolbars):
        log.debug("Creating toolbars")

    #def readFile(self, filename):
    #    tree = ET.parse(filename)
    #    root = tree.getroot()
    #    blocks = {}

    #    for xml_block in tree.findall('block'):
    #        attrib = {}
    #        params = []
    #        block_key = xml_block.find('key').text

    #        for param in xml_block.findall('param'):
    #            key = param.find('key').text
    #            value = param.find('value').text
    #            if key.startswith('_'):
    #                attrib[key] = literal_eval(value)
    #            else:
    #                params.append((key, value))

    #        # Find block in tree so that we can pull out label
    #        try:
    #            block = self.platform.blocks[block_key]

    #            new_block = Block(block_key, block.label, attrib, params)
    #            self.scene.addItem(new_block)
    #        except:
    #            log.warning("Block '{}' was not found".format(block_key))

    #    # This part no longer works now that we are using a Scene with GraphicsItems, but I'm sure there's still some way to do it
    #    #bounds = self.scene.itemsBoundingRect()
    #    #self.setSceneRect(bounds)
    #    #self.fitInView(bounds)

    def initEmpty(self):
        pass 
        #self.setSceneRect(0,0,DEFAULT_MAX_X, DEFAULT_MAX_Y)

    def set_initial_state(self):
        self.flowgraphScene.set_initial_scene()
        self.centerOn(0, 0)
        

    def wheelEvent(self,  event):
        # TODO: Support multi touch drag and drop for scrolling through the view
        #if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
        if False:
            factor = 1.1

            if event.angleDelta().y() < 0:
                factor = 1.0 / factor

            new_scalefactor = self.scalefactor * factor

            if new_scalefactor > 0.25 and new_scalefactor < 2.5:
                self.scalefactor = new_scalefactor
                self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
                self.setResizeAnchor(QtWidgets.QGraphicsView.NoAnchor)

                oldPos = self.mapToScene(event.pos())

                self.scale(factor, factor)
                newPos = self.mapToScene(event.pos())

                delta = newPos - oldPos
                self.translate(delta.x(), delta.y())
        else:
            QtWidgets.QGraphicsView.wheelEvent(self, event)

    def mousePressEvent(self,  event):
        log.debug('View: mouse press')
        if event.button() == Qt.MouseButton.LeftButton:
            log.debug("mouse pressed view")
            self.mousePressed = True
            # This will pass the mouse move event to the scene
            super(FlowgraphView, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        log.debug('View: mouse move')
        if self.mousePressed and self.isPanning:
            newPos = event.pos()
            diff = newPos - self.dragPos
            self.dragPos = newPos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - diff.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - diff.y())
            event.accept()
        else:
            ts = datetime.datetime.now().timestamp()
            log.debug("mouse moved view {}".format(ts))

            # This will pass the mouse move event to the scene
            super(FlowgraphView, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        log.debug('View: mouse release')
        if event.button() == Qt.MouseButton.LeftButton:
            self.mousePressed = False
        super(FlowgraphView, self).mouseReleaseEvent(event)

    #def mouseDoubleClickEvent(self, event): # Will be used to open up dialog box of a block
    #    log.debug("view double click 1")
    #    pass


    def mouseDoubleClickEvent(self, event):
        log.debug('View: mouse double click')
        # This will pass the double click event to the scene
        super(FlowgraphView, self).mouseDoubleClickEvent(event)



    def keyPressEvent(self, event):
        super(FlowgraphView, self).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        super(FlowgraphView, self).keyPressEvent(event)



    '''
    def dragEnterEvent(self, event):
        key = event.mimeData().text()
        self._dragged_block = self._flow_graph.add_new_block(
            str(key), self.mapToScene(event.pos()))
        event.accept()

    def dragMoveEvent(self, event):
        if self._dragged_block:
            self._dragged_block.setPos(self.mapToScene(event.pos()))
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        if self._dragged_block:
            self._flow_graph.remove_element(self._dragged_block)
            self._flow_graph.removeItem(self._dragged_block)

    def dropEvent(self, event):
        self._dragged_block = None
        event.accept()
    '''

    def load_graph(self, filename):
        self.flowgraphScene.set_scene(filename)
    
    def save(self, filename):
        self.flowgraphScene.save(filename)

    def is_dirty(self):
        return self.flowgraphScene.is_dirty()

    def reset_dirty(self):
        self.flowgraphScene.reset_dirty()

    def get_filepath(self):
        return self.flowgraphScene.get_filepath()