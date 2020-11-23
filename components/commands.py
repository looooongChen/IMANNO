__author__ = 'long, bug'

from PyQt5.QtGui import QPen, QBrush, QPolygonF, QColor, QTransform, QPainterPath 
from PyQt5.QtWidgets import QGraphicsPolygonItem
from PyQt5.QtCore import Qt, QRectF, QLineF, QPointF, QSizeF
from datetime import datetime as datim
from abc import abstractmethod
import numpy as np
import copy
import cv2

from .enumDef import *

class BaseToolClass(object):

    def __init__(self, canvas, annotationMgr):
        super().__init__()
        self.canvas = canvas
        self.annotationMgr = annotationMgr
        self.linePen = QPen(QColor(0, 200, 0, 255), 0, Qt.DashLine, Qt.RoundCap, Qt.RoundJoin)
        self.areaBrush = QBrush(QColor(0, 200, 0, 70))

    @abstractmethod
    def process(self):
        pass

    def finish(self):
        self.process()

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
        pass

    def keyReleaseEvent(self, event):
        pass

    def cancel(self):
        pass

#################################
#### class for point drawing ####
#################################


class DotPainter(BaseToolClass):
    def __init__(self, canvas, annotationMgr, start):
        super().__init__(canvas, annotationMgr)
        self.start = start
        print('======== Dot Annotation Drawing ========')

    def process(self):
        print("INFO: Dot Finished At ({},{})".format(self.start.x(), self.start.y()))
        dataObj = {'timestamp': datim.today().isoformat('@'),  
                   'type': DOT,  
                   'labels': {},  
                   'coords': [self.start.x(), self.start.y()]}
        self.annotationMgr.new_annotation(dataObj)
        self.canvas.set_tool(DOT)

###################################
#### class for line drawing ####
###################################

class CurvePainter(BaseToolClass):

    def __init__(self, canvas, annotationMgr, start):
        super().__init__(canvas, annotationMgr)

        self.start = start
        self.line = QPolygonF() << self.start
        path = QPainterPath()
        path.addPolygon(self.line)
        self.pathItem = self.canvas.addPath(path, self.linePen)
        print('======== Curve Annotation Drawing ========')

    def mouseMoveEvent(self, event):
        self.line << event.scenePos()
        path = QPainterPath()
        path.addPolygon(self.line)
        self.pathItem.setPath(path)

    def process(self):
        # get data from QPolygonF
        if self.line.size() < 2:
            print('WARN: Curve Too Short :(')
        else:
            vptr = self.line.data()
            vptr.setsize(8*2*self.line.size())
            # approximation of the original polygon
            poly = np.ndarray(shape=(self.line.size(), 2), dtype=np.float64, buffer=vptr)
            poly_appx = np.squeeze(cv2.approxPolyDP(np.float32(poly), .7, False))
            minLength = self.annotationMgr.config['minCurveLength']
            if cv2.arcLength(poly_appx, False) < minLength:
                print('WARN: Curve Too Short :(')
            else:
                bbx = self.pathItem.boundingRect()
                dataObj = {'timestamp': datim.today().isoformat('@'),  
                           'type': CURVE,  
                           'labels': {},  
                           'coords': [[poly_appx[i,0], poly_appx[i,1]] for i in range(len(poly_appx))],
                           'bbx': [bbx.x(), bbx.y(), bbx.width(), bbx.height()]}
                print("INFO: Curve Finished At: ", dataObj['bbx']) 
                print("INFO: {} Points Approxmated By {} Vertices".format(poly_appx.shape[0], len(poly_appx)))
                self.annotationMgr.new_annotation(dataObj)
        self.canvas.removeItem(self.pathItem)
        self.canvas.set_tool(CURVE)

    def cancel(self):
        print("INFO: Curve Drawing Canceled")
        self.canvas.removeItem(self.pathItem)


###################################
#### class for polygon drawing ####
###################################

class PolygonPainter(BaseToolClass):

    def __init__(self, canvas, annotationMgr, start):
        super().__init__(canvas, annotationMgr)

        self.start = start
        self.polygon = QPolygonF() << self.start
        self.polygonItem = self.canvas.addPolygon(self.polygon, self.linePen, self.areaBrush)
        print('======== Polygon Annotation Drawing ========')

    def mouseMoveEvent(self, event):
        self.polygon << event.scenePos()
        self.polygonItem.setPolygon(self.polygon)
        self.polygonItem.update()

    def process(self):
        if self.polygon.size() < 2:
            print('WARN: Polygon Too Short :(')
        else:
            vptr = self.polygon.data()
            vptr.setsize(8*2*self.polygon.size())
            # compute a approximation of the original polygon
            poly = np.ndarray(shape=(self.polygon.size(), 2), dtype=np.float64, buffer=vptr)
            poly_appx = np.squeeze(cv2.approxPolyDP(np.float32(poly), .7, True))
            minArea = self.annotationMgr.config['minPolygonArea']
            if poly_appx.shape[0] < 3:
                print('WARN: Polygon Too Short :(')
            elif cv2.contourArea(poly_appx) < minArea:
                print('WARN: Polygon Too Short :(')
            else:
                bbx = self.polygonItem.boundingRect()
                dataObj = {'timestamp': datim.today().isoformat('@'),  
                           'type': POLYGON,  
                           'labels': {},  
                           'coords': [[poly_appx[i,0], poly_appx[i,1]] for i in range(len(poly_appx))],
                           'bbx': [bbx.x(), bbx.y(), bbx.width(), bbx.height()]}
                print("INFO: Polygon Finished At: ", dataObj['bbx']) 
                print("INFO: {} Points Approxmated By {} Vertices".format(poly_appx.shape[0], len(poly_appx)))
                self.annotationMgr.new_annotation(dataObj)
        self.canvas.removeItem(self.polygonItem)
        self.canvas.set_tool(POLYGON)

    def cancel(self):
        print("INFO: Polygon Drawing Canceled")
        self.canvas.removeItem(self.polygonItem)

class LivewirePainter(PolygonPainter):

    def __init__(self, canvas, annotationMgr, start, radius=100):
        super().__init__(canvas, annotationMgr, start)

        self.radius = radius
        self.poly_tmp = QPolygonF()
        # self.canvas.sync_livewire_image()
        self.canvas.livewire.set_seed(self.start.x(), self.start.y(), self.radius)
        print('======== Livewire Drawing ========')
         
    def mouseSingleClickEvent(self, pt):
        path_x, path_y = self.canvas.livewire.get_path(pt.x(), pt.y())
        self.canvas.livewire.set_seed(pt.x(), pt.y(), self.radius)
        for i in reversed(range(len(path_x)-1)):
            self.polygon << QPointF(path_x[i], path_y[i])
        self.polygonItem.setPolygon(self.polygon)
        self.polygonItem.update()

    def mouseMoveEvent(self, event):
        pt = event.scenePos()
        self.poly_tmp.clear()
        path_x, path_y = self.canvas.livewire.get_path(pt.x(), pt.y())
        for i in reversed(range(len(path_x)-1)):
            self.poly_tmp << QPointF(path_x[i], path_y[i])
        self.polygonItem.setPolygon(self.polygon+self.poly_tmp)
        self.polygonItem.update()

    def process(self):
        self.mouseSingleClickEvent
        super().process()
        self.canvas.set_tool(LIVEWIRE)
    
###################################
#### class for ellipse drawing ####
###################################

class BBXPainter(BaseToolClass):

    def __init__(self, canvas, annotationMgr, start):
        super().__init__(canvas, annotationMgr)

        self.start = start
        self.bbx = QRectF()
        self.bbx.setTopLeft(QPointF(start))
        self.bbx.setSize(QSizeF(0,0))
        # add a box item to QGraphicsScene
        self.bbxItem = self.canvas.addRect(self.bbx, self.linePen, self.areaBrush)
        print('======== Bounding Box Drawing ========')

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
        minLength = self.annotationMgr.config['minBBXLength']
        if self.bbx.width() < minLength or self.bbx.height() < minLength:
            print('WARN: Bounding Box Too Small :(')
        else:
            dataObj = {'timestamp': datim.today().isoformat('@'),  
                       'type': BBX,  
                       'labels': {}, 
                       'bbx': [self.bbx.left(), self.bbx.top(), self.bbx.width(), self.bbx.height()]}
            print("INFO: Bounding Box Finished At: ", dataObj['bbx']) 
            self.annotationMgr.new_annotation(dataObj)
        self.canvas.removeItem(self.bbxItem)
        self.canvas.set_tool(BBX)

    def cancel(self):
        print("INFO: Bounding Box Drawing Canceled")
        self.canvas.removeItem(self.bbxItem)

##################################
#### class for circle drawing ####
##################################

class EllipsePainter(BaseToolClass):

    def __init__(self, canvas, annotationMgr, start):
        super().__init__(canvas, annotationMgr)

        self.h = 0
        self.w_ratio = 1
        self.cx = 0
        self.cy = 0
        self.angle = 0

        self.start = start
        self.bbx = QRectF()

        # add a box item to QGraphicsScene
        self.ovalItem = self.canvas.addEllipse(self.bbx, self.linePen, self.areaBrush)
        print('======== Ellipse Annotation Drawing ========')

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
        # self.bbx.setTopLeft(QPointF(-1 * self.w_ratio*self.h / 2, -1*self.h / 2))
        # self.bbx.setSize(QSizeF(self.w_ratio*self.h,self.h))
        self.bbx.setTopLeft(QPointF(-1*self.h / 2, -1 * self.w_ratio*self.h / 2))
        self.bbx.setSize(QSizeF(self.h, self.w_ratio*self.h))

    def _transformOval(self):
        t = QTransform()
        t.translate(self.cx, self.cy)
        # print(-1 * self.angle + 90)
        t.rotate(-1 * self.angle)
        self.ovalItem.setTransform(t)


    def process(self):
        minAxis = self.annotationMgr.config['minEllipseAxis']
        if self.h < minAxis or self.h * self.w_ratio < minAxis:
            print('WARN: Ellipse Too Small :(')
        else:
            dataObj = {'timestamp': datim.today().isoformat('@'),  
                       'type': ELLIPSE,  
                       'labels': {},  
                       'coords': [self.cx, self.cy],  
                       'angle': self.angle,  
                       'axis': [self.h, self.w_ratio*self.h],
                       'bbx': [0, 0, 0, 0]}
            print("INFO: Ellipse Finished at ({},{}), with axis ({},{}), in orientation {}".format(self.cx, self.cy, self.h, self.w_ratio*self.h, self.angle))
            self.annotationMgr.new_annotation(dataObj)
        self.canvas.removeItem(self.ovalItem)
        self.canvas.set_tool(ELLIPSE)


    def cancel(self):
        print("Drawing canceled")
        self.canvas.removeItem(self.ovalItem)

class DeleteAnnotation(BaseToolClass):
    def __init__(self, canvas, annotationMgr, graphItems):
        super().__init__(canvas, annotationMgr)
        self.graphItems = graphItems
        self.finish()

    def process(self):
        for item in self.graphItems:
            self.annotationMgr.delete_annotation_by_graphItem(item)

