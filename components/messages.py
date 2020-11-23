

from PyQt5.QtWidgets import QPushButton, QMessageBox, QDialog
from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5 import uic
from .enumDef import *

class ProgressDiag(QDialog):
    def __init__(self, total, msg="", parent=None):
        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/importProgress.ui', baseinstance=self)
        self.setWindowTitle(msg)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.Desktop)
        self.progressBar.setValue(0)
        self.count = 0
        self.total = total
    
    def keyPressEvent(self, e):
        if e.key() != Qt.Key_Escape:
            super().keyPressEvent(e)
    
    def new_item(self, msg):
        self.count += 1
        # self.fileList.addItem(msg)
        # self.fileList.setCurrentRow(self.fileList.count()-1)
        if int(self.count*100/self.total) - self.progressBar.value() >= 1:
            self.progressBar.setValue(self.count*100/self.total)
        self.status.setText(msg)
        if self.count == self.total:
            self.progressBar.setValue(100)
            self.close() 
        QCoreApplication.processEvents()
    

def open_message(title, msg):
    msgBox = QMessageBox()
    msgBox.setWindowFlags(Qt.Dialog | Qt.Desktop)
    msgBox.setWindowTitle(title)
    msgBox.setText(msg)
    btnImport = QPushButton('Import')
    msgBox.addButton(btnImport, QMessageBox.YesRole)
    btnCloseAndOpen = QPushButton('Close project and open file')
    msgBox.addButton(btnCloseAndOpen, QMessageBox.NoRole)
    msgBox.addButton(QPushButton('Cancel'), QMessageBox.RejectRole)
    msgBox.exec()
    if msgBox.clickedButton() is btnImport:
        return OP_IMPORT
    elif msgBox.clickedButton() is btnCloseAndOpen:
        return OP_CLOSEANDOPEN
    else:
        return OP_CANCEL

def annotation_move_message(title, msg):
    msgBox = QMessageBox()
    msgBox.setWindowFlags(Qt.Dialog | Qt.Desktop)
    msgBox.setWindowTitle(title)
    msgBox.setText(msg)
    btnMerge = QPushButton('Merge')
    msgBox.addButton(btnMerge, QMessageBox.YesRole)
    btnOverwrite = QPushButton('Overwrite')
    msgBox.addButton(btnOverwrite, QMessageBox.NoRole)
    msgBox.addButton(QPushButton('Cancel'), QMessageBox.RejectRole)
    msgBox.exec()
    if msgBox.clickedButton() is btnMerge:
        return OP_MERGE
    elif msgBox.clickedButton() is btnOverwrite:
        return OP_OVERWRITE
    else:
        return OP_CANCEL