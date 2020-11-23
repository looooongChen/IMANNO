from PyQt5 import uic
from PyQt5.QtWidgets import QDockWidget, QTreeWidgetItem, QMenu, QMessageBox, QWidget, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.Qt import QStandardItem, QStandardItemModel, QAbstractItemView
import numpy as np
import h5py
import os
from .enumDef import *

class FolderTreeItem(QTreeWidgetItem):

    def __init__(self, text=''):
        super().__init__(FOLDER)
        self.setText(0, text)
    
    def set_icon(self, icon):
        self.setIcon(0, icon)

    def clone(self):
        item = FolderTreeItem(text=self.text(0))
        return item
    
class ImageTreeItem(QTreeWidgetItem):

    def __init__(self, status=UNFINISHED, path='', idx=None):
        '''
        Args:
            status: UNFINISHED, FINISHED, CONFIRMED, PROBLEM
            path: path to the image file
            idx: id of a file in the project file 
        '''
        super().__init__(FILE)
        self.path = ''
        self.idx = None
        self.status = status
        self.set_path(path)
        self.idx = idx
    
    def set_status(self, status):
        if status in [UNFINISHED, FINISHED, CONFIRMED, PROBLEM]:
            self.status = status
            
    def set_icon(self, icon):
        self.setIcon(0, icon)

    def set_path(self, path):
        if isinstance(path, str) and len(path) > 0:
            self.path = path
            self.setText(0, os.path.basename(path))
            color = Qt.black if os.path.isfile(path) else Qt.red
            self.setForeground(0, color)
    
    def set_idx(self, idx):
        self.idx = idx

    def clone(self):
        item = ImageTreeItem(status=self.status, path=self.path, idx=self.idx)
        return item


class FileListDock(QDockWidget):

    signalImageChange = pyqtSignal(ImageTreeItem)
    signalImport = pyqtSignal()

    def __init__(self, config, project, annotationMgr, parent=None):

        super().__init__(parent=parent)
        self.ui = uic.loadUi('uis/fileList.ui', baseinstance=self)
        self.config = config
        self.project = project
        self.annotationMgr = annotationMgr
        self.folders = {}

        # init file list
        self.fileList.setColumnCount(1)
        self.fileList.setHeaderHidden(True)
        self.fileList.setIndentation(20)
        self.fileList.setRootIsDecorated(False)
        self.fileList.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.fileList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.setTitleBarWidget(QWidget())

        # init right click menu
        self.menu = QMenu(self)
        self.actionNewFolder = self.menu.addAction(QIcon(ICONS[FOLDER]), 'New folder')
        self.actionDel = self.menu.addAction(QIcon(ICONS[DELETE]), 'Delete')
        self.actionRename = self.menu.addAction(QIcon(ICONS[RENAME]), 'Rename')
        self.actionImport = self.menu.addAction(QIcon(ICONS[IMPORT]), 'Import')
        self.actionSearch = self.menu.addAction(QIcon(ICONS[SEARCH]), 'Search')

        # init buttons
        self.enableBtn(False)
        # connect signals and slots
        self.fileList.customContextMenuRequested.connect(self.show_menu)
        self.fileList.itemDoubleClicked.connect(self.double_clicked)
        self.fileList.itemChanged.connect(self.on_item_change, Qt.QueuedConnection)
        self.actionNewFolder.triggered.connect(lambda x:self.add_folder(folder_name=None))
        self.actionRename.triggered.connect(lambda x: self.rename(item=None))
        self.actionDel.triggered.connect(self.delete)
        self.actionImport.triggered.connect(self.import_folder)
        self.actionSearch.triggered.connect(self.search_images)

        self.btnMark.clicked.connect(self.mark_image)
        self.btnClose.clicked.connect(self.close_project)

    def enableBtn(self, status=True):
        # self.btnMark.setEnabled(status)
        self.btnClose.setEnabled(status)
        self.actionNewFolder.setEnabled(status)
        self.actionDel.setEnabled(status)
        self.actionRename.setEnabled(status)
        self.actionImport.setEnabled(status)
        self.actionSearch.setEnabled(status)
    
    def show_menu(self, pos):
        self.menu.exec(self.fileList.mapToGlobal(pos))

    def on_item_change(self, item, col):
        if isinstance(item, FolderTreeItem):
            keys = list(self.folders.keys())
            for k in keys:
                if self.folders[k] is item:
                    # if inconsistency exists
                    if k != item.text(0):
                        if item.text(0) not in self.folders.keys():
                            self.project.rename_folder(k, item.text(0))
                            self.folders[item.text(0)] = self.folders.pop(k)
                        else:
                            self.fileList.blockSignals(True)
                            item.setText(0, k)
                            self.fileList.blockSignals(False)
                            self.rename(item)

    
    def get_selected_folder(self):
        for s in self.fileList.selectedItems():
            if isinstance(s, FolderTreeItem):
                return s.text(0)
        return None
    
    def import_folder(self):
        self.signalImport.emit()
        
    #### initialize and add list

    def clear(self):
        self.folders = {}
        self.fileList.clear()

    def init_list(self, files, status=None, mode='file'):
        '''
        Args:
            file: a list of file path or ids in project
            mode: 'file' or 'project'
        '''
        self.clear()
        if mode == 'project':
            for f in sorted(self.project.data['folders']):
                self.add_folder(f)
        self.add_list(files, status, mode)

    def add_list(self, files, status=None, mode='file'):
        '''
        Args:
            file: a list of file path or ids in project
            status: only used in 'file' mode
            mode: 'file' or 'project'
        '''
        if mode == 'file':
            status = [UNFINISHED] * len(files) if status is None else status
            file_names = [os.path.basename(f) for f in files]
            index = sorted(range(len(file_names)), key=lambda k: file_names[k])
            for idx in index:
                item = ImageTreeItem(status=status[idx], path=files[idx])
                item.set_icon(self.config['icons'][status[idx]])
                self.fileList.addTopLevelItem(item)
        elif self.project is not None and self.project.is_open():
            file_items = [self.project.index_id[idx] for idx in files if idx in self.project.index_id.keys()]
            file_names = [item.image_name() for item in file_items]
            index = sorted(range(len(file_items)), key=lambda k: file_names[k])
            for idx in index:
                file_item = file_items[idx]
                status = file_item.status()
                item = ImageTreeItem(status=status,
                                     path=file_item.image_path(), idx=file_item.idx())
                item.set_icon(self.config['icons'][status])
                folder = file_item.folder()
                if folder is None:
                    self.fileList.addTopLevelItem(item)
                elif folder in self.folders:
                    self.folders[folder].addChild(item)
                else:
                    folder = FolderTreeItem(folder)
                    folder.set_icon(self.config['icons'][FOLDER])
                    self.fileList.addTopLevelItem(folder)
                    self.folders[folder] = folder
                    folder.addChild(item)

    #### add and remove files/folders

    def rename(self, item=None):
        '''
        rename only if the item is a folder
        '''
        item = self.fileList.selectedItems()[0] if item is None else item
        if isinstance(item, FolderTreeItem):
            self.fileList.blockSignals(True)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.fileList.editItem(item, 0)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.fileList.blockSignals(False)

    def add_folder(self, folder_name=None):
        if self.project.is_open():
            new = True if folder_name is None else False
            if folder_name is None:
                index = 0
                while True:
                    folder_name = 'unamed folder ' + str(index)
                    if folder_name not in self.folders.keys():
                        break
                    index += 1
            if folder_name not in self.folders.keys():
                self.project.add_folder(folder_name)
                folder = FolderTreeItem(folder_name)
                folder.set_icon(self.config['icons'][FOLDER])
                self.fileList.addTopLevelItem(folder)
                self.folders[folder_name] = folder
                if new:
                    self.rename(folder)
    
    def delete(self):
        if self.project.is_open():
            selected = self.fileList.selectedItems()
            if QMessageBox.No == QMessageBox.question(None, "Delete", "Are you sure you want to remove all selected files/folders (annotation files will be removed permenantly, original images unchanged)? ", QMessageBox.Yes | QMessageBox.No):
                return
            for item in selected:
                if isinstance(item, ImageTreeItem):
                    self.project.remove_image(item.idx)
                    if item.parent() is not None:
                        item.parent().removeChild(item)
                    else:
                        self.fileList.invisibleRootItem().removeChild(item)
                if isinstance(item, FolderTreeItem):
                    self.project.delete_folder(item.text(0))
                    self.fileList.invisibleRootItem().removeChild(item)

    def search_images(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Directory')
        self.project.search_image(folder)
        self.init_list(self.project.index_id.keys(), mode='project')

    def next_image(self):
        if self.fileList.topLevelItemCount() > 1:
            item = self.fileList.currentItem()
            if isinstance(item, ImageTreeItem):
                parent = item.parent() 
                if parent is None:
                    parent = self.fileList.invisibleRootItem()
                count = parent.childCount()
                if count > 1:
                    idx = parent.indexOfChild(item)
                    idx = idx + 1 if idx+1 < count else 0
                    item = parent.child(idx)
            if isinstance(item, FolderTreeItem):
                count = item.childCount()
                if count >= 1:
                    item = item.child(0)
            if item is None:
                item = topLevelItem(0)
            self.fileList.setCurrentItem(item)
            self.signalImageChange.emit(item)

    
    def previous_image(self):
        if self.fileList.topLevelItemCount() > 1:
            item = self.fileList.currentItem()
            if isinstance(item, ImageTreeItem):
                parent = item.parent()
                if parent is None:
                    parent = self.fileList.invisibleRootItem()
                count = parent.childCount()
                if count > 1:
                    idx = parent.indexOfChild(item)
                    idx = idx - 1 if idx-1 >= 0 else count-1
                    item = parent.child(idx)
            if isinstance(item, FolderTreeItem):
                count = item.childCount()
                if count >= 1:
                    item = item.child(count-1)
            if item is None:
                item = topLevelItem(0)
            self.fileList.setCurrentItem(item)
            self.signalImageChange.emit(item)

    def double_clicked(self, item):
        if item.type() == FILE:
            self.signalImageChange.emit(item)

    def mark_image(self):
        items = self.fileList.selectedItems()
        for item in items:
            if item.type() == FILE:
                if self.project.is_open():
                    idx = item.idx
                    status = self.project.get_status(idx)
                    status = self._change_mark(item, status)
                    self.project.set_status(idx, status)
                else:
                    path = os.path.splitext(item.path)[0] + ANNOTATION_EXT
                    status = self.annotationMgr.get_status(path)
                    status = self._change_mark(item, status)
                    self.annotationMgr.set_status(status, path)

    def _change_mark(self, item, status):
        if status == UNFINISHED:
            item.setIcon(0, self.config['icons'][FINISHED])
            return FINISHED
        if status == FINISHED:
            item.setIcon(0, self.config['icons'][CONFIRMED])
            return CONFIRMED
        if status == CONFIRMED:
            item.setIcon(0, self.config['icons'][PROBLEM])
            return PROBLEM
        if status == PROBLEM:
            item.setIcon(0, self.config['icons'][UNFINISHED])
            return UNFINISHED
        item.setIcon(0, self.config['icons'][UNFINISHED])
        return UNFINISHED

    def close_project(self):
        self.folders = {}
        self.project.close()
        self.fileList.clear()
        self.enableBtn(False)
  

            

