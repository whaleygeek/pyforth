# forth.py  25/12/2015  D.J.Whale
#
# An experiment to write a minimal FORTH language in Python
#
# Inspired by:
# http://angg.twu.net/miniforth-article.html


# Remember the following
# at the interpreter, all words are passed to INTERPRET
# : is just another word, it passes up to ; to the code stored against : (compiler)
# if a word is not found in the dictionary, it is passed to NUMBER
# NUMBER is just a forth word that tries to parse numbers.
# . emits top of stack
# ( ) comments - stack effects are ( -- )
# ." msg" is a string


import re


#----- STACK ------------------------------------------------------------------
#
# A generic stack (for things like the return-stack, arithmetic-stack)

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

    #TODO: stack underflow exception


#----- DICTIONARY -------------------------------------------------------------
#
# A keyed dictionary (for storing words)

class Dictionary():
    pass
# add
# remove
# find(name)
# get(index)
# list

# Eventually will store a load of FORTH definitions in a file and load them
# on start. Also note that a dictionary entry can point to any of the following:
# pyfunction - function that implements a word natively
# head? head of a chain of dictionary indexes that make up a word
# items are stored in order of definition, this is a keyed stack, so
# later definitions of words override earlier definitions.
#
# note - check what happens if a word definition binds by index, it will not
# get the new word, this is probably correct forth semantics.


#----- OUTER TEXT INTERPRETER -------------------------------------------------
#
# The outer text interpreter, implements INTERPRET?
# really this is the word parser.

class Interpreter():
    pos = 0
    line = ""

    def next(self):
        pass # get the next word from interactive stream

    def parsebypattern(self, pat):
        capture, newpos = re.match(self.line, pat, self.pos)
        if newpos:
            self.pos = newpos
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


#----- NUMBER -----------------------------------------------------------------
#
# Number parser, implements NUMBER

class Number():
    pass


#---- COMPILER ----------------------------------------------------------------
#
# Compiler, implements ':' (i.e. appears in dictionary entry : only)
# compiles into a head, and associates that with a new word in the dictionary.

class Compiler():
    pass


#----- INNER BYTECODE INTERPRETER ---------------------------------------------
#
# Executor - executes a word from the dictionary
# which includes manipulating stacks and other types of memory
# looking up words by name and words by index in the dictionary

class Executor():
    rs   = Stack()
    ds   = Stack()
    memory = []

    def next(self):
        pass # get the next word reference along this chain from current head


#----- FORTH LANGUAGE ---------------------------------------------------------
#
# The Forth language - knits everything together into one helpful object.

class Forth:
    INTERPRET = "interpret"
    STOP      = "stop"
    HEAD      = "head"
    LIT       = "lit"
    FORTH     = "forth"

    mode      = INTERPRET
    dict      = Dictionary()
    inner     = Executor()
    outer     = Interpreter()

    def run(self):
        while self.mode != self.STOP:
            m = getattr(self, self.mode)
            m()

    # Not really sure about modes yet, need to read paper more carefully
    def interpret(self):
        print("will run interpreter here")
        # This is the command prompt that reads a line and passes to INTERPRET
        #TODO: Enter mode STOP if execute 'BYE'
        self.mode = self.STOP

    def head(self):
        # not quite sure what this is for yet, read paper fully.
        print("unimplemented mode:head")

    def forth(self):
        # is this the runtime? Isn't it just 'Executor'?
        print("unimplemented mode:forth")

    def lit(self):
        # if this implements the LIT command, does it need a state?
        print("unimplemented mode:lit")


#----- RUNNER -----------------------------------------------------------------

def run():
    f = Forth()
    f.run()

if __name__ == "__main__":
    run()

# END
