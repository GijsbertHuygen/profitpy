#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2007 Troy Melhase <troy@gci.net>
# Distributed under the terms of the GNU General Public License v2


from PyQt4.QtGui import QTableWidget


class LocalTable(QTableWidget):
    def __init__(self, parent=None):
        QTableWidget.__init__(self, parent)
        self.resizedColumns = []

    def resizeColumnToContents(self, column):
        if column not in self.resizedColumns:
            self.resizedColumns.append(column)
            QTableWidget.resizeColumnToContents(self, column)

    def iterrows(self):
        cols = [i for i in range(self.columnCount())]
        for i in xrange(self.rowCount()):
            items = [self.item(i, c) for c in cols]
            yield items
