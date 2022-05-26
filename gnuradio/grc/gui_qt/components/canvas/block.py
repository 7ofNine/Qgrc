from asyncio import constants
import logging
import datetime

# third-party modules
from PyQt6 import QtGui, QtCore, QtWidgets
from PyQt6.QtCore import Qt

from . import colors
from ... import Constants
from ....core.blocks.block import Block as CoreBlock

# Logging
log = logging.getLogger(__name__)

LONG_VALUE = 20  # maximum length of a param string.
                 # if exceeded, '...' will be displayed

class ParameterEdit(QtWidgets.QWidget):
    def __init__(self, label, value):
        super().__init__()
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.addWidget(QtWidgets.QLabel(label))
        edit = QtWidgets.QLineEdit(value)
        self.layout.addWidget(edit)

#TODO: Move this to a separate file
class PropsDialog(QtWidgets.QDialog):
    def __init__(self, parent_block):
        super().__init__()
        self.setMinimumSize(600, 400)
        self._block = parent_block

        self.setWindowTitle(f"Properties: {self._block.label}")

        categories = (p.category for p in self._block.params.values())

        def unique_categories():
            seen = {Constants.DEFAULT_PARAM_TAB}
            yield Constants.DEFAULT_PARAM_TAB
            for cat in categories:
                if cat in seen:
                    continue
                yield cat
                seen.add(cat)


        self.edit_params = []

        self.tabs = QtWidgets.QTabWidget()
        for cat in unique_categories():
            qvb = QtWidgets.QGridLayout()
            qvb.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
            qvb.setVerticalSpacing(5)
            qvb.setHorizontalSpacing(20)
            i = 0
            for param in self._block.params.values():
                if param.category == cat and param.hide != 'all':
                    qvb.addWidget(QtWidgets.QLabel(param.name), i, 0)
                    if param.dtype == "enum" or param.options:
                        dropdown = QtWidgets.QComboBox()
                        for opt in param.options.values():
                            dropdown.addItem(opt)
                        dropdown.param_values = list(param.options)
                        dropdown.param = param
                        qvb.addWidget(dropdown, i, 1)
                        self.edit_params.append(dropdown)
                        if param.dtype == "enum":
                            dropdown.setCurrentIndex(dropdown.param_values.index(param.get_value()))
                        else:
                            dropdown.setEditable(True)
                            value_label = param.options[param.value] if param.value in param.options else param.value
                            dropdown.setCurrentText(value_label)
                    else:
                        line_edit = QtWidgets.QLineEdit(param.value)
                        line_edit.param = param
                        if f'dtype_{param.dtype}' in colors.LIGHT_THEME_STYLES:
                            line_edit.setStyleSheet(colors.LIGHT_THEME_STYLES[f'dtype_{param.dtype}'])
                        qvb.addWidget(line_edit, i, 1)
                        self.edit_params.append(line_edit)
                    #qvb.addWidget(QtWidgets.QLabel("unit"), i, 2)
                i+=1
            tab = QtWidgets.QWidget()
            tab.setLayout(qvb)
            self.tabs.addTab(tab, cat)

        buttons = QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QtWidgets.QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.tabs)
        self.layout.addWidget(self.buttonBox)

        self.setLayout(self.layout)

    def accept(self):
        super().accept()
        for par in self.edit_params:
            if isinstance(par, QtWidgets.QLineEdit):
                par.param.set_value(par.text())
            else: # Dropdown/ComboBox
                for key, val in par.param.options.items():
                    if val == par.currentText():
                        par.param.set_value(key)
        self._block.parent.update()   # update the scene (colour changes for blocks and connections)
        #self._block.rewrite()
        #self._block.validate()
        #self._block.create_shapes_and_labels()


'''
class BlockTitle(QtWidgets.QLabel):
    def __init__(self, block_key):
        super(BlockTitle, self).__init__()

        title = block_key.replace('_', ' ').title()
        self.setText(title)
        title_font = QtGui.QFont("Sans Serif", 9, QtGui.QFont.Bold)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(title_font)
        self.setContentsMargins(5, 5, 5, 5)
        self.title_only = False
        self.color = QtGui.QColor(0xD0, 0xD0, 0xFF)

    def paintEvent(self, event):
        # handle paintEvent just enough to provide a (partial)
        # rounded rectangle around the title

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtGui.QPen(2))
        painter.setBrush(QtGui.QBrush(self.color))

        # set rounding to include bottom of title
        # otherwise, push the bottom of the rounded rectangle
        # outside of the widget window
        height = self.height()-1 if self.title_only else self.height()+ARC
        painter.drawRoundedRect(0, 0, self.width()-1, height, ARC, ARC);

        painter.end()

        # use the default handler for everything else
        super(BlockTitle, self).paintEvent(event)

    def boundingRect(self): # required to have
        return QRectF(self.x, self.y, self.current_width, 150) # same as the rectangle we draw

    def mouseReleaseEvent(self, e):
        super(Block, self).mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        print("DETECTED DOUBLE CLICK!")
        super(Block, self).mouseDoubleClickEvent(e)

class BlockParams(QtWidgets.QWidget):
    def __init__(self, params):
        super(BlockParams, self).__init__()
        self.params_only = False

        label_font = QtGui.QFont("Sans Serif",  8, QtGui.QFont.Bold)
        value_font = QtGui.QFont("Sans Serif",  8, QtGui.QFont.Normal)

        layout = QtWidgets.QGridLayout()
        layout.setSpacing(2)
        layout.setVerticalSpacing(0)
        layout.setContentsMargins(ARC, 3, ARC, ARC)
        for row, (key, value) in enumerate(params):
            if value is not None:
                param_label = QtWidgets.QLabel(key+': ')
                param_label.setAlignment(Qt.AlignmentFlag.AlignRight)
                param_label.setFont(label_font)

                if len(value) > LONG_VALUE:
                    value = value[:LONG_VALUE-3] + '...'
                param_value = QtWidgets.QLabel(value)
                param_value.setFont(value_font)

                layout.addWidget(param_label, row, 0)
                layout.addWidget(param_value, row, 1)

        self.setLayout(layout)

        self.setContentsMargins(0, 0, 0, 5)
        self.color = QtGui.QColor(0xFA, 0xF8, 0xE0)

    def paintEvent(self, event):
        # handle paintEvent just enough to provide a (partial)
        # rounded rectangle around the title

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setPen(QtGui.QPen(2))
        painter.setBrush(QtGui.QBrush(self.color))

        # set rounding to include top of title
        # otherwise, push the top of the rounded rectangle
        # outside of the widget window
        top = 1 if self.params_only else -ARC
        painter.drawRoundedRect(0, top, self.width()-1, self.height()-1, ARC, ARC);

        painter.end()

        # use the default handler for everything else
        super(BlockParams, self).paintEvent(event)
'''

class Block(QtWidgets.QGraphicsItem, CoreBlock):

    @classmethod
    def make_cls_with_base(cls, super_cls):
        name = super_cls.__name__
        bases = (super_cls,) + cls.__bases__[:-1]
        namespace = cls.__dict__.copy()
        return type(name, bases, namespace)

    def create_shapes_and_labels(self):                       # erroneous. we have to create ports first before we can determine the size of the block and not rely on the existence of the port height!!
        log.debug("block {}: create_shapes_and_labels".format(self.key))
        self.prepareGeometryChange()

        # figure out height of block based on how many params there are
        i = 30.0
        if self.is_dummy_block: #has predetermined number of lines. SHould be a constant
            i = 50.0
        else:
            for key, item in self.params.items():
                value = item.value
                if value is not None and item.hide == 'none':    # hide determines if the attribute is shown in the graphic representation. defined in corresponding *.yml file
                    i+= 20.0

        self.height = i

        def get_min_height_for_ports(ports):
            min_height = 2 * Constants.PORT_BORDER_SEPARATION + len(ports) * Constants.PORT_SEPARATION
            # If any of the ports are bus ports - make the min height larger
            if any([p.dtype == 'bus' for p in ports]):
                min_height = 2 * Constants.PORT_BORDER_SEPARATION + sum(
                    port.height + Constants.PORT_SPACING for port in ports if port.dtype == 'bus'
                    ) - Constants.PORT_SPACING

            else:
                if ports:
                    min_height -= ports[-1].height
            return min_height

        self.height = max(self.height,
                     get_min_height_for_ports(self.active_sinks),                  # what is an active sink/source vs. a sink/source?
                     get_min_height_for_ports(self.active_sources))

        # figure out width of block based on widest line of text                   # probaably can be combined with the height determination. single methods?
        labelFont, labelFontMetric = self.getLabelFont()
        largest_width = labelFontMetric.horizontalAdvance(self.label)   # length of the label

        nameFont, nameFontMetric = self.getNameFont() #should be calculated in a single location not twice! Define Constants for GUI. Configurable??
        valueFont, valueFontMetric = self.getValueFont()

        if self.is_dummy_block:          # has only two lines
            name = 'key'
            value_label = self.key
            labelWidth = nameFontMetric.horizontalAdvance(self.label)
            full_line_length = nameFontMetric.horizontalAdvance(name + ": ") + valueFontMetric.horizontalAdvance(value_label)
            largest_width = max(labelWidth, full_line_length)

        else:
            for key, item in self.params.items():
                name = item.name
                value = item.value
                value_label = item.options[value] if value in item.options else value
                if value is not None and item.hide == 'none':
                    full_line_length = nameFontMetric.horizontalAdvance(name + ": ") + valueFontMetric.horizontalAdvance(value_label)
                    if full_line_length > largest_width:
                        largest_width = float(full_line_length)

        self.width = largest_width + 15.0
        log.debug("block {} height = {}, width = {}".format(self.key, self.height, self.width))

        bussified = self.current_bus_structure['source'], self.current_bus_structure['sink']
        for ports, has_busses in zip((self.active_sources, self.active_sinks), bussified):
            if not ports:
                continue
            port_separation = Constants.PORT_SEPARATION if not has_busses else ports[0].height + Constants.PORT_SPACING
            offset = (self.height - (len(ports) - 1) * port_separation - ports[0].height) / 2
            for port in ports:
                if port._dir == "sink":
                    port.setPos(-15.0, offset)                      # is the position dependent on the size of the port??? Is that correct?
                else:
                    port.setPos(self.width, offset)                 # position with relation to its parents coordinates. Done in __init__
                
                log.debug("{} relative block position {}".format(port._dir, port.pos()))
                port.create_shapes_and_labels()                     # where are the ports created?. see above
                '''
                port.coordinate = {                                 # changes needed for rotation. Not implemented yet
                    0: (+self.width, offset),
                    90: (offset, -port.width),
                    180: (-port.width, offset),
                    270: (offset, +self.width),
                }[port.connector_direction]
                '''

                offset += Constants.PORT_SEPARATION if not has_busses else port.height + Constants.PORT_SPACING

        self._update_colors()
        self.create_port_labels()
        self.setTransformOriginPoint(self.width / 2, self.height / 2)   # set the origin for transformations. upper right corner?


    def create_port_labels(self):
        log.debug("block {}: create_port_labels".format(self.key))
        for ports in (self.active_sinks, self.active_sources):
            max_width = 0
            for port in ports:
                port.create_shapes_and_labels() # actually ony selects colour
                #max_width = max(max_width, port.width_with_label)
            #for port in ports:
            #    port.width = max_width


    #def __init__(self, block_key, block_label, attrib, params, parent):
    def __init__(self, parent, **n):
        log.debug("block {}: create".format(self.key))
        super(self.__class__, self).__init__(parent, **n) 
        
        #CoreBlock.__init__(self, parent)      # this fails with build-in blocks. Is there a way?
        QtWidgets.QGraphicsItem.__init__(self)
        

        for sink in self.sinks:                    # the ports are created in core.block via platform.make_port. What are different port classes? are they actually used??
            sink.setParentItem(self)               # make block parent of the ports. important for coordinates
        for source in self.sources:
            source.setParentItem(self)


        #self.__dict__.update(attrib)
        #self.params = params
        #self.x = attrib['_coordinate'][0]
        #self.y = attrib['_coordinate'][1]
        #self.x = 500
        #self.y = 300
        #try:
        #    self.coordinate = tuple(self.states['coordinate'])                         # this is useless. states does not have coordinate set, yet
        #except KeyError:
        #    self.coordinate = (500,300)
        #self.width = 300.0 # default shouldnt matter, it will change immedaitely after the first paint. also useless. why is it even set?
        #self.block_key = block_key
        #self.block_label = block_label
        self.block_label = self.key   # what is this good for??


        #x,y = self.coordinate
        #self.setPos(x, y)                                     # dummy position. Do we really need this? where is the actual position loaded from *.grc file?

        self.create_shapes_and_labels()   # shouldn't that be done before setting the position

        self.moving = False
        self.movingFrom = None
        self.movingTo = None

        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

    def _update_colors(self):
        def get_bg_color():
            """
            Get the background color for this block
            Explicit is better than a chain of if/else expressions,
            so this was extracted into a nested function.
            """
            if self.is_dummy_block:
                return colors.MISSING_BLOCK_BACKGROUND_COLOR
            if self.state == 'bypassed':
                return colors.BLOCK_BYPASSED_COLOR
            if self.state == 'enabled':
                if self.deprecated:
                    return colors.BLOCK_DEPRECATED_BACKGROUND_COLOR
                return colors.BLOCK_ENABLED_COLOR
            return colors.BLOCK_DISABLED_COLOR

        def get_border_color():
            """
            Get the border color for this block
            """
            if self.is_dummy_block:
                return colors.MISSING_BLOCK_BORDER_COLOR
            if self.deprecated:
                return colors.BLOCK_DEPRECATED_BORDER_COLOR
            if self.state == 'enabled':
                return colors.BORDER_COLOR
            return colors.BORDER_COLOR_DISABLED

        self._bg_color = get_bg_color()
        #self._font_color[-1] = 1.0 if self.state == 'enabled' else 0.4
        self._border_color = get_border_color()

    def getLabelFont(self):
        return self.getNameFont()

    def getNameFont(self):
        font = QtGui.QFont(Constants.BLOCK_FONT_FAMILY, Constants.BLOCK_FONT_SIZE)
        font.setBold(True)
        fm = QtGui.QFontMetrics(font)
        return font, fm

    def getValueFont(self):
        font = QtGui.QFont(Constants.BLOCK_FONT_FAMILY, Constants.BLOCK_FONT_SIZE)
        font.setBold(False)
        fm = QtGui.QFontMetrics(font)
        return font, fm


    def paint(self, painter, option, widget):                     #painting the ports is managed by the scene not by the port. the port is a child of block
        #log.debug("paint block {}".format(self.name))

        #log.debug("block {}: paint  ".format(self.name))
        #x,y = (self.x(), self.y())                                #where has x,y been set?somewhere when loading *grc. Why are there so many versions of the coordinates ahich are all the same ultimately
        #self.states['coordinate'] = (x,y)                         # the attributes x, y, the attribute coordinate, and states[coordinate]
        #log.debug("block {}: coordinates on scene {}".format(self.key, self.states['coordinate']))
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Draw main rectangle
        pen = QtGui.QPen(1)
        if self.isSelected():
            pen = QtGui.QPen(colors.HIGHLIGHT_COLOR)
        else:
            pen = QtGui.QPen(self._border_color)

        pen.setWidth(Constants.BLOCK_BORDER_WIDTH)
        painter.setPen(pen)

        painter.setBrush(QtGui.QBrush(self._bg_color))

        painter.drawRoundedRect(QtCore.QRectF(0.0, 0.0, self.width, self.height), Constants.BLOCK_ARC_RADIUS, Constants.BLOCK_ARC_RADIUS);
        painter.setPen(QtGui.QPen(1))

        nameFont, nameFontMetric = self.getNameFont()
        # Draw block label text
        painter.setFont(nameFont)
        if self.is_valid():
            painter.setPen(QtGui.QPen(1))
        else:
            painter.setPen(Qt.GlobalColor.red)
        painter.drawText(QtCore.QRectF(0.0, 0.0 - self.height/2 + 10.0, self.width, self.height), Qt.AlignmentFlag.AlignCenter, self.label)  # NOTE the 3rd/4th arg in  QRectF seems to set the bounding box of the text, so if there is ever any clipping, thats why


        # Draw param text
        y_offset = 30 # params start 30 down from the top of the box

        if self.is_dummy_block:  # only the key is shown
            name = 'key'
            value_label = self.key

            painter.setPen(QtGui.QPen(1))
            painter.setFont(nameFont)
            x_offset = 7.5
            painter.drawText(QtCore.QRectF(x_offset, 0 + y_offset, self.width, self.height), Qt.AlignmentFlag.AlignLeft, name + ': ')
            writtenWidth = nameFontMetric.horizontalAdvance(name + ": ")
            
            valueFont, valueFontMetric = self.getValueFont()
            painter.setFont(valueFont)
            x_offset += writtenWidth # advance to after the name
            painter.drawText(QtCore.QRectF(x_offset, 0 + y_offset, self.width, self.height), Qt.AlignmentFlag.AlignLeft, value_label)
            y_offset += 20
            return

        for key, item in self.params.items():
            name = item.name
            value = item.value
            value_label = item.options[value] if value in item.options else value
            if value is not None and item.hide == 'none':
                if item.is_valid():
                    painter.setPen(QtGui.QPen(1))
                else:
                    painter.setPen(Qt.GlobalColor.red)

                painter.setFont(nameFont)
                x_offset = 7.5
                painter.drawText(QtCore.QRectF(x_offset, 0 + y_offset, self.width, self.height), Qt.AlignmentFlag.AlignLeft, name + ': ')
                writtenWidth = nameFontMetric.horizontalAdvance(name + ": ")

                # change font for value
                valueFont, valueFontMetric = self.getValueFont()
                painter.setFont(valueFont)
                x_offset += writtenWidth # advance to after the name
                painter.drawText(QtCore.QRectF(x_offset, 0 + y_offset, self.width, self.height), Qt.AlignmentFlag.AlignLeft, value_label)
                y_offset += 20

    def boundingRect(self): # required to have
        x,y = (self.x(), self.y())
        self.states['coordinate'] = (x,y)
        return QtCore.QRectF(-2.5, -2.5, self.width+5, self.height+5) # margin to avoid artifacts

    def registerMoveStarting(self):
        #log.debug("register move starting block")
        self.moving = True
        self.movingFrom = self.pos()

    def registerMoveEnding(self):
        #log.debug("register move ending block")
        self.moving = False
        self.movingTo = self.pos()

    def mouseReleaseEvent(self, e):
        log.debug("block {} mouse release".format(self.key))
        if not self.movingFrom == self.pos():
            self.parent.registerMoveCommand(self)
        super(self.__class__, self).mouseReleaseEvent(e)

    def mousePressEvent(self, e):
        log.debug("block {} mouse pressed".format(self.key))
        self.parent.registerBlockMovement(self)
        try:
            self.parent.app.DocumentationTab.setText(self.documentation[''])
        except KeyError:
            pass

        self.moveToTop()
        log.debug("block {} mouse pressed forwarded, enabled {}".format(self.key, self.enabled))
        super(self.__class__, self).mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        log.debug(f"Block double click {self.name}")
        e.accept()
        super(self.__class__, self).mouseDoubleClickEvent(e)
        props = PropsDialog(self)
        if props.exec():
            log.debug(f"Pressed Ok on block {self.name}'s PropsDialog")
        else:
            log.debug(f"Pressed Cancel on block {self.name}'s PropsDialog")

    def import_data(self, name, states, parameters, **_):
        CoreBlock.import_data(self, name, states, parameters, **_)
        self.rewrite()
        self.create_shapes_and_labels()
        x,y = tuple(states['coordinate'])
        self.setPos(x, y)

    def rotate(self, rotation):
        log.debug(f"Rotating {self.name}")
        self.setRotation(self.rotation() + rotation)

    def moveToTop(self):
        # TODO: Is there a simpler way to do this?
        self.setZValue(self.parent.getMaxZValue() + 1)

