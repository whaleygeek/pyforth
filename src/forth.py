# forth.py  25/12/2015  D.J.Whale
#
# An experiment to write a minimal FORTH language in Python
#
# Inspired by:
# http://angg.twu.net/miniforth-article.html

import re


#----- STACK ------------------------------------------------------------------

class Stack():
    def size(self):
        pass

    def push(self, item):
        pass

    def pop(self):
        pass

    def top(self):
        pass

    def __setattr__(self, key, value):
        pass

    def __getattr__(self, item):
        pass


#----- INNER BYTECODE INTERPRETER ---------------------------------------------

class Inner():
    dict = Stack()
    rs   = Stack()
    ds   = Stack()
    memory = []

    def next(self):
        pass


#----- OUTER TEXT INTERPRETER -------------------------------------------------

class Parser():
    pos = 0
    line = ""

    def next(self):
        pass

    def parsebypattern(self, pat):
        capture, newpos = re.match(self.line, pat, self.pos)
        if newpos:
            self.pos = newpos;
            return capture

    def parsespaces(self):
        return self.parsebypattern("^([ \t]*)()")

    def parseword(self):
        return self.parsebypattern("^([^ \t\n]+)()")

    def parsenewline(self):
        return self.parsebypattern("^(\n)()")

    def parserestofline(self):
        return self.parsebypattern("^([^\n]*)()")

    def parsewordornewline(self):
        return self.parseword() or self.parsenewline()

    def getword(self):
        self.parsespaces()
        return self.parseword()

    def getwordornewline(self):
        self.parsespaces()
        return self.parsewordornewline()


#----- FORTH LANGUAGE ---------------------------------------------------------

class Forth:
    INTERPRET = "interpret"
    STOP      = "stop"
    HEAD      = "head"
    LIT       = "lit"
    FORTH     = "forth"

    mode      = INTERPRET

    def run(self):
        while self.mode != self.STOP:
            m = getattr(self, self.mode)
            m()

    def interpret(self):
        print("will run interpreter here")
        self.mode = self.STOP

    def head(self):
        print("unimplemented mode:head")

    def forth(self):
        print("unimplemented mode:forth")

    def lit(self):
        print("unimplemented mode:lit")


#----- RUNNER -----------------------------------------------------------------

def run():
    f = Forth()
    f.run()

if __name__ == "__main__":
    run()

# END
