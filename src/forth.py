# forth.py  25/12/2015  D.J.Whale
#
# An experiment to write a minimal FORTH language in Python
#
# Inspired by:
# http://angg.twu.net/miniforth-article.html

# stack
# has:
#   push, pop, top

# inner interpreter - will interpret bytecodes
# has:
#   dictionary (of words, primitive and non primitive)
#   return stack
#   data stack
#   memory?? (for variables?)
#   next (run next bytecode in bytecode list)

# outer interpreter - will interpret text
# has:
#   parser:
#     line being parsed
#     pos on that line of next word
#     parsers: pattern, spaces, word, newline, restofline, wordornewline
#     getword, getwordornewline
#   interpreter:
#     interpretprimitive, interpretnonprimitive, interpretnumber

class Forth:
    INTERPRET = "interpret"
    STOP      = "stop"


    mode      = INTERPRET

    def run(self):
        while self.mode != self.STOP:
            m = getattr(self, self.mode)
            m()

    def interpret(self):
        print("will run interpreter here")
        self.mode = self.STOP

    #other modes to write
    #def head(self):
    #def forth(self):
    #def lit(self):


def run():
    f = Forth()
    f.run()

if __name__ == "__main__":
    run()

# END
