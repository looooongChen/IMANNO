# from PyQt5.QtGui import *
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QGraphicsScene, QGraphicsSceneMouseEvent, QGraphicsPathItem
from PyQt5.QtGui import QImage, QPixmap, QTransform
import numpy as np
from PIL import Image

from .commands import *
from .graphDef import *
from .annotationManager import Annotation

class Scene(QGraphicsScene):

    annotationSelected = QtCore.pyqtSignal(Annotation)
    annotationReleased = QtCore.pyqtSignal()

    # List of available tools:
    # Tool-handling here and in respective QUndoCommand-derived class
    # Results are stored and managed in an AnnotationManager
    # grabAndMove = 0
    # polygonPainter = 1
    # circlePainter = 2

    def __init__(self, config, parent=None):
        super().__init__(parent=parent)
        self.config = config
        # background image
        self.image = np.asarray(Image.open('icons/startscreen.png'))
        self.bgImage = QImage('icons/startscreen.png')
        self.bgPixmap = self.addPixmap(QPixmap.fromImage(self.bgImage))

        # components
        self.annotationMgr = None
        self.scene = None
        self.canvas = None

        # run-time stack
        self.selectedItems = []

        # run-time status
        self.drawing = False
        self.operation = None
        self.currentCommand = None
        self.display_attr = None

        # time part
        # error occurs when pass event through signal
        self.time = None
        self.clickedBtn = None
        self.clickPos = None

    def set_annotationMgr(self, annotationMgr):
        self.annotationMgr = annotationMgr

    def set_canvas(self, canvas):
        self.canvas = canvas
    
    def clear_items(self):
        for item in self.items():
            if item != self.bgPixmap:
                self.removeItem(item)
        self.selectedItems.clear()

    def setNewImage(self, image):
        self.clear_items()
        self.image = image
        self.bgImage = self.image2QImage(image)
        self.bgPixmap.setPixmap(QPixmap.fromImage(self.bgImage))
        # self.updateScene()

    def setImage(self, image):
        self.bgImage = self.image2QImage(image)
        self.bgPixmap.setPixmap(QPixmap.fromImage(self.bgImage))
        # self.updateScene()

    def deleteItem(self):
        self.currentCommand = DeleteAnnotation(self, self.annotationMgr, self.selectedItems)
        self.selectedItems.clear()

    def image2QImage(self, image):
        image = np.squeeze(image)
        if len(image.shape) == 3:
            imdat = 255 << 24 | \
                    image[:, :, 0].astype(np.uint32) << 16 | \
                    image[:, :, 1].astype(np.uint32) << 8 | \
                    image[:, :, 2].astype(np.uint32)
        else:
            imdat = 255 << 24 | \
                    image.astype(np.uint32) << 16 | \
                    image.astype(np.uint32) << 8 | \
                    image.astype(np.uint32)
        imdat = np.require(imdat, dtype='uint32', requirements='C').flatten()
        # QImage.Format_ARGB32 is to be used, other formats caused memory errors for unknown reasons
        # (even Format_RGB32 is troublesome)
        return QImage(imdat.data, image.shape[1], image.shape[0], QImage.Format_ARGB32)

    ########################
    #### update methods ####
    ########################

    def updateScene(self):
        if self.bgImage is None:
            return
        self.bgPixmap.setPixmap(QPixmap.fromImage(self.bgImage))
        self.update_display_channel()


    def update_display_channel(self):
        for timestamp in self.annotationMgr.annotations.keys():
            pen, brush = self.annotationMgr.appearance(self.annotationMgr.annotations[timestamp], self.display_attr)
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

        # self.updateScene()
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


    def cancel_operation(self):
        if self.operation == POLYGON or self.operation == BBX or self.operation == OVAL or self.operation == LINE:
            if self.drawing:
                self.drawing = False
                self.currentCommand.cancel()



    ###########################################
    #### mouse and keyboard event handling ####
    ###########################################

    def mousePressEvent(self, event):
        self.clickedBtn = event.button()
        self.clickPos = event.scenePos()
        self.timer = QTimer()
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.singleClickAction)
        self.timer.start()

    def singleClickAction(self):
        self.timer.stop()
        if self.clickedBtn & QtCore.Qt.LeftButton:
            if self.operation == POLYGON:
                if self.drawing:
                    self.currentCommand.finish()
                    self.drawing = False
                else:
                    self.currentCommand = PolygonPainter(self, self.annotationMgr, self.clickPos)
                    self.drawing = True
            elif self.operation == SMARTPOLYGON:
                if self.drawing:
                    self.currentCommand.finish()
                    self.drawing = False
                else:
                    self.currentCommand = SmartPainter(self, self.annotationMgr, self.clickPos)
                    self.drawing = True
            elif self.operation == BBX:
                if self.drawing:
                    self.currentCommand.finish()
                    self.drawing = False
                else:
                    self.currentCommand = BBXPainter(self, self.annotationMgr, self.clickPos)
                    self.drawing = True
            elif self.operation == OVAL:
                if self.drawing:
                    self.currentCommand.finish()
                    self.drawing = False
                else:
                    self.currentCommand = OvalPainter(self, self.annotationMgr, self.clickPos)
                    self.drawing = True
            elif self.operation == POINT:
                self.currentCommand = PointPainter(self, self.annotationMgr, self.clickPos, self.config['DotAnnotationRadius'])
                self.currentCommand.finish()
            elif self.operation == LINE:
                if self.drawing:
                    self.currentCommand.finish()
                    self.drawing = False
                else:
                    self.currentCommand = LinePainter(self, self.annotationMgr, self.clickPos)
                    self.drawing = True
            if self.operation == BROWSE:
                pass

    def mouseDoubleClickEvent(self, event):
        self.timer.stop()
        if event.button() == Qt.LeftButton:
            if self.drawing:
                self.currentCommand.finish()
                self.drawing = False
            else:
                self.selectItem(event)

    def mouseMoveEvent(self, event):
        assert isinstance(event, QGraphicsSceneMouseEvent)
        if self.operation == POLYGON and self.drawing:
            self.currentCommand.mouseMoveEvent(event)
        elif self.operation == SMARTPOLYGON and self.drawing:
            self.currentCommand.mouseMoveEvent(event)
        elif self.operation == LINE and self.drawing:
            self.currentCommand.mouseMoveEvent(event)
        elif self.operation == BBX and self.drawing:
            self.currentCommand.mouseMoveEvent(event)
        elif self.operation == OVAL and self.drawing:
            self.currentCommand.mouseMoveEvent(event)

    def set_tool(self, tool):
        self.operation = tool
        self.drawing = False
        self.currentCommand = None


    def wheelEvent(self, event):
        pass
        # if event.delta() < 0:
        #     if self.operation == OVAL and self.drawing:
        #         self.currentCommand.shrink()
        # elif event.delta() > 0:
        #     if self.operation == OVAL and self.drawing:
        #         self.currentCommand.expand()
        # else:
        #     pass


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.cancel_operation()
        elif self.selectedItems and event.key() == Qt.Key_Delete:
            self.deleteItem()
        elif event.key() == Qt.Key_Z:
            if self.operation == OVAL and self.drawing:
                self.currentCommand.shrink()
            elif self.operation == POINT:
                self.currentCommand.shrink()
        elif event.key() == Qt.Key_A:
            if self.operation == OVAL and self.drawing:
                self.currentCommand.expand()
            elif self.operation == POINT:
                self.currentCommand.expand()

