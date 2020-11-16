# from PyQt5.QtGui import *
from PyQt5.QtWidgets import QApplication, QMainWindow, QDockWidget, QGraphicsScene, QGraphicsView, QToolBar, QPushButton, QFileDialog, QMessageBox, QShortcut, QLabel, QLineEdit, QDoubleSpinBox, QTreeWidgetItem, QDialog
from PyQt5.QtGui import QFont, QImage, QKeySequence, QPixmap, QIcon 
from PyQt5.QtCore import Qt, QTimer
from PyQt5 import uic
import cv2
import os
from pathlib import Path
import time
import sys

from components.config import Config
from components.image import Image
from components.project import Project
from components.annotationManager import *
from components.canvas import Canvas
from components.labelDisp import LabelDispDock
from components.fileList import FileListDock, ImageTreeItem
from components.messages import open_message
from components.enumDef import *
from components.commands import *

from components.extract import AnnoExporter
from components.projectMerge import ProjectMerger
from components.annotationDistribute import AnnotationDistributor
from components.projectReport import ProjectReport
from components.setting import MaskDirDialog
from components.mask2contour import mask2contour

__author__ = 'long, bug'


class MainWindow(QMainWindow):

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        pass

    def __init__(self):
        QMainWindow.__init__(self)
        self.ui = uic.loadUi('uis/mainWindow.ui', baseinstance=self)
        self.setWindowTitle('Image Annotations Toolkit by LfB, RWTH Aachen University')
        self.config = Config('./config/config.cfg')
        self.config['icons'] = {k: QIcon(p) for k, p in ICONS.items()}
        # appearance
        self.font = QFont("Times", pointSize=10)
        self.setFont(self.font)
        self.menuBar.setFont(self.font)

        # utils
        self.livewireGranularityTimer = QTimer()
        self.maskDir = None
        self.masks = []

        ###################################
        #### setup the main components ####
        ###################################

        self.image = Image()
        # setup annotation manager
        self.annotationMgr = AnnotationManager(self.config)
        # setup project
        self.project = Project(self.annotationMgr)
        # setup the canvas
        self.canvas= Canvas(self.config, self.image, self.annotationMgr, self)
        self.annotationMgr.set_canvas(self.canvas)
        # label display docker
        self.labelDisp = LabelDispDock(self.config, self.annotationMgr, self.canvas, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.labelDisp)
        # file list docker
        self.fileList = FileListDock(self.config, self.project, self.annotationMgr, self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.fileList)
        # connect them
        self.maskDirSetting = MaskDirDialog(self)

        ############################
        #### setup the tool bar ####
        ############################
          
        self.toolBar.addWidget(QLabel(" Livewire granularity: "))
        self.livewireGranularity = QDoubleSpinBox(self.toolBar)
        self.livewireGranularity.setKeyboardTracking(False)
        self.livewireGranularity.setMinimum(1)
        # self.livewireGranularity.setMaximum(10)
        self.livewireGranularity.setSingleStep(1)
        self.livewireGranularity.setValue(1)
        self.toolBar.addWidget(self.livewireGranularity)

        ###################
        #### shortcuts ####
        ###################

        hideMaskShortcut = QShortcut(QKeySequence(Qt.Key_Tab), self)
        hideMaskShortcut.activated.connect(self.hideMask)

        ##############################
        #### setup the status bar ####
        ##############################

        self.statusBar.showMessage("Ready ")

        #################################
        #### connect signal to alots ####
        #################################

        # file menu actions
        self.actionProject.triggered.connect(self.open_project)
        self.actionOpenFile.triggered.connect(self.open_file)
        self.actionOpenDirectory.triggered.connect(self.open_directory)
        self.actionSave.triggered.connect(lambda : self.annotationMgr.save(inquiry=False))
        self.actionMask_Directory.triggered.connect(self.set_mask_dir)
        self.actionImport_Mask.triggered.connect(self.import_mask)

        # project menus
        self.actionProjectRemoveDuplicate.triggered.connect(self.project_remove_duplicate)
        self.actionProjectSearch.triggered.connect(self.project_search_images)
        self.actionProjectReport.triggered.connect(self.project_report)

        # annotation menu actions
        self.actionBrowse.triggered.connect(lambda :self.set_tool(BROWSE))
        self.actionPolygon.triggered.connect(lambda :self.set_tool(POLYGON))
        self.actionLivewire.triggered.connect(lambda :self.set_tool(LIVEWIRE, {'scale': 1/self.livewireGranularity.value()}))
        self.actionBounding_Box.triggered.connect(lambda :self.set_tool(BBX))
        self.actionEllipse.triggered.connect(lambda :self.set_tool(OVAL))
        self.actionLine.triggered.connect(lambda :self.set_tool(LINE))
        self.actionDot.triggered.connect(lambda :self.set_tool(POINT))
        self.actionDelete.triggered.connect(self.deleteItem)

        self.actionConvertAnnotations.triggered.connect(self.export_annotation)
        self.actionProjectMerge.triggered.connect(self.project_merge)
        self.actionCollectDistributeAnnotations.triggered.connect(self.collect_distribute_annotations)
        # self.actionDistributeAnnotations.triggered.connect(self.distribute_annotations)
        # self.actionCollectAnnotations.triggered.connect(self.collect_annotations)

        # label menu actions
        self.actionImportLabel.triggered.connect(lambda :self.labelDisp.import_labels(filename=None))
        self.actionExportLabel.triggered.connect(lambda :self.labelDisp.export_labels(filename=None))
        self.actionLoadDefault.triggered.connect(self.labelDisp.load_default_labels)
        self.actionSetAsDefault.triggered.connect(self.labelDisp.save_default_labels)

        # tool menu actions
        self.actionZoomIn.triggered.connect(self.zoom_in)
        self.actionZoomOut.triggered.connect(self.zoom_out)
        self.actionNextImage.triggered.connect(self.fileList.next_image)
        self.actionPreviousImage.triggered.connect(self.fileList.previous_image)
        self.actionAutoContrast.triggered.connect(self.auto_contrast)
        self.actionScreenShot.triggered.connect(self.take_screenshot)
        
        # setting menu actions
        self.actionConfig.triggered.connect(self.start_setting)
        self.actionAbout.triggered.connect(self.show_about)

        # toolBar actions
        self.livewireGranularity.valueChanged.connect(lambda x: self.livewire_granularity_changed())
        self.livewireGranularityTimer.timeout.connect(self.change_livewire_granularity)

        # signal between components
        self.canvas.signalAnnotationSelected.connect(self.labelDisp.refresh_infoTable)
        self.canvas.signalAnnotationReleased.connect(self.labelDisp.refresh_infoTable)
        self.fileList.signalImageChange.connect(self.load)
        self.fileList.signalImport.connect(self.open_directory)

    ###################################
    #### image and annotation load ####
    ###################################

    def load_image(self, image_path):
        if os.path.isfile(image_path):
            print("File opened: ", image_path)
            self.image.open(image_path)
            self.image.set_auto_contrast(self.actionAutoContrast.isChecked())
            if self.project.is_open():
                title = '(project: '+self.project.project_name+') ' + self.image.path
            else:
                title = self.image.path
            self.setWindowTitle(title)
            # refresh display
            self.canvas.sync_image()
            self.sync_statusBar()
            return True
        else:
            return False
    
    def load_annotation(self, annotation_path):
        if annotation_path is not None:
            self.annotationMgr.load(annotation_path)
            self.canvas.add_graphItems()
            self.canvas.refresh()
            self.labelDisp.refresh()

    def load(self, image):
        '''
        Args:
            image: a QTreeWidgetItem or path string
        '''
        # save annotation when necessary
        self.annotationMgr.save()
        # load image and annotation
        if self.project.is_open() and isinstance(image, ImageTreeItem):
            idx = image.idx
            image_path = self.project.get_image_path(idx)
            annotation_path = self.project.get_annotation_path(idx)
            print('open', image_path, annotation_path)
            # update path when necessary
            if not os.path.isfile(image_path):
                if QMessageBox.Yes == QMessageBox.question(None, "Image Path", "Image file not found, would you like to select file manually? You can also use 'Project->Reimport Images' to handle changed image locations in batches ", QMessageBox.Yes | QMessageBox.No):
                    image_path = QFileDialog.getOpenFileName(self, "Select File", self.config['fileDirectory'], filter="Images ("+' '.join(IMAGE_TYPES)+")")[0]
                    if os.path.exists(image_path):
                        self.project.set_image_path(idx, image_path)
                        image.setText(self.project.get_image_name(idx))
        else:
            image_path = image.path if isinstance(image, ImageTreeItem) else image
            annotation_path = os.path.splitext(image_path)[0] + '.' + ANNOTATION_EXT 
        # load image
        image_load_success = self.load_image(image_path)
        if isinstance(image, ImageTreeItem):
            color = Qt.black if image_load_success else Qt.red
            image.setForeground(0, color)
        # load annotation    
        if image_load_success:
            self.load_annotation(annotation_path)
        return image_load_success

    ####################################
    #### porject, file, folder open ####
    ####################################
        
    def open_project(self, filename=None):
        # save project
        self.project.save()
        self.annotationMgr.save()
        # read project name and open
        if not filename:
            project_dialog = QFileDialog(self, "Select Project Directory")
            project_dialog.setLabelText(QFileDialog.Accept, 'Create/Open')
            project_dialog.setNameFilter("*.improj")
            project_dialog.setLabelText(QFileDialog.FileName, 'Project Name')

            if project_dialog.exec_() == QFileDialog.Accepted:
                filename = project_dialog.selectedFiles()[0]
            else:
                filename = ''
        
        if len(filename)>0:
            self.project.open(filename)
            if self.project.is_open():
                self.fileList.init_list(self.project.index_id.keys(), mode='project')
                self.fileList.enableBtn()
                self.sync_statusBar()
                self.config['fileDirectory'] = self.project.proj_dir
    
    def import_annotation(self):
        pass

    def open_file(self):
        if self.project.is_open():
            op = open_message("Open files", "Would you like import a file/files into current project?")
            if op == OP_CANCEL:
                return
            if op == OP_CLOSEANDOPEN:
                self.fileList.close_project()
        filenames = QFileDialog.getOpenFileNames(self, "Select File:", self.config['fileDirectory'], filter="Images ("+' '.join(IMAGE_TYPES)+")")[0]
        if self.project.is_open():
            f = self.fileList.get_selected_folder()
            idx = self.project.add_images(filenames, f)
            self.fileList.add_list(idx, mode='project')
        else:
            status = [os.path.splitext(f)[0] + '.' + ANNOTATION_EXT for f in filenames]
            status = [self.annotationMgr.get_status(s) for s in status] 
            self.fileList.init_list(filenames, status, mode='file')
            if len(filenames) > 0:
                self.load(filenames[0])

    def open_directory(self):
        if self.project.is_open():
            op = open_message("Open directory:", "Would you like import a file into current project?")
            if op == OP_CANCEL:
                return
            if op == OP_CLOSEANDOPEN:
                self.fileList.close_project()
        folder = QFileDialog.getExistingDirectory(self, 'Select Directory')
        if len(folder) != 0:
            files = [str(path) for t in IMAGE_TYPES for path in Path(folder).rglob(t)]
            if self.project.is_open():
                f = self.fileList.get_selected_folder()
                idxs = self.project.add_images(files, f)
                self.fileList.add_list(idxs, mode='project')
            else:
                status = [os.path.splitext(f)[0] + '.' + ANNOTATION_EXT for f in files]
                status = [self.annotationMgr.get_status(s) for s in status] 
                self.fileList.init_list(files, status, mode='file')

    #### project related methods

    def project_search_images(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Directory')
        self.project.search_image(folder)
        self.fileList.init_list(self.project.index_id.keys(), mode='project')
    
    def project_remove_duplicate(self):
        if self.project.is_open():
            self.project.remove_duplicate()
            self.fileList.init_list(self.project.index_id.keys(), mode='project')

    def project_merge(self):
        
        # save project
        self.project.save()
        self.annotationMgr.save()
        # run project merger
        projectMerger = ProjectMerger(self.config)
        projectMerger.projectMerged.connect(self._fileList_refresh)
        if self.project.is_open():
            projectMerger.init_fileList(self.project, fileList='dst')
        projectMerger.exec()
        del projectMerger

    
    def collect_distribute_annotations(self):
        # save project
        self.project.save()
        self.annotationMgr.save()
        # run collect/distribute
        distributor = AnnotationDistributor(self.config)
        distributor.projectMerged.connect(self._fileList_refresh)
        if self.project.is_open():
            distributor.init_fileList(self.project)
        distributor.exec()
        del distributor

    def _fileList_refresh(self, path):
        if self.project.is_open() and os.path.samefile(path, self.project.proj_file):
            self.open_project(path)

    def project_report(self):
        report = ProjectReport(self.config)
        report.init_table(self.project)
        report.exec()
        del report


    def project_close(self):
        self.fileList.close_project()

    #### annotation related
    def set_tool(self, tool, paras=None):
        self.canvas.set_tool(tool, paras)
        self.sync_statusBar()

    def export_annotation(self):
        annoExporter = AnnoExporter(self.config, self.project)
        annoExporter.initial_list(self.fileList)
        annoExporter.exec()
        del annoExporter

    def set_mask_dir(self):
        self.maskDirSetting.exec() == QDialog.Accepted
        if self.maskDirSetting.import_dir is not None:
            file2index, _ = self.update_images_in_dir(self.maskDirSetting.import_dir)
            self.masks = list(file2index.keys())

    def import_mask(self):
        if self.maskDirSetting.import_dir is None:
            QMessageBox.question(self, "Select directory...", "Please set the mask import directory first.", QMessageBox.Yes)
            self.set_mask_dir()
            return
        
        matched_mask = self.match_mask(self.config['currentImageFile'])
        if matched_mask is not None:
            mask_img = cv2.imread(matched_mask, cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
            annotations = mask2contour(mask_img)
            for anno in annotations:
                anno_approxi = np.squeeze(cv2.approxPolyDP(np.float32(anno), 0.7, True))
                self.annotationMgr.new_annotation(POLYGON, anno_approxi)
    
    def match_mask(self, fname):
        if self.masks is None:
            return None
        f_base = os.path.basename(fname)

        flag = 0
        match_len = 0
        for index, mask_name in enumerate(self.masks):
            m_base = os.path.basename(mask_name)
            d = [i for i in range(min(len(f_base), len(m_base))) if f_base[i] != m_base[i]]
            if len(d) == 0:
                flag = index
                break
            elif d[0] > match_len:
                match_len = d[0]
                flag = index
        
        return self.masks[flag]
    

    def deleteItem(self):
        self.canvas.deleteItem()
        self.labelDisp.refresh_infoTable()


    def take_screenshot(self):
        msgBox = QMessageBox()
        msgBox.setWindowFlags(Qt.Dialog | Qt.Desktop)
        msgBox.setText('Which screenshot do you want to take:')
        btnSceen = QPushButton('Screen View')
        msgBox.addButton(btnSceen, QMessageBox.YesRole)
        btnIMMANO = QPushButton('IMMANO View')
        msgBox.addButton(btnIMMANO, QMessageBox.NoRole)
        msgBox.addButton(QPushButton('Image View'), QMessageBox.RejectRole)
        msgBox.exec()
        if msgBox.clickedButton() is btnSceen:
            screen = QApplication.primaryScreen().grabWindow(0)
        elif msgBox.clickedButton() is btnIMMANO:
            screen = self.grab()
        else:
            screen = self.canvas.screenshot()

        dialog = QFileDialog(self, "Save the sreenshot as:")
        dialog.setNameFilter("*.png")
        dialog.setLabelText(QFileDialog.FileName, 'File Name')

        if dialog.exec_() == QFileDialog.Accepted:
            path = dialog.selectedFiles()[0]
            path = os.path.splitext(path)[0] + '.png'
            screen.save(path, "png")

    def start_setting(self):
        pass

    def show_about(self):
        pass

    #### zoom in/out

    def zoom_in(self):
        self.canvas.zoom(ZOOM_IN_RATE)

    def zoom_out(self):
        self.canvas.zoom(ZOOM_OUT_RATE)

    #### livewire granularity

    def livewire_granularity_changed(self):
        self.livewireGranularity.clearFocus()
        self.livewireGranularityTimer.start(200)

    def change_livewire_granularity(self, granularity=None):
        self.livewireGranularityTimer.stop()
        granularity = self.livewireGranularity.value() if granularity is None else granularity
        self.canvas.sync_livewire_image(scale=1/granularity)

    #### display

    def auto_contrast(self):
        if self.actionAutoContrast.isChecked():
            self.image.set_auto_contrast(True)
        else:
            self.image.set_auto_contrast(False)
        self.canvas.sync_image()
        self.sync_statusBar()

    def sync_statusBar(self):
        if self.project.is_open():
            status = '(Project Mode) '
        else:
            status = '(File Mode) '
        
        status = status + 'Annotation Mode: ' + self.canvas.tool
        
        if self.image.auto_contrast == True:
            status = status + ', Auto Contrast: On'
        else:
            status = status + ', Auto Contrast: Off'

        self.statusBar.showMessage(status)
        return status
    
    def hideMask(self):
        channel = self.labelDisp.current_channel()
        if channel != HIDE_ALL:
            self.config['pre_display_channel'] = channel
            self.labelDisp.set_channel(HIDE_ALL)
        else:
            self.labelDisp.set_channel(self.config['pre_display_channel'])

    #### close

    def closeEvent(self, event):
        self.annotationMgr.save()
        self.project.save()
        self.config.save()
        super().closeEvent(event)
        

if __name__ == "__main__":
    # freeze_support()

    app = QApplication(sys.argv)

    with MainWindow() as win:
        win.resize(1600, 900)
        win.show()

    sys.exit(app.exec_())
