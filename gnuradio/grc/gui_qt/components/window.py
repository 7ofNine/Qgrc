# Copyright 2014-2020 Free Software Foundation, Inc.
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

from __future__ import absolute_import, print_function

# Standard modules
import logging
import os
import sys
import subprocess
from pathlib import Path
from os.path import normpath

# Third-party  modules

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtGui import QColorConstants
from PyQt6.QtGui import QClipboard

# Custom modules
from . import FlowgraphView
from .. import base, Utils
from . undoable_actions import RotateAction, MoveAction
from . import ErrorsDialog
from .canvas.block import PropsDialog
from ...core.base import Element

#from .import SaveOnCloseDialog

# Logging
log = logging.getLogger(__name__)

# Shortcuts
Action = QtGui.QAction
Menu = QtWidgets.QMenu
Toolbar = QtWidgets.QToolBar
Icons = QtGui.QIcon.fromTheme
Keys = QtGui.QKeySequence
QStyle = QtWidgets.QStyle

class SaveOnCloseDialog(QtWidgets.QMessageBox):

    def __init__(self, graphname):
        super().__init__()
        
        self.setText(f"Unsaved changes for flowgraph {graphname}!")
        self.setInformativeText("Would you like to save changes before closing")
        self.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Cancel|QtWidgets.QMessageBox.StandardButton.Save|QtWidgets.QMessageBox.StandardButton.Discard)


class MainWindow(QtWidgets.QMainWindow, base.Component):
    
    def __init__(self):
        self._close_pending = False;  # prepare closing

        QtWidgets.QMainWindow.__init__(self)
        base.Component.__init__(self)

        log.debug("Setting the main window")
        self.setObjectName('MainWindow')
        self.setWindowTitle(_('window-title'))
#        self.setDockOptions(QtWidgets.QMainWindow.AllowNestedDocks |
#                            QtWidgets.QMainWindow.AllowTabbedDocks |
#                            QtWidgets.QMainWindow.AnimatedDocks)
        self.setDockNestingEnabled(True);
        # Setup the window icon
        icon = QtGui.QIcon(self.settings.path.ICON)
        log.debug("Setting window icon - ({0})".format(self.settings.path.ICON))
        self.setWindowIcon(icon)
        screen = self.screen().availableGeometry()
        log.debug("Setting window size - ({}, {})".format(screen.width(), screen.height()))
        #self.resize(screen.width() // 2, screen.height())
        self.resize(self.screen().availableSize())

        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)

        self.menuBar().setNativeMenuBar(self.settings.window.NATIVE_MENUBAR)

        # TODO: Not sure about document mode
        #self.setDocumentMode(True)

        # Generate the rest of the window
        self.createStatusBar()

        #actions['Quit.triggered.connect(self.close)
        #actions['Report.triggered.connect(self.reportDock.show)
        #QtCore.QMetaObject.connectSlotsByName(self)




        ### Translation support

        #self.setWindowTitle(_translate("blockLibraryDock", "Library", None))
        #library.headerItem().setText(0, _translate("blockLibraryDock", "Blocks", None))
        #QtCore.QMetaObject.connectSlotsByName(blockLibraryDock)

        # TODO: Move to the base controller and set actions as class attributes
        # Automatically create the actions, menus and toolbars.
        # Child controllers need to call the register functions to integrate into the mainwindow
        self.actions = {}
        self.menus = {}
        self.toolbars = {}
        self.clipboard = None
        self.undoView = None
        self.createActions(self.actions)
        self.createMenus(self.actions, self.menus)
        self.createToolbars(self.actions, self.toolbars)
        self.connectSlots()
        self.config.recent_files_changed.connect(self.recent_files_changed)

        ### Rest of the GUI widgets

        # Map some of the view's functions to the controller class
        self.registerDockWidget = self.addDockWidget
        self.registerMenu = self.addMenu
        self.registerToolBar = self.addToolBar

        # Do other initialization stuff. View should already be allocated and
        # actions dynamically connected to class functions. Also, the log
        # functionality should be also allocated
        log.debug("__init__")

        # Add the menus from the view
        menus = self.menus
        self.registerMenu(menus["file"])
        self.registerMenu(menus["edit"])
        self.registerMenu(menus["view"])
        self.registerMenu(menus["build"])
        self.registerMenu(menus["tools"])
        self.registerMenu(menus["help"])

        toolbars = self.toolbars
        self.registerToolBar(toolbars["file"])
        self.registerToolBar(toolbars["edit"])
        self.registerToolBar(toolbars["run"])

        self.tabWidget = self.createTabWidget()
        self.setCentralWidget(self.tabWidget)

        log.debug("Loading new flowgraph model")
        fg_view = self.create_new()
        
        self.tabWidget.addTab(fg_view, "Untitled")
      
       

    '''def show(self):
        log.debug("Showing main window")
        self.show()
    '''
    def createTabWidget(self):
        tabWidget = QtWidgets.QTabWidget()
        tabWidget.setTabsClosable(True)
        tabWidget.setTabBarAutoHide(True)
        tabWidget.setElideMode(QtCore.Qt.TextElideMode.ElideLeft)
        tabWidget.tabCloseRequested.connect(self.close_triggered)
        tabWidget.currentChanged.connect(self.updateActions)

        return tabWidget


    @property
    def currentView(self):
        return self.tabWidget.currentWidget()

    @property
    def currentFlowgraph(self):
        return self.tabWidget.currentWidget().flowgraphScene

    @pyqtSlot(QtCore.QPointF)
    def createMove(self, diff):
        action = MoveAction(self.currentFlowgraph, diff)
        self.currentFlowgraph.undoStack.push(action)
        self.updateActions()
    
    def getFlowgraph(self,index):
        return self.tabWidget.widget(index).flowgraphScene

    def createActions(self, actions):
        '''
        Defines all actions for this view.
        Controller manages connecting signals to slots implemented in the controller
        '''
        log.debug("Creating actions")

        # File Actions
        actions['new'] = Action(Icons("document-new"), _("new"), self,
                                shortcut=Keys.StandardKey.New, statusTip=_("new-tooltip"))

        actions['open'] = Action(Icons("document-open"), _("open"), self,
                                 shortcut=Keys.StandardKey.Open, statusTip=_("open-tooltip"))

        recent_files = self.config.get_recent_files()

        for i, file in enumerate(recent_files):
            file_action = Action(f"{i}: {Path(file).stem}")
            file_action.setVisible(True)
            normedpath = normpath(file)
            file_action.setData(normpath(file))
            file_action.setToolTip(file)
            actions['open_recent_{}'.format(i)] = file_action


        actions['close'] = Action(Icons("window-close"), _("close"), self,
                                  shortcut=Keys.StandardKey.Close, statusTip=_("close-tooltip"))

        actions['close_all'] = Action(Icons("window-close"), _("close_all"), self,
                                      statusTip=_("close_all-tooltip"))
        actions['save'] = Action(Icons("document-save"), _("save"), self,
                                 shortcut=Keys.StandardKey.Save, statusTip=_("save-tooltip"))

        actions['save_as'] = Action(Icons("document-save-as"), _("save_as"), self,
                                    shortcut=Keys.StandardKey.SaveAs, statusTip=_("save_as-tooltip"))

        actions['save_copy'] = Action(("Save Copy"), self)

        actions['print'] = Action(Icons('document-print'), _("print"), self,
                                  shortcut=Keys.StandardKey.Print, statusTip=_("print-tooltip"))

        actions['screen_capture'] = Action(Icons('camera-photo'), _("screen_capture"), self,
                                           statusTip=_("screen_capture-tooltip"))

        actions['exit'] = Action(Icons("application-exit"), _("exit"), self,
                                 shortcut=Keys.StandardKey.Quit, statusTip=_("exit-tooltip"))

        # Edit Actions
        actions['undo'] = Action(Icons('edit-undo'), _("undo"), self,
                                 shortcut=Keys.StandardKey.Undo, statusTip=_("undo-tooltip"))

        actions['redo'] = Action(Icons('edit-redo'), _("redo"), self,
                                 shortcut=Keys.StandardKey.Redo, statusTip=_("redo-tooltip"))

        actions['view_undo_stack'] = Action("View undo stack", self)

        actions['cut'] = Action(Icons('edit-cut'), _("cut"), self,
                                shortcut=Keys.StandardKey.Cut, statusTip=_("cut-tooltip"))

        actions['copy'] = Action(Icons('edit-copy'), _("copy"), self,
                                 shortcut=Keys.StandardKey.Copy, statusTip=_("copy-tooltip"))

        actions['paste'] = Action(Icons('edit-paste'), _("paste"), self,
                                  shortcut=Keys.StandardKey.Paste, statusTip=_("paste-tooltip"))

        actions['delete'] = Action(Icons('edit-delete'), _("delete"), self,
                                   shortcut=Keys.StandardKey.Delete, statusTip=_("delete-tooltip"))

        actions['select_all'] = Action(Icons('edit-select_all'), _("select_all"), self,
                                   shortcut=Keys.StandardKey.SelectAll, statusTip=_("select_all-tooltip"))
        
        actions['select_none'] = Action(_("Select None"), self,
                                        statusTip=_("select_none-tooltip"))

        actions['rotate_ccw'] = Action(Icons('object-rotate-left'), _("rotate_ccw"), self,
                                       shortcut=Keys.StandardKey.MoveToPreviousChar,
                                       statusTip=_("rotate_ccw-tooltip"))

        actions['rotate_cw'] = Action(Icons('object-rotate-right'), _("rotate_cw"), self,
                                      shortcut=Keys.StandardKey.MoveToNextChar,
                                      statusTip=_("rotate_cw-tooltip"))

        actions['enable'] = Action(_("Enable"), self,
                                   shortcut="E")
        actions['disable'] = Action(_("Disable"), self,
                                   shortcut="D")
        actions['bypass'] = Action(_("Bypass"), self)

        actions['vertical_align_top'] = Action(_("vertical_align_top"), self)
        actions['vertical_align_middle'] = Action(_("vertical_align_middle"), self)
        actions['vertical_align_bottom'] = Action(_("vertical_align_bottom"), self)

        actions['horizontal_align_left'] = Action(_("horizontal_align_left"), self)
        actions['horizontal_align_center'] = Action(_("horizontal_align_center"), self)
        actions['horizontal_align_right'] = Action(_("horizontal_align_right"), self)

        actions['create_hier'] = Action(_("create_hier_block"), self)
        actions['open_hier'] = Action(_("open_hier_block"), self)
        actions['toggle_source_bus'] = Action(_("toggle_source_bus"), self)
        actions['toggle_sink_bus'] = Action(_("toggle_sink_bus"), self)

        actions['properties'] = Action(Icons('document-properties'), _("flowgraph-properties"),
                                       self, statusTip=_("flowgraph-properties-tooltip"))

        # View Actions
        actions['snap_to_grid'] = Action(_("snap_to_grid"), self)
        actions['snap_to_grid'].setCheckable(True)
        
        actions['toggle_grid'] = Action(_("Toggle Grid"), self, shortcut='G',
                                    statusTip=_("toggle_grid-tooltip"))
        actions['toggle_grid'].setCheckable(True)

        actions['errors'] = Action(Icons('dialog-error'), _("errors"), self, shortcut='E',
                                   statusTip=_("errors-tooltip"))

        actions['find'] = Action(Icons('edit-find'), _("find"), self,
                                 shortcut=Keys.StandardKey.Find,
                                 statusTip=_("find-tooltip"))

        # Help Actions
        actions['about'] = Action(Icons('help-about'), _("about"), self,
                                  statusTip=_("about-tooltip"))

        actions['about_qt'] = Action(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMenuButton), _("about-qt"), self,
                                     statusTip=_("about-tooltip"))

        actions['generate'] = Action(Icons('system-run'), _("process-generate"), self,
                                     shortcut='F5', statusTip=_("process-generate-tooltip"))

        actions['execute'] = Action(Icons('media-playback-start'), _("process-execute"),
                                    self, shortcut='F6',
                                    statusTip=_("process-execute-tooltip"))

        actions['kill'] = Action(Icons('process-stop'), _("process-kill"), self,
                                 shortcut='F7', statusTip=_("process-kill-tooltip"))

        actions['help'] = Action(Icons('help-browser'), _("help"), self,
                                 shortcut=Keys.StandardKey.HelpContents, statusTip=_("help-tooltip"))

        actions['types'] = Action("Types", self)

        actions['keys'] = Action(_("&Keys"), self)

        actions['parser_errors'] = Action("Parser Errors", self)
        actions['parser_errors'].setEnabled(False)

        #actions['get_involved'] = Action(_("&Get Involved"), self)

        actions['preferences'] = Action(Icons('preferences-system'), _("preferences"), self,
                                        statusTip=_("preferences-tooltip"))
        
        actions['reload'] = Action(Icons('view-refresh'), _("reload"), self,
                                        statusTip=_("reload-tooltip"))


        actions['preferences'] = Action(Icons('preferences-system'), _("preferences"), self,
                                        statusTip=_("preferences-tooltip"))

        # Tools Actions

        actions['filter_design_tool'] = Action(_("&Filter Design Tool"), self)

        actions['set_default_qt_gui_theme'] = Action(_("Set Default &Qt GUI Theme"), self)
        actions['set_default_qt_gui_theme'].setEnabled(False)
        actions['module_browser'] = Action(_("&OOT Module Browser"), self)
        actions['module_browser'].setEnabled(False)
        actions['show_flowgraph_complexity'] = Action("Show Flowgraph Complexity", self)
        actions['show_flowgraph_complexity'].setCheckable(True)
        actions['show_flowgraph_complexity'].setEnabled(False)



        # Disable some actions, by default
        actions['save'].setEnabled(False)
        actions['undo'].setEnabled(False)
        actions['redo'].setEnabled(False)
        actions['cut'].setEnabled(False)
        actions['copy'].setEnabled(False)
        actions['paste'].setEnabled(False)
        actions['delete'].setEnabled(False)
        actions['errors'].setEnabled(True) # for test
        actions['rotate_cw'].setEnabled(False)
        actions['rotate_ccw'].setEnabled(False)
        actions['enable'].setEnabled(False)
        actions['disable'].setEnabled(False)
        actions['bypass'].setEnabled(False)
        actions['properties'].setEnabled(False)


    def updateActions(self):      # don't call if there is no currentFlowgraph!
        if self._close_pending:   # do nothing. Wouldn't it be better to prevent updateAction?
            return   
        ''' Update the available actions based on what is selected '''

        # get status data
        blocks = self.currentFlowgraph.selected_blocks()
        conns = self.currentFlowgraph.selected_connections()
        undoStack = self.currentFlowgraph.undoStack
        canUndo = undoStack.canUndo()
        canRedo = undoStack.canRedo()
        valid_fg = self.currentFlowgraph.is_valid()
        dirty_fg = self.currentView.is_dirty()

        self.actions['save'].setEnabled(dirty_fg)

        self.actions['undo'].setEnabled(canUndo)
        self.actions['redo'].setEnabled(canRedo)

        self.actions['generate'].setEnabled(valid_fg)
        self.actions['execute'].setEnabled(valid_fg)
        self.actions['errors'].setEnabled(not valid_fg)
        self.actions['kill'].setEnabled(False) # TODO: Set this properly. When to set true?

        # default block actions
        self.actions['cut'].setEnabled(False)
        self.actions['copy'].setEnabled(False)
        self.actions['paste'].setEnabled(False)
        self.actions['delete'].setEnabled(False)
        self.actions['rotate_cw'].setEnabled(False)
        self.actions['rotate_ccw'].setEnabled(False)
        self.actions['enable'].setEnabled(False)
        self.actions['disable'].setEnabled(False)
        self.actions['bypass'].setEnabled(False)
        self.actions['properties'].setEnabled(False)
        self.actions['create_hier'].setEnabled(False)
        self.actions['toggle_source_bus'].setEnabled(False)
        self.actions['toggle_sink_bus'].setEnabled(False)
        
        self.actions['vertical_align_top'].setEnabled(False)
        self.actions['vertical_align_middle'].setEnabled(False)
        self.actions['vertical_align_bottom'].setEnabled(False)

        self.actions['horizontal_align_left'].setEnabled(False)
        self.actions['horizontal_align_center'].setEnabled(False)
        self.actions['horizontal_align_right'].setEnabled(False)


        if self.clipboard:                                
            self.actions['paste'].setEnabled(True)

        if conns:
            self.actions['delete'].setEnabled(True)

        if blocks:
            self.actions['cut'].setEnabled(True)
            self.actions['copy'].setEnabled(True)
            self.actions['delete'].setEnabled(True)
            self.actions['rotate_cw'].setEnabled(True)
            self.actions['rotate_ccw'].setEnabled(True)
            self.actions['enable'].setEnabled(True)
            self.actions['disable'].setEnabled(True)
            self.actions['bypass'].setEnabled(True)     #TODO: isn't ther a condition??
            self.actions['toggle_source_bus'].setEnabled(True)
            self.actions['toggle_sink_bus'].setEnabled(True)


            if len(blocks) == 1:
                self.actions['properties'].setEnabled(True)
                self.actions['create_hier'].setEnabled(True) # TODO: Other requirements for enabling this?

            if len(blocks) > 1:
                self.actions['vertical_align_top'].setEnabled(True)
                self.actions['vertical_align_middle'].setEnabled(True)
                self.actions['vertical_align_bottom'].setEnabled(True)

                self.actions['horizontal_align_left'].setEnabled(True)
                self.actions['horizontal_align_center'].setEnabled(True)
                self.actions['horizontal_align_right'].setEnabled(True)

            for block in blocks:
                if not block.can_bypass():
                    self.actions['bypass'].setEnabled(False)
                    break



    def createMenus(self, actions, menus):
        ''' Setup the main menubar for the application '''
        log.debug("Creating menus")

        # Global menu options
        self.menuBar().setNativeMenuBar(True)

        # Setup the file menu
        file = Menu("&File")
        file.addAction(actions['new'])
        file.addAction(actions['open'])

        recent = Menu(_("Recent"))
        menus['recent'] = recent

        for i in range(len(self.config.get_recent_files())):
            recent.addAction(actions[f'open_recent_{i}'])
        if recent.isEmpty():
            recent.setDisabled(True)
        file.addMenu(recent)
        
        file.addAction(actions['close'])
        file.addAction(actions['close_all'])
        file.addSeparator()
        file.addAction(actions['save'])
        file.addAction(actions['save_as'])
        file.addAction(actions['save_copy'])
        file.addSeparator()
        file.addAction(actions['screen_capture'])
        #file.addAction(actions['print'])
        file.addSeparator()
        file.addAction(actions['exit'])
        menus['file'] = file

        # Setup the edit menu
        edit = Menu("&Edit")
        edit.addAction(actions['undo'])
        edit.addAction(actions['redo'])
        edit.addAction(actions['view_undo_stack'])
        edit.addSeparator()
        edit.addAction(actions['cut'])
        edit.addAction(actions['copy'])
        edit.addAction(actions['paste'])
        edit.addAction(actions['delete'])
        edit.addAction(actions['select_all'])
        edit.addAction(actions['select_none'])
        edit.addSeparator()
        edit.addAction(actions['rotate_ccw'])
        edit.addAction(actions['rotate_cw'])

        align = Menu("&Align")
        menus['align'] = align
        align.addAction(actions['vertical_align_top'])
        align.addAction(actions['vertical_align_middle'])
        align.addAction(actions['vertical_align_bottom'])
        align.addSeparator()
        align.addAction(actions['horizontal_align_left'])
        align.addAction(actions['horizontal_align_center'])
        align.addAction(actions['horizontal_align_right'])

        edit.addMenu(align)
        edit.addSeparator()
        edit.addAction(actions['enable'])
        edit.addAction(actions['disable'])
        edit.addAction(actions['bypass'])
        edit.addSeparator()

        more = Menu("&More")
        menus['more'] = more
        more.addAction(actions['create_hier'])
        more.addAction(actions['open_hier'])
        more.addAction(actions['toggle_source_bus'])
        more.addAction(actions['toggle_sink_bus'])

        edit.addMenu(more)
        edit.addAction(actions['properties'])
        edit.addSeparator()
        edit.addAction(actions['preferences'])
        menus['edit'] = edit

        # Setup submenu
        panels = Menu("&Panels")
        menus['panels'] = panels
        panels.setEnabled(False)

        toolbars = Menu("&Toolbars")
        menus['toolbars'] = toolbars
        toolbars.setEnabled(False)

        # Setup the view menu
        view = Menu("&View")
        view.addMenu(panels)
        view.addMenu(toolbars)
        view.addSeparator()
        
        view.addAction(actions['toggle_grid'])
        view.addAction(actions['find'])
        menus['view'] = view

        # Setup the build menu
        build = Menu("&Build")
        view.addAction(actions['errors'])
        build.addAction(actions['generate'])
        build.addAction(actions['execute'])
        build.addAction(actions['kill'])
        menus['build'] = build

        # Setup the tools menu
        tools = Menu("&Tools")
        tools.addAction(actions['filter_design_tool'])
        tools.addAction(actions['set_default_qt_gui_theme'])
        tools.addAction(actions['module_browser'])
        tools.addSeparator()
        tools.addAction(actions['show_flowgraph_complexity'])
        menus['tools'] = tools


        # Setup the help menu
        help = Menu("&Help")
        help.addAction(actions['help'])
        help.addAction(actions['types'])
        help.addAction(actions['keys'])
        help.addAction(actions['parser_errors'])
        help.addSeparator()
        help.addAction(actions['about'])
        help.addAction(actions['about_qt'])
        menus['help'] = help

    def createToolbars(self, actions, toolbars):
        log.debug("Creating toolbars")

        # Main toolbar
        file = Toolbar("File")
        file.addAction(actions['new'])
        file.addAction(actions['open'])
        file.addAction(actions['save'])
        file.addAction(actions['close'])
        #file.addAction(actions['print'])
        toolbars['file'] = file

        # Edit toolbar
        edit = Toolbar("Edit")
        edit.addAction(actions['undo'])
        edit.addAction(actions['redo'])
        edit.addSeparator()
        edit.addAction(actions['cut'])
        edit.addAction(actions['copy'])
        edit.addAction(actions['paste'])
        edit.addAction(actions['delete'])
        edit.addSeparator()
        edit.addAction(actions['rotate_ccw'])
        edit.addAction(actions['rotate_cw'])
        toolbars['edit'] = edit

        # Run Toolbar
        run = Toolbar('Run')
        run.addAction(actions['errors'])
        run.addAction(actions['generate'])
        run.addAction(actions['execute'])
        run.addAction(actions['kill'])
        toolbars['run'] = run

        # Misc Toolbar
        misc = Toolbar('Misc')
        misc.addAction(actions['reload'])
        toolbars['misc'] = misc

    def createStatusBar(self): # --- 1
        log.debug("Creating status bar")
        self.statusBar().showMessage(_("ready-message"))

    def new_tab(self, flowgraph): 
        self.setCentralWidget(flowgraph)

    def open(self):  # --- 2
        Open = QtWidgets.QFileDialog.getOpenFileName
        filename, filtr = Open(self, self.actions['open'].statusTip(),
                               filter='Flow Graph Files (*.grc);;All files (*.*)')
        return filename

    def save(self, filename = None): 
        if filename:
            filter = filename
            selectedFilter =''
        else:
            filter = '*.grc'
            selectedFilter ='*.grc'
        Save = QtWidgets.QFileDialog.getSaveFileName
        filename, filtr = Save(self, self.actions['save'].statusTip(), filter, selectedFilter)
                               #filter='Flow Graph Files (*.grc);;All files (*.*)')
        return filename

    def create_new(self, filename = None):
        fg_view = FlowgraphView(self)
        if filename:
            fg_view.load_graph(filename)
        else:
            fg_view.set_initial_state()

        fg_view.flowgraphScene.selectionChanged.connect(self.updateActions)  # it's actually the current flowgraph in the tabwidget
        fg_view.flowgraphScene.flowgraph_changed.connect(self.flowgraph_changed)
        fg_view.flowgraphScene.itemMoved.connect(self.createMove)
        return fg_view

    @pyqtSlot(Element)
    def registerNewElement(self, elem):
        action = NewElementAction(self.currentFlowgraph, elem)
        self.currentFlowgraph.undoStack.push(action)
        self.updateActions()


    # Overridden methods
    def addDockWidget(self, location, widget): # --- 4
        ''' Adds a dock widget to the view. '''
        # This overrides QT's addDockWidget so that a 'show' menu auto can automatically be
        # generated for this action.
        super().addDockWidget(location, widget)
        # This is the only instance where a controller holds a reference to a view it does not
        # actually control.
        name = widget.__class__.__name__
        log.debug("Generating show action item for widget: {0}".format(name))

        # Create the new action and wire it to the show/hide for the widget
        self.menus["panels"].addAction(widget.toggleViewAction())
        self.menus['panels'].setEnabled(True)

    def addToolBar(self, toolbar): # --- 5
        ''' Adds a toolbar to the main window '''
        # This is also overridden so a show menu item can automatically be added
        super().addToolBar(toolbar)
        name = toolbar.windowTitle()
        log.debug("Generating show action item for toolbar: {0}".format(name))

        # Create the new action and wire it to the show/hide for the widget
        self.menus["toolbars"].addAction(toolbar.toggleViewAction())
        self.menus['toolbars'].setEnabled(True)

    def addMenu(self, menu): # --- 6
        ''' Adds a menu to the main window '''
        help = self.menus["help"].menuAction()
        self.menuBar().insertMenu(help, menu)


    ###############################
    # Action Handlers
    ###############################
    def new_triggered(self):  
        log.debug('new triggered')
        fg_view = self.create_new()
        self.tabWidget.addTab(fg_view, "Untitled")
        self.tabWidget.setCurrentIndex(self.tabWidget.count() - 1)



    def open_file(self, filename): 
        if filename:
            log.info("Opening flowgraph ({0})".format(filename))
            fg_view = self.create_new(filename)
            self.tabWidget.addTab(fg_view, str(os.path.basename(filename)).removesuffix(".grc"))
            self.tabWidget.setCurrentIndex(self.tabWidget.count() - 1) # make new fg active
            self.tabWidget.setTabToolTip(self.tabWidget.currentIndex(), filename)  # pop up full file path when hovering over tab

    @pyqtSlot()
    def open_triggered(self): # --- 8 
        log.debug('open triggered')
        filename = self.open()

        self.open_file(filename)
        self.config.add_recent_file(filename)
    
    @pyqtSlot()
    def open_recent_triggered(self): # --- 8 
        sender = QtCore.QObject.sender(self)
        if type(sender) is QtGui.QAction:
            filename = sender.data()
            if filename in self.config.get_recent_files():
                self.open_file(filename)
                self.config.add_recent_file(filename)
        else:
            log.debug("got something different than a QAction")
        pass

    @pyqtSlot()
    def recent_files_changed(self):  # update recent files sub menu # +++
        self.menus['recent'].clear()
        for i, file in enumerate(self.config.get_recent_files()):
            file_action = Action(f"{i}: {Path(file).stem}")
            file_action.setVisible(True)
            file_action.setData(normpath(file))
            file_action.setToolTip(file)
            action_name = 'open_recent_{}'.format(i)
            self.actions[action_name] = file_action
            self.menus['recent'].addAction(self.actions[action_name])
            file_action.triggered.connect(self.open_recent_triggered)

    @pyqtSlot()
    def save_triggered(self): # --- 9
        current_index = self.tabWidget.currentIndex()
        log.debug(f'Saving tab {current_index}')
        if current_index == -1:
            pass 
        else:
            if self.currentFlowgraph.is_dirty():    # check if we have to save
                try:
                    filename = self.currentFlowgraph.get_filepath()
                    if filename:
                        self.currentFlowgraph.save(filename) 
                        self.flowgraph_saved()  # update other data
                        log.info(f'Saved flowgraph {filename}')
                    else:
                        log.debug('Flowgraph does not have a filename')
                        self.save_as_triggered() # save with name
                        return
                except IOError:
                    log.error(f'Save failed for {filename}: ' +str(IOError))
                log.info(f"Flowgraph {filename} saved")
            else:
                log.debug("Save flowgraph triggered but graph was not dirty")


    @pyqtSlot()
    def save_as_triggered(self): # --- 10
        log.debug('save as triggered')
        filename = self.save()  # get file save name
        if filename:
            try:
                self.file_path = filename
                self.currentFlowgraph.save(filename)
                self.flowgraph_saved() # update other data
                self.update_tab(filename)
                self.config.add_recent_file(filename) #update recent files list
            except IOError:
                log.error(f'Save as failed for {filename}')
        else:
            log.debug("Save flowgraph as cancelled")
            return
        log.info(f"Flowgraph saved as {filename}")

    def save_copy_triggered(self):
        log.debug('Save Copy')
        filename = self.currentFlowgraph.get_filepath().removesuffix(".grc") +"_copy.grc"
        filename = self.save(filename) 
        if filename:
            try:
                self.platform.save_flow_graph(self.currentFlowgraph, filename)
            except IOError:
                log.error('Save (copy) failed')

            log.info(f'Saved (copy) {filename}')
            self.open_file(filename)
            self.config.add_recent_file(filename)
        else:
            log.debug('Cancelled Save Copy action')

    def close(self, flowgraph):
        if flowgraph.is_dirty():    # check if we have to save
            tabName = str(os.path.basename(flowgraph.get_filepath())).removesuffix('.grc')
            question = SaveOnCloseDialog(tabName)
            result = question.exec()
            if result == QtWidgets.QMessageBox.StandardButton.Save:
                filename = self.save(str(os.path.basename(flowgraph.get_filepath())))           # get filename for saving
                flowgraph.save(filename) 
            elif result == QtWidgets.QMessageBox.StandardButton.Discard:
                pass
            elif result == QtWidgets.QMessageBox.StandardButton.Cancel:
                return


    #@pyqtSlot(int)   #creates problems using it with the last tab
    def close_triggered(self, index):                       
        if isinstance(index, bool) and not index:           # closed via buttom index is False
            close_index = self.tabWidget.currentIndex()   
        else:
            close_index = index
        log.debug(f'Closing tab {close_index}')      
        closeFlowgraph =self.getFlowgraph(close_index)
        self.close(closeFlowgraph)

        if self.tabWidget.count() == 1:
            self.tabWidget.currentChanged.disconnect()                   # work around for problem when closing last tab in the connected slot
            self.tabWidget.removeTab(close_index)                    # causes crash. Would lead to accessing a nonexistant object 
            self.tabWidget.currentChanged.connect(self.updateActions)
        else:
            self.tabWidget.removeTab(close_index)

        if self.tabWidget.count() == 0:
            self.new_triggered()


    @pyqtSlot()
    def close_all_triggered(self):
        log.debug('close all')
        while self.tabWidget.count() > 0:
            flowgraph = self.tabWidget.widget(0).flowgraphScene
            self.close(flowgraph)
            if self.tabWidget.count() == 1:
                self.tabWidget.currentChanged.disconnect()         # work around for problem when closing last tab
                self.tabWidget.removeTab(0)                        # causes crash. Nowhere described 
                self.tabWidget.currentChanged.connect(self.updateActions)
            else:
                self.tabWidget.removeTab(0)
        
        self.new_triggered()


    def print_triggered(self):
        log.debug('print: not implemented,yet')

    @pyqtSlot()
    def screen_capture_triggered(self):
        log.debug('screen capture: not implemented, yet')
        # TODO: Should be user-set somehow
        background_transparent = True

        Save = QtWidgets.QFileDialog.getSaveFileName
        file_path, filtr = Save(self, self.actions['save'].statusTip(),
                               filter='PDF files (*.pdf);;PNG files (*.png);;SVG files (*.svg)')
        if file_path is not None:
            try:
                Utils.make_screenshot(
                    self.currentView, file_path, background_transparent)
            except ValueError:
                #Messages.send('Failed to generate screenshot\n')
                log.error("Failed to generate screenshot")


    @pyqtSlot()
    def undo_triggered(self):  # ---
        log.debug('undo')
        self.currentFlowgraph.undoStack.undo()
        self.updateActions()
    
    @pyqtSlot()
    def redo_triggered(self): # ---
        log.debug('redo')
        self.currentFlowgraph.undoStack.redo()
        self.updateActions()

    @pyqtSlot()
    def view_undo_stack_triggered(self):  # --- 
        log("view_undo_stack: To be properly implemented. will it ever??'")

    def cut_triggered(self): # --- 
        log.debug('cut')
        self.copy_triggered()
        self.currentFlowgraph.delete_selected()
        self.updateActions()

    def copy_triggered(self):
        log.debug('copy')
        self.clipboard = self.currentFlowgraph.copy_to_clipboard()
        self.updateActions()

    def paste_triggered(self):
        log.debug('paste')
        if self.clipboard:
            self.currentFlowgraph.paste_from_clipboard(self.clipboard)
            self.currentFlowgraph.update()
        else:
            log.debug('clipboard is empty')





    @pyqtSlot()
    def delete_triggered(self): # --- 
        log.debug('delete')
        self.currentFlowgraph.delete_selected()

    @pyqtSlot()
    def select_all_triggered(self): # --- 
        log.debug('select_all')
        self.currentFlowgraph.select_all()
        self.updateActions()
    
    @pyqtSlot()
    def select_none_triggered(self): # --- 
        log.debug('select_none')
        self.currentFlowgraph.clearSelection()
        self.updateActions()

    @pyqtSlot()
    def rotate_ccw_triggered(self): # --- 
        log.debug('rotate_ccw')
        rotateCommand = RotateAction(self.currentFlowgraph, -90)
        self.currentFlowgraph.undoStack.push(rotateCommand)
        self.updateActions()
    
    @pyqtSlot()
    def rotate_cw_triggered(self): # --- 
        log.debug('rotate_cw')
        rotateCommand = RotateAction(self.currentFlowgraph, 90)
        self.currentFlowgraph.undoStack.push(rotateCommand)
        self.updateActions()

    
    @pyqtSlot()
    def toggle_source_bus_triggered(self): # --- 
        log.debug('toggle_source_bus')
        for b in self.currentFlowgraph.selected_blocks():
                b.bussify('source')
        self.currentFlowgraph.update()

    @pyqtSlot()
    def toggle_sink_bus_triggered(self): # --- 
        log.debug('toggle_source_bus')
        for b in self.currentFlowgraph.selected_blocks():
                b.bussify('sink')
        self.currentFlowgraph.update()

    @pyqtSlot()
    def errors_triggered(self): # --- 
        errorDialog = ErrorsDialog(self, self.currentFlowgraph)
        errorDialog.exec()

    @pyqtSlot()
    def find_triggered(self): # --- 
        log.debug('find block')
        self._app().BlockLibrary._search_bar.setFocus()
    
    # def get_involved_triggered(self):  # DO    I REALLY want to implement this ?

    @pyqtSlot()
    def about_triggered(self): # --- 
        log.debug('about')
        self.about()
    
    @pyqtSlot()
    def about_qt_triggered(self): # --- 
        log.debug('about_qt')
        QtWidgets.QApplication.instance().aboutQt()
    
    @pyqtSlot()
    def properties_triggered(self): # --- 
        log.debug('properties')
        for block in self.currentFlowgraph.selected_blocks():
            props = PropsDialog(block)
            props.exec()

    @pyqtSlot()
    def enable_triggered(self): # --- 
        log.debug('enable')
        for block in self.currentFlowgraph.selected_blocks():
            block.state = 'enabled'
            block.create_shapes_and_labels()

    @pyqtSlot()
    def disable_triggered(self): # --- 
        log.debug('disable')
        for block in self.currentFlowgraph.selected_blocks():
            block.state = 'disabled'
            block.create_shapes_and_labels()

    @pyqtSlot()
    def bypass_triggered(self): # --- 
        log.debug('bypass')
        all_bypassed = True
        for block in self.currentFlowgraph.selected_blocks():
            if not block.state == 'bypassed':
                all_bypassed = False
                break

        if not all_bypassed:
            cmd = BypassAction(self.currentFlowgraph)
            self.currentFlowgraph.undoStack.push(cmd)
        
        self.currentFlowgraph.update()
        self.updateActions()

    @pyqtSlot()  # ---
    def generate_triggered(self):
        log.debug('generate')
        generator = self.platform.Generator(self.currentFlowgraph, os.path.dirname(self.file_path))
        generator.write()
    
    @pyqtSlot() # ---
    def execute_triggered(self):
        log.debug('execute')
        py_path = self.file_path[0:-3] + 'py'
        subprocess.Popen(f'/usr/bin/python {py_path}', shell=True)    # TODO: the path is installation dependent
    
    @pyqtSlot() # ---
    def kill_triggered(self):
        log.debug('kill: not implemented')


    @pyqtSlot() # ---
    def help_triggered(self):
        log.debug('help')
        self.help()

    def types_triggered(self): # ---
        log.debug('types')
        self.types()

    def preferences_triggered(self):
        log.debug('preferences')

    def exit_triggered(self):
        #TODO: save confirmation request dialog
        log.debug('exit: save not implemented, yet')
        # TODO: Make sure all flowgraphs have been saved 
        self.config.save()  #save configuration
        self.app.exit()
    
    @pyqtSlot() # ---
    def help_triggered(self):
        log.debug('help')
        self.help()

    @pyqtSlot() # --- 
    def keys_triggered(self):
        log.debug('keys: not implemented')

    def report_triggered(self):
        log.debug('report')

    def library_triggered(self):
        log.debug('library_triggered: not implemented')

    def library_toggled(self):
        log.debug('library_toggled: not implemented')
    
    @pyqtSlot()
    def vertical_align_top_triggered(self):
        log.warning('vertical align top: not implemented')

    @pyqtSlot()
    def vertical_align_middle_triggered(self):
        log.warning('vertical align middle: not implemented')

    @pyqtSlot()
    def vertical_align_bottom_triggered(self):
        log.warning('vertical align bottom: not implemented')

    @pyqtSlot()
    def horizontal_align_left_triggered(self):
        log.warning('horizontal align left: not implemented')
    
    @pyqtSlot()
    def horizontal_align_center_triggered(self):
        log.warning('horizontal align center: not implemented')

    @pyqtSlot()
    def horizontal_align_right_triggered(self):
        log.warning('horizontal align right: not implemented')
    
    @pyqtSlot()
    def create_hier_triggered(self):
        log.warning('create hier: not implemented')

    @pyqtSlot()
    def open_hier_triggered(self):
        log.warning('create hier: not implemented')
    
    @pyqtSlot()
    def toggle_source_bus_triggered(self):
        log.warning('toggle source bus: not implemented')



    @pyqtSlot(bool)
    def snap_to_grid_toggled(self, toggled):
        log.debug("snap_to_grid not implemented: not implemented")

    @pyqtSlot(bool)
    def toggle_grid_toggled(self, bool):
        log.debug("toggle grid  not implemented: not implemented")

    @pyqtSlot()
    def reload_triggered(self):
        log.debug("reload: not implemented")

    @pyqtSlot()
    def filter_design_tool_triggered(self):
        log.debug("filter_design_tool: not implemented")

    @pyqtSlot(bool)
    def show_flowgraph_complexity_toggled(self, bool):
        log.debug("show_flowgraph_complexity: not implemented")

    def closeEvent(self, a0):
        log.debug('close event not implemented, yet')
        #TODO: 
        #TODO: check for files to be saved!
        self._close_pending = True
        return super().closeEvent(a0)

    #######################################

    @pyqtSlot(int)
    def current_tab_changed(self, tabindex):
        self.actions['save'].setEnabled(self.currentFlowgraph.is_dirty())

    @pyqtSlot()
    def flowgraph_changed(self):
        self.actions['save'].setEnabled(True)
        current_index = self.tabWidget.currentIndex();
        self.tabWidget.tabBar().setTabTextColor(current_index,QColorConstants.Red)

    @pyqtSlot()
    def flowgraph_saved(self):
        self.currentFlowgraph.reset_dirty()
        self.updateActions()
        current_index = self.tabWidget.currentIndex();
        self.tabWidget.tabBar().setTabTextColor(current_index,QColorConstants.Black)

    def update_tab(self, filename):
        current_index = self.tabWidget.currentIndex();
        self.tabWidget.setTabText(current_index,str(os.path.basename(filename)).removesuffix(".grc"))

    def contextMenuEvent(self, event):
        #QtGui.QContextMenuEvent
        #return super().contextMenuEvent(event)
        menu = QtWidgets.QMenu()
        menu.addAction(self.actions["cut"])
        menu.addAction(self.actions["copy"])
        menu.addAction(self.actions["paste"])
        menu.addAction(self.actions["delete"])
        menu.addSeparator()
        menu.addAction(self.actions['rotate_ccw'])
        menu.addAction(self.actions['rotate_cw'])
        menu.addAction(self.actions['enable'])
        menu.addAction(self.actions['disable'])
        menu.addAction(self.actions['bypass'])
        menu.addSeparator()

        more = QtWidgets.QMenu("More")
        menu.addMenu(more)
        menu.addSeparator()
        menu.addAction(self.actions['properties']) 

        menu.exec(event.globalPos())
