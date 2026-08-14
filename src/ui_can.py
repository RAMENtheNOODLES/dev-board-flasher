# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'can.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QMetaObject, QRect)
from PySide6.QtGui import (QAction)
from PySide6.QtWidgets import (QComboBox, QFormLayout, QLabel, QMenu, QMenuBar,
                               QPlainTextEdit, QPushButton, QStatusBar,
                               QWidget)

from can_logging import CanLogging


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

        self.label_3 = QLabel(self.centralwidget)
        self.label_3.setObjectName(u"label_3")

        self.formLayout.setWidget(4, QFormLayout.ItemRole.LabelRole, self.label_3)

        self.deviceInfo = QPlainTextEdit(self.centralwidget)
        self.deviceInfo.setObjectName(u"deviceInfo")
        self.deviceInfo.setReadOnly(True)
        self.deviceInfo.setBackgroundVisible(False)

        self.formLayout.setWidget(4, QFormLayout.ItemRole.FieldRole, self.deviceInfo)

        self.connectButton = QPushButton(self.centralwidget)
        self.connectButton.setObjectName(u"connectButton")

        self.formLayout.setWidget(5, QFormLayout.ItemRole.FieldRole, self.connectButton)

        self.canLogs = CanLogging(self.centralwidget)
        self.canLogs.setObjectName(u"canLogs")

        self.formLayout.setWidget(3, QFormLayout.ItemRole.FieldRole, self.canLogs)

        self.baudRateComboBox = QComboBox(self.centralwidget)
        self.baudRateComboBox.addItem("")
        self.baudRateComboBox.addItem("")
        self.baudRateComboBox.addItem("")
        self.baudRateComboBox.addItem("")
        self.baudRateComboBox.setObjectName(u"baudRateComboBox")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.FieldRole, self.baudRateComboBox)

        self.baudRateLabel = QLabel(self.centralwidget)
        self.baudRateLabel.setObjectName(u"baudRateLabel")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.LabelRole, self.baudRateLabel)

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

        self.baudRateComboBox.setCurrentIndex(3)


        QMetaObject.connectSlotsByName(CANViewer)
    # setupUi

    def retranslateUi(self, CANViewer):
        CANViewer.setWindowTitle(QCoreApplication.translate("CANViewer", u"CAN Viewer", None))
        self.action_Load_DBC.setText(QCoreApplication.translate("CANViewer", u"&Load DBC", None))
        self.label_2.setText(QCoreApplication.translate("CANViewer", u"Device", None))
        self.label.setText(QCoreApplication.translate("CANViewer", u"Channel", None))
        self.label_3.setText(QCoreApplication.translate("CANViewer", u"Device Information", None))
        self.deviceInfo.setPlaceholderText(QCoreApplication.translate("CANViewer", u"No device found", None))
        self.connectButton.setText(QCoreApplication.translate("CANViewer", u"Connect", None))
        self.baudRateComboBox.setItemText(0, QCoreApplication.translate("CANViewer", u"125 kBits/s", None))
        self.baudRateComboBox.setItemText(1, QCoreApplication.translate("CANViewer", u"250 kBits/s", None))
        self.baudRateComboBox.setItemText(2, QCoreApplication.translate("CANViewer", u"500 kBits/s", None))
        self.baudRateComboBox.setItemText(3, QCoreApplication.translate("CANViewer", u"1000 kBits/s", None))

        self.baudRateLabel.setText(QCoreApplication.translate("CANViewer", u"Baud Rate", None))
        self.menu_File.setTitle(QCoreApplication.translate("CANViewer", u"&File", None))
    # retranslateUi

