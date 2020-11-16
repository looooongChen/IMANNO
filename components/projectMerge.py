from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QFileDialog
from components.project import Project 
from PyQt5.Qt import QAbstractItemView
from components.fileList import FolderTreeItem, ImageTreeItem
from .enumDef import *
from PyQt5.QtCore import Qt, QCoreApplication, pyqtSignal
from .func_annotation import *
# from .func_export import *
# import numpy as np
# from datetime import datetime
# from PIL import Image
# import os
# import h5py
# import csv
# import cv2
# import shutil

#################################

class ProjectMerger(QDialog):

    projectMerged = pyqtSignal(str)

    def __init__(self, config, parent=None):
        super().__init__(parent=parent)
        self.config = config
        self.ui = uic.loadUi('uis/projectMerge.ui', baseinstance=self)
        self.setWindowTitle("Merge Project")
        self.srcProject = None
        self.dstProject = None
        
        self.srcOpenButton.clicked.connect(lambda : self.open_project(fileList='src'))
        self.dstOpenButton.clicked.connect(lambda : self.open_project(fileList='dst'))
        self.srcSelectButton.clicked.connect(lambda : self.select(True, 'src'))
        self.srcUnselectButton.clicked.connect(lambda : self.select(False, 'src'))
        # self.dstSelectButton.clicked.connect(lambda : self.select(True, 'dst'))
        # self.dstUnselectButton.clicked.connect(lambda : self.select(False, 'dst'))
        self.btnMerge.clicked.connect(lambda : self.run(mode='merge'))
        self.btnOverwrite.clicked.connect(lambda : self.run(mode='overwrite'))

        # init file list
        self.srcList.setColumnCount(1)
        self.srcList.setHeaderHidden(True)
        self.srcList.setIndentation(20)
        self.srcList.setRootIsDecorated(False)
        self.srcList.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.srcList.itemChanged.connect(self.on_item_change)

        self.dstList.setColumnCount(1)
        self.dstList.setHeaderHidden(True)
        self.dstList.setIndentation(20)
        self.dstList.setRootIsDecorated(False)
        self.dstList.setSelectionMode(QAbstractItemView.ContiguousSelection)
        # self.dstList.itemChanged.connect(self.on_item_change)

        self.progressBar.setValue(0)
    
    def on_item_change(self, item, col):
        if isinstance(item, FolderTreeItem):
            for j in range(item.childCount()):
                item.child(j).setCheckState(0, item.checkState(0))

    def init_fileList(self, project, fileList='src'):
        if fileList == 'src':
            self.srcProject = project
            fileListWidget = self.srcList
        else:
            self.dstProject = project
            fileListWidget = self.dstList
        # read project name and open
        if project.is_open():
            fileListWidget.clear()
            # add folders
            folders = {}
            for f in sorted(project.data['folders']):
                folder = FolderTreeItem(f)
                folder.set_icon(self.config['icons'][FOLDER])
                if fileList == 'src':
                    folder.setCheckState(0, Qt.Unchecked)
                fileListWidget.addTopLevelItem(folder)
                folders[f] = folder
            # add files
            file_items = list(project.index_id.values())
            file_names = [item.image_name() for item in file_items]
            index = sorted(range(len(file_items)), key=lambda k: file_names[k])
            for idx in index:
                file_item = file_items[idx]
                status = file_item.status()
                item = ImageTreeItem(status=status,
                                     path=file_item.image_path(), idx=file_item.idx())
                item.set_icon(self.config['icons'][status])
                if fileList == 'src':
                    item.setCheckState(0, Qt.Unchecked)
                folder_name = file_item.folder()
                if folder_name is None:
                    fileListWidget.addTopLevelItem(item)
                elif folder_name in folders.keys():
                    folders[folder_name].addChild(item)

    def open_project(self, fileList='src'):
        project_dialog = QFileDialog(self, "Select Project Directory")
        project_dialog.setLabelText(QFileDialog.Accept, 'Create/Open')
        project_dialog.setNameFilter("*.improj")
        project_dialog.setLabelText(QFileDialog.FileName, 'Project Name')

        if project_dialog.exec_() == QFileDialog.Accepted:
            path = project_dialog.selectedFiles()[0]
            project = Project()
            project.open(path)
            if fileList == 'src':
                self.srcProject = project
            else:
                self.dstProject = project
            self.init_fileList(project, fileList)
    
    def select(self, status=True, fileList='src'):
        if fileList == 'src':
            fileList = self.srcList
        else:
            fileList = self.dstList
        if len(fileList.selectedItems()) > 0:
            status = Qt.Checked if status is True else Qt.Unchecked
            for item in fileList.selectedItems():
                item.setCheckState(0, status)

    def run(self, mode='overwrite'):
        self.progressBar.setValue(0)
        srcProject, dstProject = self.srcProject, self.dstProject 
        if srcProject is None or dstProject is None:
            return
        if os.path.samefile(srcProject.proj_file, dstProject.proj_file):
            return
        # get selected items
        items = []
        for i in range(self.srcList.topLevelItemCount()):
            item = self.srcList.topLevelItem(i)
            if isinstance(item, FolderTreeItem):
                for j in range(item.childCount()):
                    child_item = item.child(j)
                    if child_item.checkState(0) == Qt.Checked:
                        items.append(child_item)
            else:
                if item.checkState(0) == Qt.Checked:
                    items.append(item)
        # merge/overwrite items
        total = len(items)
        for progress, item_src in enumerate(items):
            if int(progress*100/total) - self.progressBar.value() >= 1:
                    self.progressBar.setValue(progress*100/total)
            QCoreApplication.processEvents()
            idx_src = item_src.idx
            item_parent = item_src.parent()
            item_src = srcProject.index_id[idx_src]
            if idx_src in dstProject.index_id.keys():
                idx_dst = idx_src
                item_dst = dstProject.index_id[idx_dst]
                checksum_src, checksum_dst = item_src.checksum(), item_dst.checksum()
                if checksum_src is None or checksum_dst is None or checksum_src != checksum_dst:
                    folder = None if item_parent is None else item_parent.text(0)
                    idx_dst = dstProject.add_image(item_src.image_path(), folder)
                    item_dst = dstProject.index_id[idx_dst]
            else:
                folder = None if item_parent is None else item_parent.text(0)
                idx_dst = dstProject.add_image(item_src.image_path(), folder)
                item_dst = dstProject.index_id[idx_dst]
            
            if mode == 'merge':
                anno_merge(item_dst.annotation_path(), item_src.annotation_path())
            else:
                shutil.copy(item_src.annotation_path(), item_dst.annotation_path())
            dstProject.set_status(idx_dst, get_status(item_dst.annotation_path()))
                
        dstProject.save()      
        self.projectMerged.emit(dstProject.proj_file)
        self.init_fileList(dstProject, fileList='dst')
        self.progressBar.setValue(100)




            
