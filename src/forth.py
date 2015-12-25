# forth.py  25/12/2015  D.J.Whale
#
# An experiment to write a minimal FORTH language in Python
#
# Inspired by:
# http://angg.twu.net/miniforth-article.html

class FinishedException(Exception):
    pass

class Mode:
    INTERPRET = "interpret"
    STOP      = "stop"

    current   = INTERPRET

    def interpret(self):
        print("will run interpreter here")
        self.current = self.STOP

    def stop(self):
        print("stopping")
        raise FinishedException


def run():
    mode = Mode()
    while True:
        method = getattr(mode, mode.current)
        method()


if __name__ == "__main__":
    try:
        run()
    except FinishedException:
        pass

# END
