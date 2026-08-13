# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'can.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QAbstractScrollArea, QApplication, QComboBox, QFormLayout,
    QLabel, QMainWindow, QMenu, QMenuBar,
    QPlainTextEdit, QSizePolicy, QStatusBar, QWidget)

class Ui_CANViewer(object):
    def setupUi(self, CANViewer):
        if not CANViewer.objectName():
            CANViewer.setObjectName(u"CANViewer")
        CANViewer.resize(800, 600)
        self.action_Load_DBC = QAction(CANViewer)
        self.action_Load_DBC.setObjectName(u"action_Load_DBC")
        self.centralwidget = QWidget(CANViewer)
        self.centralwidget.setObjectName(u"centralwidget")
        self.formLayout = QFormLayout(self.centralwidget)
        self.formLayout.setObjectName(u"formLayout")
        self.label_2 = QLabel(self.centralwidget)
        self.label_2.setObjectName(u"label_2")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_2)

        self.deviceSelect = QComboBox(self.centralwidget)
        self.deviceSelect.setObjectName(u"deviceSelect")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.deviceSelect)

        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label)

        self.channelSelect = QComboBox(self.centralwidget)
        self.channelSelect.setObjectName(u"channelSelect")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.channelSelect)

        self.plainTextEdit = QPlainTextEdit(self.centralwidget)
        self.plainTextEdit.setObjectName(u"plainTextEdit")
        self.plainTextEdit.setAcceptDrops(False)
        self.plainTextEdit.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.plainTextEdit.setUndoRedoEnabled(False)
        self.plainTextEdit.setReadOnly(True)

        self.formLayout.setWidget(2, QFormLayout.ItemRole.FieldRole, self.plainTextEdit)

        self.label_3 = QLabel(self.centralwidget)
        self.label_3.setObjectName(u"label_3")

        self.formLayout.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_3)

        self.plainTextEdit_2 = QPlainTextEdit(self.centralwidget)
        self.plainTextEdit_2.setObjectName(u"plainTextEdit_2")
        self.plainTextEdit_2.setReadOnly(True)
        self.plainTextEdit_2.setBackgroundVisible(False)

        self.formLayout.setWidget(3, QFormLayout.ItemRole.FieldRole, self.plainTextEdit_2)

        CANViewer.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(CANViewer)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 33))
        self.menu_File = QMenu(self.menubar)
        self.menu_File.setObjectName(u"menu_File")
        CANViewer.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(CANViewer)
        self.statusbar.setObjectName(u"statusbar")
        CANViewer.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menu_File.menuAction())
        self.menu_File.addAction(self.action_Load_DBC)

        self.retranslateUi(CANViewer)

        QMetaObject.connectSlotsByName(CANViewer)
    # setupUi

    def retranslateUi(self, CANViewer):
        CANViewer.setWindowTitle(QCoreApplication.translate("CANViewer", u"CAN Viewer", None))
        self.action_Load_DBC.setText(QCoreApplication.translate("CANViewer", u"&Load DBC", None))
        self.label_2.setText(QCoreApplication.translate("CANViewer", u"Device", None))
        self.label.setText(QCoreApplication.translate("CANViewer", u"Channel", None))
        self.plainTextEdit.setDocumentTitle(QCoreApplication.translate("CANViewer", u"CAN Output", None))
        self.label_3.setText(QCoreApplication.translate("CANViewer", u"Device Information", None))
        self.plainTextEdit_2.setPlaceholderText(QCoreApplication.translate("CANViewer", u"No device found", None))
        self.menu_File.setTitle(QCoreApplication.translate("CANViewer", u"&File", None))
    # retranslateUi

