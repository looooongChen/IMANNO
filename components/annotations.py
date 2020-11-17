from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF
from PyQt5.QtGui import QPolygonF, QColor, QTransform, QPainter, QPainterPath  
from PyQt5.QtWidgets import QGraphicsPolygonItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsPathItem, QGraphicsItem
import numpy as np
import math

from abc import abstractmethod
from .enumDef import *

#######################
#### label classes ####
#######################

# class Property(object):

#     def __init__(self, name, label_list=None):
#         """
#         Args:
#             name: name of the attribute e.g. Color
#             label_list: a list of label names e.g. ['red', 'blue' ...]
#         """
#         self.name = name
#         self.labels = {} # label_name - label_object
#         if label_list is not None:
#             for l in label_list:
#                 self.add_label(l)

#     def add_label(self, label_name, label_color=None):
#         if label_name not in self.labels.keys():
#             self.labels[label_name] = Label(self, label_name, label_color)

#     def remove_label(self, label):
#         label_name = label.label_name if isinstance(label, Label) else label
#         if label_name in self.labels.keys():
#             del self.labels[label.label_name]
    
#     def get_label(self, label_name):
#         if label_name in self.labels.keys():
#             return self.labels[label_name]
#         else:
#             return None
    
#     def rename(self, name):
#         if isinstance(name, str):
#             self.name = name
#             for l in self.labels:
#                 l.attr_name = name

#     def save(self, location):
#         """
#         Args:
#             location: a hdf5 root
#         """
#         attr_group = location.require_group('attributes')
#         if self.name in attr_group.keys():
#             del attr_group[self.name]
#         label_group = attr_group.create_group(self.name)
#         for label_name, label_obj in self.labels.items():
#             label_group.create_dataset(label_name, shape=(3,), dtype='uint8')
#             label_group[label_name][0] = label_obj.color[0]
#             label_group[label_name][1] = label_obj.color[1]
#             label_group[label_name][2] = label_obj.color[2]


# class Label(object):

#     def __init__(self, attr, label_name, color=None):
#         self.attr = attr
#         self.attr_name = attr.name
#         self.label_name = label_name
#         self.color = color

#     def set_color(self, r, g, b):
#         self.color = [r,g,b]

#     def rename(self, label_name):
#         if isinstance(label_name, str) and label_name not in self.attr.labels.keys():
#             self.attr.labels[label_name] = self.attr.labels.pop(self.label_name)
#             self.label_name = label_name

############################
#### annotation classes ####
############################

class Annotation(object):

    """
    class that contains the data of an annotation and labels, 
    in addition, the method giving the graph object is also implemented in the Annotation class
    """

    def __init__(self, timestamp, obj):
        '''
        Args:
            timestamp: timestamp timestamp = datim.today().isoformat('@')
            obj: dataObject or graphObject
        '''
        self.timestamp = timestamp
        if isinstance(obj, dict):
            self.dataObject = obj
            self.set_graphObject(obj)
        elif isinstance(obj, QGraphicsItem):
            self.graphObject = obj
            self.set_dataObject(obj)

    def set_label(self, prop, label):
        self.dataObject['labels'][prop] = label

    def remove_label(self, prop, label=None):
        if prop in self.dataObject['labels'].keys():
            if label is None or self.dataObject['labels'][prop] == label:
                del self.dataObject['labels'][prop]

    @abstractmethod
    def set_graphObject(self, dataObject):
        """
        an abstract method to set and return the self.graphObject from the data object
        Return: self.graphObject
        """
        pass

    @abstractmethod
    def set_dataObject(self, graphObject):
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

    def __init__(self, timestamp, dot):
        """
        Args:
            timestamp: timestamp
            dot: {'timestamp': datim.today().isoformat('@'),  
                  'type': DOT,  
                  'labels': {propperty: label, ...},  
                  'coords': [x, y]}
                or QGraphicsPolygonItem  
        """
        super().__init__(timestamp, dot)
        self.radius = 5

    def _star(self, center, R):
        star = QPointF(center[0], center[1]) + QPolygonF([QPointF(0,R), QPointF(R/3,R/3), QPointF(R,0), QPointF(R/3,-R/3), QPointF(0,-R), QPointF(-R/3,-R/3), QPointF(-R,0), QPointF(-R/3,R/3)])
        star = QGraphicsPolygonItem(star)
        return star

    def set_graphObject(self, obj):
        self.graphObject = self._star(obj['coords'], self.radius)
        return self.graphObject

    def adjust_graphObject(self, radius):
        self.radius = radius
        self.graphObject = self._star(self.dataObject['coords'], self.radius)
        return self.graphObject

    def set_dataObject(self, obj):
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

    def __init__(self, timestamp, curve):
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
        super().__init__(timestamp, curve)
    
    def set_graphObject(self, obj):
        curve = QPainterPath()
        curve.addPolygon(QPolygonF([QPointF(pt[0], pt[1]) for pt in obj['coords']]))
        self.graphObject = QGraphicsPathItem(curve)
        return self.graphObject

    def set_dataObject(self, obj):
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

    def __init__(self, timestamp, polygon):
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
        super().__init__(timestamp, polygon)


    def set_graphObject(self, obj):
        polygon = QPolygonF([QPointF(pt[0], pt[1]) for pt in obj['coords']])
        self.graphObject = QGraphicsPolygonItem(polygon)
        return self.graphObject

    def set_dataObject(self, obj):
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

    def __init__(self, timestamp, bbx):
        """
        Args:
            timestamp: timestamp
            bbx: {'timestamp': datim.today().isoformat('@'),  
                  'type': BBX,  
                  'labels': {propperty: label, ...}, 
                  'bbx': [x, y, w, h]}
                or QGraphicsRectItem
        """
        super().__init__(timestamp, bbx)

    def set_graphObject(self, obj):
        bbx = QRectF()
        bbx.setTopLeft(QPointF(obj['bbx'][0], obj['bbx'][1]))
        bbx.setSize(QSizeF(obj['bbx'][2], obj['bbx'][3]))
        self.graphObject = QGraphicsRectItem(bbx)
        return self.graphObject

    def set_dataObject(self, obj):
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

    def __init__(self, timestamp, ellipse):
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
        super().__init__(timestamp, ellipse)

    def set_graphObject(self, obj):
        bbx = QRectF()
        # add ellipse
        axis_major, axis_minor = obj['axis'][0], obj['axis'][1]
        bbx.setTopLeft(QPointF(-1 * axis_minor / 2, -1 * axis_major / 2))
        bbx.setSize(QSizeF(axis_minor, axis_major))
        self.graphObject = QGraphicsEllipseItem(bbx)
        # transfrom
        t = QTransform()
        t.translate(obj['coords'][0], obj['coords'][1])
        t.rotate(-1 * obj['angle'] + 90)
        self.graphObject.setTransform(t)

        return self.graphObject


    def set_dataObject(self, obj):
        self.dataObject = {'timestamp': self.timestamp,  
                           'type': ELLIPSE,  
                           'labels': {},  
                           'coords': [0, 0],  
                           'angle': 0,  
                           'axis': [0, 0],
                           'bbx': [0, 0, 0, 0]}
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
    

    def save_dataObject(self, location):
        """
        implementation of a abstract method
        Args:
            location: hdf5 group of a certain annotation (named as timestamp),
                in which all information about an annotation is saved

        Returns: none
        """


        if 'center' not in location.keys():
            # location.create_dataset('center', shape=(2,), data=self._getCenter())
            location.create_dataset('center', shape=(2,), data=self.dataObject['center'])
        if 'angle' not in location.keys():
            # location.create_dataset('angle', shape=(1,), data=self._getAngle())
            location.create_dataset('angle', shape=(1,), data=self.dataObject['angle'])
        if 'axis' not in location.keys():
            # location.create_dataset('axis', shape=(2,), data=self._getAxis())
            location.create_dataset('axis', shape=(2,), data=self.dataObject['axis'])


    @classmethod
    def _load_annotation(cls, location):
        """
        implementation of an abstract function
        from data in hdf5 file, regenerate a graphObject
        Args:
            location: a hdf5 group corresponding to an annotation, named as timestamp
        Returns: a graphObject
        """
        try:
            paras = {}
            paras['center'] = location['center'].value
            paras['angle'] = location['angle'].value
            paras['axis'] = location['axis'].value
            return paras
        except Exception as e:
            print('An exception occurred while loading a ellipse: ', e)
            return None
    