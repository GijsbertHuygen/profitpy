#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2007 Troy Melhase
# Distributed under the terms of the GNU General Public License v2
# Author: Troy Melhase <troy@gci.net>

""" an interactive shell control

Based on PyCute, Copyright Gerard Vermeulen
Based on Eric3, Copyright Detlev Offenbach
Based on OpenAlea, Copyright Samuel Dufour-Kowalski, Christophe Pradal

"""
import sys
from code import InteractiveInterpreter
from itertools import cycle
from os.path import exists, expanduser
from traceback import extract_tb, format_exception_only, format_list

from PyQt4.QtCore import Qt, QString
from PyQt4.QtGui import QApplication, QBrush, QColor, QFont, QTextCursor, QTextEdit

from profit.lib import Signals


class PythonInterpreter(InteractiveInterpreter):
    """ PythonInterpreter(...) -> InteractiveInterpreter with an output target

    """
    def __init__(self, output, locals=None):
        InteractiveInterpreter.__init__(self, locals=locals)
        self.output = output
        
    def showtraceback(self):
        """ Display the exception that just occurred.

        We remove the first stack item because it is our own code.

        The output is written by self.write(), below.
        """
        try:
            type, value, tb = sys.exc_info()
            sys.last_type = type
            sys.last_value = value
            sys.last_traceback = tb
            tblist = extract_tb(tb)
            del tblist[:1]
            seq = format_list(tblist)
            if seq:
                seq.insert(0, 'Traceback (most recent call last):\n')
            seq[len(seq):] = format_exception_only(type, value)
        finally:
            tblist = tb = None
        for line, color in zip(seq, cycle(('#0000cc', '#0000cc', '#cc0000'))):
            #format = self.output.currentCharFormat()
            #format.setForeground(QBrush(QColor(color)))
            #self.output.setCurrentCharFormat(format)
            self.write(line)

    def update(self, **kwds):
        self.locals.update(kwds)

class PythonShell(QTextEdit):
    """ PythonShell(...) -> python shell widget

    """
    eofPrompt = 'Use Alt-F4 (i.e. Close Window) to exit.'
    historyName = '~/.profitdevice/shellhistory'
    startScriptName = '~/.profitdevice/autostart.py'
    maxHistory = 200
    introText = (
        'Python %s on %s\n' % (sys.version, sys.platform),
        'Type "copyright", "credits" or "license" for more information on Python.\n',
    )
    ps1 = '>>> '
    ps2 = '... '
            
    def __init__(self, parent, stdout, stderr):
        QTextEdit.__init__(self, parent)

        sys.stdout.extend([stdout, self])
        sys.stderr.extend([stderr, self])
        
        self.line = QString()
        self.lines = []
        self.history = []
        self.point = self.more = self.reading = self.pointer = self.pos = 0
        self.setupInterp()        
        self.setupUi()
        self.readShellHistory()
        self.writeBanner()
        self.connect(QApplication.instance(), Signals.lastWindowClosed,
                     self.writeShellHistory)
        
    def setupInterp(self):
        self.interp = PythonInterpreter(output=sys.stderr)
        self.interp.update(shell=self, quit=self.eofPrompt, exit=self.eofPrompt)
        
    def setupUi(self):
        font = QFont(self.font())
        font.setFamily("Bitstream Vera Sans Mono")
        font.setPointSize(10)
        font.setWeight(50)
        font.setBold(False)
        self.setFont(font)
        self.setLineWrapMode(self.NoWrap)
        self.setUndoRedoEnabled(False) ## big performance hit otherwise

    def flush(self):
        pass
    
    def writeBanner(self):
        self.setText('')
        self.write(str.join('', self.introText + (self.ps1, )))

    def readShellHistory(self):
        self.historyName = name = expanduser(self.historyName)
        if exists(name):
            hist = open(name, 'r')
            lines = [line for line in hist.readlines() if line.strip()]
            self.history.extend([QString(line) for line in lines])
            hist.close()
        else:
            try:
                hist = open(name, 'w')
                hist.close()
            except (IOError, ), exc:
                sys.__stdout__.write('%s\n' % (exc, ))

    def writeShellHistory(self):
        try:
            history = [str(hl) for hl in self.history[-self.maxHistory:]]
            history = [hl.strip() for hl in history if hl.strip()]
            history = ['%s\n' % (hl, ) for hl in history if hl]
            histfile = open(self.historyName, 'w')
            histfile.writelines(history)
            histfile.close()
        except (Exception, ), exc:
            sys.__stdout__.write('%s\n' % (exc, ))

    def write(self, text):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.pos = cursor.position()
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        
    def run(self):
        self.pointer = 0
        linestr = str(self.line)
        if linestr:
            self.history.append(QString(linestr))
        self.lines.append(linestr)
        source = str.join('\n', self.lines)
        try:
            self.more = self.interp.runsource(source)
        except (SystemExit, ):
            print Exception('SystemExit attempted but not allowed')
            self.more = None
        if self.more:
            self.write(self.ps2)
        else:
            self.write(self.ps1)
            self.lines = []
        self.clearLine()

    def clearLine(self):
        self.point = 0        
        self.line.truncate(0)

    def insertPlainText(self, text):
        cursor = self.textCursor()
        cursor.insertText(text)
        self.line.insert(self.point, text)
        self.point += text.length()

    def keyPressEvent(self, e):
        key, text, mods  = e.key(), e.text(), e.modifiers()
        cursor = self.textCursor()
        control = (mods & Qt.ControlModifier)

        if control:
            if key==Qt.Key_L:
                self.clear()
            elif key==Qt.Key_C:
                self.copy()
            elif key==Qt.Key_V:
                self.paste()
            elif key==Qt.Key_D:
                self.write(self.eofPrompt + '\n')
                self.run()
            elif key==Qt.Key_A:
                self.point = 0                
                cursor.setPosition(self.pos)
                self.setTextCursor(cursor)
            elif key==Qt.Key_E:
                self.point = self.line.length()                 
                self.moveCursor(QTextCursor.EndOfLine)
            return
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            self.write('\n')
            if self.reading:
                self.reading = 0
            else:
                self.run()
        elif key==Qt.Key_Tab:
            self.insertPlainText(text)
        elif key==Qt.Key_Backspace and self.point:
            cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            self.point -= 1 
            self.line.remove(self.point, 1)
        elif key==Qt.Key_Delete:
            cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            self.line.remove(self.point, 1)
        elif key==Qt.Key_Left and self.point:
            self.point -= 1 
            self.moveCursor(QTextCursor.Left)
        elif key==Qt.Key_Right and (self.point < self.line.length()):
            self.point += 1 
            self.moveCursor(QTextCursor.Right)
        elif key==Qt.Key_Home:
            cursor.setPosition(self.pos)
            self.point = 0            
            self.setTextCursor(cursor)
        elif key==Qt.Key_End:
            self.point = self.line.length() 
            self.moveCursor(QTextCursor.EndOfLine)
        elif key==Qt.Key_Up and self.history:
            if self.pointer==0:
                self.pointer = len(self.history)
            self.pointer -= 1
            self.recall()
        elif key==Qt.Key_Down and self.history:
            self.pointer += 1
            if self.pointer==len(self.history):
                self.pointer = 0
            self.recall()
        elif text.length():
            self.insertPlainText(text)
        else:
            e.ignore()
            
    def recall(self):
        cursor = self.textCursor()
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        if self.more:
            self.write(self.ps2)
        else:
            self.write(self.ps1)
        self.clearLine()
        self.insertPlainText(self.history[self.pointer])

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.moveCursor(QTextCursor.End)
            
    def clear(self):
        self.setPlainText('')


##
## these methods are for the main gui client
##
    def sessionToNamespace(self, session):
        shelld = self.interp.locals

        shelld['device'] = self.topLevelWidget()
        shelld['session'] = session
        shelld.update(session)
        for ((tid, tsym,), tobj,) in session.tickers.items():
            shelld[tsym] = tobj

    def onGuiComplete(self):
        """ onGuiComplete() -> a callback (not a slot) for startup-complete-ness

        """
        try:
            self.startScriptName = expanduser(self.startScriptName)
            startScriptName = file(self.startScriptName, 'r')
        except (IOError, ), ex:
            pass
        else:
            try:
                for line in startScriptName.readlines():
                    self.interp.runsource(line)
            except (SyntaxError, ValueError , OverflowError), ex: 
                print 'Compiling code in startup script failed: %s' % (ex, )
            except (Exception ,), ex:
                print 'Startup script failure (non-compile): %s' % (ex, )


class MultiCast(list):
    """ MultiCast() -> multiplexes messages to registered objects 

        MultiCast is based on Multicast by Eduard Hiti (no license stated):
        http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52289
    """
    def __init__(self, *items):
        list.__init__(self)
        self.extend(items)

    def __call__(self, *args, **kwargs):
        """ x.__call__(...) <==> x(...)

        map object calls to result as a MultiCast
        """
        itemreturns = [obj(*args, **kwargs) for obj in self]
        return self.__class__(*itemreturns)

    def __getattr__(self, name):
        """ x.__getattr__('name') <==> x.name

        returns attribute wrapper for further processing
        """
        attrs = [getattr(obj, name) for obj in self]
        return self.__class__(*attrs)

    def __nonzero__(self):
        """ x.__nonzero__() <==> x != 0

        logically true if all delegate values are logically true
        """
        return bool(reduce(lambda a, b: a and b, self, 1))


if not isinstance(sys.stdout, MultiCast):
    sys.stdout = MultiCast(sys.stdout)

if not isinstance(sys.stderr, MultiCast):
    sys.stderr = MultiCast(sys.stderr)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PythonShell()
    window.show()
    sys.exit(app.exec_())
    
