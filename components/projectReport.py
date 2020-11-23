from PyQt5 import uic
from .enumDef import *
from PyQt5.QtWidgets import QTreeWidgetItem, QDialog


#################################

class ProjectReport(QDialog):


    def __init__(self, config, parent=None):
        super().__init__(parent=parent)
        self.config = config
        self.ui = uic.loadUi('uis/projectReport.ui', baseinstance=self)
        self.setWindowTitle("Project Statistics ...")
        self.project = None
        
        self.btnSave.clicked.connect(self.save)
        self.btnClose.clicked.connect(self.closeDialog)

    def init_table(self, project):
        self.report.clear()
        self.report.setHeaderLabels(['Property', 'Count'])
        total, stats = project.report()
        img_count = QTreeWidgetItem(['Images Number: ', str(len(project.index_id))])
        self.report.addTopLevelItem(img_count)
        obj_count = QTreeWidgetItem(['Objects Number: ', str(total)])
        self.report.addTopLevelItem(obj_count)
        for k, _ in stats.items():
            prop = QTreeWidgetItem([k.title(), ''])
            self.report.addTopLevelItem(prop)
            for kk, vv in stats[k].items():
                value = QTreeWidgetItem([kk.title(), str(vv)])
                prop.addChild(value)
            prop.setExpanded(True)
        self.report.resizeColumnToContents(0)
        self.report.resizeColumnToContents(1)
    
    def save(self):
        pass
    
    def closeDialog(self):
        self.close()





            
