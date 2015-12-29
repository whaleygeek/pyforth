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
        self.map = []

    def region(self, name, spec):
        size  = spec[1]
        if size < 0:
            # grows down towards low memory
            start = spec[0] - -size
        else:
            # grows up towards high memory
            start = spec[0]
        ptr = spec[0]
        end = start + size

        # check for overlaps with an existing region
        for i in self.map:
            iname, istart, isize = i
            iend = istart + isize-1
            if (start >= istart and start <= iend) or (end >= istart and end <= iend):
                raise ValueError("Region %s overlaps with %s" % (name, iname))

        self.map.append((name, start, abs(size)))
        return start, ptr, end

    def show_map(self):
        last_end = 0
        for i in self.map:
            name, start, size = i
            if start != last_end:
                uname  = "UNUSED"
                ustart = last_end
                uend   = start-1
                usize  = uend-ustart-1
                print("%10s %5d %5d %5d" %(uname, ustart, uend, usize))
            print("%10s %5d %5d %5d" % (name, start, start+size-1, size))
            last_end = start + size

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

        SV_MEM   = (0,               +1024      )
        EL_MEM   = (1024,            +0         )
        DICT_MEM = (1024,            +1024      )
        PAD_MEM  = (2048,            +80        )
        DS_MEM   = (8192,            -1024      ) # grows downwards
        TIB_MEM  = (8192,            +80        )
        RS_MEM   = (16384,           -1024      ) # grows downwards
        UV_MEM   = (16384,           +1024      )
        BB_MEM   = (65536-(1024*2),  +(1024*2)  )

        #   init sysvars
        svbase, svptr, svlimit = self.mem.region("SV", SV_MEM)
        self.sv = SysVars(self.mem, svbase, svptr, svlimit)

        #   init elective space??
        #elbase, elptr, ellimit = self.region("EL", at=, size=)

        #   init dictionary
        dictbase, dictptr, dictlimit = self.mem.region("DICT", DICT_MEM)
        self.dict = Dictionary(self.mem, dictbase, dictptr, dictlimit)

        #   init pad
        padbase, padptr, padlimit = self.mem.region("PAD", PAD_MEM)
        self.pad = Pad(self.mem, padbase, padptr, padlimit)

        #   init data stack
        dsbase, dsptr, dslimit = self.mem.region("DS", DS_MEM)
        self.ds = DataStack(self.mem, dsbase, dsptr, dslimit)

        #   init text input buffer
        tibbase, tibptr, tiblimit = self.mem.region("TIB", TIB_MEM)
        self.tib = TextInputBuffer(self.mem, tibbase, tibptr, tiblimit)

        #   init return stack
        rsbase, rsptr, rslimit = self.mem.region("RS", RS_MEM)
        self.rs = ReturnStack(self.mem, rsbase, rsptr, rslimit)

        #   init user variables (BASE, S0,...)
        uvbase, uvptr, uvlimit = self.mem.region("UV", UV_MEM)
        self.uv = UserVars(self.mem, uvbase, uvptr, uvlimit)

        #   init block buffers
        bbbase, bbptr, bblimit = self.mem.region("BB", BB_MEM)
        self.bb = BlockBuffers(self.mem, bbbase, bbptr, bblimit)

        self.mem.show_map()

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
