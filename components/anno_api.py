import json
import os 

class Project(object):

    def __init__(self, file=None):
        self.project = None
        self.base_dir = None
        self.annotations = {}
        print(file)
        self.load(file)

    def load(self, file):
        if file is not None and os.path.isfile(file):
            self.base_dir = os.path.dirname(file)
            with open(file) as json_file:
                self.project = json.load(json_file)
            for item in self.project['images']:
                image_path, anno_path = item['image_path'], item['annotation_path']
                if item['rel_path']:
                    image_path = os.path.join(self.base_dir, image_path)
                    anno_path = os.path.join(self.base_dir, anno_path)
                self.annotations[image_path] = Annotation(anno_path)
                print('loading: ', anno_path)
                

class Annotation(object):

    def __init__(self, file):
        self.data = None
        self.load(file)

    def load(self, file):
        if file is not None and os.path.isfile(file):
            with open(file) as json_file:
                self.data = json.load(json_file)

    def is_empty(self):
        return True if self.data['annotations'] == 0 else False

    def mask(self):

if __name__ == "__main__":
    project = Project('D:/Datasets/PheNeSensNematode/nematodePheNeSens.improj')
    count_empty = 0
    for _, anno in project.annotations.items():
        if anno.is_empty():
            count_empty += 1
    print(count_empty, len(project.annotations))
    
