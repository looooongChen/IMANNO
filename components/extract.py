from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QFileDialog, QProgressBar, QTreeWidgetItem 
from PyQt5.Qt import QAbstractItemView
from PyQt5.QtCore import Qt, QCoreApplication
from .enumDef import *
# from .items import *
from .fileList import FolderTreeItem, ImageTreeItem
from .func_annotation import *
from .func_export import *
import numpy as np
from datetime import datetime
from PIL import Image
import os
import h5py
import csv
import cv2
import shutil

IMAGE_FORMATS = [f[1:] for f in IMAGE_TYPES]


#################################
TP_INSTANCE_SINGLE = "Instances-Single (.png): all objects in one image, may overlap"
TP_INSTANCE_MULTI = "Instances-Multiple (.png): one mask for each object"
TP_SEMANTIC_SINGLE = "Semantic-Single (.png): semantic map in one image, objects may overlap"
TP_SEMANTIC_MULTI = "Semantic-Multiple (.png): semantic map, one map per object"
TP_BBX = "Bounding Box (.xml): PASCAL VOC format"
TP_PATCH = "Patches (.png)"
# TP_SKELETON = "Skeleton (.png)"

class AnnoExporter(QDialog):
    def __init__(self, config, project=None, parent=None):
        super().__init__(parent=parent)
        self.config = config
        self.project = project
        self.ui = uic.loadUi('uis/annoExporter.ui', baseinstance=self)
        self.setWindowTitle("Export annotations")
        self.layout.setLabelAlignment(Qt.AlignRight)
        self.layout.setFormAlignment(Qt.AlignLeft)
        
        # init type list
        self.exportType.addItem(TP_INSTANCE_SINGLE)
        self.exportType.addItem(TP_INSTANCE_MULTI)
        self.exportType.addItem(TP_SEMANTIC_SINGLE)
        self.exportType.addItem(TP_SEMANTIC_MULTI)
        self.exportType.addItem(TP_BBX)
        self.exportType.addItem(TP_PATCH)
        # self.exportType.addItem(TP_SKELETON)

        # init padding value bar
        self.valuePadding.setMinimum(0)
        self.valuePadding.setMaximum(100)
        self.valuePadding.setSingleStep(1)
        self.valuePadding.setValue(10)

        # init image list
        self.imageList.setColumnCount(1)
        self.imageList.setHeaderHidden(True)
        self.imageList.setIndentation(40)
        self.imageList.setRootIsDecorated(False)
        self.imageList.setSelectionMode(QAbstractItemView.ContiguousSelection)
        # self.fileList.itemChanged.connect(self.on_item_change, Qt.QueuedConnection)
        self.imageList.itemChanged.connect(self.on_fileList_item_change)

        # init label list
        self.labelList.setColumnCount(1)
        self.labelList.setHeaderHidden(True)
        self.labelList.setIndentation(40)
        self.labelList.setRootIsDecorated(False)
        self.labelList.setSelectionMode(QAbstractItemView.ContiguousSelection)
        # self.labelList.itemChanged.connect(self.on_item_change, Qt.QueuedConnection)
        self.labelList.itemChanged.connect(self.on_labelList_item_change)

        self.progressBar.setValue(0)
        
        self.selectAllImages.clicked.connect(lambda : self.select_all(self.imageList, 1))
        self.unselectAllImages.clicked.connect(lambda : self.select_all(self.imageList, 0))
        self.selectAllLabels.clicked.connect(lambda : self.select_all(self.labelList, 1))
        self.unselectAllLabels.clicked.connect(lambda : self.select_all(self.labelList, 0))
        self.exportAllObjects.stateChanged.connect(self.check_exportAllObjects_constraint)
        self.exportType.currentTextChanged.connect(self.update_ui)
        self.btnExport.clicked.connect(self.export)
        self.update_ui(TP_INSTANCE_SINGLE)

    ## getter of selected items
    def selected_image_items(self):
        items = []
        for i in range(self.imageList.topLevelItemCount()):
            item = self.imageList.topLevelItem(i)
            if isinstance(item, FolderTreeItem):
                for j in range(item.childCount()):
                    child_item = item.child(j)
                    if child_item.checkState(0) == Qt.Checked:
                        items.append(child_item)
            else:
                if item.checkState(0) == Qt.Checked:
                    items.append(item)
        return items
    
    def selected_labels(self):
        labels = {}
        for i in range(self.labelList.topLevelItemCount()):
            p_item = self.labelList.topLevelItem(i)
            for j in range(p_item.childCount()):
                l_item = p_item.child(j)
                if l_item.checkState(0) == Qt.Checked:
                    if p_item.text(0) in labels.keys():
                        labels[p_item.text(0)].append(l_item.text(0))
                    else:
                        labels[p_item.text(0)] = [l_item.text(0)]
        return labels
    
    def files(self, items):
        images, annotations, idxs = [], [], []
        if self.project.is_open():
            for item in items:
                idx = item.idx
                image_path, annotation_path = self.project.get_image_path(idx), self.project.get_annotation_path(idx)
                if os.path.exists(image_path) and os.path.exists(annotation_path):
                    idxs.append(idx)
                    images.append(image_path)
                    annotations.append(annotation_path)
        else:
            for item in items:
                image_path = item.path
                annotation_path = os.path.splitext(image_path)[0] + ANNOTATION_EXT
                if os.path.exists(image_path) and os.path.exists(annotation_path):
                    images.append(image_path)
                    annotations.append(annotation_path)
                    idxs.append(None)
        return images, annotations, idxs
    
    # constraints of selection

    def check_semantic_constraint(self, item=None):
        # if semantic, maximal one category could be selected
        if str(self.exportType.currentText()) in [TP_SEMANTIC_SINGLE, TP_SEMANTIC_MULTI, TP_BBX]:
            self.labelList.blockSignals(True)
            index = -1
            if item is None:
                for i in range(self.labelList.topLevelItemCount()):
                    if self.labelList.topLevelItem(i).checkState(0) == Qt.Checked:
                        index = i
                        break
            else:
                index = self.labelList.indexOfTopLevelItem(item)
                if index == -1 and item.parent():
                    index = self.labelList.indexOfTopLevelItem(item.parent())
            for i in range(self.labelList.topLevelItemCount()):
                if i != index:
                    prop = self.labelList.topLevelItem(i)
                    prop.setCheckState(0, Qt.Unchecked)
                    for j in range(prop.childCount()):
                        prop.child(j).setCheckState(0, Qt.Unchecked)
            self.labelList.blockSignals(False)

    def check_exportAllObjects_constraint(self, status=None):
        # if exportAllObject, then only the selection of a complete category is possible/necessary (if semantic)
        # no selection is necessary, if instance 
        status = self.exportAllObjects.checkState() if status is None else status
        if status == Qt.Checked:
            if str(self.exportType.currentText()) in [TP_SEMANTIC_SINGLE, TP_SEMANTIC_MULTI, TP_BBX]:
                self.labelList.collapseAll()
                self.labelList.setItemsExpandable(False)
                self.labelList.setEnabled(True)
            else:
                self.labelList.collapseAll()
                self.labelList.setEnabled(False)
        else:
            self.labelList.expandAll()
            self.labelList.setItemsExpandable(True)
            self.labelList.setEnabled(True)
    
    ## list initialization

    def initial_list(self, fileList):
        fileList = fileList.fileList
        items = []
        for i in range(fileList.topLevelItemCount()):
            item = fileList.topLevelItem(i)
            item_c = item.clone()
            item_c.setCheckState(0, Qt.Unchecked)
            if isinstance(item, FolderTreeItem):
                item_c.set_icon(self.config.icons[FOLDER])
                self.imageList.addTopLevelItem(item_c)
                for j in range(item.childCount()):
                    child_item = item.child(j).clone()
                    child_item.setCheckState(0, Qt.Unchecked)
                    child_item.set_icon(self.config.icons[child_item.status])
                    item_c.addChild(child_item)
                    items.append(child_item)
            else:
                item_c.set_icon(self.config.icons[item_c.status])
                self.imageList.addTopLevelItem(item_c)
                items.append(item_c)
        _, anno_files, _ = self.files(items)

        props = anno_props(anno_files)

        for p, lbs in props.items():
            p_item = QTreeWidgetItem(PROPERTY)
            p_item.setText(0, p)
            p_item.setCheckState(0, Qt.Unchecked)
            p_item.setIcon(0, self.config.icons[EX_STAR])
            self.labelList.addTopLevelItem(p_item)
            for lb in lbs:
                l_item = QTreeWidgetItem(LABEL)
                l_item.setText(0, lb)
                l_item.setCheckState(0, Qt.Unchecked)
                l_item.setIcon(0, self.config.icons[LABEL])
                p_item.addChild(l_item)
        
        self.update_ui(TP_INSTANCE_SINGLE)

    def on_fileList_item_change(self, item, col):
        for j in range(item.childCount()):
            item.child(j).setCheckState(0, item.checkState(0))

    def on_labelList_item_change(self, item, col):
        self.labelList.blockSignals(True)
        export_type = str(self.exportType.currentText())

        for i in range(item.childCount()):
            item.child(i).setCheckState(0, item.checkState(0))
        for i in range(self.labelList.topLevelItemCount()):
            prop = self.labelList.topLevelItem(i)
            status = Qt.Unchecked
            for j in range(prop.childCount()):
                if prop.child(j).checkState(0) == Qt.Checked:
                    status = Qt.Checked
                    break
            prop.setCheckState(0, status)
        self.check_semantic_constraint(item)
            
        self.labelList.blockSignals(False)

    def select_all(self, slist, status=1):

        status = Qt.Checked if status == 1 else Qt.Unchecked
        for i in range(slist.topLevelItemCount()):
            item = slist.topLevelItem(i)
            item.setCheckState(0, status)

    def is_empty(self, location, types):

        if 'annotations' in location.keys():
            for timestamp in location['annotations']:
                anno = location['annotations'][timestamp]
                if anno.attrs['type'] in types:
                    return False
        return True

    def update_ui(self, text):
        text = str(text)
        self.valuePadding.setEnabled(False)
        # self.exportUndefinedObject.setEnabled(True)
        # self.exportUndefinedObject.setCheckState(Qt.Unchecked)
        self.labelList.setEnabled(True)
        self.exportEmptyImage.setEnabled(True)
        self.exportEmptyImage.setCheckState(Qt.Unchecked)
        self.labelList.expandAll()
        self.labelList.setItemsExpandable(True)
        if text == TP_INSTANCE_SINGLE or text == TP_INSTANCE_MULTI:
            pass
        elif text == TP_SEMANTIC_SINGLE or text == TP_SEMANTIC_MULTI:
            self.check_semantic_constraint()
        elif text == TP_PATCH:
            self.valuePadding.setEnabled(True)
            self.exportEmptyImage.setEnabled(False)
        elif text == TP_BBX:
            self.check_semantic_constraint()
        # elif text == TP_SKELETON:
        #     pass

        self.check_exportAllObjects_constraint()

    def export(self):
        self.progressBar.setValue(0)
        
        save_dir = QFileDialog.getExistingDirectory(self, 'Select Directory')
        if len(save_dir) != 0:
            exportType = str(self.exportType.currentText())
            exportEmpty = self.exportEmptyImage.checkState() == Qt.Checked
            exportAllObjects = self.exportAllObjects.checkState() == Qt.Checked
            now = datetime.now()

            if exportType == TP_INSTANCE_SINGLE or exportType == TP_INSTANCE_MULTI:
                suffix = '-instance-'
            elif exportType == TP_SEMANTIC_SINGLE or exportType == TP_SEMANTIC_MULTI:
                suffix = '-semantic-'
            elif exportType == TP_BBX:
                suffix = '-bbx-'
            elif exportType == TP_PATCH:
                suffix = '-patch-'
            # elif exportType == TP_SKELETON:
            #     suffix = '-skeleton-'
            else:
                suffix = '-'
            save_dir = os.path.join(save_dir, 'export'+suffix + now.strftime("%Y-%b-%d-%H-%M-%S"))
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            # get selected items
            image_items = self.selected_image_items()
            # get valid images and annotations
            images, annotations, idxs = self.files(image_items)
            # selected labels:
            labels = self.selected_labels()
            if str(self.exportType.currentText()) in [TP_SEMANTIC_SINGLE, TP_SEMANTIC_MULTI, TP_BBX] and len(labels) > 0:
                category = list(labels.keys())[0]
                semantic_labels = {}
                with open(os.path.join(save_dir, 'labels.csv'), mode='w', newline='') as files:
                    file_writer = csv.writer(files, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                    for idx, lb in enumerate(labels[category]):
                        semantic_labels[lb] = idx+1
                        file_writer.writerow([category, lb, idx+1])
                    if exportAllObjects:
                        file_writer.writerow([category, 'undefined', len(labels[category])+1])



            # export annotations and the list
            total = len(images)
            with open(os.path.join(save_dir, 'files.csv'), mode='w', newline='') as files:
                file_writer = csv.writer(files, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                progress, sn = 0, 0
                for img, anno, idx in zip(images, annotations, idxs):
                    progress += 1
                    if int(progress*100/total) - self.progressBar.value() >= 1:
                        self.progressBar.setValue(progress*100/total)
                    QCoreApplication.processEvents()
                    # export mask single
                    if exportType == TP_INSTANCE_SINGLE:
                        if exportAllObjects:
                            export, is_empty = export_mask(anno, img, save_as_one=True, export_labels=None)
                        elif len(labels) > 0:
                            export, is_empty = export_mask(anno, img, save_as_one=True, export_labels=labels)
                        else:
                            continue
                        if (not exportEmpty) and is_empty:
                            continue
                        sn += 1
                        save_name = "instance_{:08d}.png".format(sn)
                        save_path = os.path.join(save_dir, save_name)
                        cv2.imwrite(save_path, export)
                        # file_writer.writerow([img, save_path])
                        file_writer.writerow([idx, img, save_name])
                    # export mask multiple
                    elif exportType == TP_INSTANCE_MULTI:
                        if exportAllObjects:
                            export, is_empty = export_mask(anno, img, save_as_one=False, export_labels=None)
                        elif len(labels) > 0:
                            export, is_empty = export_mask(anno, img, save_as_one=False, export_labels=labels)
                        else:
                            continue
                        if (not exportEmpty) and is_empty:
                            continue
                        sn += 1
                        save_name = "instance_{:08d}".format(sn)
                        save_path = os.path.join(save_dir, save_name)
                        # save_path = os.path.join(save_dir, "mask_{:08d}").format(sn)
                        os.makedirs(save_path)
                        for j, mask in enumerate(export):
                            cv2.imwrite(os.path.join(save_path, 'obj_{:03d}.png'.format(j)), mask)
                        # file_writer.writerow([img, save_path])
                        file_writer.writerow([idx, img, save_name])
                    # export semantic single
                    elif exportType == TP_SEMANTIC_SINGLE:
                        if len(labels) == 0:
                            continue
                        export, is_empty = export_semantic(anno, img, category, semantic_labels, export_undefined=exportAllObjects, save_as_one=True)
                        if (not exportEmpty) and is_empty:
                            continue
                        sn += 1
                        save_name = "semantc_{:08d}.png".format(sn)
                        save_path = os.path.join(save_dir, save_name)
                        # save_path = os.path.join(save_dir, "semantic_{:08d}.png").format(sn)
                        cv2.imwrite(save_path, export)
                        file_writer.writerow([idx, img, save_name])
                    # export semantic multi
                    elif exportType == TP_SEMANTIC_MULTI:
                        if len(labels) == 0:
                            continue
                        export, is_empty = export_semantic(anno, img, category, semantic_labels, export_undefined=exportAllObjects, save_as_one=False)
                        if (not exportEmpty) and is_empty:
                            continue
                        sn += 1
                        save_name = "semantic_{:08d}".format(sn)
                        save_path = os.path.join(save_dir, save_name)
                        # save_path = os.path.join(save_dir, "semantic_{:08d}").format(sn)
                        os.makedirs(save_path)
                        for j, mask in enumerate(export):
                            cv2.imwrite(os.path.join(save_path, 'obj_{:03d}.png'.format(j)), mask)
                        file_writer.writerow([idx, img, save_name])
                    # export bounding box
                    elif exportType == TP_BBX:
                        if len(labels) == 0:
                            continue
                        export, is_empty = export_bbx(anno, img, category, semantic_labels, export_undefined=exportAllObjects)
                        if (not exportEmpty) and is_empty:
                            continue
                        sn += 1
                        save_name = "bbx_{:08d}.xml".format(sn)
                        save_path = os.path.join(save_dir, save_name)
                        # save_path = os.path.join(save_dir, "bbx_{:08d}.xml").format(sn)
                        createXml(export, img, save_path)
                        file_writer.writerow([idx, img, save_name])
                    # export patches
                    elif exportType == TP_PATCH:
                        padding = self.valuePadding.value()
                        if exportAllObjects:
                            imgs, masks = extract_patch(anno, img, padding/100, export_labels=None)
                        elif len(labels) > 0:
                            imgs, masks = extract_patch(anno, img, padding/100, export_labels=labels)
                        else:
                            continue
                        if len(imgs) == 0:
                            continue
                        sn += 1
                        save_name = "patch_{:08d}".format(sn)
                        save_path = os.path.join(save_dir, save_name)
                        # save_path = os.path.join(save_dir, "patch_{:08d}").format(sn)
                        img_dir = os.path.join(save_path, 'images')
                        mask_dir = os.path.join(save_path, 'masks')
                        os.makedirs(img_dir)
                        os.makedirs(mask_dir)
                        for j in range(len(imgs)):
                            # img_patch_path = os.path.join(img_dir, 'patch_{:03d}.png'.format(j))
                            img_patch_name = os.path.join(save_name, 'images', 'patch_{:03d}.png'.format(j))
                            imgs[j].save(os.path.join(save_dir, img_patch_name))
                            if masks[j] is not None:
                                mask_patch_name = os.path.join(save_name, 'masks',  'patch_{:03d}.png'.format(j))
                                cv2.imwrite(os.path.join(save_dir, mask_patch_name), masks[j])
                            else:
                                mask_patch_path = ''
                            file_writer.writerow([idx, img_patch_name, mask_patch_name])
                    # elif exportType == TP_SKELETON:

                    #     if exportAllObjects:
                    #         export, is_empty = export_skeleton(anno, img, export_labels=None)
                    #     elif len(labels) > 0:
                    #         export, is_empty = export_skeleton(anno, img, export_labels=labels)
                    #     else:
                    #         continue
                    #     if (not exportEmpty) and is_empty:
                    #         continue
                    #     sn += 1
                    #     save_path = os.path.join(save_dir, "skeleton_{:08d}.png").format(sn)
                    #     cv2.imwrite(save_path, export.astype(np.uint8)*20)
                    #     file_writer.writerow([img, save_path])
                    else:
                        sn -= 1
                        print("Unsupported output type")
                    
        
            self.progressBar.setValue(100)    








            
