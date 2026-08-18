# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'remote_configs.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
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
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QApplication, QDialog,
    QDialogButtonBox, QFormLayout, QLayout, QListWidget,
    QListWidgetItem, QPushButton, QSizePolicy, QVBoxLayout,
    QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(575, 338)
        self.formLayout = QFormLayout(Dialog)
        self.formLayout.setObjectName(u"formLayout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.addNewConfigBtn = QPushButton(Dialog)
        self.addNewConfigBtn.setObjectName(u"addNewConfigBtn")

        self.verticalLayout.addWidget(self.addNewConfigBtn)

        self.browseConfigBtn = QPushButton(Dialog)
        self.browseConfigBtn.setObjectName(u"browseConfigBtn")

        self.verticalLayout.addWidget(self.browseConfigBtn)

        self.removeConfigsBtn = QPushButton(Dialog)
        self.removeConfigsBtn.setObjectName(u"removeConfigsBtn")

        self.verticalLayout.addWidget(self.removeConfigsBtn)


        self.formLayout.setLayout(0, QFormLayout.ItemRole.FieldRole, self.verticalLayout)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)

        self.formLayout.setWidget(2, QFormLayout.ItemRole.LabelRole, self.buttonBox)

        self.configsList = QListWidget(Dialog)
        self.configsList.setObjectName(u"configsList")
        self.configsList.setAcceptDrops(True)
        self.configsList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.configsList.setSelectionRectVisible(True)

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.configsList)


        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Dialog", None))
        self.addNewConfigBtn.setText(QCoreApplication.translate("Dialog", u"Add New Config", None))
        self.browseConfigBtn.setText(QCoreApplication.translate("Dialog", u"Browse For New Configs", None))
        self.removeConfigsBtn.setText(QCoreApplication.translate("Dialog", u"Remove Config(s)", None))
    # retranslateUi

