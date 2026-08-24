# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'a2l.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QGridLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMenu,
    QMenuBar, QPushButton, QSizePolicy, QStatusBar,
    QTreeWidget, QTreeWidgetItem, QWidget)

class Ui_A2LViewer(object):
    def setupUi(self, A2LViewer):
        if not A2LViewer.objectName():
            A2LViewer.setObjectName(u"A2LViewer")
        A2LViewer.resize(800, 666)
        self.action_Load_A2L = QAction(A2LViewer)
        self.action_Load_A2L.setObjectName(u"action_Load_A2L")
        self.centralwidget = QWidget(A2LViewer)
        self.centralwidget.setObjectName(u"centralwidget")
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.openA2LFileBtn = QPushButton(self.centralwidget)
        self.openA2LFileBtn.setObjectName(u"openA2LFileBtn")

        self.gridLayout.addWidget(self.openA2LFileBtn, 1, 3, 1, 1)

        self.a2lTree = QTreeWidget(self.centralwidget)
        self.a2lTree.setObjectName(u"a2lTree")
        self.a2lTree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.a2lTree.setAlternatingRowColors(True)
        self.a2lTree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.a2lTree.setSortingEnabled(True)

        self.gridLayout.addWidget(self.a2lTree, 3, 0, 6, 5)

        self.a2lFileLabel = QLabel(self.centralwidget)
        self.a2lFileLabel.setObjectName(u"a2lFileLabel")

        self.gridLayout.addWidget(self.a2lFileLabel, 1, 0, 1, 1)

        self.a2lFileLineEdit = QLineEdit(self.centralwidget)
        self.a2lFileLineEdit.setObjectName(u"a2lFileLineEdit")

        self.gridLayout.addWidget(self.a2lFileLineEdit, 1, 1, 1, 1)

        self.parseFileButton = QPushButton(self.centralwidget)
        self.parseFileButton.setObjectName(u"parseFileButton")

        self.gridLayout.addWidget(self.parseFileButton, 10, 1, 1, 1)

        A2LViewer.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(A2LViewer)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 33))
        self.menu_File = QMenu(self.menubar)
        self.menu_File.setObjectName(u"menu_File")
        A2LViewer.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(A2LViewer)
        self.statusbar.setObjectName(u"statusbar")
        A2LViewer.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menu_File.menuAction())
        self.menu_File.addAction(self.action_Load_A2L)

        self.retranslateUi(A2LViewer)

        QMetaObject.connectSlotsByName(A2LViewer)
    # setupUi

    def retranslateUi(self, A2LViewer):
        A2LViewer.setWindowTitle(QCoreApplication.translate("A2LViewer", u"A2L Viewer", None))
        self.action_Load_A2L.setText(QCoreApplication.translate("A2LViewer", u"&Load A2L...", None))
#if QT_CONFIG(statustip)
        self.action_Load_A2L.setStatusTip(QCoreApplication.translate("A2LViewer", u"Load A2L File", None))
#endif // QT_CONFIG(statustip)
        self.openA2LFileBtn.setText(QCoreApplication.translate("A2LViewer", u"Open File", None))
        ___qtreewidgetitem = self.a2lTree.headerItem()
        ___qtreewidgetitem.setText(3, QCoreApplication.translate("A2LViewer", u"Description", None))
        ___qtreewidgetitem.setText(2, QCoreApplication.translate("A2LViewer", u"Address / Value", None))
        ___qtreewidgetitem.setText(1, QCoreApplication.translate("A2LViewer", u"Type", None))
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("A2LViewer", u"Name", None))
        self.a2lFileLabel.setText(QCoreApplication.translate("A2LViewer", u"A2L File", None))
        self.parseFileButton.setText(QCoreApplication.translate("A2LViewer", u"Parse", None))
        self.menu_File.setTitle(QCoreApplication.translate("A2LViewer", u"&File", None))
    # retranslateUi

