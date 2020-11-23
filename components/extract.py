from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QFileDialog, QProgressBar 
from PyQt5.Qt import QAbstractItemView
from PyQt5.QtCore import Qt, QCoreApplication
from .enumDef import *
from .fileList import FolderTreeItem, ImageTreeItem
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
TP_MASK_SINGLE = "Mask-Single (.png): all objects in one image, may overlap"
TP_MASK_MULTI = "Mask-Multiple (.png): one mask for each object"
TP_BBX = "Bounding Box (.xml): PASCAL VOC format"
TP_PATCH = "Patches (.png)"
TP_SKELETON = "Skeleton (.png)"

class AnnoExporter(QDialog):
    def __init__(self, config, project=None, parent=None):
        super().__init__(parent=parent)
        self.config = config
        self.ui = uic.loadUi('uis/annoExporter.ui', baseinstance=self)
        self.setWindowTitle("Export annotations")
        self.project = project
        
        self.btnSelect.clicked.connect(self.select)
        self.btnSelectAll.clicked.connect(self.select_all)
        self.btnExport.clicked.connect(self.export)
        self.exportType.currentTextChanged.connect(self.update_ui)
        
        self.exportType.addItem(TP_MASK_SINGLE)
        self.exportType.addItem(TP_MASK_MULTI)
        self.exportType.addItem(TP_BBX)
        self.exportType.addItem(TP_PATCH)
        self.exportType.addItem(TP_SKELETON)

        # init file list
        self.fileList.setColumnCount(1)
        self.fileList.setHeaderHidden(True)
        self.fileList.setIndentation(20)
        self.fileList.setRootIsDecorated(False)
        self.fileList.setSelectionMode(QAbstractItemView.ContiguousSelection)
        # self.fileList.itemChanged.connect(self.on_item_change, Qt.QueuedConnection)
        self.fileList.itemChanged.connect(self.on_item_change)

        self.progressBar.setValue(0)
        self.valuePadding.setMinimum(0)
        self.valuePadding.setMaximum(100)
        self.valuePadding.setSingleStep(1)
        self.valuePadding.setValue(10)

    def initial_list(self, fileList):
        fileList = fileList.fileList
        for i in range(fileList.topLevelItemCount()):
            item = fileList.topLevelItem(i)
            item_c = item.clone()
            item_c.setCheckState(0, Qt.Unchecked)
            if isinstance(item, FolderTreeItem):
                item_c.set_icon(self.config['icons'][FOLDER])
                self.fileList.addTopLevelItem(item_c)
                for j in range(item.childCount()):
                    child_item = item.child(j).clone()
                    child_item.setCheckState(0, Qt.Unchecked)
                    child_item.set_icon(self.config['icons'][child_item.status])
                    item_c.addChild(child_item)
            else:
                item_c.set_icon(self.config['icons'][item_c.status])
                self.fileList.addTopLevelItem(item_c)
    
    def on_item_change(self, item, col):
        if isinstance(item, FolderTreeItem):
            for j in range(item.childCount()):
                item.child(j).setCheckState(0, item.checkState(0))

    def select(self):
        if len(self.fileList.selectedItems()) > 0:
            status = self.fileList.selectedItems()[0].checkState(0)
            if status == Qt.Checked:
                status = Qt.Unchecked
            else:
                status = Qt.Checked

        for item in self.fileList.selectedItems():
            item.setCheckState(0, status)
    
    def select_all(self):
        if self.fileList.topLevelItemCount() > 0:
            status = self.fileList.topLevelItem(0).checkState(0)
            if status == Qt.Checked:
                status = Qt.Unchecked
            else:
                status = Qt.Checked

        for i in range(self.fileList.topLevelItemCount()):
            item = self.fileList.topLevelItem(i)
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
        self.valueProperty.setEnabled(False)
        self.valuePadding.setEnabled(False)
        self.exportEmpty.setEnabled(True)
        self.exportEmpty.setCheckState(Qt.Unchecked)
        self.exportGt.setEnabled(False)
        self.exportGt.setCheckState(Qt.Checked)
        self.exportApproximate.setEnabled(False)
        self.exportApproximate.setCheckState(Qt.Unchecked)
        if text == TP_MASK_SINGLE or text == TP_MASK_MULTI:
            self.valueProperty.setEnabled(False)
            self.valuePadding.setEnabled(False)
            self.exportApproximate.setEnabled(True)
            self.exportApproximate.setCheckState(Qt.Unchecked)
        elif text == TP_PATCH:
            self.valueProperty.setEnabled(False)
            self.valuePadding.setEnabled(True)
            self.exportEmpty.setEnabled(False)
            self.exportEmpty.setCheckState(Qt.Unchecked)
            self.exportGt.setEnabled(True)
            self.exportGt.setCheckState(Qt.Checked)
        elif text == TP_BBX:
            self.valueProperty.setEnabled(True)
            self.valuePadding.setEnabled(False)
        elif text == TP_SKELETON:
            pass

    def export(self):
        self.progressBar.setValue(0)
        
        save_dir = QFileDialog.getExistingDirectory(self, 'Select Directory')
        if len(save_dir) != 0:
            exportType = str(self.exportType.currentText())
            ignore = self.exportEmpty.checkState() == Qt.Checked
            now = datetime.now()

            if exportType == TP_MASK_SINGLE or exportType == TP_MASK_MULTI:
                suffix = '-mask-'
            elif exportType == TP_BBX:
                suffix = '-bbx-'
            elif exportType == TP_PATCH:
                suffix = '-patch-'
            elif exportType == TP_SKELETON:
                suffix = '-skeleton-'
            else:
                suffix = '-'

            save_dir = os.path.join(save_dir, 'export'+suffix + now.strftime("%Y-%b-%d-%H-%M-%S"))
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            # get selected items
            items = []
            for i in range(self.fileList.topLevelItemCount()):
                item = self.fileList.topLevelItem(i)
                if isinstance(item, FolderTreeItem):
                    for j in range(item.childCount()):
                        child_item = item.child(j)
                        if child_item.checkState(0) == Qt.Checked:
                            items.append(child_item)
                else:
                    if item.checkState(0) == Qt.Checked:
                        items.append(item)
            # get valid images and annotations
            images, annotations = [], []
            if self.project.is_open():
                for item in items:
                    idx = item.idx
                    image_path = self.project.get_image_path(idx)
                    annotation_path = self.project.get_annotation_path(idx)
                    if os.path.exists(image_path) and os.path.exists(annotation_path):
                        images.append(image_path)
                        annotations.append(annotation_path)
            else:
                for item in itmes:
                    image_path = item.path
                    annotation_path = os.path.splitext(image_path)[0] + '.' + ANNOTATION_EXT
                    if os.path.exists(image_path) and os.path.exists(annotation_path):
                        images.append(image_path)
                        annotations.append(annotation_path)
            # export annotations and the list
            total = len(images)
            with open(os.path.join(save_dir, 'files.csv'), mode='w', newline='') as files:
                file_writer = csv.writer(files, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                progress, sn = 0, 0
                for img, anno in zip(images, annotations):
                    progress += 1
                    if int(progress*100/total) - self.progressBar.value() >= 1:
                        self.progressBar.setValue(progress*100/total)
                    QCoreApplication.processEvents()
                    # export mask single
                    if exportType == TP_MASK_SINGLE:
                        export, is_empty = export_mask(anno, img, save_as_one=True)
                        if ignore and is_empty:
                            continue
                        sn += 1
                        save_path = os.path.join(save_dir, "mask_{:08d}.png").format(sn)
                        cv2.imwrite(save_path, export)
                        file_writer.writerow([img, save_path])
                    # export mask multiple
                    elif exportType == TP_MASK_MULTI:
                        export, is_empty = export_mask(anno, img, save_as_one=False)
                        if ignore and is_empty:
                            continue
                        sn += 1
                        save_path = os.path.join(save_dir, "mask_{:08d}").format(sn)
                        os.makedirs(save_path)
                        for j, mask in enumerate(export):
                            cv2.imwrite(os.path.join(save_path, 'obj_{:03d}.png'.format(j)), mask)
                        file_writer.writerow([img, save_path])
                    # export bounding box
                    elif exportType == TP_BBX:
                        export_property = str(self.valueProperty.text()).strip()
                        export, is_empty = export_bbx(anno, img, export_property)
                        if ignore and is_empty:
                            continue
                        sn += 1
                        save_path = os.path.join(save_dir, "bbx_{:08d}.xml").format(sn)
                        createXml(export, img, save_path)
                        file_writer.writerow([img, save_path])
                    # export patches
                    elif exportType == TP_PATCH:
                        padding = self.valuePadding.value()
                        imgs, masks = extract_patch(anno, img, padding/100)
                        if len(imgs) == 0:
                            continue
                        sn += 1
                        save_path = os.path.join(save_dir, "patch_{:08d}").format(sn)
                        img_dir = os.path.join(save_path, 'images')
                        mask_dir = os.path.join(save_path, 'masks')
                        os.makedirs(img_dir)
                        os.makedirs(mask_dir)
                        for j in range(len(imgs)):
                            img_patch_path = os.path.join(img_dir, 'patch_{:03d}.png'.format(j))
                            imgs[j].save(img_patch_path)
                            if masks[j] is not None:
                                mask_patch_path = os.path.join(mask_dir, 'patch_{:03d}.png'.format(j))
                                cv2.imwrite(mask_patch_path, masks[j])
                            else:
                                mask_patch_path = ''
                            file_writer.writerow([img_patch_path, mask_patch_path])
                    elif exportType == TP_SKELETON:
                        export, is_empty = export_skeleton(anno, img)
                        if ignore and is_empty:
                            continue
                        sn += 1
                        save_path = os.path.join(save_dir, "skeleton_{:08d}.png").format(sn)
                        cv2.imwrite(save_path, export.astype(np.uint8)*20)
                        file_writer.writerow([img, save_path])
                    else:
                        sn -= 1
                        print("Unsupported output type")
                    
        
            self.progressBar.setValue(100)    








            
