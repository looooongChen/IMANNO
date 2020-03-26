from PyQt5 import uic
from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF, QLineF
from PyQt5.QtGui import QPen, QBrush, QPolygonF, QColor, QTransform, QPainter, \
            QPixmap, QIcon, QTransform, QPainterPath  
from PyQt5.QtWidgets import QApplication, QColorDialog, QDialog, \
    QMainWindow, QDockWidget, QListWidgetItem, QUndoCommand, \
    QGraphicsPolygonItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsPathItem
from datetime import datetime as datim
import numpy as np
import h5py
import sys
import math


from abc import ABC, abstractmethod

from .graphDef import *

__author__ = 'bug, long'


#######################
#### label classes ####
#######################

class Label(object):

    def __init__(self, attr, label_name, color=None):
        self.attr = attr
        self.attr_name = attr.attr_name
        self.label_name = label_name
        self.color = color

    def set_color(self, r, g, b):
        self.color = [r,g,b]

    def rename(self, name):
        assert isinstance(name, str)
        if name not in (self.attr.labels.keys()):
            self.label_name = name

class Attribute(object):

    def __init__(self, attr_name, label_list=None):
        """
        constructor of Attribute class
        Args:
            name: name of the attribute
            label_list: a list of label names e.g. ['label1', 'label2' ...]
        """
        self.attr_name = attr_name
        self.labels = {} # label_name - label_object

        if label_list is not None:
            self.add_label_list(label_list)

    def add_label_list(self, label_list):
        existing_labels = list(self.labels.keys())
        for label in label_list:
            if label not in existing_labels:
                self.labels[label] = Label(self, label)

    def add_label(self, label_name, label_color = None):
        existing_labels = list(self.labels.keys())
        if label_name not in existing_labels:
            self.labels[label_name] = Label(self, label_name, label_color)

    def remove_label(self, label):
        if isinstance(label, Label):
            del self.labels[label.label_name]
        else:
            del self.labels[label_name]

    def get_label(self, label_name):
        if label_name in list(self.labels.keys()):
            return self.labels[label_name]
        return None

    def rename(self, name):
        assert isinstance(name, str)
        self.attr_name = name

    def save(self, location):
        """
        save the attributes and its labels
        Args:
            location: a hdf5 root
        Returns: none
        """
        attr_group = location.require_group('attributes')
        if self.attr_name in attr_group.keys():
            del attr_group[self.attr_name]
        label_group = attr_group.create_group(self.attr_name)
        for label_name, label_obj in self.labels.items():
            label_group.create_dataset(label_name, shape=(3,), dtype='uint8')
            label_group[label_name][0] = label_obj.color[0]
            label_group[label_name][1] = label_obj.color[1]
            label_group[label_name][2] = label_obj.color[2]



############################
#### annotation classes ####
############################

class Annotation(object):

    """
    class that contains the data of an annotation, graph item is kept in Annotation manage, they have the same timestamp
    """

    def __init__(self, timestamp, dataObject, type, scale_factor=(1,1), **kwargs):
        self.type = type
        self.timestamp = timestamp
        if scale_factor[0] != 1 or scale_factor[1] != 1:
            self.dataObject = self.process_dataObject(dataObject, scale_factor)
        else:
            self.dataObject = dataObject
        self.graphObject = None
        self.labels = []

    def add_label(self, label_obj):
        """
        add a certain label
        Args:
            label: an Label object
        Returns: none
        """
        for i in range(len(self.labels)):
            if self.labels[i].attr_name == label_obj.attr_name:
                del self.labels[i]
                break
        self.labels.append(label_obj)

    def remove_label(self, label_obj):
        try:
            index = self.labels.index(label_obj)
            del self.labels[index]
        except Exception as e:
            return

    @abstractmethod
    def process_dataObject(self, dataObject, scale_factor):
        pass
    
    @abstractmethod
    def save_dataObject(self, location):
        """
        an abstract function
        save the data of an Annotation(the data may be different for different kinds of dataObjects),
        must be implemented in subclass
        Args:
            location: hdf5 group of a certain annotation (named as timestamp),
                in which all information about an annotation is saved

        Returns: none
        """
        pass

    def save_labels(self, location):
        """
        save labels related to as Annotaion
        Args:
            location: hdf5 group of a certain annotation (named as timestamp),
                in which all information about an annotation is saved
        Returns: none

        """
        if 'labels' in list(location.keys()):
            del location['labels']
        label_group = location.require_group('labels')
        for label in self.labels:
            label_group.require_group(label.attr_name)
            label_group[label.attr_name].attrs['label_name'] = label.label_name

    def save(self, location):
        """
        save all information of an annotation
        Args:
            location: a hdf5 roof

        Returns: none
        """
        # get the 'folder' to save the annotation, named by the timestamp
        annotation = location.require_group('/annotations/' + self.timestamp)
        # add attributes
        annotation.attrs['type'] = self.type
        annotation.attrs['timestamp'] = self.timestamp
        # save data
        self.save_dataObject(annotation)
        # save labels
        self.save_labels(annotation)

    @classmethod
    def _load_annotation(cls, location):
        """
        an abstract function
        from data in hdf5 file, regenerate a dataObject
        Args:
            location: a hdf5 group corresponding to an annotation, named as timestamp
        Returns: a dataObject, which contains data of a certrain annotation type
        """
        pass

    @classmethod
    def load(cls, location, attr_group, **kwargs):
        """
        load data from a hdf5 group and return an Annotation object
        Args:
            location: a hdf5 group corresponding to an annotation, named as timestamp
            attr_group: a group of Attribute objects, saved as a dict (attr_name - attr_obj)
        Returns: an Annotation object
        """
        timestamp = location.attrs['timestamp']
        dataObject = cls._load_annotation(location)
        annotation = cls(timestamp, dataObject, (1,1), **kwargs)

        if 'labels' in location.keys():
            for attr_name in location['labels'].keys():
                label_name = location['labels'][attr_name].attrs['label_name']
                annotation.add_label(attr_group[attr_name].get_label(label_name))
        return annotation

    @abstractmethod
    def get_graphObject(self, scale_factor):
        """
        an method to return the graph object,
        notice that graphObject and dataObject may be different in some cases
        in that case the method should be overwritten
        :return: graphObject
        """
        pass

class PointAnnotation(Annotation):

    def __init__(self, timestamp, pt, scale_factor=(1,1), radius=2):
        """
        constructor of PointAnnotation
        Args:
            timestamp: time stamp
            polygon: a QPolygonF object
        """
        self.radius = radius
        super().__init__(timestamp, pt, POINT, scale_factor)

    def process_dataObject(self, dataObject, scale_factor):
        dataObject[0] = dataObject[0]/scale_factor[0]
        dataObject[1] = dataObject[1]/scale_factor[1]
        return dataObject

    def save_dataObject(self, location):
        """
        implementation of a abstract method
        Args:
            location: hdf5 group of a certain annotation (named as timestamp),
                in which all information about an annotation is saved

        Returns: none
        """
        if 'pt' not in location.keys():
            location.create_dataset('pt', shape=(2,), data=self.dataObject)

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
            print('An exception occurred while loading a polygon: ', e)

    def get_graphObject(self, scale_factor):
        bbx = QRectF()
        bbx.setTopLeft(QPointF(self.dataObject[0]*scale_factor[0]-self.radius, self.dataObject[1]*scale_factor[1] -self.radius))
        bbx.setSize(QSizeF(self.radius*2, self.radius*2))
        ellipse = QGraphicsEllipseItem(bbx)
        self.graphObject = ellipse
        return self.graphObject

class LineAnnotation(Annotation):

    def __init__(self, timestamp, line, scale_factor=(1,1)):
        """
        constructor of LineAnnotation
        Args:
            timestamp: time stamp
            line: a nx2 numpy containing coordinated of the line
        """
        super().__init__(timestamp, line, LINE, scale_factor)
    
    def process_dataObject(self, dataObject, scale_factor):
        dataObject[:,0] = dataObject[:,0]/scale_factor[0]
        dataObject[:,1] = dataObject[:,1]/scale_factor[1]
        return dataObject

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

    def get_graphObject(self, scale_factor):
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

    def __init__(self, timestamp, polygon, scale_factor=(1,1)):
        """
        constructor of PolygonAnnotation
        Args:
            timestamp: time stamp
            polygon: a nx2 numpy containing coordinated of the polygon
        """
        super().__init__(timestamp, polygon, POLYGON, scale_factor)
    
    def process_dataObject(self, dataObject, scale_factor):
        dataObject[:,0] = dataObject[:,0]/scale_factor[0]
        dataObject[:,1] = dataObject[:,1]/scale_factor[1]
        return dataObject

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

    def get_graphObject(self, scale_factor):
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

    def __init__(self, timestamp, bbx, scale_factor=(1,1)):
        """
        constructor of PolygonAnnotation
        Args:
            timestamp: time stamp
            polygon: a QRectF object
        """
        super().__init__(timestamp, bbx, BBX, scale_factor)
    
    def process_dataObject(self, dataObject, scale_factor):
        dataObject[0] = dataObject[0]/scale_factor[0]
        dataObject[1] = dataObject[1]/scale_factor[1]
        dataObject[2] = dataObject[2]/scale_factor[0]
        dataObject[3] = dataObject[3]/scale_factor[1]
        return dataObject

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

    def get_graphObject(self, scale_factor):
        bbx = QRectF()
        bbx.setTopLeft(QPointF(self.dataObject[0]*scale_factor[0], self.dataObject[1]*scale_factor[1]))
        bbx.setSize(QSizeF(self.dataObject[2]*scale_factor[0], self.dataObject[3]*scale_factor[1]))
        self.graphObject = QGraphicsRectItem(bbx)
        return self.graphObject

class OVALAnnotation(Annotation):

    def __init__(self, timestamp, paras, scale_factor):
        """
        constructor of PolygonAnnotation
        Args:
            timestamp: time stamp
            polygon: a QRectF object
        """
        super().__init__(timestamp, paras, OVAL, scale_factor)
    
    def process_dataObject(self, dataObject, scale_factor):

        axis_major = dataObject['axis'][0]
        axis_minor = dataObject['axis'][1]
        c = math.cos(math.radians(dataObject['angle']))
        s = math.sin(math.radians(dataObject['angle']))
        axis_major = math.sqrt((axis_major * c / scale_factor[0]) ** 2 + (axis_major * s / scale_factor[1]) ** 2)
        axis_minor = math.sqrt((axis_minor * s / scale_factor[0]) ** 2 + (axis_minor * c / scale_factor[1]) ** 2)
        dataObject['axis'][0] = axis_major
        dataObject['axis'][1] = axis_minor

        dataObject['center'][0] = dataObject['center'][0] / scale_factor[0]
        dataObject['center'][1] = dataObject['center'][1] / scale_factor[1]

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

    def get_graphObject(self, scale_factor):
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


#####################################################
#### area under construction, but already in use ####
#####################################################


class AnnotationManager(object):
    def __init__(self, config):

        self.config = config
        self.scene = None

        self.attributes = {} # name - Attribute object
        self.annotations = {} # timestamp - Annotation object

        #### variables about the status ####
        self.needsSave = False


    def set_scene(self, scene):
        self.scene = scene

    ############################
    #### method for add new ####
    ############################

    def new_attribute(self, attr_name, label_list=None):
        if attr_name not in self.attributes.keys():
            self.attributes[attr_name] = Attribute(attr_name, label_list)
        else:
            print("Attribute has existed!")
        self.needsSave = True

    def new_label(self, attr_name, label_name, label_color=None):
        if attr_name in self.attributes.keys():
            self.attributes[attr_name].add_label(label_name, label_color)
        else:
            print("Attribute does not exist")

    def new_annotation(self, type, dataObject, skip_dlg=False):

        timestamp = datim.today().isoformat('@')
        while timestamp in self.annotations.keys():
            timestamp = datim.today().isoformat('@')

        if type == POLYGON:
            annotation = PolygonAnnotation(timestamp, dataObject, self.config['scale_factor'])
        elif type == BBX:
            annotation = BBXAnnotation(timestamp, dataObject, self.config['scale_factor'])
        elif type == OVAL:
            annotation = OVALAnnotation(timestamp, dataObject, self.config['scale_factor'])
        elif type == POINT:
            annotation = PointAnnotation(timestamp, dataObject, self.config['scale_factor'], radius=self.config["DotAnnotationRadius"])
        elif type == LINE:
            annotation = LineAnnotation(timestamp, dataObject, self.config['scale_factor'])
        else:
            print("Unknown annotation type")

        self.add_annotation(annotation, self.config['display_channel'])
        self.needsSave = True

    def add_graphItem(self, annotation, display_channel=None):
        if self.scene:
            pen, brush = self.appearance(annotation, display_channel)
            graphObj = annotation.get_graphObject(self.config['scale_factor'])
            graphObj.setPen(pen)
            graphObj.setBrush(brush)
            self.scene.addItem(graphObj)
    
    def add_annotation(self, annotation, display_channel=None):
        self.annotations[annotation.timestamp] = annotation
        self.add_graphItem(annotation, display_channel)

    def add_existing_graphItems(self, display_channel=None):
        if self.scene:
            self.scene.clear_items()
            for _, annotation in self.annotations.items():
                self.add_graphItem(annotation, display_channel)

    def add_label_to_selected_annotations(self, label_name, attr_name):

        if attr_name not in (self.attributes.keys()):
            return
        if label_name not in list(self.attributes[attr_name].labels.keys()):
            return
        annotations = self.get_selected_annotations()
        if annotations:
            for annotation in annotations:
                label_obj = self.attributes[attr_name].labels[label_name]
                annotation.add_label(label_obj)
            self.needsSave = True

    ############################
    #### methods for get ####
    ############################

    def get_annotation_by_graphItem(self, graphItem):
        timestamp = [timestamp for timestamp, item in self.annotations.items() if graphItem is item.graphObject][0]
        return self.annotations[timestamp]

    def get_selected_annotations(self):
        if self.scene is None:
            return None
        if len(self.scene.selectedItems) == 0:
            return None
        annotations = []
        for item in self.scene.selectedItems:
            annotations.append(self.get_annotation_by_graphItem(item))
        return annotations

    ############################
    #### methods for remove ####
    ############################

    def delete_annotation_by_graphItem(self, graphItem):
        timestamp = [timestamp for timestamp, item in self.annotations.items() if graphItem is item.graphObject][0]
        del self.annotations[timestamp]
        if self.scene:
            self.scene.removeItem(graphItem)
        self.needsSave = True

    def remove_label(self, label, attr_name=None):
        if attr_name is None:
            assert isinstance(label, Label)
            label_obj = label
            attr_name = label.attr_name
        elif attr_name in list(self.attributes.keys()):
            label_obj = self.attributes[attr_name].get_label(label)
        else:
            return
        self._remove_label_from_all_annotations(label_obj)
        self.attributes[attr_name].remove_label(label_obj)

        self.needsSave = True

    def remove_label_from_selected_annotation(self, label_name, attr_name):
        if attr_name not in (self.attributes.keys()):
            return
        if label_name not in list(self.attributes[attr_name].labels.keys()):
            return
        annotations = self.get_selected_annotations()
        if annotations:
            annotation = annotations[0]
            label_obj = self.attributes[attr_name].labels[label_name]
            annotation.remove_label(label_obj)
            self.needsSave = True

    def remove_attr(self, attr):
        if isinstance(attr, Attribute):
            attr_name = attr.attr_name
            attr_obj = attr
        elif attr in list(self.attributes.keys()):
            attr_name = attr
            attr_obj = self.attributes[attr]
        else:
            return
        for label_obj in attr_obj.labels.values():
            self._remove_label_from_all_annotations(label_obj)
        del self.attributes[attr_name]

        self.needsSave = True

    def _remove_label_from_all_annotations(self, label_obj):
        for timestamp in self.annotations.keys():
            self.annotations[timestamp].remove_label(label_obj)

    ############################
    #### methods for rename ####
    ############################

    def rename_label(self, name, label, attr_name=None):
        if attr_name is None:
            assert isinstance(label, Label)
            label_name = label.label_name
            label.rename(name)
        elif attr_name in list(self.attributes.keys()):
            label_name = label
            self.attributes[attr_name].get_label(label).rename(name)
        self.attributes[attr_name].labels[name] = self.attributes[attr_name].labels.pop(label_name)

        self.needsSave = True

    def rename_attr(self, name, attr):
        if name in list(self.attributes.keys()):
            return
        if isinstance(attr, Attribute):
            attr_name = attr.attr_name
            attr_obj = attr
        elif attr in list(self.attributes.keys()):
            attr_name = attr
            attr_obj = self.attributes[attr]
        else:
            return
        attr_obj.rename(name)
        self.attributes[name] = self.attributes.pop(attr_name)
        for label in self.attributes[name].labels.values():
            label.attr_name = name

        self.needsSave = True

    ##################################
    #### method for save and load ####
    ##################################

    def save_to_file(self, filename):

        if filename is None:
            return

        with h5py.File(filename, 'w') as location:
            to_save = []
            # save the annotations
            for timestamp in self.annotations.keys():
                self.annotations[timestamp].save(location)
                to_save.append(timestamp)
            if 'attributes' in location.keys():
                del location['attributes']
            for attr_name, attr in self.attributes.items():
                # attr.save() has its own clean-ups
                attr.save(location)
            # some clean-up, same annotations may be deleted
            annotation_grp = location.require_group('annotations')
            for timestamp in annotation_grp.keys():
                if timestamp not in to_save:
                    del annotation_grp[timestamp]

            location.flush()
            location.close()

        self.needsSave = False


    def load_from_file(self, filename):
        self.attributes.clear()
        self.annotations.clear()

        with h5py.File(filename) as location:
            self.load_attributes(location)

            if 'annotations' in location.keys():
                for timestamp in location['annotations']:
                    annotation = self.load_single_annotation(location['annotations'][timestamp], self.attributes)
                    self.add_annotation(annotation)

            location.flush()
            location.close()


    def load_attributes(self, location):

        if 'attributes' not in location.keys():
            print("Attributes not found !")
            return
        attributes = location['attributes']
        for attr_name in attributes.keys():
            self.attributes[attr_name] = Attribute(attr_name)
            for label_name in attributes[attr_name].keys():
                # print(attributes[label_name])
                color = [attributes[attr_name][label_name][0],attributes[attr_name][label_name][1],
                         attributes[attr_name][label_name][2]]
                self.attributes[attr_name].add_label(label_name, color)

    def load_single_annotation(self, location, attr_group):

        type = location.attrs['type']
        if type == POLYGON:
            return PolygonAnnotation.load(location, attr_group)
        elif type == BBX:
            return BBXAnnotation.load(location, attr_group)
        elif type == OVAL:
            return OVALAnnotation.load(location, attr_group)
        elif type == POINT:
            return PointAnnotation.load(location, attr_group, radius=self.config["DotAnnotationRadius"])
        elif type == LINE:
            return LineAnnotation.load(location, attr_group)
        else:
            print("Unknown annotation type")

    def appearance(self, anno, display_channel=None):
        if isinstance(display_channel, str):
            for label in anno.labels:
                if display_channel == label.attr_name:
                    c = label.color
                    linePen = QPen(QColor(c[0], c[1], c[2], 255), 0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    areaBrush = QBrush(QColor(c[0], c[1], c[2], 70))
                    return linePen, areaBrush
            linePen = QPen(QColor(0, 0, 0, 255), 0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            areaBrush = QBrush(QColor(0, 0, 0, 70))
        elif display_channel == 1:
            linePen = QPen(QColor(0, 200, 0, 255), 0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            areaBrush = QBrush(QColor(0, 200, 0, 70))
        else:
            linePen = QPen(QColor(0, 0, 0, 0), 0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            areaBrush = QBrush(QColor(0, 0, 0, 0))
        
        if anno.type == LINE:
            linePen.setWidth(int(self.config['lineAnnotationWidth']))
            areaBrush = QBrush(QColor(0, 200, 0, 0))

        return linePen, areaBrush










