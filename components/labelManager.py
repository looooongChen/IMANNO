from .base import Table

class LabelManager(Table):

    def __init__(self, config, label_dict=None):
        self.config = config
        super().__init__()

    #######################################
    #### parse / render save structure ####
    #######################################

    def parse_labels(self, label_dict, mode='json'):
        self.clear()
        ## hdf5 compatible
        if mode == 'hdf5':
            if 'attributes' in label_dict.keys():
                props = label_dict['attributes']
                for prop in props.keys():
                    self.add_property(prop)
                    for label in props[prop].keys():
                        color = [props[prop][label][0], props[prop][label][1], props[prop][label][2]]
                        self.add_label(prop, label, color)
        else:
            for prop, labels in label_dict.items():
                self.add_property(prop)
                for label, color in labels.items():
                    self.add_label(prop, label, color)

    def render_save(self):
        label_dict = {}
        for prop_name, prop in self.items():
            label_dict[prop_name] = {label_name: label.color for label_name, label in prop.items()}
        return label_dict

    ###############################
    #### add / remove property ####
    ###############################

    def add_property(self, prop_name):
        if prop_name not in self.keys():
            return Property(self, prop_name)
    
    def remove_property(self, prop):
        '''
        remove property, lables belonging to the property will also be removed
        Args:
            prop: property name or a Property object
        '''
        prop_name = prop.name if isinstance(prop, Property) else prop
        if prop_name in self.keys():
            self[prop_name].remove_all()
            del self[prop_name]

    ############################
    #### add / remove label ####
    ############################
            
    def add_label(self, prop, label_name, color=None):
        '''
        Args:
            prop: property name or a Property object
        '''
        prop_name = prop.name if isinstance(prop, Property) else prop
        if prop_name in self.keys():
            return self[prop_name].add_label(label_name, color)
    
    def remove_label(self, property, label):
        '''
        Args:
            prop: property name or a Property object
            label: label name or a Label object
        '''
        prop_name = prop.name if isinstance(prop, Property) else prop
        if prop_name in self.keys():
            self[prop_name].remove_label(label)

    ##################################
    #### assign / withdraw labels ####
    ##################################

    def assign(self, annotation, prop, label):
        '''
        Args:
            annotation: an annotions.Annotation object
            prop: property name or a Property object
            label: label name or a Label object
        '''
        prop_name = prop.name if isinstance(prop, Property) else prop
        label_name = label.name if isinstance(label, Label) else label
        if prop_name in self.keys():
            if label_name in self[prop_name].keys():
                self[prop_name][label_name].assign(annotation)

    def withdraw(self, annotation, prop, label):
        '''
        Args:
            annotation: an annotions.Annotation object
            prop: property name or a Property object
            label: label name or a Label object
        '''
        prop_name = prop.name if isinstance(prop, Property) else prop
        label_name = label.name if isinstance(label, Label) else label
        if prop_name in self.keys():
            if label_name in self[prop_name].keys():
                self[prop_name][label_name].withdraw(annotation)

    ################
    #### others ####
    ################

    def clear(self):
        '''
        all assigned lables will also be cleared
        '''
        for _, prop in self.items():
            prop.remove_all()
        super().clear()



class Property(Table):

    def __init__(self, labelMgr, prop_name):
        """
        Args:
            prop_name: name of a property e.g. Color
        """
        super().__init__()
        assert prop_name not in labelMgr.keys()
        self.labelMgr = labelMgr
        self.name = prop_name
        self.labelMgr[prop_name] = self
    
    def rename(self, prop_name):
        if prop_name not in self.labelMgr.keys():
            self.labelMgr[prop_name] = self.labelMgr[self.name].pop()
            self.name = prop_name

    def add_label(self, label_name, label_color=None):
        if label_name not in self.keys():
            return Label(self, label_name, label_color)
        else:
            return None

    def remove_label(self, label):
        '''
        Args:
            label: label name or a Label object 
        '''
        label_name = label.name if isinstance(label, Label) else label
        if label_name in self.keys():
            self[label_name].withdraw_all()
            del self[label_name]
    
    def remove_all(self):
        for _, label in self.items():
            label.withdraw_all()
        self.clear()

    def withdraw_all(self):
        for _, label in self.items():
            label.withdraw_all()
    
class Label(Table):

    def __init__(self, prop, label_name, label_color=None):
        '''
        Args:
            prop: a Property object
            label_name: name of a label
            color: [r, g, b]
        '''
        super().__init__()
        assert label_name not in prop.keys()
        self.property = prop
        self.name = label_name
        self.color = label_color
        self.property[label_name] = self

    def rename(self, label_name):
        if label_name not in self.property.keys():
            self.property[label_name] = self.property.pop(self.label_name)
            self.label_name = label_name

    def set_color(self, r, g, b):
        self.color = [r,g,b]

    def assign(self, annotation):
        annotation.labels[self.property] = self
        self[hash(annotation)] = annotation

    def withdraw(self, annotation):
        if self.property in annotation.labels.keys():
            del annotation.labels[self.property]
        anno_k = hash(annotation)
        if anno_k in self.keys():
            del self[anno_k]

    def withdraw_all(self):
        for _, anno in self.items():
            if self.property in anno.labels.keys():
                del anno.labels[self.property]
        self.clear()


if __name__ == "__main__":
    from annotations import *
    import pprint
    DD = {'color': {'red': [255,0,0], 'blue': [0,255,0]}, 'shape': {'round': [12,35,123]}}
    pprint.pprint(DD)
    labelMgr = LabelManager({})
    labelMgr.parse_labels(DD)
    print('==== regenerated ====')
    pprint.pprint(labelMgr.render_save())
    print('==== operation test ====')
    anno = DotAnnotation('timestamp', {'coords':[100,100]}, labelMgr)
    labelMgr.assign(anno, 'shape', 'round')
    print(labelMgr['shape']['round'], anno.labels)
    # labelMgr['shape'].remove_all()
    labelMgr.withdraw(anno, 'shape', 'round')
    print(labelMgr['shape']['round'], anno.labels)
    # labelMgr.remove_property('shape')
    # print(labelMgr, anno.labels)