# Copyright 2008, 2009, 2016 Free Software Foundation, Inc.
# This file is part of GNU Radio
#
# SPDX-License-Identifier: GPL-2.0-or-later
#


from PyQt6.QtWidgets import (QDialog, QTableView, QVBoxLayout, QDialogButtonBox, QHeaderView)
from PyQt6.QtGui import (QStandardItemModel, QStandardItem, QFont)

class ErrorsDialog(QDialog):
    """ Display errors present in the flowgraph. """

    def __init__(self, parent, flowgraph):
        QDialog.__init__(self)

        self.setWindowTitle('Error and Warnings')
        self.setModal(True)
        self.setSizeGripEnabled(True)
        self.setMinimumSize(600, 400)
        
        #self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        dialogLayout = QVBoxLayout()

        self.model = QStandardItemModel()
        self.populate(flowgraph)   # populate the data model

        self.ErrorView = QTableView()
        self.ErrorView.setCornerButtonEnabled(False)
        self.ErrorView.setContentsMargins(10, 10, 10, 10)

        self.ErrorView.setModel(self.model)
        self.ErrorView.resizeColumnsToContents()
        self.ErrorView.resizeRowsToContents()
        self.ErrorView.setShowGrid(False)
        self.ErrorView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.ErrorView.horizontalHeader().setStretchLastSection(True)
        self.ErrorView.setSortingEnabled(True)

        self.OKButtonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, self)
        self.OKButtonBox.button(QDialogButtonBox.StandardButton.Ok).setAutoDefault(True)
        self.OKButtonBox.accepted.connect(self.accept)
        
        dialogLayout.addWidget(self.ErrorView)
        dialogLayout.addWidget(self.OKButtonBox)

        self.setLayout(dialogLayout)
        self.adjustSize()


    def populate(self, flowgraph):
        tableFont = QFont('Helvetica', 9)
        self.model.setHorizontalHeaderLabels(['Block', 'Aspect', 'Message'])
        for element, message in flowgraph.iter_error_messages():
            if element.is_block:
                src, aspect = element.name, ''
            elif element.is_connection:
                src = element.source_block.name
                aspect = "Connection to '{}'".format(element.sink_block.name)
            elif element.is_port:
                src = element.parent_block.name
                aspect = "{} '{}'".format(
                    'Sink' if element.is_sink else 'Source', element.name)
            elif element.is_param:
                src = element.parent_block.name
                aspect = "Param '{}'".format(element.name)
            else:
                src = aspect = ''
            itemSrc = QStandardItem(src)
            itemSrc.setFont(tableFont)
            itemAspect = QStandardItem(aspect)
            itemAspect.setFont(tableFont)
            itemMessage = QStandardItem(message)
            itemMessage.setFont(tableFont)
            self.model.appendRow([itemSrc, itemAspect, itemMessage])
