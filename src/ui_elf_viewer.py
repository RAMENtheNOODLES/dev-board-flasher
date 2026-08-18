# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'elf_viewer.ui'
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
from PySide6.QtWidgets import (QApplication, QFormLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QStatusBar, QTreeWidget,
    QTreeWidgetItem, QWidget)

class Ui_ElfViewer(object):
    def setupUi(self, ElfViewer):
        if not ElfViewer.objectName():
            ElfViewer.setObjectName(u"ElfViewer")
        ElfViewer.resize(800, 592)
        self.action_Open = QAction(ElfViewer)
        self.action_Open.setObjectName(u"action_Open")
        self.centralwidget = QWidget(ElfViewer)
        self.centralwidget.setObjectName(u"centralwidget")
        self.formLayout = QFormLayout(self.centralwidget)
        self.formLayout.setObjectName(u"formLayout")
        self.sectionsWidget = QTreeWidget(self.centralwidget)
        self.sectionsWidget.setObjectName(u"sectionsWidget")

        self.formLayout.setWidget(2, QFormLayout.ItemRole.SpanningRole, self.sectionsWidget)

        self.parseElfBtn = QPushButton(self.centralwidget)
        self.parseElfBtn.setObjectName(u"parseElfBtn")

        self.formLayout.setWidget(3, QFormLayout.ItemRole.LabelRole, self.parseElfBtn)

        self.startAddressLabel = QLabel(self.centralwidget)
        self.startAddressLabel.setObjectName(u"startAddressLabel")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.startAddressLabel)

        self.startAddressLineEdit = QLineEdit(self.centralwidget)
        self.startAddressLineEdit.setObjectName(u"startAddressLineEdit")
        self.startAddressLineEdit.setReadOnly(True)

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.startAddressLineEdit)

        self.archLabel = QLabel(self.centralwidget)
        self.archLabel.setObjectName(u"archLabel")

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.archLabel)

        self.archLineEdit = QLineEdit(self.centralwidget)
        self.archLineEdit.setObjectName(u"archLineEdit")
        self.archLineEdit.setReadOnly(True)

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.archLineEdit)

        ElfViewer.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(ElfViewer)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 33))
        self.menu_File = QMenu(self.menubar)
        self.menu_File.setObjectName(u"menu_File")
        ElfViewer.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(ElfViewer)
        self.statusbar.setObjectName(u"statusbar")
        ElfViewer.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menu_File.menuAction())
        self.menu_File.addAction(self.action_Open)

        self.retranslateUi(ElfViewer)

        QMetaObject.connectSlotsByName(ElfViewer)
    # setupUi

    def retranslateUi(self, ElfViewer):
        ElfViewer.setWindowTitle(QCoreApplication.translate("ElfViewer", u"Elf Viewer", None))
        self.action_Open.setText(QCoreApplication.translate("ElfViewer", u"&Open...", None))
        ___qtreewidgetitem = self.sectionsWidget.headerItem()
        ___qtreewidgetitem.setText(3, QCoreApplication.translate("ElfViewer", u"Type", None))
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("ElfViewer", u"Size", None))
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("ElfViewer", u"Start Address", None))
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("ElfViewer", u"Name", None))
        self.parseElfBtn.setText(QCoreApplication.translate("ElfViewer", u"Parse Elf File", None))
        self.startAddressLabel.setText(QCoreApplication.translate("ElfViewer", u"Start Address", None))
        self.archLabel.setText(QCoreApplication.translate("ElfViewer", u"Arch", None))
        self.menu_File.setTitle(QCoreApplication.translate("ElfViewer", u"&File", None))
    # retranslateUi

