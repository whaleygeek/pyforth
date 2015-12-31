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


#----- MEMORY -----------------------------------------------------------------
#
# Access to a block of memory, basically a Python list.

class Memory():
    def __init__(self, size):
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

    def readn(self, addr):
        """Read a cell sized 2 byte variable"""
        #TODO endianness BIG?
        value = self.mem[addr]<<8 + self.mem[addr+1]
        return value

    def readb(self, addr):
        """Read a 1 byte variable"""
        value = self.mem[addr]
        return value

    def readd(self, addr):
        """Read a double length variable (4 byte, 32 bits)"""
        #TODO endianness BIG?
        value = self.mem[addr]<<24 + self.mem[addr+1]<<16 + self.mem[addr+2]<<8 + self.mem[addr+3]
        return value

    def writen(self, addr, value):
        """Write a cell sized 2 byte variable"""
        #TODO endianness BIG??
        high = (value & 0xFF00)>>8
        low = (value & 0xFF)
        self.mem[addr] = high
        self.mem[addr+1] = low

    def writeb(self, addr, value):
        """Write a 1 byte variable"""
        low = (value & 0xFF)
        self.mem[addr] = low

    def writed(self, addr, value):
        """Write a double length variable (4 byte, 32 bits)"""
        byte0 = (value & 0xFF000000)>>24
        byte1 = (value & 0x00FF0000)>>16
        byte2 = (value & 0x0000FF00)>>8
        byte3 = (value & 0x000000FF)
        self.mem[addr]   = byte0
        self.mem[addr+1] = byte1
        self.mem[addr+2] = byte2
        self.mem[addr+3] = byte3


#----- PYTHON WRAPPERS FOR FORTH DATA STRUCTURES -----------------------------------
#
# A useful abstraction to allow Python to meddle directly with Forth's
# data structure regions in memory. This is useful when you want to rewrite
# the implementation code for a word in Python to get better execution speed.

class Vars():
    def __init__(self, mem, base, ptr, size):
        self.mem  = mem
        self.base = base
        self.ptr  = ptr
        self.size = size

    def create(self, size=2):
        """Create a new constant or variable of the given size in bytes"""
        addr = self.ptr
        self.ptr += size
        #TODO limit check?
        return addr

    def readn(self, addr):
        #TODO limit check?
        return self.mem.readn(addr)

    def readb(self, addr):
        #TODO limit check?
        return self.mem.readb(addr)

    def readd(self, addr):
        #TODO limit check?
        return self.mem.readd(addr)

    def writen(self, addr, value):
        #TODO limit check?
        self.mem.writen(addr, value)

    def writeb(self, addr, value):
        #TODO limit check?
        self.mem.writeb(addr, value)

    def writed(self, addr, value):
        #TODO limit check?
        self.mem.writed(addr, value)


class SysVars(Vars):
    def __init__(self, mem, start, size):
        Vars.__init__(self, mem, start, size)


class UserVars(Vars):
    def __init__(self, mem, start, size):
        Vars.__init__(self, mem, start, size)


class Dictionary():
    def __init__(self, mem, base, ptr, size):
        self.mem = mem
        self.base = base
        self.ptr = ptr
        self.size = size

    def create(self, name):
        pass

    def tick(self, name):
        pass

    def cfa(self, addr):
        pass

    def pfa(self, addr):
        pass

    def allot(self):
        pass

    def here(self):
        pass

    def forget(self, addr):
        pass


class Stack():
    def __init__(self, mem, base, ptr, size):
        self.mem  = mem
        self.base = base
        self.size = size
        self.ptr  = ptr

    def pushn(self, value):
        pass

    def pushb(self, value):
        pass

    def pushd(self, value):
        pass

    def popn(self):
        pass

    def popb(self):
        pass

    def popd(self):
        pass

    def getn(self, relindex):
        pass

    def getb(self, relindex):
        pass

    def getd(self, relindex):
        pass

    def setn(self, relindex, value):
        pass

    def setb(self, relindex, value):
        pass

    def setd(self, relindex, value):
        pass

    def clear(self):
        pass

    def dup(self):
        pass

    def swap(self):
        pass

    def rot(self):
        pass

    def over(self):
        pass

    def drop(self):
        pass


class DataStack(Stack):
    def __init__(self, mem, base, limit):
        Stack.__init__(self, base, limit)


class ReturnStack(Stack):
    def __init__(self, mem, base, limit):
        Stack.__init__(self, base, limit)


#class TextInputBuffer():
#    def __init__(self, mem, base, ptr, limit):
#        pass
#    # addr, erase, read, write, advance, retard


#class Pad():
#    def __init__(self, mem, base, ptr, limit):
#        pass
#    # addr, clear, read, write, advance, retard, reset, move?


#class BlockBuffers():
#    def __init__(self, mem, base, ptr, limit):
#        pass
#    # addr, read, write, erase
#    # cache index


#---- INPUT -------------------------------------------------------------------
#
# Interface to keyboard input

#class Input():
#    def __init__(self):
#        pass
#
#    def check(self):
#        return True
#
#    def read(self):
#        return '*'


#----- OUTPUT -----------------------------------------------------------------
#
# Interface to screen output

#class Output():
#    def __init__(self):
#        pass
#
#    def write(self, ch):
#        print(ch)


#----- DISK -------------------------------------------------------------------
#
# TODO: Probably an interface to reading and writing blocks in a nominated
# disk file image.

#class Disk():
#    def __init__(self):
#        pass


#----- FORTH CONTEXT ----------------------------------------------------------
#
# The Forth language - knits everything together into one helpful object.

class Forth:
    def boot(self):
        self.build_ds()
        self.build_nucleus()
        return self

    def build_ds(self):
        # BOOT DATASTRUCTURES (base, ptr, limit for each)
        MEM_SIZE  = 65536
        SV_MEM   = (0,               +1024      )
        #EL_MEM   = (1024,            +0         )
        DICT_MEM = (1024,            +1024      )
        #PAD_MEM  = (2048,            +80        )
        DS_MEM   = (8192,            -1024      ) # grows downwards
        #TIB_MEM  = (8192,            +80        )
        RS_MEM   = (16384,           -1024      ) # grows downwards
        #UV_MEM   = (16384,           +1024      )
        #BB_MEM   = (65536-(1024*2),  +(1024*2)  )

        self.mem = Memory(MEM_SIZE)

        #   init sysvars
        svbase, svptr, svlimit = self.mem.region("SV", SV_MEM)
        self.sv = SysVars(self.mem, svbase, svptr, svlimit)

        #   init elective space??
        #elbase, elptr, ellimit = self.region("EL", at=, size=)

        #   init dictionary
        dictbase, dictptr, dictlimit = self.mem.region("DICT", DICT_MEM)
        self.dict = Dictionary(self.mem, dictbase, dictptr, dictlimit)

        #   init pad
        #padbase, padptr, padlimit = self.mem.region("PAD", PAD_MEM)
        #self.pad = Pad(self.mem, padbase, padptr, padlimit)

        #   init data stack
        dsbase, dsptr, dslimit = self.mem.region("DS", DS_MEM)
        self.ds = DataStack(self.mem, dsbase, dsptr, dslimit)

        #   init text input buffer
        #tibbase, tibptr, tiblimit = self.mem.region("TIB", TIB_MEM)
        #self.tib = TextInputBuffer(self.mem, tibbase, tibptr, tiblimit)

        #   init return stack
        rsbase, rsptr, rslimit = self.mem.region("RS", RS_MEM)
        self.rs = ReturnStack(self.mem, rsbase, rsptr, rslimit)

        #   init user variables (BASE, S0,...)
        #uvbase, uvptr, uvlimit = self.mem.region("UV", UV_MEM)
        #self.uv = UserVars(self.mem, uvbase, uvptr, uvlimit)

        #   init block buffers
        #bbbase, bbptr, bblimit = self.mem.region("BB", BB_MEM)
        #self.bb = BlockBuffers(self.mem, bbbase, bbptr, bblimit)

        self.mem.show_map()

    def build_nucelus(self):
        class Native():
            def __init__(self, parent):
                self.parent = parent
                #sv   = parent.sv
                #dict = parent.dict
                #mem  = parent.mem

                # for CONST/VAR, allocate address in SV
                # 'memory-map' this address to a python function that returns that value when accessed
                # perhaps by just storing a python function at that address
                # note, will need to know data width of read/write to allow correct access

                # for CODE, memory map native function into a NUCLEUS region address in low memory
                # perhaps a 16 bit cell with a unique native number index in it
                # store python function in that mem[] cell that is called on read/write
                # note, will need to know data width of read/write to allow correct access

                # GROUP 1
                #   CONSTANT SV0   - address of start of system vars
                #     dict.create("SV0", link=dict.prev, cfa=@PFA, pfa=svbase)

                #   CONSTANT D0    - address of bottom of dict
                #     dict.create("D0", link=dict.prev, cfa=@PFA, pfa=dictbase)

                #   VARIABLE HERE  - address of dictionary pointer
                #     TODO

                #   CONSTANT S0    - address of bottom of data stack
                #     dict.create("S0", link=dict.prev, cfa=@PFA, pfa=dsbase)

                #   VARIABLE SP    - address of data stack pointer
                #     TODO

                #   CONSTANT 0     - value 0
                #     dict.create("0", link=dict.prev, cfa=@PFA, pfa=0)

                #   CONSTANT 1     - value 1
                #     dict.create("1", link=dict.prev, cfa=@PFA, pfa=1)

                #   CONSTANT R0    - address of bottom of return stack
                #     dict.create("R0", link=dict.prev, cfa=@PFA, pfa=rsbase)

                #   VARIABLE RP    - address of return stack pointer
                #     TODO

                #   VARIABLE IP    - address of next instruction to interpret
                #     TODO

                #   CODE !         - address of "store single number into addr'
                #     TODO

                #   CODE @         - address of "fetch from address"
                #     TODO

        self.native = Native(self)
        # any value stored in mem[] that is a python function, is called, to read/write said value
        # implies need to know if read/write and if width is 8/16/32
        # 4 individual byte accesses vs 1 32 bit word access need to set/get same data
        # in a 'safe' way?



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
