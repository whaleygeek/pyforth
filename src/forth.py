# forth.py  25/12/2015  D.J.Whale
#
# An experiment to write a minimal FORTH language in Python
#
# Inspired by:
# http://angg.twu.net/miniforth-article.html


# inner interpreter - will interpret bytecodes
# outer interpreter - will interpret text

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


#class TextParser # the outer interpreter
#class CodeRunner # the inner interpreter


def run():
    f = Forth()
    f.run()

if __name__ == "__main__":
    run()

# END
