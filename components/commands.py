__author__ = 'long, bug'

from PyQt5.QtGui import QPen, QBrush, QPolygonF, QColor, QTransform, QPainterPath 
from PyQt5.QtWidgets import QGraphicsPolygonItem
from PyQt5.QtCore import Qt, QRectF, QLineF, QPointF, QSizeF
# from PyQt4.QtWidgets import
# from PyQt5.QtCore import *
# import FESI as fesi
import numpy as np
import cv2

from abc import abstractmethod
import copy

from .graphDef import *

class BaseToolClass(object):

    def __init__(self, scene, annotationMgr):
        super().__init__()
        self.scene = scene
        self.annotationMgr = annotationMgr

    @abstractmethod
    def process(self):
        pass

    def finish(self):
        self.process()
        # self.scene.commandCompleted.emit(self)

    def undo(self):
        pass

    def redo(self):
        pass

    def clean(self):
        pass

    # Mouse Events
    def mousePressEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        pass

    def mouseDoubleClickEvent(self, event):
        pass

    # Keyboard Events
    def keyPressEvent(self, event):
        # if event.key() == Qt.Key_Escape:
        #     self.parent.currentUndoCommand = None
        #     self.clean()
        pass

    def keyReleaseEvent(self, event):
        pass

    def cancel(self):
        pass

#################################
#### class for point drawing ####
#################################


class PointPainter(BaseToolClass):
    def __init__(self, scene, annotationMgr, start, radius=2):
        super().__init__(scene, annotationMgr)

        self.linePen = QPen(QColor(0, 200, 0, 255), 0, Qt.DashLine, Qt.RoundCap, Qt.RoundJoin)
        self.areaBrush = QBrush(QColor(0, 200, 0, 255))

        self.start = start
        self.radius = radius

        self.dotItem = self.scene.addEllipse(start.x()-self.radius,start.y()-self.radius, self.radius*2, self.radius*2, self.linePen, self.areaBrush)

        print('====================================')
        print('A new point is drawed')

    def process(self):
        try:
            print("Point finished: (", self.start.x(), ', ', self.start.y(), ')')
            # transfer the data to annotation manager
            print("Pass the point to annotationMgr")
            self.scene.removeItem(self.dotItem)
            self.annotationMgr.new_annotation(POINT, np.array([self.start.x(), self.start.y()]))
            # set default tool and update scene
            self.scene.set_tool(POINT)
            # self.scene.updateScene()
        except Exception as e:
            print(e)
            print("Point annotation saving error :-(")

###################################
#### class for line drawing ####
###################################

class LinePainter(BaseToolClass):

    def __init__(self, scene, annotationMgr, start):
        super().__init__(scene, annotationMgr)

        self.start = start
        self.line = QPolygonF()
        self.line << self.start
        # add a polygon figure to QGraphicsScene
        self.linePen = QPen(QColor(0, 200, 0, 255), 0, Qt.DashLine, Qt.RoundCap, Qt.RoundJoin)
        path = QPainterPath()
        path.addPolygon(self.line)

        self.pathItem = self.scene.addPath(path, self.linePen)
        print('====================================')
        print('Drawing a new line')

    def mouseMoveEvent(self, event):
        self.line << event.scenePos()
        path = QPainterPath()
        path.addPolygon(self.line)
        self.pathItem.setPath(path)
        # self.polygonItem.update()

    def process(self):
        try:
            # get data from QPolygonF
            vptr = self.line.data()
            vptr.setsize(8*2*self.line.size())
            # compute a approximation of the original polygon
            poly = np.ndarray(shape=(self.line.size(), 2), dtype=np.float64, buffer=vptr)
            poly_appx = np.squeeze(cv2.approxPolyDP(np.float32(poly), .7, False))
            # display message
            print("Line finished: ", self.pathItem.boundingRect(), poly.shape[0], " points are approxmated by ", poly_appx.shape[0], " points")
            print("Pass the line to annotationMgr")
            self.scene.removeItem(self.pathItem)
            self.annotationMgr.new_annotation(LINE, poly_appx)
            self.scene.set_tool(LINE)
        except Exception as e:
            print(e)
            print("You should move the mouse a little more before finishing a polygon :-)")

    def cancel(self):
        print("Drawing canceled")
        self.scene.removeItem(self.pathItem)


###################################
#### class for polygon drawing ####
###################################

class PolygonPainter(BaseToolClass):

    def __init__(self, scene, annotationMgr, start):
        super().__init__(scene, annotationMgr)

        self.start = start
        self.polygon = QPolygonF()
        self.polygon << self.start
        # add a polygon figure to QGraphicsScene
        self.linePen = QPen(QColor(0, 200, 0, 255), 0, Qt.DashLine, Qt.RoundCap, Qt.RoundJoin)
        self.areaBrush = QBrush(QColor(0, 200, 0, 70))
        self.polygonItem = self.scene.addPolygon(self.polygon, self.linePen, self.areaBrush)
        print('====================================')
        print('Drawing a new polygon')

    def mouseMoveEvent(self, event):
        self.polygon << event.scenePos()
        self.polygonItem.setPolygon(self.polygon)
        self.polygonItem.update()

    def process(self):
        try:
            # get data from QPolygonF
            vptr = self.polygon.data()
            vptr.setsize(8*2*self.polygon.size())
            # compute a approximation of the original polygon
            poly = np.ndarray(shape=(self.polygon.size(), 2), dtype=np.float64, buffer=vptr)
            poly_appx = np.squeeze(cv2.approxPolyDP(np.float32(poly), .7, True))
            if poly_appx.shape[0] <= 3:
                print("You should move the mouse a little more before finishing a polygon :-)")
            else:
                print("Polygon finished: ", self.polygonItem.boundingRect(), poly.shape[0], " points are approxmated by ", poly_appx.shape[0], " points")
                print("Pass the polygon to annotationMgr")
                self.annotationMgr.new_annotation(POLYGON, poly_appx)
            self.scene.removeItem(self.polygonItem)
            self.scene.set_tool(POLYGON)
        except Exception as e:
            print(e)

    def cancel(self):
        print("Drawing canceled")
        self.scene.removeItem(self.polygonItem)

class LivewirePainter(PolygonPainter):

    def __init__(self, scene, annotationMgr, start):
        super().__init__(scene, annotationMgr, start)

        self.poly_tmp = QPolygonF()
        self.scene.refresh_livewire()
        self.scene.livewire.set_seed((self.start.x(), self.start.y()))
        print('====================================')
        print('Livewire tool activated')
         
    def mouseSingleClickEvent(self, pt):
        path_x, path_y = self.scene.livewire.get_path((pt.x(), pt.y()))
        self.scene.livewire.set_seed((pt.x(), pt.y()))
        for i in reversed(range(len(path_x)-1)):
            self.polygon << QPointF(path_x[i], path_y[i])
        self.polygonItem.setPolygon(self.polygon)
        self.polygonItem.update()

    def mouseMoveEvent(self, event):
        pt = event.scenePos()
        self.poly_tmp.clear()
        path_x, path_y = self.scene.livewire.get_path((pt.x(), pt.y()))
        for i in reversed(range(len(path_x)-1)):
            self.poly_tmp << QPointF(path_x[i], path_y[i])
        self.polygonItem.setPolygon(self.polygon+self.poly_tmp)
        self.polygonItem.update()
        # for i in reversed(range(len(path_x)-1)):
        #     self.polygon.remove(-1)

    def process(self):
        super().process()
        self.scene.set_tool(LIVEWIRE)
    
###################################
#### class for ellipse drawing ####
###################################

class BBXPainter(BaseToolClass):

    def __init__(self, scene, annotationMgr, start):
        super().__init__(scene, annotationMgr)

        self.start = start
        self.bbx = QRectF()
        self.bbx.setTopLeft(QPointF(start))
        self.bbx.setSize(QSizeF(0,0))
        # add a box item to QGraphicsScene
        self.linePen = QPen(QColor(0, 200, 0, 255), 0, Qt.DashLine, Qt.RoundCap, Qt.RoundJoin)
        self.areaBrush = QBrush(QColor(0, 200, 0, 70))
        self.bbxItem = self.scene.addRect(self.bbx, self.linePen, self.areaBrush)
        print('====================================')
        print('Drawing a new bounding box')

    def mouseMoveEvent(self, event):
        topleft, size = self._getRectParas(self.start, event.scenePos())
        self.bbx.setTopLeft(topleft)
        self.bbx.setSize(size)
        self.bbxItem.setRect(self.bbx)
        self.bbxItem.update()

    def _getRectParas(self, p1, p2):
        x = min(p1.x(), p2.x())
        y = min(p1.y(), p2.y())
        w = abs(p1.x()-p2.x())
        h = abs(p1.y()-p2.y())
        return QPointF(x, y), QSizeF(w, h)

    def process(self):
        try:
            print("Bounding box finished: top left point (", self.bbx.left(), ', ', self.bbx.top(),
                  '), size (', self.bbx.width(), ', ', self.bbx.height(), ')')
            # transfer the data to annotation manager
            print("Pass the bounding box to annotationMgr")
            self.scene.removeItem(self.bbxItem)
            self.annotationMgr.new_annotation(BBX, np.array((self.bbx.x(), self.bbx.y(), self.bbx.width(), self.bbx.height())))
            self.scene.set_tool(BBX)
        except Exception as e:
            print(e)
            print("Bounding box drawing error :-(")

    def cancel(self):
        print("Drawing canceled")
        self.scene.removeItem(self.bbxItem)

##################################
#### class for circle drawing ####
##################################

class OvalPainter(BaseToolClass):

    def __init__(self, scene, annotationMgr, start):
        super().__init__(scene, annotationMgr)

        self.h = 0
        self.w_ratio = 1
        self.cx = 0
        self.cy = 0
        self.angle = 0

        self.start = start
        self.bbx = QRectF()

        # add a box item to QGraphicsScene
        self.linePen = QPen(QColor(0, 200, 0, 255), 0, Qt.DashLine, Qt.RoundCap, Qt.RoundJoin)
        self.areaBrush = QBrush(QColor(0, 200, 0, 70))
        self.ovalItem = self.scene.addEllipse(self.bbx, self.linePen, self.areaBrush)
        print('====================================')
        print('Drawing a new ellipse')


    def mouseMoveEvent(self, event):
        self._updateSize(self.start, event.scenePos())
        self._updateOval()

    def shrink(self):
        self.w_ratio = self.w_ratio * 0.9
        self._updateOval()

    def expand(self):
        self.w_ratio = self.w_ratio * 1.1
        self._updateOval()

    def _updateSize(self, p1, p2):
        self.h = ((p1.x()-p2.x())**2+(p1.y()-p2.y())**2)**0.5
        self.cx = (p1.x() + p2.x()) / 2
        self.cy = (p1.y() + p2.y()) / 2
        self.angle = QLineF(p1,p2).angle() % 180

    def _updateOval(self):
        self._resizeBBX()
        self.ovalItem.setRect(self.bbx)
        self._transformOval()
        self.ovalItem.update()

    def _resizeBBX(self):
        self.bbx.setTopLeft(QPointF(-1 * self.w_ratio*self.h / 2, -1*self.h / 2))
        self.bbx.setSize(QSizeF(self.w_ratio*self.h,self.h))

    def _transformOval(self):
        t = QTransform()
        t.translate(self.cx, self.cy)
        # print(-1 * self.angle + 90)
        t.rotate(-1 * self.angle + 90)
        self.ovalItem.setTransform(t)


    def process(self):
        try:
            print("Ellipse finished: center (", self.cx, ', ', self.cy,
                  '), size (', self.h, ', ', self.w_ratio*self.h, '), orientation ', self.angle)
            print("Pass the ellipse to annotationMgr")
            paras = {'center': np.array((self.cx, self.cy)), 'angle': self.angle,
                     'axis': np.array((self.h, self.h*self.w_ratio))}
            self.scene.removeItem(self.ovalItem)
            self.annotationMgr.new_annotation(OVAL, paras)
            self.scene.set_tool(OVAL)
        except Exception as e:
            print(e)
            print("Ellipse drawing error :-(")

    def cancel(self):
        print("Drawing canceled")
        self.scene.removeItem(self.ovalItem)

class DeleteAnnotation(BaseToolClass):
    def __init__(self, scene, annotationMgr, graphItems):
        super().__init__(scene, annotationMgr)
        self.graphItems = graphItems
        self.finish()

    def process(self):
        for item in self.graphItems:
            self.annotationMgr.delete_annotation_by_graphItem(item)

