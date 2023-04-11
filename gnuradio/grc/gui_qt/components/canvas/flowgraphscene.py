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
import sys

from PyQt6 import QtGui, QtCore, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal

from itertools import count

from ....core.base import Element
from ... import base 
from .connection import Connection
from .RubberBand import RubberBand
from ....core.FlowGraph import FlowGraph as CoreFlowgraph
#from .. import MoveAction
from ..undoable_actions import MoveAction
from ... import Constants
#from . import Port how to make this import work? incompletely initialized initialization sequence

log = logging.getLogger(__name__)



class FlowgraphScene(QtWidgets.QGraphicsScene, base.Component, CoreFlowgraph):

    itemMoved = pyqtSignal([QtCore.QPointF])
    flowgraph_changed = pyqtSignal()
    newElement = pyqtSignal([Element])
    deleteElement = pyqtSignal([Element])
    blockPropsChange = pyqtSignal([Element])


    def __init__(self):
        super(FlowgraphScene, self).__init__()
        self.parent = self.platform
        self.parent_platform = self.platform
        CoreFlowgraph.__init__(self, self.platform)
        self.isPanning    = False
        self.mousePressed = False
        
        self.rubberband = None
        self.startPort = None

        self.undoStack = QtGui.QUndoStack()
        self.undoAction = self.undoStack.createUndoAction(self, "Undo")
        self.redoAction = self.undoStack.createRedoAction(self, "Redo")

        self.dirty = False  # flag for flowgraph has changed has to be saved on close
        self.clickPos = None
        

    def update(self):
        """
        Call the top level rewrite and validate.
        Call the top level create labels and shapes.  
        """
        log.debug("FGS: update")
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
        log.debug("drag enter")
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

    def selected_connections(self):
        conns = []
        for item in self.selectedItems():
            if item.is_connection:
                conns.append(item)
        return conns

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
        log.debug("Scene: register block move")
        # We need to pass the clicked block here because
        # it hasn't been registered as selected yet
        #log.debug("register block move scene")
        for block in self.selected_blocks() + [clicked_block]:
            block.registerMoveStarting()

    def registerMoveCommand(self, block):
        log.debug("Scene: register move")
        ts = datetime.datetime.now().timestamp()
        log.debug('fr{} move_cmd '.format(ts))
        for block in self.selected_blocks():
            block.registerMoveEnding()
        moveCommand = MoveAction(self, self.selected_blocks())
        self.undoStack.push(moveCommand)
        self.app.MainWindow.updateActions()


    def _createElement(self, new_con):
        self.add_element(new_con)
        self.newElement.emit(new_con)
        self.update()
        return True

    def mousePressEvent(self,  event):
        log.debug("Scene: mouse press")
        item = self.itemAt(event.scenePos(), QtGui.QTransform())
        selected = self.selectedItems()
        self.movingThings = False
        if item:
            if item.is_block:
                self.movingThings = True
        self.clickPos = event.scenePos()
        conn_made = False
        if item:
            if item.is_port:
                 if len(selected) == 1:
                     if selected[0].is_port and selected[0] != item:
                        if selected[0].is_source and item.is_sink:
                            log.debug("Creating connection: source -> sink")
                            new_con = Connection(self, selected[0], item)
                            conn_made = self._createElement(new_con)
                        elif selected[0].is_sink and item.is_source:
                            log.debug("Created connection (click): sink <- source")
                            new_con = Connection(self, item, selected[0])
                            conn_made = self._createElement(new_con)
                        else:
                            log.debug("Could not determine source or sink. Not connected")
                            conn_made = False

                 if not conn_made:
                    self.startPort = item  # can we prevent creating rubberband when single click?
                ##NEW    if item.is_source:
                ##NEW         self.newConnection = ConnectionArrow(self, item.connection_point, event.scenePos())
                ##NEW         self.newConnection.setPen(QtGui.QPen(1))
                ##NEW         self.addItem(self.newConnection)

            #if item.is_port:   # this prepares a temporary line drawn from source to sink before actually drawing the connection. Just a common convinience
                    #self.startPort = item
                    log.debug("mouse start: " +str(event.scenePos()))
                    self.rubberband = RubberBand(event)
                    self.addItem(self.rubberband)
                    log.debug('Scene: clicked a port')
        if event.button() == Qt.MouseButton.LeftButton:
            log.debug("Scene: mouse press forwarded")
            self.mousePressed = True
            super(FlowgraphScene, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        #ts = datetime.datetime.now().timestamp()
        log.debug('Scene: mouse move')

        if self.rubberband:
            log.debug("move end point: " + str(event.scenePos()))
            self.rubberband.update(event)

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
        log.debug("Scene: mouse release ")
        if self.rubberband:
            log.debug("Scene: mouse release 1")
            items = list(filter(lambda x : isinstance(x, Element), self.items(event.scenePos())))
            if len(items) == 1:
                item = items[0]
                log.debug("Scene: mouse release 2")
                if item.is_port and item != self.startPort:
                    if (item.is_sink and self.startPort.is_source) or (item.is_source and self.startPort.is_sink): 
                        log.debug("Connecting two ports")
                        connectionPath = Connection(self, self.startPort, item)
                        self.connections.add(connectionPath)
                        self.update()
                    else:
                        log.debug("Can't connect in->in/out->out")
            self.removeItem(self.rubberband)   
            self.rubberband = None
            log.debug('rubberband destroyed')
        else:
            log.debug("Scene: mouse release 3")
            if self.clickPos != event.scenePos():
                log.debug("Scene: mouse release 4")
                if self.movingThings:
                    log.debug("Scene: mouse release 5")
                    self.itemMoved.emit(event.scenePos() - self.clickPos)
            
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
        log.debug("Scene: mouse release 6")
        super(FlowgraphScene, self).mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event): # Will be used to open up dialog box of a block
        log.debug("Scene: mouse double click")
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
        log.debug("Scene: Creating menus")

    def createToolbars(self, actions, toolbars):
        log.debug("Scene: Creating toolbars")


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

    def add_element(self, element):
        #super(CoreFlowgraph, self).add_element(element) # does not exist in flowgraph (even in original)
        self.addItem(element)

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





    def copy_to_clipboard(self):
        """
        Copy the selected blocks and connections into the clipboard.

        Returns:
            the clipboard
        """
        # get selected blocks
        blocks = list(self.selected_blocks())
        if not blocks:
            return None
        # calc x and y min
        x_min, y_min = blocks[0].states['coordinate']
        for block in blocks:
            x, y = block.states['coordinate']
            x_min = min(x, x_min)
            y_min = min(y, y_min)
        # get connections between selected blocks
        connections = list(filter(
            lambda c: c.source_block in blocks and c.sink_block in blocks,
            self.connections,
        ))
        clipboard = (
            (x_min, y_min),
            [block.export_data() for block in blocks],
            [connection.export_data() for connection in connections],
        )
        return clipboard

    
    def paste_from_clipboard(self, clipboard):
        """
        Paste the blocks and connections from the clipboard.

        Args:
            clipboard: the nested data of blocks, connections
        """
        self.clearSelection()
        (x_min, y_min), blocks_n, connections_n = clipboard
        '''
        # recalc the position
        scroll_pane = self.drawing_area.get_parent().get_parent()
        h_adj = scroll_pane.get_hadjustment()
        v_adj = scroll_pane.get_vadjustment()
        x_off = h_adj.get_value() - x_min + h_adj.get_page_size() / 4
        y_off = v_adj.get_value() - y_min + v_adj.get_page_size() / 4

        if len(self.get_elements()) <= 1:
            x_off, y_off = 0, 0
        '''
        x_off, y_off = 10, 10

        # create blocks
        pasted_blocks = {}
        for block_n in blocks_n:
            block_key = block_n.get('id')
            if block_key == 'options':
                continue

            block_name = block_n.get('name')
            # Verify whether a block with this name exists before adding it
            if block_name in (blk.name for blk in self.blocks):
                block_n = block_n.copy()
                block_n['name'] = self._get_unique_id(block_name)

            block = self.new_block(block_key)
            if not block:
                continue  # unknown block was pasted (e.g. dummy block)

            block.import_data(**block_n)
            pasted_blocks[block_name] = block  # that is before any rename

            block.moveBy(x_off, y_off)
            self.addItem(block)
            block.moveToTop()
            block.setSelected(True)
            '''
            while any(Utils.align_to_grid(block.states['coordinate']) == Utils.align_to_grid(other.states['coordinate'])
                      for other in self.blocks if other is not block):
                block.moveBy(Constants.CANVAS_GRID_SIZE,
                           Constants.CANVAS_GRID_SIZE)
                # shift all following blocks
                x_off += Constants.CANVAS_GRID_SIZE
                y_off += Constants.CANVAS_GRID_SIZE
            '''

        # update before creating connections
        self.update()
        # create connections
        for src_block, src_port, dst_block, dst_port in connections_n:
            source = pasted_blocks[src_block].get_source(src_port)
            sink = pasted_blocks[dst_block].get_sink(dst_port)
            connection = self.connect(source, sink)
            connection.setSelected(True)


