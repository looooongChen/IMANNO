# from PyQt5.QtGui import *
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, Qt, QRect
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsSceneMouseEvent, QGraphicsPathItem, QGraphicsView, QSizePolicy
from PyQt5.QtGui import QImage, QPixmap, QTransform, QCursor
import numpy as np
# from PIL import Image

from .image import Image
from .livewire import Livewire
from .commands import *
from .enumDef import *
from .annotations import *

class Canvas(QGraphicsScene):

    signalAnnotationSelected = QtCore.pyqtSignal(Annotation)
    signalAnnotationReleased = QtCore.pyqtSignal()

    def __init__(self, config, image, annotationMgr, parent=None):
        
        super().__init__(parent=parent)
        # class members
        self.config = config
        self.image = image
        self.annotationMgr = annotationMgr
        self.annotationMgr.set_canvas(self)
        # set view
        self.view = View(self.config)
        self.view.setScene(self)
        self.view.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.view.show()
        self.bgPixmap = self.addPixmap(QPixmap.fromImage(QImage('icons/startscreen.png')))
        # setup livewire
        self.livewire = Livewire()
        self.livewire.set_image(image)
        # run-time status
        self.selected = []
        self.tool = BROWSE
        self.drawing = False
        self.currentCommand = None
        self.currentScale = 1
        # time part
        # error occurs when pass event through signal
        self.time = None
        self.clickPos = None
        self.clickBtn = None
    
    def clear(self):
        for item in self.items():
            if item != self.bgPixmap:
                self.removeItem(item)
        self.selected.clear()

    ###############################
    #### graph item management ####
    ###############################

    def add_item(self, anno):
        graphObj = anno.graphObject
        self.addItem(graphObj)
        anno.sync_disp(self.config)

    def remove_item(self, anno):
        self.removeItem(anno.graphObject)

    # def add_graphItems(self):
    #     self.clear()
    #     for _, annotation in self.annotationMgr.items():
    #         self.add_item(annotation)

    def assign_selected_items(self, label):
        for anno in self.selected:
            label.assign(anno)
            anno.sync_disp(self.config)
        if len(self.selected) > 0:
            anno = self.selected[-1]
            self.signalAnnotationSelected.emit(anno)

    #########################
    #### take screenshot ####
    ######################### 

    def screenshot(self):
        sz = self.bgPixmap.boundingRect()
        sz = self.view.mapFromScene(sz).boundingRect() 
        return self.view.grab(sz)  
    
    ##############################
    #### zoom in and out view ####
    ############################## 

    def zoom(self, scale):
        self.view.scale(scale,scale)
        self.currentScale = self.currentScale * scale

    def recovery_scale(self):
        self.view.scale(1/self.currentScale, 1/self.currentScale)
        self.currentScale = 1

    ###################################
    #### synchronize image display ####
    ###################################

    def sync(self):
        self.sync_image()
        self.sync_disp()

    def sync_image(self):
        if self.image.is_open():
            self.bgPixmap.setPixmap(QPixmap.fromImage(self.image.get_QImage()))
            self.view.setSceneRect(0,0,self.image.width,self.image.height)
            vis_rect = self.view.mapToScene(self.view.rect()).boundingRect()
            scale = min(vis_rect.width()/self.image.width, vis_rect.height()/self.image.height)
            self.view.scale(scale, scale)
            if self.tool == LIVEWIRE:
                self.livewire.sync_image()

    def sync_disp(self):
        for _, anno in self.annotationMgr.items():
            # print('sss', anno.labels)
            anno.sync_disp(self.config)
    
    def set_tool(self, tool, paras=None):
        self.tool = tool
        paras = paras if isinstance(paras, dict) else {}
        if self.tool == LIVEWIRE:
            self.livewire.sync_image(**paras)
        self.drawing = False
        self.currentCommand = None

    ##################################
    #### display relavant methods ####
    ##################################

    def highlight_selected_items(self, status):
        for item in self.selected:
            item.highlight(status)

    ###########################################
    #### mouse and keyboard event handling ####
    ###########################################

    def cancel_operation(self):
        if self.drawing:
            self.drawing = False
            self.currentCommand.cancel()

    def mousePressEvent(self, event):
        self.event = event
        self.clickPos = self.event.scenePos()
        self.clickBtn = self.event.button()
        self.timer = QTimer()
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.singleClickAction)
        self.timer.start()

    def singleClickAction(self):
        self.timer.stop()
        if self.clickBtn & QtCore.Qt.LeftButton:
            if self.tool == POLYGON:
                if self.drawing:
                    self.currentCommand.finish()
                    self.drawing = False
                else:
                    self.currentCommand = PolygonPainter(self, self.annotationMgr, self.clickPos)
                    self.drawing = True
            elif self.tool == LIVEWIRE:
                if self.drawing:
                    self.currentCommand.mouseSingleClickEvent(self.clickPos)
                else:
                    self.currentCommand = LivewirePainter(self, self.annotationMgr, self.clickPos)
                    self.drawing = True
            elif self.tool == BBX:
                if self.drawing:
                    self.currentCommand.finish()
                    self.drawing = False
                else:
                    self.currentCommand = BBXPainter(self, self.annotationMgr, self.clickPos)
                    self.drawing = True
            elif self.tool == ELLIPSE:
                if self.drawing:
                    self.currentCommand.finish()
                    self.drawing = False
                else:
                    self.currentCommand = EllipsePainter(self, self.annotationMgr, self.clickPos)
                    self.drawing = True
            elif self.tool == DOT:
                self.currentCommand = DotPainter(self, self.annotationMgr, self.clickPos)
                self.currentCommand.finish()
            elif self.tool == CURVE:
                if self.drawing:
                    self.currentCommand.finish()
                    self.drawing = False
                else:
                    self.currentCommand = CurvePainter(self, self.annotationMgr, self.clickPos)
                    self.drawing = True
            if self.tool == BROWSE:
                pass

    def mouseDoubleClickEvent(self, event):
        self.timer.stop()
        if self.clickBtn == Qt.LeftButton:
            if self.drawing:
                if self.tool == LIVEWIRE:
                    self.currentCommand.mouseSingleClickEvent(self.clickPos)
                self.currentCommand.finish()
                self.drawing = False
            else:
                self.selectItem(event)

    def mouseMoveEvent(self, event):
        assert isinstance(event, QGraphicsSceneMouseEvent)
        if self.tool == POLYGON and self.drawing:
            self.currentCommand.mouseMoveEvent(event)
        elif self.tool == LIVEWIRE and self.drawing:
            self.currentCommand.mouseMoveEvent(event)
        elif self.tool == CURVE and self.drawing:
            self.currentCommand.mouseMoveEvent(event)
        elif self.tool == BBX and self.drawing:
            self.currentCommand.mouseMoveEvent(event)
        elif self.tool == ELLIPSE and self.drawing:
            self.currentCommand.mouseMoveEvent(event)

    def wheelEvent(self, event):
        pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancel_operation()
        elif event.key() == Qt.Key_Delete:
            self.deleteItem()
        elif event.key() == Qt.Key_Z:
            if self.tool == ELLIPSE and self.drawing:
                self.currentCommand.shrink()
            elif self.tool == DOT:
                self.currentCommand.shrink()
        elif event.key() == Qt.Key_A:
            if self.tool == ELLIPSE and self.drawing:
                self.currentCommand.expand()
            elif self.tool == DOT:
                self.currentCommand.expand()

    def selectItem(self, event):
        self.highlight_selected_items(False)

        item = self.itemAt(event.scenePos(), QTransform())
        anno = self.annotationMgr.get_annotation_by_graphItem(item)
        if not event.modifiers() & Qt.ControlModifier:
            self.selected.clear()
        if item is not self.bgPixmap and item not in self.selected:
            self.selected.append(anno)
            self.signalAnnotationSelected.emit(anno)
        else:
            self.signalAnnotationReleased.emit()
            self.selected.clear()

        self.highlight_selected_items(True)

    def deleteItem(self):
        if self.drawing:
            self.cancel_operation()
            self.drawing
        else:
            for item in self.selected:
                self.annotationMgr.remove_annotation(item)
                self.signalAnnotationReleased.emit()
            self.selected.clear()


class View(QGraphicsView):
    def __init__(self, config, parent=None):
        super().__init__(parent=parent)
        self.config = config
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.setAlignment(Qt.AlignCenter)

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