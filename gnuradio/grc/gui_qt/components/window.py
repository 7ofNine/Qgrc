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

# Custom modules
from . import FlowgraphView
from .. import base
from . import RotateCommand
from . import ErrorsDialog
from .canvas.block import PropsDialog
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

    def __init__(self):
        super().__init__()
        
        self.setText("Unsaved changes!")
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
        self.registerMenu(menus["help"])

        toolbars = self.toolbars
        self.registerToolBar(toolbars["file"])
        self.registerToolBar(toolbars["edit"])
        self.registerToolBar(toolbars["run"])

        self.tabWidget = self.createTabWidget()
        self.setCentralWidget(self.tabWidget)

        log.debug("Loading flowgraph model")
        fg_view = FlowgraphView(self)                         # introduce better logical structure. Who should load the data. Scene -> update View. Or the view?   
        fg_view.set_initial_state()
        log.debug("Adding flowgraph view")                         
        
        self.tabWidget.addTab(fg_view, "Untitled")
        
        self.currentFlowgraph.selectionChanged.connect(self.updateActions)  # it's actually the current flowgraph in the tabwidget
        #self.new_tab(self.flowgraph)

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
        tabWidget.currentChanged.connect(self.current_tab_changed)

        return tabWidget


    @property
    def currentView(self):
        return self.tabWidget.currentWidget()

    @property
    def currentFlowgraph(self):
        return self.tabWidget.currentWidget().flowgraphScene

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

        actions['rotate_ccw'] = Action(Icons('object-rotate-left'), _("rotate_ccw"), self,
                                       shortcut=Keys.StandardKey.MoveToPreviousChar,
                                       statusTip=_("rotate_ccw-tooltip"))

        actions['rotate_cw'] = Action(Icons('object-rotate-right'), _("rotate_cw"), self,
                                      shortcut=Keys.StandardKey.MoveToNextChar,
                                      statusTip=_("rotate_cw-tooltip"))

        actions['enable'] = Action(_("enable"), self,
                                   shortcut="E")
        actions['disable'] = Action(_("disable"), self,
                                   shortcut="D")
        actions['bypass'] = Action(_("bypass"), self)

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



        actions['preferences'] = Action(Icons('preferences-system'), _("preferences"), self,
                                        statusTip=_("preferences-tooltip"))

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


    def updateActions(self):
        if self._close_pending:   # do nothing. Wouldn't it be better to prevent updateAction?
            return   
        ''' Update the available actions based on what is selected '''

        def there_are_blocks_in(selection):
            for element in selection:
                if element.is_block:
                    return True
            return False

        def there_are_connections_in(selection):
            for element in selection:
                if element.is_connection:
                    return True
            return False

        selected_elements = self.currentFlowgraph.selectedItems()
        undoStack = self.currentFlowgraph.undoStack
        canUndo = undoStack.canUndo()
        canRedo = undoStack.canRedo()

        self.actions['undo'].setEnabled(canUndo)
        self.actions['redo'].setEnabled(canRedo)
        self.actions['cut'].setEnabled(False)
        self.actions['copy'].setEnabled(False)
        self.actions['paste'].setEnabled(False)
        self.actions['delete'].setEnabled(False)
        self.actions['rotate_cw'].setEnabled(False)
        self.actions['rotate_ccw'].setEnabled(False)
        self.actions['enable'].setEnabled(False)
        self.actions['disable'].setEnabled(False)
        self.actions['bypass'].setEnabled(False)

        if there_are_connections_in(selected_elements):
            self.actions['delete'].setEnabled(True)

        if there_are_blocks_in(selected_elements):
            self.actions['cut'].setEnabled(True)
            self.actions['copy'].setEnabled(True)
            self.actions['paste'].setEnabled(True)
            self.actions['delete'].setEnabled(True)
            self.actions['rotate_cw'].setEnabled(True)
            self.actions['rotate_ccw'].setEnabled(True)
            self.actions['enable'].setEnabled(True)
            self.actions['disable'].setEnabled(True)

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
        
        #file.addAction(actions['open_recent'])
        file.addAction(actions['close'])
        file.addAction(actions['close_all'])
        file.addSeparator()
        file.addAction(actions['save'])
        file.addAction(actions['save_as'])
        file.addSeparator()
        file.addAction(actions['screen_capture'])
        file.addAction(actions['print'])
        file.addSeparator()
        file.addAction(actions['exit'])
        menus['file'] = file

        # Setup the edit menu
        edit = Menu("&Edit")
        edit.addAction(actions['undo'])
        edit.addAction(actions['redo'])
        edit.addSeparator()
        edit.addAction(actions['cut'])
        edit.addAction(actions['copy'])
        edit.addAction(actions['paste'])
        edit.addAction(actions['delete'])
        edit.addAction(actions['select_all'])
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
        view.addAction(actions['errors'])
        view.addAction(actions['find'])
        menus['view'] = view

        # Setup the build menu
        build = Menu("&Build")
        build.addAction(actions['generate'])
        build.addAction(actions['execute'])
        build.addAction(actions['kill'])
        menus['build'] = build

        # Setup the help menu
        help = Menu("&Help")
        help.addAction(actions['help'])
        help.addAction(actions['types'])
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
        file.addAction(actions['print'])
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
        run.addAction(actions['generate'])
        run.addAction(actions['execute'])
        run.addAction(actions['kill'])
        toolbars['run'] = run

    def createStatusBar(self):
        log.debug("Creating status bar")
        self.statusBar().showMessage(_("ready-message"))

    def new_tab(self, flowgraph):
        self.setCentralWidget(flowgraph)

    def open(self):
        Open = QtWidgets.QFileDialog.getOpenFileName
        filename, filtr = Open(self, self.actions['open'].statusTip(),
                               filter='Flow Graph Files (*.grc);;All files (*.*)')
        return filename

    def save(self, filename = None):
        if filename == "":
            filter = '*.grc'
        else:
            filter = filename
        Save = QtWidgets.QFileDialog.getSaveFileName
        filename, filtr = Save(self, self.actions['save'].statusTip(), filter)

                               #filter='Flow Graph Files (*.grc);;All files (*.*)')
                               
        return filename

    # Overridden methods
    def addDockWidget(self, location, widget):
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

    def addToolBar(self, toolbar):
        ''' Adds a toolbar to the main window '''
        # This is also overridden so a show menu item can automatically be added
        super().addToolBar(toolbar)
        name = toolbar.windowTitle()
        log.debug("Generating show action item for toolbar: {0}".format(name))

        # Create the new action and wire it to the show/hide for the widget
        self.menus["toolbars"].addAction(toolbar.toggleViewAction())
        self.menus['toolbars'].setEnabled(True)

    def addMenu(self, menu):
        ''' Adds a menu to the main window '''
        help = self.menus["help"].menuAction()
        self.menuBar().insertMenu(help, menu)

    # Action Handlers
    def new_triggered(self):
        log.debug('new triggered')
        fg_view = FlowgraphView(self)
        fg_view.set_initial_state()
        self.tabWidget.addTab(fg_view, "Untitled")



    def open_file(self, filename):         
        if filename:
            log.info("Opening flowgraph ({0})".format(filename))
            new_flowgraph = FlowgraphView(self)
            new_flowgraph.load_graph(filename)
            new_flowgraph.flowgraphScene.selectionChanged.connect(self.updateActions)
            new_flowgraph.flowgraphScene.flowgraph_changed.connect(self.flowgraph_changed)
            self.tabWidget.addTab(new_flowgraph, str(os.path.basename(filename)).removesuffix(".grc"))
            self.tabWidget.setCurrentIndex(self.tabWidget.count() - 1)
            self.tabWidget.setTabToolTip(self.tabWidget.currentIndex(), filename)

    @pyqtSlot()
    def open_triggered(self):
        log.debug('open triggered')
        filename = self.open()

        self.open_file(filename)
        self.config.add_recent_file(filename)
    
    @pyqtSlot()
    def open_recent_triggered(self):
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
    def recent_files_changed(self):  # update recent files sub menu
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
    def save_triggered(self):
        current_index = self.tabWidget.currentIndex()
        log.debug(f'Saving tab {current_index}')
        if current_index == -1:
            pass 
        else:
            if self.currentFlowgraph.is_dirty():    # check if we have to save
                try:
                    #filename = self.save(str(os.path.basename(self.currentFlowgraph.get_filepath())))              # get filename for saving
                    filename = self.currentFlowgraph.get_filepath()
                    if bool(filename):
                        self.currentFlowgraph.save(filename) 
                        self.flowgraph_saved()  # update other data
                        log.info(f'Saved flowgraph {filename}')
                    else:
                        log.debug("Save flowgraph cancelled")
                        return
                except IOError:
                    log.error(f'Save failed for {filename}: ' +str(IOError))
                log.info(f"Flowgraph {filename} saved")
            else:
                log.debug("Save flowgraph triggered but graph was not dirty")


    @pyqtSlot()
    def save_as_triggered(self):
        log.debug('save as triggered')
        filename = self.save()  # get file save name
        if bool(filename):
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

    @pyqtSlot()
    def close_triggered(self):           # tab is being closed why does index not contain the current (closing) tab??
                                                # TODO: extend by dialog for save confirmation
        current_index = self.tabWidget.currentIndex()
        log.debug(f'Closing tab {current_index}')
        if current_index == -1:
            pass 
        else:
            if self.currentFlowgraph.is_dirty():    # check if we have to save
                question = SaveOnCloseDialog()
                result = question.exec()
                if result == QtWidgets.QMessageBox.StandardButton.Save:
                    filename = self.save(str(os.path.basename(self.currentFlowgraph.get_filepath())))           # get filename for saving
                    self.currentFlowgraph.save(filename) 
                elif result == QtWidgets.QMessageBox.StandardButton.Discard:
                    pass
                elif result == QtWidgets.QMessageBox.StandardButton.Cancel:
                    return

            if self.tabWidget.count() == 1:
                self.tabWidget.blockSignals(True)                              # work around for problem when closing last tab
                self.tabWidget.removeTab(current_index)                        # causes crash. Nowhere described 
                self.tabWidget.blockSignals(False)
            else:
                self.tabWidget.removeTab(current_index)

            if self.tabWidget.count() == 0:
                self.new_triggered()


    @pyqtSlot()
    def close_all_triggered(self):
        # TODO: extend by dialog for save confirmation
        log.debug('close all')
        while self.tabWidget.count() > 0:
            flowgraphview = self.tabWidget.widget(0)
            if flowgraphview.is_dirty():    # check if we have to save
                filename = self.save(str(os.path.basename(flowgraphview.get_filepath())))              # get filename for saving
                flowgraphview.save(filename) # TODO: add dialog for file already exists ?  
            if self.tabWidget.count() == 1:
                self.tabWidget.blockSignals(True)                              # work around for problem when closing last tab
                self.tabWidget.removeTab(0)                        # causes crash. Nowhere described 
                self.tabWidget.blockSignals(False)
            else:
                self.tabWidget.removeTab(0)
        
        self.new_triggered()


    def print_triggered(self):
        log.debug('print: not implemented,yet')

    def screen_capture_triggered(self):
        log.debug('screen capture: not implemented, yet')

    @pyqtSlot()
    def undo_triggered(self):
        log.debug('undo')
        self.currentFlowgraph.undoStack.undo()
        self.updateActions()
    
    @pyqtSlot()
    def redo_triggered(self):
        log.debug('redo')
        self.currentFlowgraph.undoStack.redo()
        self.updateActions()

    def cut_triggered(self):
        log.debug('cut: not implemented, yet')

    def copy_triggered(self):
        log.debug('copy: not implemented, yet')

    def paste_triggered(self):
        log.debug('paste: not implemented, yet')

    @pyqtSlot()
    def delete_triggered(self):
        log.debug('delete')
        self.currentFlowgraph.delete_selected()

    @pyqtSlot()
    def rotate_ccw_triggered(self):
        log.debug('rotate_ccw')
        rotateCommand = RotateCommand(self.currentFlowgraph, -90)
        self.currentFlowgraph.undoStack.push(rotateCommand)
        self.updateActions()
    
    @pyqtSlot()
    def rotate_cw_triggered(self):
        log.debug('rotate_cw')
        rotateCommand = RotateCommand(self.currentFlowgraph, 90)
        self.currentFlowgraph.undoStack.push(rotateCommand)
        self.updateActions()

    @pyqtSlot()
    def errors_triggered(self):
        errorDialog = ErrorsDialog(self, self.currentFlowgraph)
        errorDialog.exec()
    
    @pyqtSlot()
    def find_triggered(self):
        log.debug('find block')
        self._app().BlockLibrary._search_bar.setFocus()
    
    @pyqtSlot()
    def about_triggered(self):
        log.debug('about')
        self.about()
    
    @pyqtSlot()
    def about_qt_triggered(self):
        log.debug('about_qt')
        QtWidgets.QApplication.instance().aboutQt()
    
    @pyqtSlot()
    def properties_triggered(self):
        log.debug('properties')
        for block in self.currentFlowgraph.selected_blocks():
            props = PropsDialog(block)
            props.exec()

    @pyqtSlot()
    def enable_triggered(self):
        log.debug('enable')
        for block in self.currentFlowgraph.selected_blocks():
            block.state = 'enabled'
            block.create_shapes_and_labels()

    @pyqtSlot()
    def disable_triggered(self):
        log.debug('disable')
        for block in self.currentFlowgraph.selected_blocks():
            block.state = 'disabled'
            block.create_shapes_and_labels()

    @pyqtSlot()
    def execute_triggered(self):
        log.debug('execute')
        py_path = self.file_path[0:-3] + 'py'
        subprocess.Popen(f'/usr/bin/python {py_path}', shell=True)
    
    @pyqtSlot()
    def generate_triggered(self):
        log.debug('generate')
        generator = self.platform.Generator(self.currentFlowgraph, os.path.dirname(self.file_path))
        generator.write()

    def types_triggered(self):
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
    
    @pyqtSlot()
    def help_triggered(self):
        log.debug('help')
        self.help()

    def kill_triggered(self):
        log.debug('kill')

    def report_triggered(self):
        log.debug('report')

    def library_triggered(self):
        log.debug('library_triggered')

    def library_toggled(self):
        log.debug('library_toggled')
    
    @pyqtSlot()
    def select_all_triggered(self):
        log.warning('select all')
        self.currentFlowgraph.select_all()
    
    @pyqtSlot()
    def bypass_triggered(self):
        log.warning('bypass')

    @pyqtSlot()
    def vertical_align_top_triggered(self):
        log.warning('vertical align top')

    @pyqtSlot()
    def vertical_align_middle_triggered(self):
        log.warning('vertical align middle')

    @pyqtSlot()
    def vertical_align_bottom_triggered(self):
        log.warning('vertical align bottom')

    def horizontal_align_left_triggered(self):
        log.warning('horizontal align left')

    def horizontal_align_center_triggered(self):
        log.warning('horizontal align center')

    def horizontal_align_right_triggered(self):
        log.warning('horizontal align right')

    def create_hier_triggered(self):
        log.warning('create hier')

    def open_hier_triggered(self):
        log.warning('create hier')

    def toggle_source_bus_triggered(self):
        log.warning('toggle source bus')

    def toggle_sink_bus_triggered(self):
        log.warning('toggle sink bus')

    def about(self):
        log.debug('about method not implemented, yet')

    def types(self):
        log.debug('types() method not implemented, yet')

    def help(self):
        log.debug('help not implemented, yet')

    
    def closeEvent(self, a0):
        log.debug('close event not implemented, yet')
        #TODO: 
        #TODO: check for files to be saved!
        self._close_pending = True
        return super().closeEvent(a0)

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
        self.actions['save'].setEnabled(False)
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
