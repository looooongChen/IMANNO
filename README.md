# IMANNO (IMage ANNOtation toolkit)
An image annotation toolkit   
by Institut of Imaging & Computer Vision, RWTH Aachen University, Germany
(https://www.lfb.rwth-aachen.de/en/)

![ui](docs/ui.PNG)

## updates:
- current: folder rename bug fix, project merge, dialog of distribute/collect annotations, annotation exporter update
- release_Oct_2020: unicode path support; screenshot; search missing images; distribute/collect annotations to/from image file locations; project: managing files as a project
- release_Mar_2020: Livewire tool
- release_Dec_2019: support for bmp images; fix line annotation bug

## Dependencies:

- python = 3.x
- opencv = 3.x 
- pyqt = 5.x
- h5py
- scikit-image

optional:
- pyinstaller

### Set up you own python environment
We recommend using anaconda to setup the enironment:
env.yml list the complete packages, which can be easily used by conda: 
```
conda env create -f env.yml
```

/release_MM_YYYY/ contains an independent executable for windows users

## Usage:
https://www.youtube.com/watch?v=1drqp9zhjbY

## Features:

### Drawing
- Polygons: free drawing
- Livewire/Intelligent Scissor: draw by clicking points, lines between points are estimated by the software
- Ellipses:
- Bounding Box
- Dot

### Labeling

Label docker on the right side:
- add new attributes
- add new labels to an attribute
- save current attributes and labels as default
- load default

Give labels:
- double click to select (+Ctrl for multiple selection)
- double click a label in the label docker to give that label to selected objects

Display channel (attribute):
- objects displayed with different colors based on the labels of the selectes attribute channel
- objecst without a label will be black 

### Managing annotations as a project

- merge two projects
- check duplicates in the same project: 

Note: conflict labels will be delete, so please make sure the lables are consitent

### Annotation formats

Annotations are saved in .hdf5 file with the same name of the image. Some tools are provided to export the annotations as other formats.

#### .json struture ####

anno_file = {'status': 'unfinished'/'finished'/'confirmed'/'problematic',
             'labels': {'property1': {'label1': [r,g,b], 'label2': [r,g,b], ...}, ...},  
             'annotations': {'timestamp': , ... } }

#### .hdf5 structure
/attributes/<attr_name>/<label_name>
/annotations/<timestamp_of_annotation>(attr:type, timestamp)  
/annotations/<timestamp_of_annotation>/labels/<attribute_name>(attr: label_name)   

Polygon:  
- /annotations/<timestamp_of_annotation>/boundingBox:(4,)
- /annotations/<timestamp_of_annotation>/polygon:(N,2)

anno_polygon = {'timestamp': datim.today().isoformat('@'),  
                'type': 'polygon',
                'labels': {property: label, ...},
                'coords': [[x1, y1], [x2, y2], ...], 
                'bbx': [x, y, w, h]}

Livewire:
- save as a polygon object

Bouding box:  
- /annotations/<timestamp_of_annotation>/boundingBox:(4,)

anno_bbx = {'timestamp': datim.today().isoformat('@'),  
            'type': 'bbx',  
            'labels': {property: label, ...},  
            'bbx': [x, y, w, h]}

Ellipse: 

- /annotations/<timestamp_of_annotation>/center:(2,)  
- /annotations/<timestamp_of_annotation>/angle:(1,)   
- /annotations/<timestamp_of_annotation>/axis:(2,)  

anno_ellipse = {'timestamp': datim.today().isoformat('@'),  
                'type': 'ellipse',  
                'labels': {property: label, ...},  
                'coords': [x, y],  
                'angle': angle,  
                'axis': [axis_major, axis_minor],
                'bbx': [x, y, w, h]}

Dot:  
- /annotations/<timestamp_of_annotation>/pt:(2,) 

anno_dot = {'timestamp': datim.today().isoformat('@'),  
            'type': 'dot',  
            'labels': {property: label, ...},  
            'coords': [x, y]}

anno_curve = {'timestamp': datim.today().isoformat('@'),  
              'type': 'curve',  
              'labels': {property: label, ...},  
              'coords': [[x1, y1], [x2, y2], ...],
              'bbx': [x, y, w, h]}

Data structure
- boundingBox(4,): x, y, w, h  
- polygon(N,2): coordinates  
- center(2,): image coordinate x-right y-down  
- angle(1,): 0 angle - right (in degree)
- axis(2,): main axis lenght, side axis length  
- pt(2,): x, y  

#### export annotation as other formats
Edit -> Export Annotations
- mask, single (.png): export segmentation masks in a single image (objects may overlap)
- mask, multiple (.png): exports segmetation masks, each image for an object
- boundingbox (.xml): PASCAL VOC format
- patches (.png): exports an image patch and segmentation patch for each object
- skeleton (.png): exports skeletons of objects

options:
- ignore images without objects annotates: empty images will ignored, otherwise an empty annotation will be generated
- copy images: copy original image to the save folder, together with the exported annotations
- padding (only for patches): add a margin (%) to the patch
- export label of property (only for bounding box): save labels of given property in .xml

## TODOs:

- config menu
- screen shot

## Export executable (windows10 tested)

- install pyinstaller
- run command: 
```
pyinstaller main.py
```
- copy ./config ./icons ./uis to the directory of your executable (which contains main.exe)
- copy platform directory to the directory of your executable. You'll find the platform directory at a location like c:\Users\<username>\envs\<environmentname>\Library\plugins\platforms
