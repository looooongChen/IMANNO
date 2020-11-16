from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF
from PyQt5.QtGui import QPolygonF, QColor, QTransform, QPainter, QPainterPath  
from PyQt5.QtWidgets import QGraphicsPolygonItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsPathItem
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

    def __init__(self, timestamp, dataObject):
        self.timestamp = timestamp
        self.dataObject = dataObject
        self.graphObject = None

    def set_label(self, prop, label):
        self.dataObject['labels'][prop] = label

    def remove_label(self, prop, label=None):
        if prop in self.dataObject['labels'].keys():
            if label is None or self.dataObject['labels'][prop] == label:
                del self.dataObject['labels'][prop]

    @abstractmethod
    def get_graphObject(self, scale_factor):
        """
        an method to return the graph object,
        notice that graphObject and dataObject may be different in some cases
        in that case the method should be overwritten
        :return: graphObject
        """
        pass

    ## hdf5 compatible
    @classmethod
    def _load_annotation(cls, location):
        """
        an abstract function
        from hdf5, regenerate a dataObject
        Args:
            location: a hdf5 group
        Returns: a dataObject, which contains data of a certrain annotation type
        """
        pass

    @classmethod
    def load(cls, anno, mode='json'):
        ## hdf5 compatible
        if mode == 'hdf5':
            timestamp = anno.attrs['timestamp']
            dataObject = cls._load_annotation(anno)
            dataObject['labels'] = {}
            if 'labels' in anno.keys():
                for attr_name in anno['labels'].keys():
                    label_name = anno['labels'][attr_name].attrs['label_name']
                    dataObject['labels'][attr_name] = label_name
        else:
            timestamp = anno['timestamp']
            dataObject = anno

        if dataObject is not None:
            annotation = cls(timestamp, dataObject)
            return annotation
        else:
            print("Warning: damaged annotation, will be cleaned after next save")
            return None


class PointAnnotation(Annotation):

    def __init__(self, timestamp, pt):
        """
        constructor of PointAnnotation
        Args:
            timestamp: time stamp
            pt: data of a dot annotation
        """
        super().__init__(timestamp, pt)

    @classmethod
    def _load_annotation(cls, location):
        """
        implementation of an abstract function
        from data in hdf5 file, regenerate a dataObject
        Args:
            location: a hdf5 group corresponding to an annotation, named as timestamp
        Returns: a dataObject
        """
        try:
            return np.array([location['pt'][0], location['pt'][1]])
        except Exception as e:
            print('An exception occurred while loading a point annotation: ', e)
            return None

    def get_graphObject(self, radius=5):

        bbx = QRectF()
        bbx.setTopLeft(QPointF(self.dataObject[0]-radius, self.dataObject[1]-radius))
        bbx.setSize(QSizeF(radius*2, radius*2))
        ellipse = QGraphicsEllipseItem(bbx)
        self.graphObject = ellipse
        return self.graphObject

class LineAnnotation(Annotation):

    def __init__(self, timestamp, line):
        """
        constructor of LineAnnotation
        Args:
            timestamp: time stamp
            line: a nx2 numpy containing coordinated of the line
        """
        super().__init__(timestamp, line, LINE)
    
    def save_dataObject(self, location):
        """
        implementation of a abstract method
        Args:
            location: hdf5 group of a certain annotation (named as timestamp),
                in which all information about an annotation is saved

        Returns: none
        """
        if 'boundingBox' not in location.keys():
            # print('saved', self._get_boundingBox())
            bbx = self._get_boundingBox()
            location.create_dataset('boundingBox', shape=(4,), data=bbx)

        if 'line' not in location.keys():
            pts = np.stack([self.dataObject[:,0]-bbx[0], self.dataObject[:,1]-bbx[1]], axis=1)
            location.create_dataset('line', shape=self.dataObject.shape, data=pts)


    @classmethod
    def _load_annotation(cls, location):
        """
        implementation of an abstract function
        from data in hdf5 file, regenerate a dataObject
        Args:
            location: a hdf5 group corresponding to an annotation, named as timestamp
        Returns: a dataObject
        """
        try:
            bbx = location['boundingBox']
            line = np.stack([location['line'][:,0]+bbx[0], location['line'][:,1]+bbx[1]], axis=1)
            return line
        except Exception as e:
            print('An exception occurred while loading a line: ', e)
            return None

    def get_graphObject(self, scale_factor=(1,1)):
        line = QPolygonF([QPointF(self.dataObject[i, 0]*scale_factor[0], self.dataObject[i, 1]*scale_factor[1]) for i in range(self.dataObject.shape[0])])
        path = QPainterPath()
        path.addPolygon(line)
        self.graphObject = QGraphicsPathItem(path)
        return self.graphObject

    def _get_boundingBox(self):
        """
        get the bounding box of a polygon
        Returns: a numpy arrary [x, y, width, height]
        """
        originalRect = QRectF(self.graphObject.boundingRect())
        bbx = np.zeros((4,))
        bbx[0] = originalRect.x()
        bbx[1] = originalRect.y()
        bbx[2] = originalRect.width()
        bbx[3] = originalRect.height()
        return bbx

class PolygonAnnotation(Annotation):

    def __init__(self, timestamp, polygon):
        """
        constructor of PolygonAnnotation
        Args:
            timestamp: time stamp
            polygon: a nx2 numpy containing coordinated of the polygon
        """
        super().__init__(timestamp, polygon, POLYGON)
    
    def save_dataObject(self, location):
        """
        implementation of a abstract method
        Args:
            location: hdf5 group of a certain annotation (named as timestamp),
                in which all information about an annotation is saved

        Returns: none
        """
        if 'boundingBox' not in location.keys():
            # print('saved', self._get_boundingBox())
            bbx = self._get_boundingBox()
            location.create_dataset('boundingBox', shape=(4,), data=bbx)

        if 'polygon' not in location.keys():
            pts = np.stack([self.dataObject[:,0]-bbx[0], self.dataObject[:,1]-bbx[1]], axis=1)
            location.create_dataset('polygon', shape=self.dataObject.shape, data=pts)

    @classmethod
    def _load_annotation(cls, location):
        """
        implementation of an abstract function
        from data in hdf5 file, regenerate a dataObject
        Args:
            location: a hdf5 group corresponding to an annotation, named as timestamp
        Returns: a dataObject
        """
        try:
            bbx = location['boundingBox']
            polygon = np.stack([location['polygon'][:,0]+bbx[0], location['polygon'][:,1]+bbx[1]], axis=1)
            return polygon
        except Exception as e:
            print('An exception occurred while loading a polygon: ', e)
            return None

    def get_graphObject(self, scale_factor=(1,1)):
        polygon = QPolygonF([QPointF(self.dataObject[i, 0]*scale_factor[0], self.dataObject[i, 1]*scale_factor[1]) for i in range(self.dataObject.shape[0])])
        self.graphObject = QGraphicsPolygonItem(polygon)
        return self.graphObject
    
    def _get_boundingBox(self):
        """
        get the bounding box of a polygon
        Returns: a numpy arrary [x, y, width, height]
        """
        originalRect = QRectF(self.graphObject.boundingRect())
        bbx = np.zeros((4,))
        bbx[0] = originalRect.x()
        bbx[1] = originalRect.y()
        bbx[2] = originalRect.width()
        bbx[3] = originalRect.height()
        return bbx

class BBXAnnotation(Annotation):

    def __init__(self, timestamp, bbx):
        """
        constructor of PolygonAnnotation
        Args:
            timestamp: time stamp
            polygon: a QRectF object
        """
        super().__init__(timestamp, bbx, BBX)
    
    # def process_dataObject(self, dataObject, scale_factor):
    #     dataObject[0] = dataObject[0]/scale_factor[0]
    #     dataObject[1] = dataObject[1]/scale_factor[1]
    #     dataObject[2] = dataObject[2]/scale_factor[0]
    #     dataObject[3] = dataObject[3]/scale_factor[1]
    #     return dataObject

    def save_dataObject(self, location):
        """
        implementation of a abstract method
        Args:
            location: hdf5 group of a certain annotation (named as timestamp),
                in which all information about an annotation is saved

        Returns: none
        """
        if 'boundingBox' not in location.keys():
            # location.create_dataset('boundingBox', shape=(4,), data=self._get_boundingBox())
            location.create_dataset('boundingBox', shape=(4,), data=self.dataObject)


    @classmethod
    def _load_annotation(cls, location):
        """
        implementation of an abstract function
        from data in hdf5 file, regenerate a dataObject
        Args:
            location: a hdf5 group corresponding to an annotation, named as timestamp
        Returns: a dataObject
        """
        try:
            bbx = location['boundingBox'].value
            # boundingBox = QRectF(bbx[0], bbx[1], bbx[2], bbx[3])
            return bbx
        except Exception as e:
            print('An exception occurred while loading a boundingBox: ', e)
            return None

    def get_graphObject(self, scale_factor=(1,1)):
        bbx = QRectF()
        bbx.setTopLeft(QPointF(self.dataObject[0]*scale_factor[0], self.dataObject[1]*scale_factor[1]))
        bbx.setSize(QSizeF(self.dataObject[2]*scale_factor[0], self.dataObject[3]*scale_factor[1]))
        self.graphObject = QGraphicsRectItem(bbx)
        return self.graphObject

class OVALAnnotation(Annotation):

    def __init__(self, timestamp, paras):
        """
        constructor of PolygonAnnotation
        Args:
            timestamp: time stamp
            polygon: a QRectF object
        """
        super().__init__(timestamp, paras, OVAL)
    
    # def process_dataObject(self, dataObject, scale_factor):

    #     axis_major = dataObject['axis'][0]
    #     axis_minor = dataObject['axis'][1]
    #     c = math.cos(math.radians(dataObject['angle']))
    #     s = math.sin(math.radians(dataObject['angle']))
    #     axis_major = math.sqrt((axis_major * c / scale_factor[0]) ** 2 + (axis_major * s / scale_factor[1]) ** 2)
    #     axis_minor = math.sqrt((axis_minor * s / scale_factor[0]) ** 2 + (axis_minor * c / scale_factor[1]) ** 2)
    #     dataObject['axis'][0] = axis_major
    #     dataObject['axis'][1] = axis_minor

    #     dataObject['center'][0] = dataObject['center'][0] / scale_factor[0]
    #     dataObject['center'][1] = dataObject['center'][1] / scale_factor[1]

    #     return dataObject

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
    
    def get_graphObject(self, scale_factor=(1,1)):
        bbx = QRectF()

        axis_major = self.dataObject['axis'][0]
        axis_minor = self.dataObject['axis'][1]
        c = math.cos(math.radians(self.dataObject['angle']))
        s = math.sin(math.radians(self.dataObject['angle']))
        axis_major = math.sqrt((axis_major * c * scale_factor[0]) ** 2 + (axis_major * s * scale_factor[1]) ** 2)
        axis_minor = math.sqrt((axis_minor * s * scale_factor[0]) ** 2 + (axis_minor * c * scale_factor[1]) ** 2)

        bbx.setTopLeft(QPointF(-1 * axis_minor / 2, -1 * axis_major / 2))
        bbx.setSize(QSizeF(axis_minor, axis_major))
        ellipse = QGraphicsEllipseItem(bbx)

        t = QTransform()
        t.translate(self.dataObject['center'][0]*scale_factor[0], self.dataObject['center'][1]*scale_factor[1])
        t.rotate(-1 * self.dataObject['angle'] + 90)
        ellipse.setTransform(t)

        self.graphObject = ellipse
        return self.graphObject