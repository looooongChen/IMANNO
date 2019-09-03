import os.path as ospath
import os
# from PyQt5.QtGui import *
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsView, QSizePolicy, QWidget, QToolBar, \
    QPushButton, QFileDialog, QMessageBox, QShortcut
from PyQt5.QtGui import QFont, QImage, QKeySequence
from PyQt5 import QtCore
import json
import cv2

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
IMAGE_FORMATS = ['jpg', 'jpeg', 'tif', 'tiff', 'png']



def defaultConfig():
    return {'fileDirectory': './demo_images'}


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

    def dropEvent(self, event):
        fname = str(event.mimeData().data('text/uri-list'), encoding='utf-8')
        fname = fname.replace('file:///', '')
        fname = fname.rstrip('\r\n')
        print(fname, ' -> D')
        self.parent().open(filename=fname)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-qt-windows-mime;value="FileNameW"'):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        pass



class MainWindow(QMainWindow):

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        pass

    def __init__(self):
        QMainWindow.__init__(self)

        # variables
        self.currentImageFile = ''
        self.currentAnnoFile = None
        self.image = None

        # appearance
        self.font = QFont("Times", pointSize=13)
        self.setFont(self.font)

        # status
        self.auto_contrast = False
        self.currentDir = None
        self.maskDir = None
        self.img2index = {}
        self.index2img = {}
        self.masks = []
        self.display_channel_buffer = None

        ####################################
        #### load or create config file ####
        ####################################

        # in json format
        if ospath.exists('./config/config.cfg'):
            with open('./config/config.cfg', 'r') as f:
                self.config = json.load(f)
        else:
            self.config = defaultConfig()
        # main window initialization
        self.setWindowTitle('Image Annotations Toolkit by LfB')

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

        #############################
        #### stepup the menu bar ####
        #############################

        mBar = self.menuBar()
        self.menus = {}
        menu = mBar.addMenu('File')
        menu.addAction('Open', self.open, 'CTRL+O')
        menu.addAction('Save', self.save_annotations, 'CTRL+S')
        self.menus['file'] = menu

        menu = mBar.addMenu('Edit')
        menu.addAction('Export Annotations', self.export_annotation)
        menu.addAction('Clean Noisy Annotations', self.clean_annotation)
        self.menus['edit'] = menu

        menu = mBar.addMenu('Mode')
        menu.addAction('Browse', lambda :self.scene.set_tool(BROWSE))
        menu.addAction('Polygon', lambda :self.scene.set_tool(POLYGON), 'P')
        menu.addAction('Ellipse', lambda :self.scene.set_tool(OVAL), 'E')
        menu.addAction('Bounding Box', lambda :self.scene.set_tool(BBX), 'B')
        menu.addAction('Line', lambda :self.scene.set_tool(LINE), 'L')
        menu.addAction('Dot', lambda :self.scene.set_tool(POINT), 'D')
        self.menus['mode'] = menu

        menu = mBar.addMenu('Label')
        menu.addAction('Import', self.labelDock.import_labels)
        menu.addAction('Export', self.labelDock.export_labels)
        menu.addAction('Set as default', self.labelDock.save_default_labels)
        menu.addAction('Load default', self.labelDock.load_default_labels)
        self.menus['label'] = menu

        menu = mBar.addMenu('Process')
        self.menus['process'] = menu

        menu = mBar.addMenu('Setting')
        self.menus['setting'] = menu

        mBar.setFont(self.font)
        # for _, k in self.menus.items():
        #     k.setFont(self.font)


        ############################
        #### setup the tool bar ####
        ############################

        self.tool = QToolBar(self)

        btnOpen = QPushButton(QIcon('icons/open.png'), "Open", self)
        btnOpen.setToolTip('(CTRL+O) open a slide')
        # btnOpen.setShortcut('CTRL+O')
        btnOpen.clicked.connect(self.open)

        btnSave = QPushButton(QIcon('icons/save.png'), "Save", self)
        btnSave.setToolTip('(CTRL+S) save all Annotations to HDF5 Format')
        # btnSave.setShortcut('CTRL+S')
        btnSave.clicked.connect(self.save_annotations)

        btnMaskDir = QPushButton(QIcon('icons/mask.png'), "Mask Dir", self)
        btnMaskDir.clicked.connect(self.set_mask_dir)

        btnImMask = QPushButton(QIcon('icons/mask.png'), "Imp. Mask", self)
        btnImMask.clicked.connect(self.import_mask)

        btnExMask = QPushButton(QIcon('icons/mask.png'), "Exp. Mask", self)
        btnExMask.clicked.connect(self.extract_current_mask)

        ####

        btnContrast = QPushButton(QIcon('icons/contrast.png'), 'Contrast', self)
        btnContrast.clicked.connect(self.adjust_contrast)

        btnZoomIn = QPushButton(QIcon('icons/zoom_in.png'), 'Zoom in', self)
        btnZoomIn.setToolTip('(CTRL+A) zoom in')
        btnZoomIn.setShortcut('CTRL+A')
        btnZoomIn.clicked.connect(self.zoom_in)

        btnZoomOut = QPushButton(QIcon('icons/zoom_out.png'), 'Zoom out', self)
        btnZoomOut.setToolTip('(CTRL+Z) zoom out')
        btnZoomOut.setShortcut('CTRL+Z')
        btnZoomOut.clicked.connect(self.zoom_out)


        btnNext = QPushButton(QIcon('icons/next.png'), 'Next', self)
        btnNext.setToolTip('(CTRL+N) next image')
        btnNext.setShortcut('CTRL+N')
        btnNext.clicked.connect(self.next_image)

        btnPre = QPushButton(QIcon('icons/previous.png'), 'Prev', self)
        btnPre.setToolTip('(CTRL+P) next image')
        btnPre.setShortcut('CTRL+P')
        btnPre.clicked.connect(self.previous_image)

        # btnRedo = QPushButton(QIcon('icons/redo.ico'), '', self)
        #
        # btnUndo = QPushButton(QIcon('icons/undo.ico'), '', self)

        ####
        
        btnGrab = QPushButton(QIcon('icons/browse.png'), 'Browse', self)
        btnGrab.setToolTip('(SPACE) browse mode, no drawing')
        # btnGrab.setShortcut('SPACE')
        btnGrab.clicked.connect(lambda : self.scene.set_tool(BROWSE))

        btnPoly = QPushButton(QIcon('icons/polygon.png'), 'Polygon', self)
        btnPoly.setToolTip('(P) draw an annotation polygon')
        # btnPoly.setShortcut('P')
        btnPoly.clicked.connect(lambda : self.scene.set_tool(POLYGON))

        btnCircle = QPushButton(QIcon('icons/circle.png'), 'Ellipse', self)
        btnCircle.setToolTip('(E) draw an annotation Ellipse')
        # btnCircle.setShortcut('E')
        btnCircle.clicked.connect(lambda: self.scene.set_tool(OVAL))

        btnBBX = QPushButton(QIcon('icons/bbx.png'), 'BBX', self)
        btnBBX.setToolTip('(B) draw an annotation bounding box')
        # btnBBX.setShortcut('B')
        btnBBX.clicked.connect(lambda: self.scene.set_tool(BBX))

        btnLine = QPushButton(QIcon('icons/line.png'), 'Line', self)
        btnLine.setToolTip('(L) draw an annotation line')
        # btnDot.setShortcut('D')
        btnLine.clicked.connect(lambda: self.scene.set_tool(LINE))

        btnDot = QPushButton(QIcon('icons/dot.png'), 'Dot', self)
        btnDot.setToolTip('(D) draw an annotation key point')
        # btnDot.setShortcut('D')
        btnDot.clicked.connect(lambda: self.scene.set_tool(POINT))

        btnDel = QPushButton(QIcon('icons/delete.png'), 'Delete', self)
        # btnDel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        btnDel.setToolTip('(Delete) delete an annotation')
        btnDel.setShortcut('Delete')
        btnDel.clicked.connect(self.deleteItem)

        ####

        btnLabels = QPushButton(QIcon('icons/label.png'), 'Label', self)
        btnLabels.setToolTip('(CTRL+L) open Label Manager')
        btnLabels.setShortcut('CTRL+L')
        btnLabels.clicked.connect(self.labelDock.new_label)

        btnScreenshot = QPushButton(QIcon('icons/screenshot.png'), 'Shot', self)
        btnScreenshot.setToolTip('(F3) save a screenshot to an image file')
        btnScreenshot.setShortcut('F3')
        btnScreenshot.clicked.connect(self.take_screenshot)

        btnSetting = QPushButton(QIcon('icons/config.png'), 'Config', self)
        btnSetting.clicked.connect(self.start_setting)


        self.tool.addWidget(btnOpen)
        self.tool.addWidget(btnSave)
        self.tool.addSeparator()

        self.tool.addWidget(btnMaskDir)
        self.tool.addWidget(btnImMask)
        self.tool.addWidget(btnExMask)
        self.tool.addSeparator()

        self.tool.addWidget(btnContrast)
        self.tool.addWidget(btnZoomIn)
        self.tool.addWidget(btnZoomOut)
        self.tool.addWidget(btnNext)
        self.tool.addWidget(btnPre)
        self.tool.addSeparator()

        self.tool.addWidget(btnGrab)
        self.tool.addWidget(btnPoly)
        self.tool.addWidget(btnCircle)
        self.tool.addWidget(btnBBX)
        self.tool.addWidget(btnLine)
        self.tool.addWidget(btnDot)
        self.tool.addWidget(btnDel)
        self.tool.addSeparator()

        self.tool.addWidget(btnLabels)
        self.tool.addWidget(btnScreenshot)
        self.tool.addWidget(btnSetting)


        self.addToolBar(Qt.LeftToolBarArea, self.tool)

        ###################
        #### shortcuts ####
        ###################

        hideMaskShortcut = QShortcut(QKeySequence(QtCore.Qt.Key_Tab), self)
        hideMaskShortcut.activated.connect(self.hideMask)

        ##############################
        #### setup the status bar ####
        ##############################

        self.status = self.statusBar()
        # self.setStatusBar(statusBar)
        self.status.showMessage("Ready ")

        # self.labelDock.hide()

        ##################################
        #### connect signal and slots ####
        ##################################

        self.scene.annotationSelected.connect(self.labelDock.update_info_table)
        self.scene.annotationReleased.connect(self.labelDock.initialize_info_table)
        self.labelDock.ui.channel.currentIndexChanged.connect(self.update_display_channel)
        self.labelDock.graphItemsUpdate.connect(self.scene.update_display_channel)


    def open(self, filename=None):
        if self.annotationMgr.needsSave:
            if QMessageBox.Yes == QMessageBox.question(self, "Important...", "Would you like to save the changes in your annotations?", QMessageBox.Yes | QMessageBox.No):
                self.save_annotations()
            self.annotationMgr.needsSave = False
        if not filename:
            filename = QFileDialog.getOpenFileName(self, "Select File", self.config['fileDirectory'])
            filename = filename[0]
            if len(filename) != 0:
                print("File opened: ", filename)
            else:
                return
        self.currentImageFile = str(filename)

        # read image
        self.auto_contrast = False
        self.image = cv2.imread(self.currentImageFile, cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
        ii = np.iinfo(self.image.dtype)
        self.image = self.image.astype(np.float)
        self.image = 255*(self.image - ii.min)/(ii.max-ii.min)


        # get the annotation file name
        dirname = ospath.dirname(self.currentImageFile)
        basefilename, filetype = ospath.splitext(ospath.basename(self.currentImageFile))
        self.currentDir = dirname

        if not (any(self.img2index) and self.currentDir == \
                ospath.dirname(list(self.img2index.keys())[0])):
            self.img2index, self.index2img = self.update_images_in_dir(self.currentDir)
        
        
        self.currentAnnoFile = ospath.join(dirname, basefilename + '.hdf5')

        # set new image in the scene for display
        # self.undoStack.clear()
        self.setWindowTitle(self.currentImageFile)
        self.scene.setNewImage(self.image)
        self.adjust_contrast()

        # load annotation into annotation manager
        self.annotationMgr.load_from_file(self.currentAnnoFile)
        self.labelDock.initialize()
        self.status.showMessage(self.status_string())
        # self.scene.updateScene()

    def save_annotations(self):
        self.annotationMgr.save_to_file(self.currentAnnoFile)

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
        
        matched_mask = self.match_mask(self.currentImageFile)
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

    def extract_current_mask(self):
        self.save_annotations()
        self.annotationMgr.needsSave = False
        if self.maskDirSetting.export_dir is None:
            QMessageBox.question(self, "Select directory...", "Please set the mask export directory first.", QMessageBox.Yes)
            self.set_mask_dir()
            return
        
        fname = os.path.splitext(os.path.basename(self.currentImageFile))[0]
        with h5py.File(self.currentAnnoFile) as location:
            if 'annotations' in location.keys():
                masks = MaskExtractor.generate_mask(location, [self.image.shape[0], self.image.shape[1]], save_as_one=True)
                MaskExtractor.save_mask_as_png(self.maskDirSetting.export_dir, fname, masks, True)
        QMessageBox.question(self, "Mask saved...", "Single image mask saved: " +  \
            os.path.join(self.maskDirSetting.export_dir, fname) + "_mask.png \n" + \
            "Overlapping area was suppressed, for more options refer to 'Edit -> Extract Masks'", \
                QMessageBox.Yes)
    

    def adjust_contrast(self):
        if self.image is None:
            return
        if not self.auto_contrast:
            img = self.image.copy()
            img = 255*(img-img.min())/(img.max()-img.min())
            self.scene.setImage(img)
            self.auto_contrast = True
            self.status.showMessage(self.status_string())
        else:
            self.scene.setImage(self.image)
            self.auto_contrast = False
            self.status.showMessage(self.status_string())

    def deleteItem(self):
        self.scene.deleteItem()
        self.labelDock.initialize_info_table()

    def closeEvent(self, event):
        if self.annotationMgr.needsSave:
            if QMessageBox.Yes == QMessageBox.question(self, "Important...", "Would you like to save the changes in your annotations?", QMessageBox.Yes | QMessageBox.No):
                self.save_annotations()
        with open('./config/config.cfg', 'w') as f:
            json.dump(self.config, f)
        super().closeEvent(event)

    def take_screenshot(self):
        pass

    def start_setting(self):
        pass

    #### newly constructed

    def zoom_in(self):
        self.canvas.zoom(ZOOM_IN_RATE)

    def zoom_out(self):
        self.canvas.zoom(ZOOM_OUT_RATE)

    #### next/previous image

    def next_image(self):
        ind = self.img2index[ospath.normpath(self.currentImageFile)] + 1
        if ind > len(self.img2index):
            ind = 1
        self.open(self.index2img[ind])

    def previous_image(self):
        ind = self.img2index[ospath.normpath(self.currentImageFile)] - 1
        if ind == 0:
            ind = len(self.img2index)
        self.open(self.index2img[ind])

    #### update function

    def update_display_channel(self, index):
        attr_name = self.labelDock.channel.itemText(index)
        if len(attr_name) == 0:
            return
        if attr_name == "Display without a certain channel.":
            self.scene.display_attr = 1
        elif attr_name == "Do not display masks.":
            self.scene.display_attr = None
        else:
            self.scene.display_attr = attr_name
        self.scene.update_display_channel()

    def update_images_in_dir(self, directory):
        
        file2index = {}
        index2file = {}

        imgs = []
        for file in os.listdir(directory):
            ext = file.split(".")[-1]
            if ext.lower() in IMAGE_FORMATS:
                imgs.append(file)
        imgs.sort()
        file2index = {ospath.normpath(ospath.join(directory, f)): ind for ind, f in enumerate(imgs,1)}
        index2file = {v: k for k, v in file2index.items()}
        return file2index, index2file

    def export_annotation(self):
        annoExporter = AnnoExporter()
        annoExporter.exec()
        del annoExporter

    def clean_annotation(self):
        annotationCleaner = AnnotationCleaner()
        annotationCleaner.exec()
        del annotationCleaner

    def status_string(self):
        status = ''
        if self.currentImageFile != '':
            ind = self.img2index[ospath.normpath(self.currentImageFile)]
            status = status + 'Image ' + str(ind) + " of " + str(len(self.img2index))    
        if self.auto_contrast == True:
            status = status + ', Auto Contrast: On'
        else:
            status = status + ', Auto Contrast: Off'
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
