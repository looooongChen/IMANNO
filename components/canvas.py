# from PyQt5.QtGui import *
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, Qt, QRect
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsSceneMouseEvent, QGraphicsPathItem, QGraphicsView, QSizePolicy
from PyQt5.QtGui import QImage, QPixmap, QTransform
import numpy as np
# from PIL import Image

from .image import Image
from .livewire import Livewire
from .commands import *
from .enumDef import *
from .annotations import Annotation

class Canvas(QGraphicsScene):

    signalAnnotationSelected = QtCore.pyqtSignal(Annotation)
    signalAnnotationReleased = QtCore.pyqtSignal()

    def __init__(self, config, image, annotationMgr, parent=None):
        
        super().__init__(parent=parent)
        # class members
        self.config = config
        self.image = None
        self.annotationMgr = annotationMgr
        self.parent = parent
        self.view = View(parent)
        self.bgPixmap = self.addPixmap(QPixmap.fromImage(QImage('icons/startscreen.png')))
        self.livewire = Livewire()
        # setup 
        self.set_image(image)
        self.set_view(self.view)
        # run-time stack
        self.selectedItems = []
        # run-time status
        self.tool = BROWSE
        self.drawing = False
        self.currentCommand = None
        self.current_scale = 1
        # time part
        # error occurs when pass event through signal
        self.time = None
        self.clickPos = None
        self.clickBtn = None
    
    def set_image(self, image):
        if isinstance(image, Image):
            self.image = image
            self.livewire.set_image(image)

    def set_view(self, view):
        if isinstance(view, QGraphicsView):
            self.view = view
            self.view.setScene(self)
            if self.parent is not None:
                self.parent.setCentralWidget(view)
            self.view.show()

    def screenshot(self):
        sz = self.bgPixmap.boundingRect()
        sz = self.view.mapFromScene(sz).boundingRect()
        return self.view.grab(sz)  
    
    ##############################
    #### zoom in and out view ####
    ############################## 

    def zoom(self, scale):
        self.view.scale(scale,scale)
        self.current_scale = self.current_scale * scale

    def recovery_scale(self):
        self.view.scale(1/self.current_scale, 1/self.current_scale)
        self.current_scale = 1

    ###################################
    #### synchronize image display ####
    ###################################

    def sync_image(self, image=None):
        self.set_image(image)
        if self.image is not None and self.image.is_open():
            self.bgPixmap.setPixmap(QPixmap.fromImage(self.image.get_QImage()))
            self.view.setSceneRect(0,0,self.image.width,self.image.height)
            vis_rect = self.view.mapToScene(self.view.rect()).boundingRect()
            scale = min(vis_rect.width()/self.image.width, vis_rect.height()/self.image.height)
            self.view.scale(scale, scale)
            if self.tool == LIVEWIRE:
                self.sync_livewire_image()
    
    def sync_livewire_image(self, image=None, scale=None):
        self.livewire.sync_image(image=image, scale=scale)

    def set_tool(self, tool, paras=None):
        self.tool = tool
        paras = paras if isinstance(paras, dict) else {}
        if self.tool == LIVEWIRE:
            self.sync_livewire_image(**paras)
        self.drawing = False
        self.currentCommand = None

    ####################################
    #### add and remove graph items ####
    ####################################

    def deleteItem(self):
        self.currentCommand = DeleteAnnotation(self, self.annotationMgr, self.selectedItems)
        self.selectedItems.clear()

    def clear_items(self):
        for item in self.items():
            if item != self.bgPixmap:
                self.removeItem(item)
        self.selectedItems.clear()

    def add_graphItem(self, annotation, display_channel=None):
        pen, brush = self.annotationMgr.appearance(annotation, display_channel)
        graphObj = annotation.get_graphObject()
        graphObj.setPen(pen)
        graphObj.setBrush(brush)
        self.addItem(graphObj)

    def add_graphItems(self, display_channel=None):
        self.clear_items()
        for _, annotation in self.annotationMgr.annotations.items():
            self.add_graphItem(annotation, display_channel)

    ##################################
    #### display relavant methods ####
    ##################################

    def refresh(self):
        for _, item in self.annotationMgr.annotations.items():
            pen, brush = self.annotationMgr.appearance(item, self.config['display_channel'])
            item.graphObject.setPen(pen)
            item.graphObject.setBrush(brush)
        self.highlight_items(self.selectedItems)
        
    def selectItem(self, event):
        item = self.itemAt(event.scenePos(), QTransform())

        for selected in self.selectedItems:
            self.highlight(selected, 'restore')

        if not event.modifiers() & Qt.ControlModifier:
            self.selectedItems.clear()
        if item is not self.bgPixmap and item not in self.selectedItems:
            self.selectedItems.append(item)
            self.signalAnnotationSelected.emit(self.annotationMgr.get_annotation_by_graphItem(item))
        else:
            self.signalAnnotationReleased.emit()
            self.selectedItems.clear()

        self.highlight_items(self.selectedItems)

    def highlight(self, item, mode='highlight'):
        if mode == "highlight":
            d1, d2 = 1, 100
        elif mode == "restore":
            d1, d2 = -1, -100
        
        pen = item.pen()
        if pen:
            pen.setWidth(pen.width() + d1)
            item.setPen(pen)

        brush = item.brush()
        if brush:
            
            color = brush.color()
            if isinstance(item, QGraphicsPathItem):
                color.setAlpha(0)
            else:    
                color.setAlpha(color.alpha() + d2)
            brush.setColor(color)
            # brush.setStyle(Qt.SolidPattern)
            item.setBrush(brush)

    def highlight_items(self, item_list, mode='highlight'):
        for item in item_list:
            self.highlight(item, mode)

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
            elif self.tool == OVAL:
                if self.drawing:
                    self.currentCommand.finish()
                    self.drawing = False
                else:
                    self.currentCommand = OvalPainter(self, self.annotationMgr, self.clickPos)
                    self.drawing = True
            elif self.tool == POINT:
                self.currentCommand = PointPainter(self, self.annotationMgr, self.clickPos, self.config['DotAnnotationRadius'])
                self.currentCommand.finish()
            elif self.tool == LINE:
                if self.drawing:
                    self.currentCommand.finish()
                    self.drawing = False
                else:
                    self.currentCommand = LinePainter(self, self.annotationMgr, self.clickPos)
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
        elif self.tool == LINE and self.drawing:
            self.currentCommand.mouseMoveEvent(event)
        elif self.tool == BBX and self.drawing:
            self.currentCommand.mouseMoveEvent(event)
        elif self.tool == OVAL and self.drawing:
            self.currentCommand.mouseMoveEvent(event)

    def wheelEvent(self, event):
        pass
        # if event.delta() < 0:
        #     if self.tool == OVAL and self.drawing:
        #         self.currentCommand.shrink()
        # elif event.delta() > 0:
        #     if self.tool == OVAL and self.drawing:
        #         self.currentCommand.expand()
        # else:
        #     pass


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancel_operation()
        elif self.selectedItems and event.key() == Qt.Key_Delete:
            self.deleteItem()
        elif event.key() == Qt.Key_Z:
            if self.tool == OVAL and self.drawing:
                self.currentCommand.shrink()
            elif self.tool == POINT:
                self.currentCommand.shrink()
        elif event.key() == Qt.Key_A:
            if self.tool == OVAL and self.drawing:
                self.currentCommand.expand()
            elif self.tool == POINT:
                self.currentCommand.expand()


class View(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
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