# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'remote_configs.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QAbstractScrollArea, QApplication,
    QDialog, QDialogButtonBox, QFormLayout, QLayout,
    QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
    QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(600, 338)
        self.formLayout = QFormLayout(Dialog)
        self.formLayout.setObjectName(u"formLayout")
        self.formLayout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.configsList = QListWidget(Dialog)
        self.configsList.setObjectName(u"configsList")
        self.configsList.setAcceptDrops(True)
        self.configsList.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.configsList.setTabKeyNavigation(True)
        self.configsList.setAlternatingRowColors(True)
        self.configsList.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.configsList.setSelectionRectVisible(True)

        self.formLayout.setWidget(0, QFormLayout.ItemRole.SpanningRole, self.configsList)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.formLayout.setWidget(5, QFormLayout.ItemRole.LabelRole, self.buttonBox)

        self.addNewConfigBtn = QPushButton(Dialog)
        self.addNewConfigBtn.setObjectName(u"addNewConfigBtn")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.addNewConfigBtn)

        self.browseConfigBtn = QPushButton(Dialog)
        self.browseConfigBtn.setObjectName(u"browseConfigBtn")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.FieldRole, self.browseConfigBtn)

        self.removeConfigsBtn = QPushButton(Dialog)
        self.removeConfigsBtn.setObjectName(u"removeConfigsBtn")

        self.formLayout.setWidget(3, QFormLayout.ItemRole.FieldRole, self.removeConfigsBtn)


        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"External Configurations", None))
        self.addNewConfigBtn.setText(QCoreApplication.translate("Dialog", u"Add New Config", None))
        self.browseConfigBtn.setText(QCoreApplication.translate("Dialog", u"Browse For New Configs", None))
        self.removeConfigsBtn.setText(QCoreApplication.translate("Dialog", u"Remove Config(s)", None))
    # retranslateUi

