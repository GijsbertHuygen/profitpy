#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2007 Troy Melhase <troy@gci.net>
# Distributed under the terms of the GNU General Public License v2

from functools import partial
from time import ctime

from PyQt4.QtCore import QAbstractTableModel, QVariant, Qt, pyqtSignature
from PyQt4.QtGui import QBrush, QColor, QColorDialog, QIcon, QFrame, QMenu
from PyQt4.QtGui import QPixmap, QSortFilterProxyModel

from ib.opt.message import registry

from profit.lib import Signals, nogc
from profit.widgets.ui_messagedisplay import Ui_MessageDisplay


def messageTypeNames():
    """ Builds set of message type names.

    @return set of all message type names as strings
    """
    return set([t.__name__ for t in registry.values()])


def messageRow(index, mtuple):
    """ Extracts the row number from an index and its message.

    @param index QModelIndex instance
    @param mtuple two-tuple of (message time, message object)
    @return row number as integer
    """
    return index.row()


def messageTime(index, (mtime, message)):
    """ Extracts the message time from an index and its message.

    @param index QModelIndex instance
    @param mtime message time as float
    @param message message instance
    @return mtime formatted with ctime call
    """
    return ctime(mtime)


def messageName(index, (mtime, message)):
    """ Extracts the type name from an index and its message.

    @param index QModelIndex instance
    @param mtime message time as float
    @param message message instance
    @return type name of message as string
    """
    return message.__class__.__name__


def messageText(index, (mtime, message)):
    """ Extracts the items from an index and its message.

    @param index QModelIndex instance
    @param mtime message time as float
    @param message message instance
    @return message string formatted with message key=value pairs
    """
    return str.join(', ', ['%s=%s' % (k, v) for k, v in message.items()])


class MessagesTableModel(QAbstractTableModel):
    """ Data model for session messages.

    """
    columnTitles = ['Index', 'Time', 'Type', 'Fields']
    dataExtractors = {0:messageRow, 1:messageTime,
                      2:messageName, 3:messageText}

    def __init__(self, session, brushes, parent=None):
        """ Constructor.

        @param session Session instance
        @param brushes mapping of typenames to foreground brushes
        @param parent ancestor object
        """
        QAbstractTableModel.__init__(self, parent)
        self.brushes = brushes
        self.setSession(session)

    def setSession(self, session):
        """ Saves reference to session.

        @param session Session instance
        @return None
        """
        self.session = session
        self.messages = session.messages

    def data(self, index, role):
        """ Framework hook to determine data stored at index for given role.

        @param index QModelIndex instance
        @param role Qt.DisplayRole flags
        @return QVariant instance
        """
        if not index.isValid():
            return QVariant()
        message = self.messages[index.row()]
        if role == Qt.ForegroundRole:
            return QVariant(self.brushes[message[1].__class__.__name__])
        if role != Qt.DisplayRole:
            return QVariant()
        try:
            val = self.dataExtractors[index.column()](index, message)
            val = QVariant(val)
        except (KeyError, ):
            val = QVariant()
        return val

    def headerData(self, section, orientation, role):
        """ Framework hook to determine header data.

        @param section integer specifying header (e.g., column number)
        @param orientation Qt.Orientation value
        @param role Qt.DisplayRole flags
        @return QVariant instance
        """
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.columnTitles[section])
        return QVariant()

    def rowCount(self, parent=None):
        """ Framework hook to determine data model row count.

        @param parent ignored
        @return number of rows (message count)
        """
        return len(self.messages)

    def columnCount(self, parent=None):
        """ Framework hook to determine data model column count.

        @param parent ignored
        @return number of columns (see columnTitles)
        """
        return len(self.columnTitles)


class MessagesFilterModel(QSortFilterProxyModel):
    """ Filters messages from display.

    """
    def __init__(self, session, types, parent=None):
        """ Constructor.

        @param session Session instance
        @param types set of typenames for display
        @param parent ancestor object
        """
        QSortFilterProxyModel.__init__(self, parent)
        self.session = session
        self.messages = session.messages
        self.types = types

    def filterAcceptsRow(self, row, index):
        """ Framework hook to control row visibility

        @param row row number as integer
        @param index QModelIndex instance (ignored)
        @return True if message should be displayed, False if not
        """
        msg = self.messages[row][1]
        return msg.__class__.__name__ in self.types


class MessageDisplay(QFrame, Ui_MessageDisplay):
    """ Table view of session messages with nifty controls.

    """
    pauseButtonIcons = {
        True:':/images/icons/player_play.png',
        False:':/images/icons/player_pause.png',
    }

    pauseButtonText = {
        True:'Resume',
        False:'Pause',
    }

    def __init__(self, session, parent=None):
        """ Constructor.

        @param session instance of Session
        @param parent ancestor of this widget
        """
        QFrame.__init__(self, parent)
        self.setupUi(self)
        self.paused = False
        self.messageTable.verticalHeader().hide()
        self.setupModel(session)
        self.setupColorButton()
        self.setupDisplayButton()
        session.registerAll(self.on_sessionMessage)

    def colorIcon(self, color, width=10, height=10):
        """ Creates an icon filled with color.

        @param color QColor instance
        @param width width of icon in pixels
        @param height of icon in pixels
        @return QIcon instance
        """
        pixmap = QPixmap(width, height)
        pixmap.fill(color)
        return QIcon(pixmap)

    def setupColorButton(self):
        """ Configures the color highlight button.

        @return None
        """
        self.colorPop = pop = QMenu(self.colorButton)
        self.colorButton.setMenu(pop)
        self.colorTypes = messageTypeNames()
        self.colorActions = actions = \
            [pop.addAction(v) for v in sorted(self.colorTypes)]
        for action in actions:
            action.color = color = QColor(0,0,0)
            action.setIcon(self.colorIcon(color))
            target = nogc(partial(self.on_colorChange, action=action))
            self.connect(action, Signals.triggered, target)
        self.brushMap.update(
            dict([(str(a.text()), QBrush(a.color)) for a in actions])
            )

    def setupDisplayButton(self):
        """ Configures the display types button.

        @return None
        """
        self.displayPop = pop = QMenu(self.displayButton)
        self.displayButton.setMenu(pop)
        self.displayActions = actions = []
        allAction = pop.addAction('All')
        actions.append(allAction)
        pop.addSeparator()
        actions.extend([pop.addAction(v) for v in sorted(self.displayTypes)])
        for action in actions:
            action.setCheckable(True)
            target = nogc(partial(self.on_displayChange, action=action))
            self.connect(action, Signals.triggered, target)
        allAction.setChecked(True)

    def setupModel(self, session):
        self.messages = session.messages
        self.brushMap = brushes = {}
        self.dataModel = MessagesTableModel(session, brushes, self)
        self.displayTypes = types = messageTypeNames()
        self.proxyModel = MessagesFilterModel(session, types, self)
        self.proxyModel.setSourceModel(self.dataModel)
        self.messageTable.setModel(self.proxyModel)

    def on_colorChange(self, action):
        """ Signal handler for color change actions.

        @param QAction instance
        @return None
        """
        color = QColorDialog.getColor(action.color, self)
        if color.isValid():
            action.color = color
            action.setIcon(self.colorIcon(color))
            self.brushMap[str(action.text())] = QBrush(color)
            self.proxyModel.reset()

    def on_displayChange(self, action):
        """ Signal handler for display types actions.

        @param QAction instance
        @return None
        """
        index = self.displayActions.index(action)
        allAction = self.displayActions[0]
        allChecked = allAction.isChecked()
        actionChecked = action.isChecked()
        if allChecked and action is not allAction:
            allAction.setChecked(False)
            self.displayTypes.clear()
            self.displayTypes.add(str(action.text()))
        elif allChecked and action is allAction:
            self.displayTypes.clear()
            self.displayTypes.update(messageTypeNames())
            for act in self.displayActions[1:]:
                act.setChecked(False)
        elif not allChecked and action is allAction:
            self.displayTypes.clear()
        elif not allChecked and action is not allAction:
            text = str(action.text())
            if actionChecked:
                self.displayTypes.add(text)
            else:
                self.displayTypes.discard(text)
        self.proxyModel.reset()

    @pyqtSignature('bool')
    def on_pauseButton_clicked(self, checked=False):
        """ Signal handler for pause button.

        @param checked toggled state of button
        @return None
        """
        self.paused = checked
        self.pauseButton.setText(self.pauseButtonText[checked])
        self.pauseButton.setIcon(QIcon(self.pauseButtonIcons[checked]))
        self.on_sessionMessage(None)

    def on_sessionMessage(self, message):
        """ Signal handler for incoming messages.

        @param message message instance
        @return None
        """
        if not self.paused:
            self.dataModel.emit(Signals.layoutChanged)
            self.messageTable.scrollToBottom()
