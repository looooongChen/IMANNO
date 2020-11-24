from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF
from PyQt5.QtGui import QPolygonF, QColor, QTransform, QPainter, QPainterPath, QPen, QBrush
from PyQt5.QtWidgets import QGraphicsPolygonItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsPathItem, QGraphicsItem
import numpy as np
import math

from abc import abstractmethod
from .enumDef import *
from .labelManager import Property, Label


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
        self.highlighted = False
        self.config = None
        self.labels = {}
        self.dataObject = self._dataObject(obj)
        self.graphObject = self._graphObject(self.dataObject)
        self.parse_labels()

    def parse_labels(self):
        if 'labels' in self.dataObject.keys():
            for prop_name, label_name in self.dataObject['labels'].items():
                self.labelMgr.assign(self, prop_name, label_name, saved=True)
            self.dataObject['labels'] = {}
    
    def render_save(self):
        save_dict = self.dataObject.copy()
        save_dict['labels'] = {prop.name: label.name for prop, label in self.labels.items()}
        return save_dict

    def assign_label(self, prop_name, label_name):
        self.labelMgr.assign(self, prop_name, label_name)

    def withdraw_label(self, prop_name, label_name):
        self.labelMgr.withdraw(self, prop_name, label_name)

    def has(self, tag):
        if isinstance(tag, Property):
            return True if tag in self.labels.keys() else False
        elif isinstance(tag, Label):
            if tag.property not in self.labels.keys():
                return False
            else:
                return True if self.labels[tag.property] is tag else False
        else:
            return False
        
    def highlight(self, status):
        if self.highlighted != status:
            self.highlighted = status
            self.sync_disp()

    def _color(self, config):

        if config.disp == SHOW_ALL:
            color = QColor(DEFAULT_COLOR)
        elif config.disp == HIDE_ALL:
            color = QColor('#000000')
        elif config.disp in self.labels.keys():
            color = self.labels[config.disp].color
            color = QColor(color[0], color[1], color[2])
        else:
            color = QColor(SHADOW_COLOR)

        return color

    def sync_disp(self, config=None):
        if config is None:
            config = self.config
        else:
            self.config = config
        # set appearance
        alpah_pen = 255
        width_pen, alpha_brush = config['PenWidth'], config['BrushAlpha']
        if self.highlighted:
            width_pen += config['HighlightIncrWidth'] 
            alpha_brush += config['HighlightIncrAlpha']
        if config.disp == HIDE_ALL:
            alpah_pen, alpha_brush = 0, 0
        color = self._color(config)
        color.setAlpha(alpah_pen)
        pen = QPen(color, width_pen, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        color.setAlpha(alpha_brush)
        brush = QBrush(color, Qt.SolidPattern)
        self.graphObject.setPen(pen)
        self.graphObject.setBrush(brush)

        return self.graphObject
        
    @abstractmethod
    def _dataObject(self, dataObject):
        """
        an abstract method to get graphObject from a dataObject
        Return: graphObject
        """
        pass

    @abstractmethod
    def _graphObject(self, graphObject):
        """
        an abstract method to dataObject from the graphObject/dataObject,
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
        self.radius = 10
        super().__init__(timestamp, dot, labelMgr)

    def _star(self, center, R):
        star = [QPointF(0,R), QPointF(R/6,R/6), QPointF(R,0), QPointF(R/6,-R/6), QPointF(0,-R), QPointF(-R/6,-R/6), QPointF(-R,0), QPointF(-R/6,R/6), QPointF(0,R)]
        star = [pt + QPointF(center[0], center[1]) for pt in star]
        star = QPolygonF(star)
        star = QGraphicsPolygonItem(star)
        return star

    def _graphObject(self, obj):
        return self._star(obj['coords'], self.radius)

    def sync_disp(self, config=None):
        if config is None:
            config = self.config
        else:
            self.config = config
        # set transfrom
        self.graphObject.resetTransform()
        s = config['DotAnnotationRadius']/self.radius
        t1, t2 = self.dataObject['coords'][0], self.dataObject['coords'][1]
        t = QTransform(s,0,0,0,s,0,t1-s*t1, t2-s*t2, 1)
        self.graphObject.setTransform(t)
        # set appearance
        alpah = 255
        width = config['PenWidth']
        if self.highlighted:
            width += config['HighlightIncrWidth']
        color = self._color(config)
        color.setAlpha(alpah)
        pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.MiterJoin)
        brush = QBrush(color, Qt.SolidPattern)
        self.graphObject.setPen(pen)
        self.graphObject.setBrush(brush)

        return self.graphObject

    def _dataObject(self, obj):
        if isinstance(obj, QGraphicsItem):
            dataObject = {'timestamp': self.timestamp,  
                          'type': DOT,  
                          'labels': {},  
                          'coords': [0, 0]}
            center = obj.polygon().boundingRect().center()
            dataObject['coords'] = [center.x(), center.y()]
        else:
            dataObject = obj
        # normalization
        dataObject['coords'] = [int(round(x)) for x in dataObject['coords']]
        return dataObject
    
    @classmethod
    def dataObject_from_hdf5(cls, anno):
        dataObject = Annotation.dataObject_from_hdf5(anno)
        dataObject['type'] = DOT
        dataObject['coords'] = [anno['pt'][0], anno['pt'][1]]
        # normalization
        dataObject['coords'] = [int(round(x)) for x in dataObject['coords']]
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

    def sync_disp(self, config=None):
        if config is None:
            config = self.config
        else:
            self.config = config
        # set appearance
        alpah_pen = 255
        width_pen, alpha_brush = config['CurveAnnotationWidth'], 0
        if self.highlighted:
            width_pen += config['HighlightIncrWidth'] 
        color = self._color(config)
        color.setAlpha(alpah_pen)
        pen = QPen(color, width_pen, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        color.setAlpha(alpha_brush)
        brush = QBrush(color, Qt.SolidPattern)
        self.graphObject.setPen(pen)
        self.graphObject.setBrush(brush)
        return self.graphObject
    
    def _graphObject(self, obj):
        curve = QPainterPath()
        curve.addPolygon(QPolygonF([QPointF(pt[0], pt[1]) for pt in obj['coords']]))
        return QGraphicsPathItem(curve)

    def _dataObject(self, obj):
        if isinstance(obj, QGraphicsItem):
            dataObject = {'timestamp': self.timestamp,  
                          'type': CURVE,  
                          'labels': {},  
                          'coords': [],
                          'bbx': [0,0,0,0]}
            # add coords
            curve = obj.path()
            for i in range(curve.elementCount()):
                pt = curve.elementAt(i)
                dataObject['coords'].append([pt.x(), pt.y()])
            # add bbx
            bbx = curve.boundingRect()
            dataObject['bbx'] = [bbx.x(), bbx.y(), bbx.width(), bbx.height()]
        else:
            dataObject = obj
        # normalization
        dataObject['coords'] = [[int(round(pt[0])), int(round(pt[1]))] for pt in dataObject['coords']]
        dataObject['bbx'] = [int(round(x)) for x in dataObject['bbx']]
        return dataObject
    
    @classmethod
    def dataObject_from_hdf5(cls, anno):
        dataObject = Annotation.dataObject_from_hdf5(anno)
        dataObject['type'] = CURVE
        dataObject['bbx'] = list(anno['boundingBox'])
        xx, yy = anno['line'][:,0]+dataObject['bbx'][0], anno['line'][:,1]+dataObject['bbx'][1]
        dataObject['coords'] = [[x, y] for x,y in zip(xx, yy)]
        # normalization
        dataObject['coords'] = [[int(round(pt[0])), int(round(pt[1]))] for pt in dataObject['coords']]
        dataObject['bbx'] = [int(round(x)) for x in dataObject['bbx']]
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


    def _graphObject(self, obj):
        polygon = QPolygonF([QPointF(pt[0], pt[1]) for pt in obj['coords']])
        return QGraphicsPolygonItem(polygon)

    def _dataObject(self, obj):
        if isinstance(obj, QGraphicsItem):
            dataObject = {'timestamp': self.timestamp,  
                          'type': POLYGON,  
                          'labels': {},  
                          'coords': [],
                          'bbx': [0,0,0,0]}
            # add coords
            polygon = obj.polygon()
            for i in range(polygon.count()):
                pt = polygon[i]
                dataObject['coords'].append([pt.x(), pt.y()])
            # add bbx
            bbx = polygon.boundingRect()
            dataObject['bbx'] = [bbx.x(), bbx.y(), bbx.width(), bbx.height()]
        else:
            dataObject = obj
        # normalization
        dataObject['coords'] = [[int(round(pt[0])), int(round(pt[1]))] for pt in dataObject['coords']]
        dataObject['bbx'] = [int(round(x)) for x in dataObject['bbx']]
        return dataObject
    
    @classmethod
    def dataObject_from_hdf5(cls, anno):
        dataObject = Annotation.dataObject_from_hdf5(anno)
        dataObject['type'] = POLYGON
        dataObject['bbx'] = list(anno['boundingBox'])
        xx, yy = anno['polygon'][:,0]+dataObject['bbx'][0], anno['polygon'][:,1]+dataObject['bbx'][1]
        dataObject['coords'] = [[x, y] for x,y in zip(xx, yy)]
        # normalization
        dataObject['coords'] = [[int(round(pt[0])), int(round(pt[1]))] for pt in dataObject['coords']]
        dataObject['bbx'] = [int(round(x)) for x in dataObject['bbx']]
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

    def _graphObject(self, obj):
        bbx = QRectF()
        bbx.setTopLeft(QPointF(obj['bbx'][0], obj['bbx'][1]))
        bbx.setSize(QSizeF(obj['bbx'][2], obj['bbx'][3]))
        return QGraphicsRectItem(bbx)

    def _dataObject(self, obj):
        if isinstance(obj, QGraphicsItem):
            dataObject = {'timestamp': self.timestamp,  
                          'type': BBX,  
                          'labels': {},  
                          'bbx': [0,0,0,0]}
            # add bbx
            bbx = obj.rect()
            dataObject['bbx'] = [bbx.x(), bbx.y(), bbx.width(), bbx.height()]
        else:
            dataObject = obj
        # normalization
        dataObject['bbx'] = [int(round(x)) for x in dataObject['bbx']]
        return dataObject
    
    @classmethod
    def dataObject_from_hdf5(cls, anno):
        dataObject = Annotation.dataObject_from_hdf5(anno)
        dataObject['type'] = BBX
        dataObject['bbx'] = list(anno['boundingBox'])
        # normalization
        dataObject['bbx'] = [int(round(x)) for x in dataObject['bbx']]
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

    def _graphObject(self, obj):
        bbx = QRectF()
        # add ellipse
        axis_major, axis_minor = obj['axis'][0], obj['axis'][1]
        bbx.setTopLeft(QPointF(-1 * axis_major / 2, -1 * axis_minor / 2))
        bbx.setSize(QSizeF(axis_major, axis_minor))
        graphObject = QGraphicsEllipseItem(bbx)
        # transfrom
        t = QTransform()
        t.translate(obj['coords'][0], obj['coords'][1])
        t.rotate(-1 * obj['angle'])
        graphObject.setTransform(t)

        return graphObject


    def _dataObject(self, obj):
        if isinstance(obj, QGraphicsItem):
            dataObject = {'timestamp': self.timestamp,  
                          'type': ELLIPSE,  
                          'labels': {},  
                          'coords': [0, 0],  
                          'angle': 0,  
                          'axis': [0, 0],
                          'bbx': [0, 0, 0, 0]}
            t = obj.transform()
            dataObject['coords'] = [t.m31(), t.m32()] 
            dataObject['angle'] = math.degrees(math.acos(t.m11()))
            dataObject['axis'] = [obj.rect().x(), obj.rect().y()]
            a, b = dataObject['axis'][0]/2, dataObject['axis'][1]/2
            c, s = math.cos(math.radians(-dataObject['angle'])), math.sin(math.radians(-dataObject['angle']))
            X, Y = math.sqrt((a*c)**2+(b*s)**2), math.sqrt((a*s)**2+(b*c)**2) 
            dataObject['bbx'] = [t.m31()-X, t.m33()-Y, 2*X, 2*Y]
        else:
            dataObject = obj
        # normalization
        dataObject['coords'] = [int(round(x)) for x in dataObject['coords']]
        dataObject['angle'] = int(round(dataObject['angle']))
        dataObject['axis'] = [int(round(x)) for x in dataObject['axis']]
        dataObject['bbx'] = [int(round(x)) for x in dataObject['bbx']]
        return dataObject
    
    @classmethod
    def dataObject_from_hdf5(cls, anno):
        dataObject = Annotation.dataObject_from_hdf5(anno)
        dataObject['type'] = ELLIPSE
        dataObject['coords'] = list(anno['center'])
        dataObject['angle'] = anno['angle'][0]
        dataObject['axis'] = list(anno['axis'])
        a, b = dataObject['axis'][0]/2, dataObject['axis'][1]/2
        c, s = math.cos(math.radians(-dataObject['angle'])), math.sin(math.radians(-dataObject['angle']))
        X, Y = math.sqrt((a*c)**2+(b*s)**2), math.sqrt((a*s)**2+(b*c)**2) 
        dataObject['bbx'] = [dataObject['coords'][0]-X, dataObject['coords'][1]-Y, 2*X, 2*Y]
        # normalization
        dataObject['coords'] = [int(round(x)) for x in dataObject['coords']]
        dataObject['angle'] = int(round(dataObject['angle']))
        dataObject['axis'] = [int(round(x)) for x in dataObject['axis']]
        dataObject['bbx'] = [int(round(x)) for x in dataObject['bbx']]
    
        return dataObject
    