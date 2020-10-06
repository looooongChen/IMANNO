import os.path as ospath
import os
# from PyQt5.QtGui import *
from PyQt5.QtWidgets import QApplication, QMainWindow, QDockWidget, QGraphicsScene, QGraphicsView, QSizePolicy, QWidget, QToolBar, QPushButton, QFileDialog, QMessageBox, QShortcut, QLabel, QLineEdit, QDoubleSpinBox, QListWidgetItem
from PyQt5.QtGui import QFont, QImage, QKeySequence
from PyQt5.QtCore import Qt, QTimer
import json
import cv2
from PyQt5 import uic

from components.scene import Scene
from components.labelDisp import LabelDispDock
from components.fileList import FileListDock
from components.extract import AnnoExporter
from components.clean_data import AnnotationCleaner
from components.setting import MaskDirDialog
from components.mask2contour import mask2contour
from components.image import Image
from components.project import Project
from pathlib import Path
import time
import sys


from multiprocessing import freeze_support, set_executable
# import openslide as osl

from components.enumDef import *
from components.commands import *
from components.annotationManager import *


__author__ = 'long, bug'


class Config(dict):

    def __init__(self, basic_config=None):
        self.static_config = ['fileDirectory', 'defaultLabelListDir', 'DotAnnotationRadius', 'lineAnnotationWidth']
        # default config
        self['fileDirectory'] = './demo_images'
        self['defaultLabelListDir'] = './config'
        self['DotAnnotationRadius'] = 2
        self['lineAnnotationWidth'] = 2
        if basic_config is not None and ospath.exists(basic_config):
            with open(basic_config, 'r') as f:
                for k, value in json.load(f).items():
                    self[k] = value
                    self.static_config.append(k)

    def save(self, path):
        save_dict = {}
        for k in self.static_config:
            save_dict[k] = self[k]
        with open(path, 'w') as f:
            json.dump(save_dict, f)


class Canvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setAcceptDrops(True)
        self.current_scale = 1
        self.setMouseTracking(True)

    def zoom(self, scale):
        self.scale(scale,scale)
        self.current_scale = self.current_scale * scale

    def recovery_scale(self):
        self.scale(1/self.current_scale, 1/self.current_scale)
        self.current_scale = 1

    # def dropEvent(self, event):
    #     fname = str(event.mimeData().data('text/uri-list'), encoding='utf-8')
    #     fname = fname.replace('file:///', '')
    #     fname = fname.rstrip('\r\n')
    #     print(fname, ' -> D')
    #     self.parent().open(filename=fname)

    # def dragEnterEvent(self, event):
    #     if event.mimeData().hasFormat('application/x-qt-windows-mime;value="FileNameW"'):
    #         event.acceptProposedAction()

    # def dragMoveEvent(self, event):
    #     pass


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
        # appearance
        self.font = QFont("Times", pointSize=10)
        self.setFont(self.font)
        self.menuBar.setFont(self.font)

        # data
        self.project = Project()
        self.image = Image()
        self.annotation_file = ''

        self.maskDir = None
        self.masks = []
        self.display_channel_buffer = None

        # utils
        self.livewireGranularityTimer = QTimer()

        ###################################
        #### setup the main components ####
        ###################################

        # setup the grahicsView for display
        self.canvas = Canvas(parent=self)
        # setup the scene
        self.scene = Scene(config=self.config, image=self.image, canvas=self.canvas, parent=self)
        # label display docker
        self.labelDisp = LabelDispDock(config=self.config, scene=self.scene, parent=self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.labelDisp)
        self.labelDisp.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.labelDisp.setTitleBarWidget(QWidget())
        # file list docker
        self.fileList = FileListDock(self.project, self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.fileList)
        self.fileList.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.fileList.setTitleBarWidget(QWidget())
        # setup annotation manager
        self.annotationMgr = AnnotationManager(config=self.config, project=self.project, scene=self.scene, labelDisp=self.labelDisp)
        # connect them

        self.maskDirSetting = MaskDirDialog(self)

        # initial display
        self.canvas.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.canvas.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(self.canvas)
        self.canvas.show()

        
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
        # self.labelDisp.hide()

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
        # self.actionProjectMerge.triggered.connect()
        self.actionProjectCheckDuplicate.triggered.connect(self.project_check_duplicate)
        self.actionProjectReimport.triggered.connect(self.project_reimport_images)

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
        self.actionCleanNoisyAnnotations.triggered.connect(self.clean_annotation)
        self.actionFileLocationsToProject.triggered.connect(self.collect_annotations)
        self.actionProjectToFileLocations.triggered.connect(self.distribute_annotations)

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
        self.scene.annotationSelected.connect(self.labelDisp.refresh_infoTable)
        self.scene.annotationReleased.connect(self.labelDisp.refresh_infoTable)
        self.fileList.signalImageChange.connect(self.load)

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
            self.scene.sync_image()
            self.sync_statusBar()
            return True
        else:
            return False

    def load(self, image, annotation_path=''):
        '''
        Args:
            image: a QListWidgetItem or path string
        '''
        # save annotation when necessary
        self.annotationMgr.save()
        # load image and annotation
        image_id = image.data(Qt.UserRole) if isinstance(image, QListWidgetItem) else image
        if self.project.is_open():
            # update path when necessary
            path_updated = False
            image_path = self.project.get_image_path(image_id)
            if not os.path.isfile(image_path):
                if QMessageBox.Yes == QMessageBox.question(None, "Image Path", "Image file not found, would you like to select file manually? You can also use 'Project->Reimport Images' to handle changed image locations in batches ", QMessageBox.Yes | QMessageBox.No):
                    image_path = QFileDialog.getOpenFileName(self, "Select File", self.config['fileDirectory'], filter="Images ("+' '.join(IMAGE_TYPES)+")")[0]
                    self.project.set_image_path(image_id, image_path)
                    path_updated = True
            # load image
            image_load_success = self.load_image(image_path)
            color = Qt.black if image_load_success else Qt.red
            image.setForeground(color)
            if image_load_success: 
                if self.project.get_checksum(image_id) is None or path_updated:
                    self.project.set_checksum(image_id, self.image)
                if path_updated:
                    image.setText(self.project.get_image_name(image_id))
        else:
            image_path = image_id
            image_load_success = self.load_image(image_path)
            
        if image_load_success:
            self.annotationMgr.load_annotation(image_id)
        return image_load_success
        
    def open_project(self, filename=None):
        # save project
        self.project.save()
        # read project name and open
        if not filename:
            project_dialog = QFileDialog(self, "Select Project Directory")
            project_dialog.setLabelText(QFileDialog.Accept, 'Create/Open')
            project_dialog.setNameFilter("*.improj")
            project_dialog.setLabelText(QFileDialog.FileName, 'Project Name')

            if project_dialog.exec_() == QFileDialog.Accepted:
                path = project_dialog.selectedFiles()[0]
                self.project.open(path)
            
            if self.project.is_open():
                self.fileList.init_list(*self.project.filenames(check_exist=True))
                self.fileList.enableBtn()
                self.sync_statusBar()

    def open_file(self):
        if self.project.is_open():
            if QMessageBox.No == QMessageBox.question(None, "Important...", "Would you like import a file into current project?", QMessageBox.Yes | QMessageBox.No):
                self.project_close()
        filename = QFileDialog.getOpenFileName(self, "Select File", self.config['fileDirectory'], filter="Images ("+' '.join(IMAGE_TYPES)+")")[0]
        if len(filename) != 0:
            if self.project.is_open():
                idx, fname = self.project.add_image(filename)
                self.fileList.add_list([fname], ids=[idx])
            else:
                self.fileList.init_list([filename])
                self.load(filename)

    def open_directory(self):
        if self.project.is_open():
            if QMessageBox.No == QMessageBox.question(None, "Important...", "Would you like import a directory into current project?", QMessageBox.Yes | QMessageBox.No):
                self.project_close()
        folder = QFileDialog.getExistingDirectory(self, 'Select Directory')
        if len(folder) != 0:
            files = [str(path) for t in IMAGE_TYPES for path in Path(folder).rglob(t)]
            if self.project.is_open():
                ids, fnames = self.project.add_images(files)
                self.fileList.add_list(fnames, ids=ids)
            else:
                self.fileList.init_list(files)

    #### project related methods

    def project_reimport_images(self):
        folder = QFileDialog.getExistingDirectory(self, 'Select Directory')
        self.project.reimport_image(folder)
        self.fileList.init_list(*self.project.filenames(check_exist=True))
    
    def project_check_duplicate(self):
        self.project.check_duplicate()
        self.fileList.init_list(*self.project.filenames(check_exist=True))
    
    def project_close(self):
        self.fileList.close_project()

    #### annotation related
    def set_tool(self, tool, paras=None):
        self.scene.set_tool(tool, paras)
        self.sync_statusBar()

    def export_annotation(self):
        annoExporter = AnnoExporter()
        annoExporter.exec()
        del annoExporter

    def clean_annotation(self):
        annotationCleaner = AnnotationCleaner()
        annotationCleaner.exec()
        del annotationCleaner

    def collect_annotations(self):
        pass

    def distribute_annotations(self):
        pass

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
        self.scene.deleteItem()
        self.labelDisp.refresh_infoTable()


    def take_screenshot(self):
        pass

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
        self.scene.sync_livewire_image(scale=1/granularity)

    #### display

    def auto_contrast(self):
        if self.actionAutoContrast.isChecked():
            self.image.set_auto_contrast(True)
        else:
            self.image.set_auto_contrast(False)
        self.scene.sync_image()
        self.sync_statusBar()

    def sync_statusBar(self):
        if self.project.is_open():
            status = '(Project Mode) '
        else:
            status = '(File Mode) '
        
        status = status + 'Annotation Mode: ' + self.scene.tool
        
        if self.image.auto_contrast == True:
            status = status + ', Auto Contrast: On'
        else:
            status = status + ', Auto Contrast: Off'

        self.statusBar.showMessage(status)
        return status
    
    def hideMask(self):
        curIndex = self.labelDisp.ui.channel.currentIndex()
        if curIndex != 1:
            self.display_channel_buffer = curIndex
            self.labelDisp.ui.channel.setCurrentIndex(1)
        elif self.display_channel_buffer is not None:
            self.labelDisp.ui.channel.setCurrentIndex(self.display_channel_buffer)
        else:
            self.labelDisp.ui.channel.setCurrentIndex(0)

    #### close

    def closeEvent(self, event):
        self.annotationMgr.save()
        if self.project is not None:
            self.project.save()
        self.config.save('./config/config.cfg')
        super().closeEvent(event)
        

if __name__ == "__main__":
    freeze_support()

    app = QApplication(sys.argv)

    with MainWindow() as win:
        win.resize(1600, 900)
        win.show()

    sys.exit(app.exec_())
