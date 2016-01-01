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

def error(msg):
    print(msg)
    import sys
    sys.exit()

def warning(msg):
    print("warning:%s" % str(msg))

def trace(msg):
    print(str(msg))


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

    def create(self, nf, cf=0, pf=[]):
        trace("dict.create: nf:%s cf:%d pf:%s" % (nf, cf, str(pf)))
        #TODO create new dict entry and link LF to PREV
        #adjust HERE pointer

    def tick(self, name):
        pass # TODO

    def cfa(self, addr):
        pass # TODO

    def pfa(self, addr):
        pass # TODO

    def allot(self):
        pass # TODO

    def here(self):
        pass # TODO

    def forget(self, addr):
        pass # TODO


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



#----- MACHINE ----------------------------------------------------------------
#
# The native machine simulation
# This is a minimal simulation, it could though simulate a complete CPU.

class Machine():
    def __init__(self, parent):
        self.parent = parent
        self.sv   = parent.sv
        self.dict = parent.dict
        self.mem  = parent.mem
        self.ds   = parent.ds
        self.rs   = parent.rs
        # need to expose these through mem[] holes for read/write access
        self.ip = 0
        self.dp = 0 # how does parent.ds get access to dp?
        self.rp = 0 # how does parent.rs get access to rp?

        # dispatch table for jsr(n)
        self.index = [
            ("NOP",    self.n_nop),
            ("STORE",  self.n_store),  # self.mem.store
            ("FETCH",  self.n_fetch),  # self.mem.fetch
            ("STORE8", self.n_store8), # self.mem.store8
            ("FETCH8", self.n_fetch8), # self.mem.fetch8
            ("ADD",    self.n_add),
            ("SUB",    self.n_sub),
            ("AND",    self.n_and),
            ("OR",     self.n_or),
            ("XOR",    self.n_xor),
            ("MULT",   self.n_mult),
            ("DIV",    self.n_div),
            ("MOD",    self.n_mod),
            ("FLAGS",  self.n_flags),
            ("SWAP",   self.ds.swap),
            ("DUP",    self.ds.dup),
            ("OVER",   self.ds.over),
            ("ROT",    self.ds.rot),
            ("DROP",   self.ds.drop),
            ("KEY",    self.n_key),    # self.in.key
            ("KEYQ",   self.n_keyq),   # self.in.keyq
            ("EMIT",   self.n_emit),   # self.out.emit
            ("RDPFA",  self.n_rdpfa),
            ("ADRUV",  self.n_adruv),  # self.uv.adruv
            ("BRANCH", self.n_branch),
            ("0BRANCH",self.n_0branch),
            ("NEXT",   self.n_next),
            ("EXIT",   self.n_exit),
            ("DODOES", self.n_dodoes),
            ("RBLK",   self.n_rblk),   # self.disk.rblk
            ("WBLK",   self.n_wblk)    # self.disk.wblk
        ]

    def n_nop(self):
        pass

    def n_store(self):
        #: n_STORE   ( n a -- )
        # { a=ds_pop; n0=ds_pop8; n1=ds_pop8; mem[a]=n0; mem[a+1]=n1} ;
        a = self.ds.popn()
        n0 = self.ds.popb()
        n1 = self.ds.popb()
        self.mem[a] = n0
        self.mem[a+1] = n1

    def n_fetch(self):
        #: n_FETCH  ( a -- n)
        # { a=ds_pop; n0=mem[a]; n1=mem[a+1]; ds_push8(n0); ds_push8(n1) } ;
        a = self.ds.popn()
        n0 = self.mem[a]
        n1 = self.mem[a+1]
        self.ds.pushb(n0)
        self.ds.pushb(n1)

    def n_store8(self):
        #: n_STORE8  ( b a -- )
        # { a=ds_pop; b=ds_pop8; mem[a]=b } ;
        a = self.ds.popn()
        b = self.ds.popb()
        self.mem[a] = b

    def n_fetch8(self):
        #: n_FETCH8   ( a -- b)
        # { a=ds_pop; b=mem[a]; ds_push8(b) } ;
        a = self.ds.popn()
        b = self.mem[a]
        self.ds.pushb(b)
        pass

    def n_add(self):
        #: n_ADD   ( n1 n2 -- n-sum)
        # { n2=ds_pop; n1=ds_pop; r=n1+n2; flags=zncv; ds_push(r) } ;
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 + n2
        flags = 0 # TODO ZNCV
        self.ds.pushn(r)

    def n_sub(self):
        #: n_SUB   ( n1 n2 -- n-diff)
        # { n2=ds_pop; n1=ds_pop; r=n1-n2; flags=zncv; ds_push(r) } ;
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 - n2
        flags = 0; # TODO ZNCV
        self.ds.pushn(r)

    def n_and(self):
        #: n_AND   ( n1 n2 -- n-and)
        # { n2=ds_pop; n1=ds_pop; r=n1 and n2; flags=zncv; ds_push(r) } ;
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 & n2
        flags = 0 # TODO ZNCV
        self.ds.pushn(r)

    def n_or(self):
        #: n_OR   ( n1 n2 -- n-or)
        # { n2=ds_pop; n1=ds_pop; r=n1 or n2; flags=zncv; ds_push(r) } ;
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 | n2
        flags = 0 # TODO ZNCV
        self.ds.pushn(r)

    def n_xor(self):
        #: n_XOR   ( n1 n2 -- n-xor)
        # { n2=ds_pop; n1=ds_pop; r=n1 xor n2; flags=zncv; ds_push(r) } ;
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 ^ n2
        flags = 0 # TODO ZNCV
        self.ds.pushn(r)

    def n_mult(self):
        #: n_MULT   ( n1 n2 -- n-prod)
        # { n2=ds_pop; n1=ds_pop; r=n1*n2; flags=zncv; ds_push(r) } ;
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 * n2
        flags = 0 # TODO ZNCV
        self.ds.pushn(r)

    def n_div(self):
        #: n_DIV   ( n1 n2 -- n-quot)
        # { n2=ds_pop; n2=ds_pop; r=n1/n2; flags=zncv; ds_push(c) } ;
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 / n2
        flags = 0 # TODO ZNCV
        self.ds.pushn(r)

    def n_mod(self):
        #: n_MOD   ( n1 n2 -- n-rem)
        # { n2=ds_pop; n1=ds_pop; r=n1 mod n2; flags=zncv; ds_push(r) } ;
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 % n2
        flags = 0 # TODO ZNCV
        self.ds.pushn(r)

    def n_flags(self):
        #: n_FLAGS   ( -- )
        # { mem[FLAGS]=flags } ;
        pass

    def n_keyq(self): # TODO Input()
        #: n_KEYQ   ( -- ?)
        # { ds_push8(kbhit) } ;
        pass # knit to Input()

    def n_key(self): # TODO Input()
        #: n_KEY   ( -- c)
        # { ds_push8(getch) } ;
        pass # knit to Input()

    def n_emit(self): # TODO Output()
        #: n_EMIT   ( c -- )
        # { putch(ds_pop8) } ;
        pass # knit to Output()

    def n_rdpfa(self):
        #: n_RDPFA   ( a-pfa -- n)
        # { pfa=ds_pop; r=mem[pfa]; ds_push(r) } ;
        pfa = self.ds.popn()
        r = self.mem[pfa]
        self.ds.pushn(r)

    def n_adruv(self):
        #: n_ADRUV   ( a-pfa -- a)
        # { pfa=ds_pop; rel=mem[pfa]; a=uservars+rel; ds_push(a) } ;
        pfa = self.ds.popn()
        rel = self.mem[pfa]
        uservars = 0 # TODO per-task offset to uservars
        a = uservars + rel
        self.ds.pushn(a)

    def n_branch(self):
        #: n_BRANCH   ( -- )
        # { rel=mem[ip]; ip+=2; abs=ip-rel; ip=abs } ;
        ip = self.ip
        rel = self.mem[ip]
        ip += 2
        abs = ip - rel
        self.ip = abs

    def n_0branch(self):
        #: n_0BRANCH   ( ? -- )
        # { f=ds_pop; r=mem[ip]; if f==0:ip=ip-r else: ip+=2 } ;
        f = self.ds.popn()
        ip = self.ip
        rel = self.mem[ip]
        if f==0:
            self.ip = ip-rel
        else:
            self.ip += 2

    def n_next(self):
        #: n_NEXT   ( -- )
        # { cfa=mem[ip]; ip+=2; jsr(cfa) } ;
        cfa = self.mem[self.ip]
        self.ip += 2
        self.jsr(cfa)

    def n_exit(self):
        #: n_EXIT   ( -- )
        # { ip=rs_pop() } ;
        self.ip = self.rs.popn()

    def n_dodoes(self):
        #: n_DODOES   ( -- )
        # { while True: n_NEXT} ; / beware of python stack on return?
        while True:
            self.n_next()

    def n_rblk(self): # TODO Disk()
        #: n_RBLK  ( n a -- )
        # { a=ds_pop; n=ds_pop; b=disk_rd(1024*b, mem, a, 1024) } ;
        a = self.ds.popn()
        n = self.ds.popn()
        b = self.disk_rd(1024*n, self.mem, a, 1024)

    def n_wblk(self): # TODO Disk()
        #: n_WBLK  ( n a -- )
        # { a=ds_pop; n=ds_pop; disk_wr(1024*b, mem, a, 1024) } ;
        a = self.ds.popn()
        n = self.ds.popn()
        self.disk_wr(1024*n, self.mem, a, 1024)

    def disk_rd(self, diskaddr, mem, memaddr, size): # TODO Disk()
        warning("disk_rd not implemented")

    def disk_wr(self, diskaddr, mem, memaddr, size): # TODO Disk()
        warning("disk_wr not implemented")

    def jsr(self, addr):
        # if address is in self.native.index, invoke function, else NOP
        if addr < len(self.index):
            name, fn = self.index[addr]
            trace("calling native fn:%s" % name)
            fn()
        else:
            error("call to unknown native address: %d" % addr)


#TODO memory mapped variables need to be wired up too
# any value stored in mem[] that is a python function, is called, to read/write said value
# implies need to know if read/write and if width is 8/16/32
# 4 individual byte accesses vs 1 32 bit word access need to set/get same data
# in a 'safe' way?


#----- FORTH CONTEXT ----------------------------------------------------------
#
# The Forth language - knits everything together into one helpful object.



class Forth:
    def boot(self):
        self.build_ds()
        self.build_native()
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


    def build_native(self):
        self.machine = Machine(self)

        #iterate through native.index and register all DICT entries for them
        for i in range(len(self.machine.index)):
            n = self.machine.index[i]
            name, fn = n
            self.dict.create(nf=name, cf=i, pf=[])


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
