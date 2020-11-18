from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF
from PyQt5.QtGui import QPolygonF, QColor, QTransform, QPainter, QPainterPath  
from PyQt5.QtWidgets import QGraphicsPolygonItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsPathItem, QGraphicsItem
import numpy as np
import math

from abc import abstractmethod
from enumDef import *


############################
#### annotation classes ####
############################

class Annotation(object):

    """
    class that contains the data of an annotation and labels, 
    in addition, the method giving the graph object is also implemented in the Annotation class
    """

    def __init__(self, timestamp, obj, labelMgr):
        '''
        Args:
            timestamp: datim.today().isoformat('@')
            obj: dataObject or graphObject
            labelMgr: labelManager.LableManager object
        '''
        self.timestamp = timestamp
        self.labelMgr = labelMgr
        self.labels = {}
        if isinstance(obj, dict):
            self.dataObject = obj
            self.from_dataObject(obj)
            self.parse_labels()
        elif isinstance(obj, QGraphicsItem):
            self.graphObject = obj
            self.from_graphObject(obj)

    def parse_labels(self):
        if 'labels' in self.dataObject.keys()
            for prop_name, label_name in self.dataObject['labels'].items():
                self.labelMgr.assign(self, prop_name, label_name)
            self.dataObject['labels'] = {}
    
    def render_save(self):
        save_dict = self.dataObject.copy()
        save_dict['labels'] = {label.property.name: label.name for label in self.labels}
        return save_dict

    def assign_label(self, prop_name, label_name):
        self.labelMgr.assign(self, prop_name, label_name)

    def withdraw_label(self, prop_name, label_name):
        self.labelMgr.withdraw(self, prop_name, label_name)

    @abstractmethod
    def from_dataObject(self, dataObject):
        """
        an abstract method to set and return the self.graphObject from the data object
        Return: self.graphObject
        """
        pass

    @abstractmethod
    def from_graphObject(self, graphObject):
        """
        an abstract method to set and return the self.dataObject from the graph object,
        Return: self.dataObject
        """
        pass

    ## hdf5 compatible
    @classmethod
    def dataObject_from_hdf5(cls, anno):
        dataObject = {'timestamp': anno.attrs['timestamp'],
                      'labels': {}}
        if 'labels' in anno.keys():
            for attr_name in anno['labels'].keys():
                label_name = anno['labels'][attr_name].attrs['label_name']
                dataObject['labels'][attr_name] = label_name

        return dataObject



class DotAnnotation(Annotation):

    def __init__(self, timestamp, dot, labelMgr):
        """
        Args:
            timestamp: timestamp
            dot: {'timestamp': datim.today().isoformat('@'),  
                  'type': DOT,  
                  'labels': {propperty: label, ...},  
                  'coords': [x, y]}
                or QGraphicsPolygonItem  
        """
        self.radius = 5
        super().__init__(timestamp, dot, labelMgr)

    def _star(self, center, R):
        star = [QPointF(0,R), QPointF(R/3,R/3), QPointF(R,0), QPointF(R/3,-R/3), QPointF(0,-R), QPointF(-R/3,-R/3), QPointF(-R,0), QPointF(-R/3,R/3)]
        star = [pt + QPointF(center[0], center[1]) for pt in star]
        star = QPolygonF(star)
        star = QGraphicsPolygonItem(star)
        return star

    def from_dataObject(self, obj):
        self.graphObject = self._star(obj['coords'], self.radius)
        return self.graphObject

    def adjust_graphObject(self, radius):
        self.radius = radius
        self.graphObject = self._star(self.dataObject['coords'], self.radius)
        return self.graphObject

    def from_graphObject(self, obj):
        self.dataObject = {'timestamp': self.timestamp,  
                           'type': DOT,  
                           'labels': {},  
                           'coords': [0, 0]}
        center = obj.polygon().boundingRect().center()
        self.dataObject['coords'] = [center.x(), center.y()]
        return self.dataObject
    
    @classmethod
    def dataObject_from_hdf5(cls, anno):
        dataObject = Annotation.dataObject_from_hdf5(anno)
        dataObject['type'] = DOT
        dataObject['coords'] = [anno['pt'][0], anno['pt'][1]]
        return dataObject

class CurveAnnotation(Annotation):

    def __init__(self, timestamp, curve, labelMgr):
        """
        Args:
            timestamp: timestamp
            curve: {'timestamp': datim.today().isoformat('@'),  
                    'type': CURVE,  
                    'labels': {propperty: label, ...},  
                    'coords': [[x1, y1], [x2, y2], ...],
                    'bbx': [x, y, w, h]}
                  or QGraphicsPathItem
        """
        super().__init__(timestamp, curve, labelMgr)
    
    def from_dataObject(self, obj):
        curve = QPainterPath()
        curve.addPolygon(QPolygonF([QPointF(pt[0], pt[1]) for pt in obj['coords']]))
        self.graphObject = QGraphicsPathItem(curve)
        return self.graphObject

    def from_graphObject(self, obj):
        self.dataObject = {'timestamp': self.timestamp,  
                           'type': CURVE,  
                           'labels': {},  
                           'coords': [],
                           'bbx': [0,0,0,0]}
        # add coords
        curve = obj.path()
        for i in range(curve.elementCount()):
            pt = curve.elementAt(i)
            self.dataObject['coords'].append([pt.x(), pt.y()])
        # add bbx
        bbx = curve.boundingRect()
        self.dataObject['bbx'] = [bbx.x(), bbx.y(), bbx.width(), bbx.height()]
        return self.dataObject
    
    @classmethod
    def dataObject_from_hdf5(cls, anno):
        dataObject = Annotation.dataObject_from_hdf5(anno)
        dataObject['type'] = CURVE
        dataObject['bbx'] = list(anno['boundingBox'])
        xx, yy = anno['line'][:,0]+dataObject['bbx'][0], anno['line'][:,1]+dataObject['bbx'][1]
        dataObject['coords'] = [[x, y] for x,y in zip(xx, yy)]
        return dataObject
    

class PolygonAnnotation(Annotation):

    def __init__(self, timestamp, polygon, labelMgr):
        """
        Args:
            timestamp: timestamp
            polygon: {'timestamp': datim.today().isoformat('@'),  
                      'type': POLYGON,  
                      'labels': {propperty: label, ...},  
                      'coords': [[x1, y1], [x2, y2], ...],
                      'bbx': [x, y, w, h]}
                    or QGraphicsPathItem
        """
        super().__init__(timestamp, polygon, labelMgr)


    def from_dataObject(self, obj):
        polygon = QPolygonF([QPointF(pt[0], pt[1]) for pt in obj['coords']])
        self.graphObject = QGraphicsPolygonItem(polygon)
        return self.graphObject

    def from_graphObject(self, obj):
        self.dataObject = {'timestamp': self.timestamp,  
                           'type': POLYGON,  
                           'labels': {},  
                           'coords': [],
                           'bbx': [0,0,0,0]}
        # add coords
        polygon = obj.polygon()
        for i in range(polygon.count()):
            pt = polygon[i]
            self.dataObject['coords'].append([pt.x(), pt.y()])
        # add bbx
        bbx = polygon.boundingRect()
        self.dataObject['bbx'] = [bbx.x(), bbx.y(), bbx.width(), bbx.height()]
        return self.dataObject
    
    @classmethod
    def dataObject_from_hdf5(cls, anno):
        dataObject = Annotation.dataObject_from_hdf5(anno)
        dataObject['type'] = POLYGON
        dataObject['bbx'] = list(anno['boundingBox'])
        xx, yy = anno['polygon'][:,0]+dataObject['bbx'][0], anno['polygon'][:,1]+dataObject['bbx'][1]
        dataObject['coords'] = [[x, y] for x,y in zip(xx, yy)]
        return dataObject
   

class BBXAnnotation(Annotation):

    def __init__(self, timestamp, bbx, labelMgr):
        """
        Args:
            timestamp: timestamp
            bbx: {'timestamp': datim.today().isoformat('@'),  
                  'type': BBX,  
                  'labels': {propperty: label, ...}, 
                  'bbx': [x, y, w, h]}
                or QGraphicsRectItem
        """
        super().__init__(timestamp, bbx, labelMgr)

    def from_dataObject(self, obj):
        bbx = QRectF()
        bbx.setTopLeft(QPointF(obj['bbx'][0], obj['bbx'][1]))
        bbx.setSize(QSizeF(obj['bbx'][2], obj['bbx'][3]))
        self.graphObject = QGraphicsRectItem(bbx)
        return self.graphObject

    def from_graphObject(self, obj):
        self.dataObject = {'timestamp': self.timestamp,  
                           'type': BBX,  
                           'labels': {},  
                           'bbx': [0,0,0,0]}
        # add bbx
        bbx = obj.rect()
        self.dataObject['bbx'] = [bbx.x(), bbx.y(), bbx.width(), bbx.height()]
        return self.dataObject
    
    @classmethod
    def dataObject_from_hdf5(cls, anno):
        dataObject = Annotation.dataObject_from_hdf5(anno)
        dataObject['type'] = BBX
        dataObject['bbx'] = list(anno['boundingBox'])
        return dataObject


class EllipseAnnotation(Annotation):

    def __init__(self, timestamp, ellipse, labelMgr):
        """
        Args:
            timestamp: timestamp
            ellipse: {'timestamp': datim.today().isoformat('@'),  
                      'type': ELLIPSE,  
                      'labels': {propperty: label, ...},  
                      'coords': [x, y],  
                      'angle': angle,  
                      'axis': [axis_major, axis_minor],
                      'bbx': [x, y, w, h]}
        """
        super().__init__(timestamp, ellipse, labelMgr)

    def from_dataObject(self, obj):
        bbx = QRectF()
        # add ellipse
        axis_major, axis_minor = obj['axis'][0], obj['axis'][1]
        # bbx.setTopLeft(QPointF(-1 * axis_minor / 2, -1 * axis_major / 2))
        # bbx.setSize(QSizeF(axis_minor, axis_major))
        bbx.setTopLeft(QPointF(-1 * axis_major / 2, -1 * axis_minor / 2))
        bbx.setSize(QSizeF(axis_major, axis_minor))
        self.graphObject = QGraphicsEllipseItem(bbx)
        # transfrom
        t = QTransform()
        # t.rotate(-1 * obj['angle'] + 90)
        t.rotate(-1 * obj['angle'])
        t.translate(obj['coords'][0], obj['coords'][1])
        self.graphObject.setTransform(t)

        return self.graphObject


    def from_graphObject(self, obj):
        self.dataObject = {'timestamp': self.timestamp,  
                           'type': ELLIPSE,  
                           'labels': {},  
                           'coords': [0, 0],  
                           'angle': 0,  
                           'axis': [0, 0],
                           'bbx': [0, 0, 0, 0]}
        t = obj.transform()
        self.dataObject['coords'] = [t.m31(), t.m32()] 
        self.dataObject['angle'] = math.degrees(math.acos(t.m11()))
        self.dataObject['axis'] = [obj.rect().x(), obj.rect().y()]
        a, b = self.dataObject['axis'][0]/2, self.dataObject['axis'][1]/2
        c, s = math.cos(math.radians(-self.dataObject['angle'])), math.sin(math.radians(-self.dataObject['angle']))
        X, Y = math.sqrt((a*c)**2+(b*s)**2), math.sqrt((a*s)**2+(b*c)**2) 
        self.dataObject['bbx'] = [t.m31()-X, t.m33()-Y, 2*X, 2*Y]
        return self.dataObject
    
    @classmethod
    def dataObject_from_hdf5(cls, anno):
        dataObject = Annotation.dataObject_from_hdf5(anno)
        dataObject['type'] = ELLIPSE
        dataObject['coords'] = list(anno['center'])
        dataObject['angle'] = anno['angle'].value
        dataObject['axis'] = list(anno['axis'])
        a, b = dataObject['axis'][0]/2, dataObject['axis'][1]/2
        c, s = math.cos(math.radians(-dataObject['angle'])), math.sin(math.radians(-dataObject['angle']))
        X, Y = math.sqrt((a*c)**2+(b*s)**2), math.sqrt((a*s)**2+(b*c)**2) 
        dataObject['bbx'] = [dataObject['coords'][0]-X, dataObject['coords'][1]-Y, 2*X, 2*Y]
        
        return dataObject
    