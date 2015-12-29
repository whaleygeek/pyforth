# forth.py  25/12/2015  D.J.Whale
#
# An experiment to write a minimal FORTH language on top of Python.
# The main purpose of this is to study the design of the FORTH language
# by attempting a modern implementation of it.
#
# The idea is to allow multiple simultaneous Forth context objects,
# perhaps with some shared data with copy-on-write semantics,
# so that core objects could be written in little Forth package
# objects, and integrated into a bigger system (so each Forth
# context is like a mini self-contained sandbox with it's own
# memory space and execution thread).


# BOOT REST OF LANGUAGE (do this in FORTH itself)
#   other compiler words
#   conditionals
#   other forth DS words
#   other forth RS words
#   other forth words

#----- MEMORY -----------------------------------------------------------------
#
# Access to a block of memory, basically a Python list.

class Memory():
    def __init__(self, size=65535):
        self.size = size
        self.mem = [0 for i in range(size)]

    def write(self, addr, value):
        self.mem[addr] = value

    def read(self, addr):
        return self.mem[addr]


#---- INPUT -------------------------------------------------------------------
#
# Interface to keyboard input

class Input():
    def __init__(self):
        pass

    def check(self):
        return True

    def read(self):
        return '*'


#----- OUTPUT -----------------------------------------------------------------
#
# Interface to screen output

class Output():
    def __init__(self):
        pass

    def write(self, ch):
        print("out:%s" % ch)


#----- DISK -------------------------------------------------------------------
#
# TODO: Probably an interface to reading and writing blocks in a nominated
# disk file image.

class Disk():
    def __init__(self):
        pass



#----- PYTHON WRAPPERS FOR FORTH DATA STRUCTURES -----------------------------------
#
# A useful abstraction to allow Python to meddle directly with Forth's
# data structure regions in memory. This is useful when you want to rewrite
# the implementation code for a WORD in Python to get better execution speed.

class SysVars():
    def __init__(self, mem, base, ptr, limit):
        pass
    # addr, create, read, write


class BlockBuffers():
    def __init__(self, mem, base, ptr, limit):
        pass
    # addr, read, write, erase
    # cache index


class Dictionary():
    def __init__(self, mem, base, ptr, limit):
        pass
    # addr, create, find, read, forget, here


class UserVars():
    def __init__(self, mem, base, ptr, limit):
        pass
    # addr. create, find, read, write


class ReturnStack():
    def __init__(self, mem, base, ptr, limit):
        pass
    # addr, push, pop, top, clear, size


class TextInputBuffer():
    def __init__(self, mem, base, ptr, limit):
        pass
    # addr, erase, read, write, advance, retard


class DataStack():
    def __init__(self, mem, base, ptr, limit):
        pass
    # addr, push, pop, top, clear, size


class Pad():
    def __init__(self, mem, base, ptr, limit):
        pass
    # addr, clear, read, write, advance, retard, reset, move?


#----- FORTH CONTEXT ----------------------------------------------------------
#
# The Forth language - knits everything together into one helpful object.

class Forth:
    mem    = Memory()
    input  = Input()
    output = Output()

    def region(self, name, at, size):
        # reserved for a later memory-map overlap error checker
        return at, at, size

    def boot(self):
        self.makeds()
        #self.boot_sys_vars() (including init of base/ptr vars of various regions)
        #self.boot_user_vars()
        #self.boot_native_words()
        #self.boot_forth_words()
        #self.boot_min_interpreter()
        #self.boot_min_compiler()
        #self.boot_min_editor()
        return self

    def makeds(self):
        # BOOT DATASTRUCTURES (base, ptr, limit for each)
        #TODO: Need a way to define this memory map as a single configuration
        #set of constants, that can be overriden with an external config file

        #   init sysvars
        svbase, svptr, svlimit = self.region("SV", at=0, size=1024)
        self.sv = SysVars(self.mem, svbase, svptr, svlimit)

        #   init block buffers
        bbbase, bbptr, bblimit = self.region("BB", at=65535-(1024*2), size=(1024*2))
        self.bb = BlockBuffers(self.mem, bbbase, bbptr, bblimit)

        #   init elective space??
        #elbase, elptr, ellimit = self.region("EL", at=, size=)

        #   init dictionary
        dictbase, dictptr, dictlimit = self.region("DICT", at=0, size=1024)
        self.dict = Dictionary(self.mem, dictbase, dictptr, dictlimit)

        #   init user variables (BASE, S0,...)
        uvbase, uvptr, uvlimit = self.region("UV", at=0, size=1024)
        self.uv = UserVars(self.mem, uvbase, uvptr, uvlimit)

        #   init return stack
        rsbase, rsptr, rslimit = self.region("RS", at=0, size=1024)
        self.rs = ReturnStack(self.mem, rsbase, rsptr, rslimit)

        #   init text input buffer
        tibbase, tibptr, tiblimit = self.region("TIB", at=0, size=1024)
        self.tib = TextInputBuffer(self.mem, tibbase, tibptr, tiblimit)

        #   init data stack
        dsbase, dsptr, dslimit = self.region("DS", at=0, size=1024)
        self.ds = DataStack(self.mem, dsbase, dsptr, dslimit)

        #   init pad
        padbase, padptr, padlimit = self.region("PAD", at=0, size=1024)
        self.pad = Pad(self.mem, padbase, padptr, padlimit)

    def boot_min_interpreter(self):
        # BOOT MIN INTERPRETER (some in FORTH, some in Python?)
        #   BYE
        #   BL CR . ." EMIT
        #   RESET ABORT
        #   KEY? KEY
        #   FALSE TRUE BEGIN UNTIL
        #   WORD NUMBER
        #   EXPECT SPAN
        #   QUERY
        #   EXECUTE
        #   INTERPRET
        #   QUIT EXIT
        pass

    def boot_min_compiler(self):
        # BOOT MIN COMPILER (might do this in FORTH itself)
        #   , @ ,C VARIABLE
        #   CREATE
        #   <BUILDS DOES> COMPILE
        #   : ;
        pass

    def run(self):
        #NOTE: can boot() then clone(), and then customise and run() multiple clones
        # optionally load app?
        # run main interpreter loop (optionally in a thread?)
        # only gets here when see a 'BYE' command.
        print("warning: No interpreter yet")

#----- RUNNER -----------------------------------------------------------------

def test():
    f = Forth().boot()
    f.run()

if __name__ == "__main__":
    test()

# END
