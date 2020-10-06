# from PyQt5.QtGui import *
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsSceneMouseEvent, QGraphicsPathItem, QGraphicsView
from PyQt5.QtGui import QImage, QPixmap, QTransform
import numpy as np
# from PIL import Image

from .image import Image
from .livewire import Livewire
from .commands import *
from .enumDef import *
from .annotations import Annotation
# from .annotationManager import AnnotationManager

class Scene(QGraphicsScene):

    annotationSelected = QtCore.pyqtSignal(Annotation)
    annotationReleased = QtCore.pyqtSignal()

    # List of available tools:
    # Tool-handling here and in respective QUndoCommand-derived class
    # Results are stored and managed in an AnnotationManager
    # grabAndMove = 0
    # polygonPainter = 1
    # circlePainter = 2

    def __init__(self, config, image, canvas, annotationMgr=None, parent=None):
        
        super().__init__(parent=parent)
        self.config = config
        self.annotationMgr = None
        self.image = None
        self.canvas = None
        self.bgPixmap = self.addPixmap(QPixmap.fromImage(QImage('icons/startscreen.png')))
        self.livewire = Livewire()

        self.set_image(image)
        self.set_canvas(canvas)
        self.set_annotationMgr(annotationMgr)
        # run-time stack
        self.selectedItems = []
        # run-time status
        self.tool = BROWSE
        self.drawing = False
        self.currentCommand = None
        # time part
        # error occurs when pass event through signal
        self.time = None
        self.clickPos = None
        self.clickBtn = None

    def set_annotationMgr(self, annotationMgr):
        # self.annotationMgr = annotationMgr if isinstance(annotationMgr, AnnotationManager) else None
        self.annotationMgr = annotationMgr

    def set_image(self, image):
        if isinstance(image, Image):
            self.image = image
            self.livewire.set_image(image)
        
    def set_canvas(self, canvas):
        if isinstance(canvas, QGraphicsView):
            self.canvas = canvas
            self.canvas.setScene(self) 
    
    ###################################
    #### synchronize image display ####
    ###################################

    def sync_image(self, image=None):
        self.set_image(image)
        if self.image is not None and self.image.is_open():
            self.bgPixmap.setPixmap(QPixmap.fromImage(self.image.get_QImage()))
            self.canvas.setSceneRect(0,0,self.image.width,self.image.height)
            vis_rect = self.canvas.mapToScene(self.canvas.rect()).boundingRect()
            scale = min(vis_rect.width()/self.image.width, vis_rect.height()/self.image.height)
            self.canvas.scale(scale, scale)
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
        for timestamp in self.annotationMgr.annotations.keys():
            pen, brush = self.annotationMgr.appearance(self.annotationMgr.annotations[timestamp], self.config['display_channel'])
            self.annotationMgr.annotations[timestamp].graphObject.setPen(pen)
            self.annotationMgr.annotations[timestamp].graphObject.setBrush(brush)
        self.highlight_items(self.selectedItems)
        
    def selectItem(self, event):
        item = self.itemAt(event.scenePos(), QTransform())

        for selected in self.selectedItems:
            self.highlight(selected, 'restore')

        if not event.modifiers() & Qt.ControlModifier:
            self.selectedItems.clear()
        if item is not self.bgPixmap and item not in self.selectedItems:
            self.selectedItems.append(item)
            self.annotationSelected.emit(self.annotationMgr.get_annotation_by_graphItem(item))
        else:
            self.annotationReleased.emit()
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

