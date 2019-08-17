#!/usr/bin/env python3

import os
import sys

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import *
import pyqtgraph as pg

import parser


pg.setConfigOption('background', 'w')


class PlotGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.log = None
        self.initUI()

    def initUI(self):

        self.message_timeout = 2500

        # ======================================================================
        # widgets
        # ======================================================================
        self.log_name_text_edit = QLineEdit()  # TODO allow passing in via command line
        self.browse_button = QPushButton('Browse...')
        self.process_button = QPushButton('Process')

        self.plot_manager_widget = PlotManagerWidget()

        # -----------------------------------------------------------------------
        # initial states
        # -----------------------------------------------------------------------
        self.process_button.setEnabled(False)

        # ======================================================================
        # signals and slots
        # ======================================================================
        self.log_name_text_edit.textChanged.connect(self.onLogNameTextChanged)
        self.browse_button.clicked.connect(self.onBrowseClicked)
        self.process_button.clicked.connect(self.onProcessClicked)

        # ======================================================================
        # layout
        # ======================================================================

        # -----------------------------------------------------------------------
        # info bar
        # -----------------------------------------------------------------------
        self.log_name_text_edit.setMaximumHeight(24)

        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel('Log File:'))
        info_layout.addWidget(self.log_name_text_edit)
        info_layout.addWidget(self.browse_button)
        info_layout.addWidget(self.process_button)

        # -----------------------------------------------------------------------
        # finalize
        # -----------------------------------------------------------------------
        root_layout = QVBoxLayout()

        root_layout.addLayout(info_layout)

        root_layout.addWidget(self.plot_manager_widget)
        root_layout.setStretchFactor(self.plot_manager_widget, 1)

        main_widget = QWidget()
        main_widget.setLayout(root_layout)
        self.setCentralWidget(main_widget)

        # ======================================================================
        # show window
        # ======================================================================
        self.setWindowTitle('Log Plotting GUI')
        self.statusBar().show()
        self.show()

    def onLogNameTextChanged(self):
        if os.path.isfile(self.log_name_text_edit.text()):
            self.log_name_text_edit.setStyleSheet('color: black;')
            self.process_button.setEnabled(True)
        else:
            self.log_name_text_edit.setStyleSheet('color: red;')
            self.process_button.setEnabled(False)

    def onBrowseClicked(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Open File', '~')
        self.log_name_text_edit.setText(filename)

    def onProcessClicked(self):
        log_file = self.log_name_text_edit.text()

        self.statusBar().showMessage('Processing...')
        self.lockUI()
        try:
            self.log = parser.Log(log_file)
            self.plot_manager_widget.onLogProccessed(self.log)
        except FileNotFoundError:
            self.statusBar().showMessage('Error', self.message_timeout)
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle('Log File Error')
            msg.setText("Log file '{}' not found".format(log_file))
            msg.setStandardButtons(QMessageBox.Close)
            msg.exec_()
        except parser.InvalidLogFile:
            self.statusBar().showMessage('Error', self.message_timeout)
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle('Log File Error')
            msg.setText("File '{}' is not a valid log file".format(log_file))
            msg.setStandardButtons(QMessageBox.Close)
            msg.exec_()
        except:
            self.statusBar().showMessage('Error', self.message_timeout)
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle('Log File Error')
            msg.setText(
                "There was an error processing file '{}'".format(log_file))
            msg.setStandardButtons(QMessageBox.Close)
            msg.exec_()
        else:
            self.statusBar().showMessage('Done', self.message_timeout)
            print("Found streams {}".format(self.log.data.keys()))
            # pass # handle successful parsing of log file
        finally:
            self.unlockUI()

    def lockUI(self):
        self.process_state = self.process_button.isEnabled()

        self.process_button.setEnabled(False)
        self.browse_button.setEnabled(False)
        self.log_name_text_edit.setEnabled(False)
        self.repaint()

    def unlockUI(self):
        self.process_button.setEnabled(self.process_state)
        self.browse_button.setEnabled(True)
        self.log_name_text_edit.setEnabled(True)
        self.repaint()


class PlotManagerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # widgets
        self.tree_manager = TreeManagerWidget()

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)

        self.tabs.addTab(pg.PlotWidget(), "Tab 1")
        self.tabs.addTab(QTextBrowser(), "Tab 2")

        meh = pg.PlotWidget()
        self.tabs.addTab(meh, "Meh")
        meh.plot([1, 2, 3, 4, 5], [3, 4, 2, 6, 4],
                 pen=pg.mkPen(width=2, color=(2, 9)))

        # signals and slots
        self.tree_manager.addPlot.connect(self.onAddPlot)
        self.tabs.tabCloseRequested.connect(self.onTabCloseRequested)

        # layout
        splitter = QSplitter()

        splitter.addWidget(self.tree_manager)
        splitter.addWidget(self.tabs)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        root_layout = QGridLayout()
        root_layout.addWidget(splitter)
        self.setLayout(root_layout)

    def onLogProccessed(self, log):
        self.tree_manager.onLogProccessed(log)

    def onAddPlot(self):
        self.tabs.addTab(QTextBrowser(), "New Tab")
        self.tabs.setCurrentIndex(self.tabs.count() - 1)

    def onTabCloseRequested(self, index):
        self.tabs.removeTab(index)


class TreeManagerWidget(QWidget):
    addPlot = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # widgets
        self.add_plot_button = QPushButton("Add New Plot")
        self.tree = PlotTreeWidget()

        self.single_axis_button = QRadioButton("Single Y Axis")
        self.individual_axes_button = QRadioButton("Individual Y Axes")

        # initial states
        self.single_axis_button.setChecked(True)

        # signals and slots
        self.add_plot_button.clicked.connect(self.onAddPlotClicked)

        # layout
        layout = QVBoxLayout()
        layout.addWidget(self.add_plot_button)
        layout.addWidget(self.tree)

        button_layout = QVBoxLayout()
        button_layout.addWidget(self.single_axis_button)
        button_layout.addWidget(self.individual_axes_button)

        group = QGroupBox("Axis Options")
        group.setLayout(button_layout)

        layout.addWidget(group)

        self.setLayout(layout)

    def onLogProccessed(self, log):
        self.tree.onLogProccessed(log)

    def onAddPlotClicked(self):
        self.addPlot.emit()


class PlotTreeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.tree = QTreeWidget()

        self.tree.setColumnCount(1)
        self.tree.setHeaderLabels(["Name"])

        # self.tree.setSortingEnabled(True)
        # self.tree.sortItems(0, Qt.AscendingOrder)

        # signals and slots
        self.tree.itemChanged.connect(self.onItemSelectionChanged)

        # layout
        layout = QGridLayout()
        layout.addWidget(self.tree)
        self.setLayout(layout)

    def onLogProccessed(self, log):
        self.populateTree(log)
        self.initializeState(log)

    def populateTree(self, log):
        self.tree.clear()

        for name, data in log.data.items():

            if data.ndim == 1:
                type_str = ""
            elif data.ndim == 2:
                type_str = " ({}-Vector; {})".format(
                    data.shape[1], data.dtype.name)
            elif data.ndim == 3:
                type_str = " ({}x{} Matrix; {})".format(
                    data.shape[1], data.shape[2], data.dtype.name)

            parent = QTreeWidgetItem(["{}{}".format(name, type_str)])
            parent.setFlags(parent.flags() |
                            Qt.ItemIsTristate | Qt.ItemIsUserCheckable)

            if data.ndim == 1:  # scalar
                for field, (dtype, _) in data.dtype.fields.items():
                    child = QTreeWidgetItem(["{} ({})".format(field, dtype.name)])
                    child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                    child.setCheckState(0, Qt.Unchecked)
                    parent.addChild(child)
            elif data.ndim == 2:  # vector
                for i in range(data.shape[1]):
                    child = QTreeWidgetItem(["[{}]".format(i)])
                    child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                    child.setCheckState(0, Qt.Unchecked)
                    parent.addChild(child)
            elif data.ndim == 3:  # matrix
                for i in range(data.shape[1]):
                    for j in range(data.shape[2]):
                        child = QTreeWidgetItem(["[{}, {}]".format(i, j)])
                        child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                        child.setCheckState(0, Qt.Unchecked)
                        parent.addChild(child)

            parent.setExpanded(True)
            self.tree.addTopLevelItem(parent)

        # self.tree.expandAll()

    def initializeState(self, log):
        self.state = {}
        for name, data in log.data.items():
            self.state[name] = {}

            if data.ndim == 1: # scalar
                for field in data.dtype.names:
                    self.state[name][field] = False
            elif data.ndim == 2: # vector
                for i in range(data.shape[1]):
                    self.state[name][i] = False
            elif data.ndim == 3: # matrix
                for i in range(data.shape[1]):
                    self.state[name][i] = {}
                    for j in range(data.shape[2]):
                        self.state[name][i][j] = False

    def onItemSelectionChanged(self, item):
        print(item.checkState(0))
        print(self.state)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = PlotGUI()
    sys.exit(app.exec_())
