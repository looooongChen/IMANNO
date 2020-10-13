

from PyQt5.QtWidgets import QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from .enumDef import *

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