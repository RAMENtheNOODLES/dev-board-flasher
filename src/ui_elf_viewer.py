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
from PySide6.QtWidgets import (QApplication, QGridLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QSpacerItem, QStatusBar,
    QTreeWidget, QTreeWidgetItem, QWidget)

class Ui_ElfViewer(object):
    def setupUi(self, ElfViewer):
        if not ElfViewer.objectName():
            ElfViewer.setObjectName(u"ElfViewer")
        ElfViewer.resize(800, 514)
        self.action_Open = QAction(ElfViewer)
        self.action_Open.setObjectName(u"action_Open")
        self.centralwidget = QWidget(ElfViewer)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.archLineEdit = QLineEdit(self.centralwidget)
        self.archLineEdit.setObjectName(u"archLineEdit")
        self.archLineEdit.setReadOnly(True)

        self.gridLayout.addWidget(self.archLineEdit, 4, 1, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.gridLayout.addItem(self.verticalSpacer, 2, 1, 1, 1)

        self.startAddressLabel = QLabel(self.centralwidget)
        self.startAddressLabel.setObjectName(u"startAddressLabel")

        self.gridLayout.addWidget(self.startAddressLabel, 3, 0, 1, 1)

        self.startAddressLineEdit = QLineEdit(self.centralwidget)
        self.startAddressLineEdit.setObjectName(u"startAddressLineEdit")
        self.startAddressLineEdit.setReadOnly(True)

        self.gridLayout.addWidget(self.startAddressLineEdit, 3, 1, 1, 1)

        self.elfFileLineEdit = QLineEdit(self.centralwidget)
        self.elfFileLineEdit.setObjectName(u"elfFileLineEdit")

        self.gridLayout.addWidget(self.elfFileLineEdit, 0, 1, 1, 1)

        self.archLabel = QLabel(self.centralwidget)
        self.archLabel.setObjectName(u"archLabel")

        self.gridLayout.addWidget(self.archLabel, 4, 0, 1, 1)

        self.elfFileLabel = QLabel(self.centralwidget)
        self.elfFileLabel.setObjectName(u"elfFileLabel")

        self.gridLayout.addWidget(self.elfFileLabel, 0, 0, 1, 1)

        self.openFileBtn = QPushButton(self.centralwidget)
        self.openFileBtn.setObjectName(u"openFileBtn")

        self.gridLayout.addWidget(self.openFileBtn, 0, 2, 1, 1)

        self.sectionsWidget = QTreeWidget(self.centralwidget)
        self.sectionsWidget.setObjectName(u"sectionsWidget")

        self.gridLayout.addWidget(self.sectionsWidget, 5, 0, 1, 3)

        self.parseElfBtn = QPushButton(self.centralwidget)
        self.parseElfBtn.setObjectName(u"parseElfBtn")

        self.gridLayout.addWidget(self.parseElfBtn, 2, 2, 1, 1)

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
#if QT_CONFIG(statustip)
        self.action_Open.setStatusTip(QCoreApplication.translate("ElfViewer", u"Open an elf file from disk to parse.", None))
#endif // QT_CONFIG(statustip)
        self.startAddressLabel.setText(QCoreApplication.translate("ElfViewer", u"Start Address", None))
        self.archLabel.setText(QCoreApplication.translate("ElfViewer", u"Arch", None))
        self.elfFileLabel.setText(QCoreApplication.translate("ElfViewer", u"ELF File", None))
#if QT_CONFIG(statustip)
        self.openFileBtn.setStatusTip(QCoreApplication.translate("ElfViewer", u"Open an elf file from disk to parse.", None))
#endif // QT_CONFIG(statustip)
        self.openFileBtn.setText(QCoreApplication.translate("ElfViewer", u"Open File", None))
        ___qtreewidgetitem = self.sectionsWidget.headerItem()
        ___qtreewidgetitem.setText(3, QCoreApplication.translate("ElfViewer", u"Type", None))
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("ElfViewer", u"Size", None))
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("ElfViewer", u"Start Address", None))
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("ElfViewer", u"Name", None))
#if QT_CONFIG(statustip)
        self.parseElfBtn.setStatusTip(QCoreApplication.translate("ElfViewer", u"Parse the currently loaded elf file.", None))
#endif // QT_CONFIG(statustip)
        self.parseElfBtn.setText(QCoreApplication.translate("ElfViewer", u"Parse Elf File", None))
        self.menu_File.setTitle(QCoreApplication.translate("ElfViewer", u"&File", None))
    # retranslateUi

