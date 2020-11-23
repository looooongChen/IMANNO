from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox
from components.project import Project 
from PyQt5.Qt import QAbstractItemView
from components.fileList import FolderTreeItem, ImageTreeItem
from .enumDef import *
from PyQt5.QtCore import Qt, QCoreApplication, pyqtSignal
from .func_annotation import *
from .messages import annotation_move_message


#################################

class AnnotationDistributor(QDialog):

    projectMerged = pyqtSignal(str)

    def __init__(self, config, parent=None):
        super().__init__(parent=parent)
        self.config = config
        self.ui = uic.loadUi('uis/distributeCollect.ui', baseinstance=self)
        self.setWindowTitle("Collect/Distribute Annotion Files to Image Locations ...")
        self.project = None
        
        self.btnOpen.clicked.connect(self.open_project)
        self.btnSelect.clicked.connect(lambda : self.select(True))
        self.btnUnselect.clicked.connect(lambda : self.select(False))
        self.btnDistribute.clicked.connect(lambda : self.run(mode='distribute'))
        self.btnCollect.clicked.connect(lambda : self.run(mode='collect'))
        self.btnDelete.clicked.connect(lambda : self.run(mode='delete'))

        # init file list
        self.fileList.setColumnCount(1)
        self.fileList.setHeaderHidden(True)
        self.fileList.setIndentation(20)
        self.fileList.setRootIsDecorated(False)
        self.fileList.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.fileList.itemChanged.connect(self.on_item_change)


        self.progressBar.setValue(0)
    
    def on_item_change(self, item, col):
        if isinstance(item, FolderTreeItem):
            for j in range(item.childCount()):
                item.child(j).setCheckState(0, item.checkState(0))

    def init_fileList(self, project):

        self.project = project
        if project.is_open():
            self.fileList.clear()
            # add folders
            folders = {}
            for f in sorted(project.data['folders']):
                folder = FolderTreeItem(f)
                folder.set_icon(self.config['icons'][FOLDER])
                folder.setCheckState(0, Qt.Unchecked)
                self.fileList.addTopLevelItem(folder)
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
                item.setCheckState(0, Qt.Unchecked)
                folder_name = file_item.folder()
                if folder_name is None:
                    self.fileList.addTopLevelItem(item)
                elif folder_name in folders.keys():
                    folders[folder_name].addChild(item)

    def open_project(self):
        project_dialog = QFileDialog(self, "Select Project Directory")
        project_dialog.setLabelText(QFileDialog.Accept, 'Create/Open')
        project_dialog.setNameFilter("*.improj")
        project_dialog.setLabelText(QFileDialog.FileName, 'Project Name')

        if project_dialog.exec_() == QFileDialog.Accepted:
            path = project_dialog.selectedFiles()[0]
            project = Project()
            project.open(path)
            self.project = project
            self.init_fileList(project)
    
    def select(self, status=True):
        if len(self.fileList.selectedItems()) > 0:
            status = Qt.Checked if status is True else Qt.Unchecked
            for item in self.fileList.selectedItems():
                item.setCheckState(0, status)

    def run(self, mode='distribute'):
        '''
        Args:
            mode: 'distribute'/'collect'/'delete'
        '''
        self.progressBar.setValue(0)
        if self.project is not None and self.project.is_open():
            # query
            if mode == 'distribute':
                op = annotation_move_message('Distribute annotations', 'Would you like to merge or overwrite annotation files?')
            elif mode == 'collect':
                op = annotation_move_message('Collect annotations', 'Would you like to merge or overwrite annotation files?')
            elif mode == 'delete':
                if QMessageBox.No == QMessageBox.question(None, "Image Path", "Would you like to delete annotation files alongside the images?", QMessageBox.Yes | QMessageBox.No):
                    op = OP_CANCEL
                else:
                    op = OP_OVERWRITE
            else:
                return
            if op != OP_CANCEL:
                # get selected items
                items = []
                for i in range(self.fileList.topLevelItemCount()):
                    item = self.fileList.topLevelItem(i)
                    if isinstance(item, FolderTreeItem):
                        for j in range(item.childCount()):
                            child_item = item.child(j)
                            if child_item.checkState(0) == Qt.Checked:
                                items.append(child_item)
                    else:
                        if item.checkState(0) == Qt.Checked:
                            items.append(item)
                # operate
                total = len(items)
                for progress, item in enumerate(items):
                    if int(progress*100/total) - self.progressBar.value() >= 1:
                        self.progressBar.setValue(progress*100/total)
                    idx = item.idx
                    file_item = self.project.index_id[idx]
                    image_path = file_item.image_path()
                    if os.path.isfile(image_path):
                        if mode == 'distribute':
                            ## hdf5 compatible
                            anno_path = os.path.splitext(image_path)[0] + os.path.splitext(file_item.annotation_path())[1]
                            if op == OP_MERGE:
                                anno_merge(anno_path, file_item.annotation_path())
                            elif op == OP_OVERWRITE:
                                anno_copy(anno_path, file_item.annotation_path())
                        elif mode == 'collect':
                            ## hdf5 compatible
                            anno_path = os.path.splitext(image_path)[0] + ANNOTATION_EXT
                            if not os.path.isfile(anno_path):
                                anno_path = os.path.splitext(image_path)[0] + '.hdf5'
                            if op == OP_MERGE:
                                anno_merge(file_item.annotation_path(), anno_path)
                            elif op == OP_OVERWRITE:
                                anno_copy(file_item.annotation_path(), anno_path)
                            self.project.set_status(idx, get_status(file_item.annotation_path()))
                        elif mode == 'delete':
                            if os.path.isfile(anno_path):
                                os.remove(anno_path)
                self.project.save()      
                self.projectMerged.emit(self.project.proj_file)
                self.init_fileList(self.project)
                self.progressBar.setValue(100)




            
