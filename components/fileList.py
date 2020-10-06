from PyQt5 import uic
from PyQt5.QtWidgets import QDockWidget, QListWidgetItem
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import Qt, pyqtSignal
import numpy as np
import h5py
import os
from .enumDef import *

class FileListDock(QDockWidget):

    signalImageChange = pyqtSignal(QListWidgetItem)

    def __init__(self, project=None, parent=None):

        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/fileList.ui', baseinstance=self)
        self.project = project

        icon_path = os.path.join(os.path.dirname(__file__), '../icons/')
        # read in icons
        self.icons = {}
        icon = QPixmap()
        icon.load(os.path.join(icon_path, 'marker.png'))
        self.icons[MARKER] = QIcon(icon)
        icon = QPixmap()
        icon.load(os.path.join(icon_path, 'confirmed.png'))
        self.icons[CONFIRMED] = QIcon(icon)
        icon = QPixmap()
        icon.load(os.path.join(icon_path, 'problem.png'))
        self.icons[PROBLEM] = QIcon(icon)
        # init buttons
        self.enableBtn(False)
        # connect signals and slots
        self.fileList.itemDoubleClicked.connect(self.signalImageChange.emit)
        self.btnDelete.clicked.connect(self.delete_image)
        self.btnMark.clicked.connect(self.mark_image)
        self.btnClose.clicked.connect(self.close_project)

    def enableBtn(self, status=True):
        self.btnDelete.setEnabled(status)
        self.btnMark.setEnabled(status)
        self.btnClose.setEnabled(status)

    def init_list(self, file_list, ids=None, status=None, file_exist=None):
        self.fileList.clear()
        self.add_list(file_list, ids, status, file_exist)

    def add_list(self, file_list, ids=None, status=None, file_exist=None):
        if len(file_list) != 0:
            if status is None:
                status = [MARKER for f in file_list]
            if ids is None:
                ids = file_list
            if file_exist is None:
                file_exist = [True] * len(file_list)
            for f, idx, s, ex in zip(file_list, ids, status, file_exist):
                item = QListWidgetItem(self.icons[s], os.path.basename(f))
                if ex is False:
                    item.setForeground(Qt.red)
                item.setData(Qt.UserRole, idx)
                self.fileList.addItem(item)
    
    def next_image(self):
        count = self.fileList.count()
        if count != 1:
            idx = self.fileList.currentRow()
            idx = idx + 1 if idx+1 < count else 0
            self.fileList.setCurrentRow(idx)
            self.signalImageChange.emit(self.fileList.item(idx))
    
    def previous_image(self):
        count = self.fileList.count()
        if count != 1:
            idx = self.fileList.currentRow()
            idx = idx - 1 if idx-1 >= 0 else count-1
            self.fileList.setCurrentRow(idx)
            self.signalImageChange.emit(self.fileList.item(idx))

    def delete_image(self):
        if self.project.is_open():
            if self.fileList.currentRow() >= 0:
                item = self.fileList.takeItem(self.fileList.currentRow())
                self.project.remove_image(item.data(Qt.UserRole))

    def mark_image(self):
        if self.project.is_open():
            item = self.fileList.currentItem()
            if item is not None:
                idx = item.data(Qt.UserRole)
                s = self.project.get_status(item.data(Qt.UserRole))
                if s == MARKER:
                    self.project.set_status(idx, CONFIRMED)
                    item.setIcon(self.icons[CONFIRMED])
                if s == CONFIRMED:
                    self.project.set_status(idx, PROBLEM)
                    item.setIcon(self.icons[PROBLEM])
                if s == PROBLEM:
                    self.project.set_status(idx, MARKER)
                    item.setIcon(self.icons[MARKER])

    def close_project(self):
        self.project.close()
        self.fileList.clear()
        self.enableBtn(False)

            

