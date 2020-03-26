import os.path as ospath
import os
# from PyQt5.QtGui import *
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QSizePolicy, QWidget, QToolBar, \
    QPushButton, QFileDialog, QMessageBox, QShortcut, QLabel, QLineEdit, QDoubleSpinBox
from PyQt5.QtGui import QFont, QImage, QKeySequence
from PyQt5 import QtCore
import json
import cv2
from PyQt5 import uic

from components.scene import Scene
from components.labelDock import LabelDock
from components.extract import AnnoExporter
from components.clean_data import AnnotationCleaner
from components.setting import MaskDirDialog
from components.mask2contour import mask2contour



from multiprocessing import freeze_support, set_executable
# import openslide as osl

from components.graphDef import *
from components.commands import *
from components.annotationManager import *


__author__ = 'long, bug'


ZOOM_IN_RATE = 1.2
ZOOM_OUT_RATE = 1/ZOOM_IN_RATE
IMAGE_FORMATS = ['jpg', 'jpeg', 'tif', 'tiff', 'png', 'bmp']


class Config(dict):

    def __init__(self, basic_config=None):
        self.static_config = ['fileDirectory', 'DotAnnotationRadius', 'lineAnnotationWidth']
        # default config
        self['fileDirectory'] = './demo_images'
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
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent=parent)
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

        # runtime config
        self.config['currentImageFile'] = ''
        self.config['currentAnnoFile'] = None
        self.config['image_origin'] = None
        self.config['image'] = None
        self.config['image_size'] = None
        self.config['auto_contrast'] = False
        self.config['display_channel'] = 1
        self.config['scale_factor'] = (1.0, 1.0)

        self.maskDir = None
        self.img2index = {}
        self.index2img = {}
        self.masks = []
        self.display_channel_buffer = None

        ###################################
        #### setup the main components ####
        ###################################

        # setup annotation manager
        self.annotationMgr = AnnotationManager(config=self.config)
        # setup the scene
        self.scene = Scene(config=self.config, parent=self)
        # setup the grahicsView for display
        self.canvas = Canvas(self.scene, parent=self)
        self.maskDirSetting = MaskDirDialog(self)
        # connect them
        self.annotationMgr.set_scene(self.scene)
        self.scene.set_annotationMgr(self.annotationMgr)
        self.scene.set_canvas(self.canvas)

        # initial display
        self.canvas.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.canvas.setAlignment(QtCore.Qt.AlignCenter)
        # self.canvas.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # self.canvas.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setCentralWidget(self.canvas)
        self.canvas.show()

        #############################
        #### setup the dock area ####
        #############################

        self.labelDock = LabelDock(self.annotationMgr, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.labelDock)
        # self.labelDock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.labelDock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        self.labelDock.setTitleBarWidget(QWidget())

        ############################
        #### setup the tool bar ####
        ############################
          
        self.toolBar.addWidget(QLabel(" Rescale: "))
        self.spinScale = QDoubleSpinBox(self.toolBar)
        # self.spinScale.setFocusPolicy(QtCore.Qt.NoFocus)
        self.spinScale.setRange(0.1, 2)
        self.spinScale.setValue(1)
        self.spinScale.setSingleStep(0.1)
        self.toolBar.addWidget(self.spinScale)

        ###################
        #### shortcuts ####
        ###################

        hideMaskShortcut = QShortcut(QKeySequence(QtCore.Qt.Key_Tab), self)
        hideMaskShortcut.activated.connect(self.hideMask)

        ##############################
        #### setup the status bar ####
        ##############################

        self.statusBar.showMessage("Ready ")
        # self.labelDock.hide()

        #################################
        #### connect signal to alots ####
        #################################

        # file menu actions
        self.actionOpen.triggered.connect(self.open)
        self.actionSave.triggered.connect(self.save_annotations)
        self.actionMask_Directory.triggered.connect(self.set_mask_dir)
        self.actionImport_Mask.triggered.connect(self.import_mask)

        # annotation menu actions
        self.actionBrowse.triggered.connect(lambda :self.scene.set_tool(BROWSE))
        self.actionPolygon.triggered.connect(lambda :self.scene.set_tool(POLYGON))
        self.actionLivewire.triggered.connect(lambda :self.scene.set_tool(LIVEWIRE))
        self.actionBounding_Box.triggered.connect(lambda :self.scene.set_tool(BBX))
        self.actionEllipse.triggered.connect(lambda :self.scene.set_tool(OVAL))
        self.actionLine.triggered.connect(lambda :self.scene.set_tool(LINE))
        self.actionDot.triggered.connect(lambda :self.scene.set_tool(POINT))
        self.actionDelete.triggered.connect(self.deleteItem)

        # label menu actions
        self.actionImport_Label.triggered.connect(self.labelDock.import_labels)
        self.actionExport_Lbale.triggered.connect(self.labelDock.export_labels)
        self.actionLoad_Default.triggered.connect(self.labelDock.load_default_labels)
        self.actionSet_as_Default.triggered.connect(self.labelDock.save_default_labels)

        # tool menu actions
        self.actionZoom_In.triggered.connect(self.zoom_in)
        self.actionZoom_Out.triggered.connect(self.zoom_out)
        self.actionNext_Image.triggered.connect(self.next_image)
        self.actionPrevious_Image.triggered.connect(self.previous_image)
        self.actionAuto_Contrast.triggered.connect(self.auto_contrast)
        self.actionExport_Annotations.triggered.connect(self.export_annotation)
        self.actionClean_Noisy_Annotations.triggered.connect(self.clean_annotation)
        self.actionScreen_Shot.triggered.connect(self.take_screenshot)
        
        # setting menu actions
        self.actionConfig.triggered.connect(self.start_setting)
        self.actionAbout.triggered.connect(self.show_about)

        # toolBar actions
        self.spinScale.valueChanged.connect(self.scale_changed)

        # signal between components
        self.scene.annotationSelected.connect(self.labelDock.refresh_infoTable)
        self.scene.annotationReleased.connect(self.labelDock.refresh_infoTable)
        self.labelDock.ui.channel.currentIndexChanged.connect(self.refresh_display_channel)
        self.labelDock.graphItemsUpdate.connect(self.refresh_display_channel)


    def open(self, filename=None):

        # save annotation when necessary
        if self.annotationMgr.needsSave:
            if QMessageBox.Yes == QMessageBox.question(self, "Important...", "Would you like to save the changes in your annotations?", QMessageBox.Yes | QMessageBox.No):
                self.save_annotations()
            self.annotationMgr.needsSave = False

        # get image file name
        if not filename:
            filename = QFileDialog.getOpenFileName(self, "Select File", self.config['fileDirectory'])
            filename = filename[0]
            if len(filename) != 0:
                print("File opened: ", filename)
            else:
                return
        self.config['currentImageFile'] = str(filename)

        # read image
        self.config['auto_contrast'] = False
        self.config['image'] = cv2.imread(self.config['currentImageFile'], cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
        if len(self.config['image'].shape) == 3:
            self.config['image'] = np.flip(self.config['image'], 2)
        self.config['image_size'] = tuple(self.config['image'].shape[0:2])
        ii = np.iinfo(self.config['image'].dtype)
        self.config['image'] = self.config['image'].astype(np.float)
        self.config['image'] = 255*(self.config['image'] - ii.min)/(ii.max-ii.min)
        self.config['image_origin'] = self.config['image'].copy()
        self.setWindowTitle(self.config['currentImageFile'])

        # get the annotation
        currentDir = ospath.dirname(self.config['currentImageFile'])
        basefilename, filetype = ospath.splitext(ospath.basename(self.config['currentImageFile']))

        if not (any(self.img2index) and currentDir == \
                ospath.dirname(list(self.img2index.keys())[0])):
            self.img2index, self.index2img = self.update_images_in_dir(currentDir)
        
        self.config['currentAnnoFile'] = ospath.join(currentDir, basefilename + '.hdf5')
        self.annotationMgr.load_from_file(self.config['currentAnnoFile'])

        self.refresh()

    def save_annotations(self):
        self.annotationMgr.save_to_file(self.config['currentAnnoFile'])

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

    # def extract_current_mask(self):
    #     self.save_annotations()
    #     self.annotationMgr.needsSave = False
    #     if self.maskDirSetting.export_dir is None:
    #         QMessageBox.question(self, "Select directory...", "Please set the mask export directory first.", QMessageBox.Yes)
    #         self.set_mask_dir()
    #         return
        
    #     fname = os.path.splitext(os.path.basename(self.config['currentImageFile']))[0]
    #     with h5py.File(self.config['currentAnnoFile']) as location:
    #         if 'annotations' in location.keys():
    #             masks = MaskExtractor.generate_mask(location, [self.config['image'].shape[0], self.config['image'].shape[1]], save_as_one=True)
    #             MaskExtractor.save_mask_as_png(self.maskDirSetting.export_dir, fname, masks, True)
    #     QMessageBox.question(self, "Mask saved...", "Single image mask saved: " +  \
    #         os.path.join(self.maskDirSetting.export_dir, fname) + "_mask.png \n" + \
    #         "Overlapping area was suppressed, for more options refer to 'Edit -> Extract Masks'", \
    #             QMessageBox.Yes)
    
    def auto_contrast(self):
        if not self.config['auto_contrast']:
            self.config['auto_contrast'] = True
        else:
            self.config['auto_contrast'] = False
        self.adjust_contrast()

    def adjust_contrast(self):
        if self.config['image'] is None:
            return
        if self.config['auto_contrast']:
            self.actionAuto_Contrast.setChecked(True)
            img = self.config['image'].copy()
            img = 255*(img-img.min())/(img.max()-img.min())
            self.scene.setImage(img)
        else:
            self.actionAuto_Contrast.setChecked(False)
            self.scene.setImage(self.config['image'])
        self.refresh_statusBar()
    
    # def change_scale(self, scale):
    #     self.scale = scale
    #     scale = self.spinScale.value()
    #     self.config['image'] = cv2.resize(self.config['image_origin'], (int(self.config['image_size'][1] * scale), int(self.config['image_size'][0] * scale)))
    #     self.config['scale_factor'] = [self.config['image'].shape[1]/self.config['image_size'][1], self.config['image'].shape[0]/self.config['image_size'][0]]
    #     self.refresh()
    #     self.refresh_statusBar()

    def deleteItem(self):
        self.scene.deleteItem()
        self.labelDock.refresh_infoTable()

    def closeEvent(self, event):
        if self.annotationMgr.needsSave:
            if QMessageBox.Yes == QMessageBox.question(self, "Important...", "Would you like to save the changes in your annotations?", QMessageBox.Yes | QMessageBox.No):
                self.save_annotations()
        self.config.save('./config/config.cfg')
        super().closeEvent(event)

    def take_screenshot(self):
        pass

    def start_setting(self):
        pass

    def show_about(self):
        pass
    
    def export_annotation(self):
        annoExporter = AnnoExporter()
        annoExporter.exec()
        del annoExporter

    def clean_annotation(self):
        annotationCleaner = AnnotationCleaner()
        annotationCleaner.exec()
        del annotationCleaner

    #### zoom in/out

    def zoom_in(self):
        self.canvas.zoom(ZOOM_IN_RATE)

    def zoom_out(self):
        self.canvas.zoom(ZOOM_OUT_RATE)

    #### next/previous image

    def next_image(self):
        ind = self.img2index[ospath.normpath(self.config['currentImageFile'])] + 1
        if ind > len(self.img2index):
            ind = 1
        self.open(self.index2img[ind])

    def previous_image(self):
        ind = self.img2index[ospath.normpath(self.config['currentImageFile'])] - 1
        if ind == 0:
            ind = len(self.img2index)
        self.open(self.index2img[ind])

    #### update function
    def scale_changed(self, scale):
        self.spinScale.clearFocus()
        self.refresh()

    def refresh(self):
        if self.config['image_origin'] is None:
            return
        # recompute scale
        scale = self.spinScale.value()
        W_new = int(self.config['image_size'][1] * scale)
        H_new = int(self.config['image_size'][0] * scale)
        scale_factor_x = W_new/self.config['image_size'][1]
        scale_factor_y = H_new/self.config['image_size'][0]
        self.config['image'] = cv2.resize(self.config['image_origin'], (W_new, H_new))
        self.config['scale_factor'] = (scale_factor_x, scale_factor_y)
        # display
        self.scene.setNewImage(self.config['image'])
        self.adjust_contrast()
        self.annotationMgr.add_existing_graphItems()
        self.labelDock.refresh()
        self.refresh_display_channel()
        self.refresh_statusBar()

    def refresh_display_channel(self, index=None):
        index = self.labelDock.channel.currentIndex()
        attr_name = self.labelDock.channel.itemText(index)
        if len(attr_name) == 0:
            return
        if attr_name == "All":
            self.config['display_channel'] = 1
        elif attr_name == "Hidden":
            self.config['display_channel'] = None
        else:
            self.config['display_channel'] = attr_name
        self.scene.refresh_display_channel()

    def update_images_in_dir(self, directory):
        
        file2index = {}
        index2file = {}

        imgs = []
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if not os.path.isfile(file_path):
                continue
            ext = file.split(".")[-1]
            if ext.lower() in IMAGE_FORMATS:
                imgs.append(file)
        imgs.sort()
        file2index = {ospath.normpath(ospath.join(directory, f)): ind for ind, f in enumerate(imgs,1)}
        index2file = {v: k for k, v in file2index.items()}
        return file2index, index2file

    def refresh_statusBar(self):
        status = ''
        if self.config['currentImageFile'] != '':
            ind = self.img2index[ospath.normpath(self.config['currentImageFile'])]
            status = status + 'Image ' + str(ind) + " of " + str(len(self.img2index))    
        
        if self.config['auto_contrast'] == True:
            status = status + ', Auto Contrast: On'
        else:
            status = status + ', Auto Contrast: Off'
        
        status = status + ', Image Rescaled: ' + '{:.1f}'.format(self.spinScale.value())
        
        self.statusBar.showMessage(status)
        return status
    
    def hideMask(self):
        curIndex = self.labelDock.ui.channel.currentIndex()
        if curIndex != 1:
            self.display_channel_buffer = curIndex
            self.labelDock.ui.channel.setCurrentIndex(1)
        elif self.display_channel_buffer is not None:
            self.labelDock.ui.channel.setCurrentIndex(self.display_channel_buffer)
        else:
            self.labelDock.ui.channel.setCurrentIndex(0)
            

        
        

if __name__ == "__main__":
    freeze_support()

    app = QApplication(sys.argv)

    with MainWindow() as win:
        win.resize(1600, 900)
        win.show()

    sys.exit(app.exec_())
