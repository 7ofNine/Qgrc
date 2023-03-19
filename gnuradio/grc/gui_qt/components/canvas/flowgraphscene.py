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
import datetime

from PyQt6 import QtGui, QtCore, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal

from itertools import count

from ....core.base import Element
from ... import base 
from .connection import Connection
from ....core.FlowGraph import FlowGraph as CoreFlowgraph
from ..undoable_actions import MoveCommand
from ... import Constants

log = logging.getLogger(__name__)



class FlowgraphScene(QtWidgets.QGraphicsScene, base.Component, CoreFlowgraph):

    flowgraph_changed = pyqtSignal()

    def __init__(self):
        super(FlowgraphScene, self).__init__()
        self.parent = self.platform
        self.parent_platform = self.platform
        CoreFlowgraph.__init__(self, self.platform)
        self.isPanning    = False
        self.mousePressed = False
        
        self.newConnection = None
        self.startPort = None

        self.undoStack = QtGui.QUndoStack()
        self.undoAction = self.undoStack.createUndoAction(self, "Undo")
        self.redoAction = self.undoStack.createRedoAction(self, "Redo")

        self.dirty = False  # flag for flowgraph has changed has to be saved on close


    def update(self):
        """
        Call the top level rewrite and validate.
        Call the top level create labels and shapes.  
        """
        
        self.rewrite()
        self.validate()
        for block in self.blocks:
            block.create_shapes_and_labels()

        if not self.dirty:
            self.flowgraph_changed.emit()   # emit flowgraphscene changed
        self.dirty = True
        #self.update_elements_to_draw()
        #self.create_labels()
        #self.create_shapes()

    def dragEnterEvent(self, event):
        log.debug("drop enter")
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        log.debug("drag move")
        if event.mimeData().hasUrls:
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def decode_data(self, bytearray):
        data = []
        item = {}
        ds = QtCore.QDataStream(bytearray)
        while not ds.atEnd():
            row = ds.readInt32()
            column = ds.readInt32()
            map_items = ds.readInt32()
            for i in range(map_items):
                key = ds.readInt32()
                value = QtCore.QVariant()
                ds >> value
                item[Qt.ItemDataRole(key)] = value
            data.append(item)
        return data
    
    def _get_unique_id(self, base_id=''):
        """
        Get a unique id starting with the base id.

        Args:
            base_id: the id starts with this and appends a count

        Returns:
            a unique id
        """
        block_ids = set(b.name for b in self.blocks)
        for index in count():
            block_id = '{}_{}'.format(base_id, index)
            if block_id not in block_ids:
                break
        return block_id

    def dropEvent(self, event):
        log.debug("scene: dropEvent")
        QtWidgets.QGraphicsScene.dropEvent(self, event)
        if event.mimeData().hasUrls:
            data = event.mimeData()
            if data.hasFormat('application/x-qabstractitemmodeldatalist'):
                bytearray = data.data('application/x-qabstractitemmodeldatalist')
                data_items = self.decode_data(bytearray)

                # Find block in tree so that we can pull out label
                block_key = data_items[0][QtCore.Qt.ItemDataRole.UserRole].value()
                block = self.platform.blocks[block_key]

                # Add block of this key at the cursor position
                cursor_pos = event.scenePos()

                # Pull out its params (keep in mind we still havent added the dialog box that lets you change param values so this is more for show)
                params = []
                for p in block.parameters_data: # block.parameters_data is a list of dicts, one per param
                    if 'label' in p: # for now let's just show it as long as it has a label
                        key = p['label']
                        value = p.get('default', '') # just show default value for now
                        params.append((key, value))

                # Tell the block where to show up on the canvas
                #attrib = {'coordinate':(cursor_pos.x(), cursor_pos.y())}
                coordinates = [cursor_pos.x(),cursor_pos.y()]
                id = self._get_unique_id(block_key)
                
                block = self.new_block(block_key)
                block.states['coordinate'] = coordinates
                block.setPos(cursor_pos.x(), cursor_pos.y())
                block.params['id'].set_value(id)
                self.addItem(block)
                block.moveToTop()
                self.update()

                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
            else:
                return QtGui.QStandardItemModel.dropMimeData(self, data, action, row, column, parent)
        else:
            event.ignore()

    def selected_blocks(self):
        blocks = []
        for item in self.selectedItems():
            if item.is_block:
                blocks.append(item)
        return blocks

    def delete_selected(self):
        for item in self.selectedItems():
            self.remove_element(item)

    def rotate_selected(self, rotation):
        """
        Rotate the selected blocks by multiples of 90 degrees.
        Args:
            rotation: the rotation in degrees
        Returns:
            true if changed, otherwise false.
        """
        selected_blocks = self.selected_blocks()
        if not any(selected_blocks):
            return False
        #initialize min and max coordinates
        min_x, min_y = max_x, max_y = selected_blocks[0].x(),selected_blocks[0].y()
        # rotate each selected block, and find min/max coordinate
        for selected_block in selected_blocks:
            selected_block.rotate(rotation)
            #update the min/max coordinate
            x, y = selected_block.x(),selected_block.y()
            min_x, min_y = min(min_x, x), min(min_y, y)
            max_x, max_y = max(max_x, x), max(max_y, y)
        #calculate center point of selected blocks
        ctr_x, ctr_y = (max_x + min_x)/2, (max_y + min_y)/2
        #rotate the blocks around the center point
        for selected_block in selected_blocks:
            x, y = selected_block.x(),selected_block.y()
            x, y = self.get_rotated_coordinate((x - ctr_x, y - ctr_y), rotation)
            selected_block.setPos(x + ctr_x, y + ctr_y)
        return True

    def registerBlockMovement(self, clicked_block):
        # We need to pass the clicked block here because
        # it hasn't been registered as selected yet
        #log.debug("register block move scene")
        for block in self.selected_blocks() + [clicked_block]:
            block.registerMoveStarting()

    def registerMoveCommand(self, block):
        #log.debug("register move command scene")
        ts = datetime.datetime.now().timestamp()
        log.debug('fr{} move_cmd '.format(ts))
        for block in self.selected_blocks():
            block.registerMoveEnding()
        moveCommand = MoveCommand(self, self.selected_blocks())
        self.undoStack.push(moveCommand)
        self.app.MainWindow.updateActions()

    def mousePressEvent(self,  event):
        log.debug("mouse pressed scene")
        item = self.itemAt(event.scenePos(), QtGui.QTransform())
        if item:
            if item.is_port:
                self.startPort = item
                log.debug("mouse start: " +str(event.scenePos()))
                self.newConnection = QtWidgets.QGraphicsLineItem(QtCore.QLineF(event.scenePos(), event.scenePos()))
                linePen = QtGui.QPen(QtCore.Qt.PenStyle.DotLine)
                linePen.setColor(QtGui.QColor(255,0,0)) #temporary
                self.newConnection.setPen(linePen)
                self.addItem(self.newConnection)
                print("clicked a port")
        if event.button() == Qt.MouseButton.LeftButton:
            #log.debug("mouse pressed forwarded scene")
            self.mousePressed = True
            super(FlowgraphScene, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        ts = datetime.datetime.now().timestamp()
        log.debug('mouse moved scene {}'.format(ts))

        if self.newConnection:
            log.debug("move end point: " + str(event.scenePos()))
            newConnection_ = QtCore.QLineF(self.newConnection.line().p1(), event.scenePos())
            self.newConnection.setLine(newConnection_)

        if self.mousePressed and self.isPanning:
            newPos = event.pos()
            diff = newPos - self.dragPos
            self.dragPos = newPos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - diff.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - diff.y())
            event.accept()
        else:
            itemUnderMouse = self.itemAt(event.pos(), QtGui.QTransform()) # the 2nd arg lets you transform some items and ignore others
            if  itemUnderMouse is not None:
                #~ print itemUnderMouse
                pass

            super(FlowgraphScene, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        log.debug("mouse released scene")
        if self.newConnection:
            item = self.itemAt(event.scenePos(), QtGui.QTransform())
            if isinstance(item, Element):
                if item.is_port and item != self.startPort:
                    log.debug("Connecting two ports")
                    self.connectionPath = Connection(self, self.startPort, item)
                    self.connections.add(self.connectionPath)
                    self.update()
            self.removeItem(self.newConnection)   #remove temporary straight line
            self.newConnection = None
            
        '''
        if event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                #self.setCursor(Qt.CursorShape.OpenHandCursor)
                pass
            else:
                self.isPanning = False
                #self.setCursor(Qt.CursorShape.ArrowCursor)
            self.mousePressed = False
        '''
        super(FlowgraphScene, self).mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event): # Will be used to open up dialog box of a block
        log.debug("scene double click")
        super(FlowgraphScene, self).mouseDoubleClickEvent(event)



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


    def import_data(self, data):
        super(FlowgraphScene, self).import_data(data)
        for block in self.blocks:
            self.addItem(block) 
        # where are the connections

    def getMaxZValue(self):
        z_values = []
        for block in self.blocks:
             z_values.append(block.zValue())
        return max(z_values)

    def remove_element(self, element):
        if element is not self.options_block:    # the options block can not be deleted
            self.removeItem(element)
            super(FlowgraphScene, self).remove_element(element)

    def select_all(self):
        """Select all blocks in the flow graph"""
        for item in self.items():
            item.setSelected(True)


    def get_rotated_coordinate(self, coor, rotation):
        """
        Rotate the coordinate by the given rotation.
        Args:
            coor: the coordinate x, y tuple
            rotation: the angle in degrees
        Returns:
            the rotated coordinates
        """
        # handles negative angles
        rotation = (rotation + 360) % 360
        if rotation not in Constants.POSSIBLE_ROTATIONS:
            raise ValueError('unusable rotation angle "%s"'%str(rotation))
        # determine the number of degrees to rotate
        cos_r, sin_r = {
            0: (1, 0), 90: (0, 1), 180: (-1, 0), 270: (0, -1),
        }[rotation]
        x, y = coor
        return x * cos_r + y * sin_r, -x * sin_r + y * cos_r

    def set_initial_scene(self):
        self.import_data(self.parent_platform.initial_graph())

    def set_scene(self, filename):
        self.import_data(self.parent_platform.parse_flow_graph(filename))
        self.grc_file_path = filename  #preserve file name

    def save(self, filename):
        self.parent_platform.save_flow_graph(self, filename)

    def is_dirty(self):
        return self.dirty

    def reset_dirty(self):
        self.dirty = False

    def get_filepath(self):
        return self.grc_file_path


