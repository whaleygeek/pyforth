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


#----- DEBUG ------------------------------------------------------------------

class Debug():
    @staticmethod
    def out(ty, msg):
        print("%s:%s" % (str(ty), str(msg)))

    @staticmethod
    def trace(msg):
        Debug.out("debug", msg)

    @staticmethod
    def info(msg):
        Debug.out("info", msg)

    @staticmethod
    def warning(msg):
        Debug.out("warning", msg)

    @staticmethod
    def fail(msg):
        Debug.out("fail", msg)
        import sys
        sys.exit()


#----- NUMBER and DOUBLE accessors --------------------------------------------

class NumberBigEndian():
    @staticmethod
    def from_bytes(b):
        b0 = (b[0] & 0xFF)
        b1 = (b[1] & 0xFF)
        return (b0<<8)+b1

    @staticmethod
    def to_bytes(n):
        b0 = (n & 0xFF00)>>8
        b1 = (n & 0xFF)
        return (b0, b1)

class Number(NumberBigEndian):pass


class DoubleBigEndian():
    @staticmethod
    def from_bytes(b):
        b0 = (b[0] & 0xFF)
        b1 = (b[1] & 0xFF)
        b2 = (b[2] & 0xFF)
        b3 = (b[3] & 0xFF)
        return (b0<<24)+(b1<<16)+(b2<<8)+b3

    @staticmethod
    def to_bytes(n):
        b0 = (n & 0xFF000000)>>24
        b1 = (n & 0x00FF0000)>>16
        b2 = (n & 0x0000FF00)>>8
        b3 = (n & 0x000000FF)
        return (b0, b1, b2, b3)

class Double(DoubleBigEndian):pass


#----- MEMORY -----------------------------------------------------------------
#
# Access to a block of memory, basically a Python list.

MEMSIZE = 65536
mem = [0 for i in range(MEMSIZE)]

class Memory():
    def __init__(self, storage, size=None, offset=0):
        if size == None:
            size = len(storage)
        self.size = size
        #self.offset = offset #TODO: Apply offset throughout
        self.mem = storage
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
        value = Number.from_bytes((self.mem[addr], self.mem[addr+1]))
        return value

    def readb(self, addr):
        """Read a 1 byte variable"""
        value = self.mem[addr]
        return value

    def readd(self, addr):
        """Read a double length variable (4 byte, 32 bits)"""
        value = Number.from_bytes((self.mem[addr], self.mem[addr+1], self.mem[addr+2], self.mem[addr+3]))
        return value

    def writen(self, addr, value):
        """Write a cell sized 2 byte variable"""
        b0, b1 = Number.to_bytes(value)
        self.mem[addr]   = b0
        self.mem[addr+1] = b1

    def writeb(self, addr, value):
        """Write a 1 byte variable"""
        low = (value & 0xFF)
        self.mem[addr] = low

    def writed(self, addr, value):
        """Write a double length variable (4 byte, 32 bits)"""
        b0, b1, b2, b3 = Double.to_bytes(value)
        self.mem[addr]   = b0
        self.mem[addr+1] = b1
        self.mem[addr+2] = b2
        self.mem[addr+3] = b3


#----- PYTHON WRAPPERS FOR FORTH DATA STRUCTURES -----------------------------------
#
# A useful abstraction to allow Python to meddle directly with Forth's
# data structure regions in memory. This is useful when you want to rewrite
# the implementation code for a word in Python to get better execution speed.

#----- VARS -------------------------------------------------------------------

class Vars():
    def __init__(self, storage, offset, size):
        self.mem  = storage
        self.base = offset
        self.ptr  = offset
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
    def __init__(self, storage, offset, size):
        Vars.__init__(self, storage, offset, size)

    # functions used to implement memory mapped registers
    def rd_sv0(self):
        return self.offset

    def rd_svz(self):
        return self.size

    def rd_svp(self):
        return self.ptr

    def wr_svp(self, number):
        self.ptr = number


#TODO: There should be one copy of these for each user task in a multiprogrammed setup.
#e.g. BASE

class UserVars(Vars):
    def __init__(self, storage, offset, size):
        Vars.__init__(self, storage, offset, size)

    # functions used to implement memory mapped registers
    def rd_uv0(self):
        return self.offset

    def rd_uvz(self):
        return self.size

    def rd_uvp(self):
        return self.ptr

    def wr_uvp(self, number):
        self.ptr = number


#----- DICTIONARY -------------------------------------------------------------
#
# Structure:
#   HEADER
#     NFA->NF (name field) {count byte, chars} (16 bit aligned) bit7 of count byte set = 'immediate'
#     LFA->LF (link field) {16bit addr of prev entry} TODO: which field?
#   BODY
#     CFA->CF (code field) {16bit addr of machine code routine}  TODO: If zero, not used?
#     PFA->PF (parameter field) list of {16 bit parameters specific to CFA type}

# Note, how do H and HERE interrelate?
# is one the NFA of the last entry, the other the latest byte being written?

# Also, when building an entry, I think it is marked as unusable until it is completed,
# where is the flag for this stored?

class Dictionary():
    def __init__(self, storage, offset, size):
        self.mem  = storage
        self.base = offset
        self.ptr  = offset
        self.size = size
        #TODO: First entry must be a cell with 0 in it (marks end of chain)
        #is this zero in the count byte of the NFA, or a zero in the LFA?

    def create(self, nf, cf=None, pf=None, immediate=False, finished=False):
        Debug.trace("dict.create: nf:%s cf:%d pf:%s" % (nf, cf, str(pf)))
        #TODO create new dict entry and link LF to PREV (NFA?)
        #adjust HERE pointer and H
        #mark it as 'in progress'?
        #mark as immediate?

    def allot(self):
        self.ptr += 2

    def write(self, number):
        b0, b1 = Number.to_bytes(number)
        self.mem[self.ptr]   = b0
        self.mem[self.ptr+1] = b1

    def prev(self, addr=None):
        #TODO: get addr of previous word (if no addr, get last-1)
        pass

    def cfa(self, addr):
        pass # TODO get CFA of (?FA)

    def pfa(self, addr):
        pass # TODO get PFA of (?FA)

    def find(self, name):
        pass # TODO search chain for name and get it's address (NFA?)

    # how do H and HERE interrelate?
    #def here(self):
    #    pass # TODO get the ptr

    def forget(self, name):
        pass # TODO walk to name, set ptr back to NFA? LFA?
        # find name, get addr
        # set HERE/H back to addr if non zero

    # functions for memory mapped registers

    def rd_d0(self):
        return self.base

    def rd_h(self):
        return self.ptr

    def wr_h(self, number):
        self.ptr = number

    # difference between HERE and H??
    # addr of NFA of latest entry, vs addr of next byte to write?


#----- STACK ------------------------------------------------------------------

class Stack():
    def __init__(self, mem, base, size, grows=1, incwrite=True):
        self.mem  = mem
        self.base = base
        self.size = size
        if grows > 0:
            self.grows = 1
            self.ptr = base
        else:
            self.grows = -1
            self.ptr = base+size
        self.incwrite = incwrite

    def clear(self):
        if self.grows > 0:
            self.ptr = self.base
        else:
            self.ptr = self.base + self.size

    def grow(self, bytes):
        self.ptr += bytes * self.grows

    def shrink(self, bytes):
        self.ptr -= bytes * self.grows

    def pushn(self, number):
        b0, b1 = Number.to_bytes(number)
        if self.incwrite: self.grow(2)
        self.mem[self.ptr]   = b0
        self.mem[self.ptr+1] = b1
        if not self.incwrite: self.grow(2)

    def pushb(self, byte):
        if self.incwrite: self.grow(1)
        self.mem[self.ptr] = byte & 0xFF
        if not self.incwrite: self.grow(1)

    def pushd(self, double):
        b0, b1, b2, b3 = Double.to_bytes(double)
        if self.incwrite: self.grow(4)
        self.mem[self.ptr]   = b0
        self.mem[self.ptr+1] = b1
        self.mem[self.ptr+2] = b2
        self.mem[self.ptr+3] = b3
        if not self.incwrite: self.grow(4)

    def popn(self):
        if self.incwrite: self.grow(2)
        b0 = self.mem[self.ptr]
        b1 = self.mem[self.ptr+1]
        number = Number.from_bytes((b0, b1))
        if not self.incwrite: self.grow(2)
        return number

    def popb(self):
        if not self.incwrite: self.shrink(1)
        byte = self.mem[self.ptr]
        if self.incwrite: self.shrink(1)
        return byte

    def popd(self):
        if not self.incwrite: self.shrink(4)
        b0 = self.mem[self.ptr]
        b1 = self.mem[self.ptr+1]
        b2 = self.mem[self.ptr+2]
        b3 = self.mem[self.ptr+3]
        double = Double.from_bytes((b0, b1, b2, b3))
        if self.incwrite: self.shrink(4)
        return double

    def getn(self, relindex):
        ofs = (relindex*2)*self.grow
        b0 = self.mem[self.ptr+ofs]
        b1 = self.mem[self.ptr+ofs+1]
        number = Number.from_bytes((b0, b1))
        return number

    def getb(self, relindex):
        ofs = relindex * self.grow
        byte = self.mem[self.ptr+ofs]
        return byte

    def getd(self, relindex):
        ofs = (relindex*4)*self.grow
        b0 = self.mem[self.ptr+ofs]
        b1 = self.mem[self.ptr+ofs+1]
        b2 = self.mem[self.ptr+ofs+2]
        b3 = self.mem[self.ptr+ofs+3]
        double = Double.from_bytes((b0, b1, b2, b3))
        return double

    def setn(self, relindex, number):
        ofs = (relindex*2)*self.grow
        b0, b1 = Number.to_bytes(number)
        self.mem[self.ptr+ofs]   = b0
        self.mem[self.ptr+ofs+1] = b1

    def setb(self, relindex, byte):
        ofs = relindex*self.grow
        self.mem[self.ptr+ofs] = byte

    def setd(self, relindex, double):
        ofs = (relindex*4)*self.grow
        b0, b1, b2, b3 = Double.to_bytes(double)
        self.mem[self.ptr+ofs]   = b0
        self.mem[self.ptr+ofs+1] = b1
        self.mem[self.ptr+ofs+2] = b2
        self.mem[self.ptr+ofs+3] = b3

    def dup(self): # ( n -- n n)
        n = self.getn(0)
        self.pushn(n)

    def swap(self): # ( n1 n2 -- n2 n1)
        n0 = self.getn(0)
        n1 = self.getn(1)
        self.setn(0, n1)
        self.setn(1, n0)

    def rot(self): # ( n1 n2 n3 -- n2 n3 n1)
        n3 = self.getn(0)
        n2 = self.getn(1)
        n1 = self.getn(2)
        self.setn(0, n1)
        self.setn(1, n3)
        self.setn(2, n2)

    def over(self): # ( n1 n2 -- n1 n2 n1)
        n = self.getn(1)
        self.pushn(n)

    def drop(self): # ( n -- )
        self.popn()


class DataStack(Stack):
    def __init__(self, mem, base, size):
        Stack.__init__(self, mem, base, size, grows=1, incwrite=False)

    # functions to allow memory mapped registers
    def rd_s0(self):
        return self.base

    def rd_sz(self):
        return self.size

    def rd_sp(self):
        return self.ptr

    def wr_sp(self, number):
        self.ptr = number


class ReturnStack(Stack):
    def __init__(self, mem, base, size):
        Stack.__init__(self, mem, base, size, grows=-1, incwrite=False)

    # functions to allow memory mapped registers
    def rd_r0(self):
        return self.base

    def rd_rz(self):
        return self.size

    def rd_rp(self):
        return self.ptr

    def wr_rp(self, number):
        self.ptr = number


#----- BUFFERS ----------------------------------------------------------------

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


#---- I/O ---------------------------------------------------------------------
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
# Interface to screen output


#class Output():
#    def __init__(self):
#        pass
#
#    def write(self, ch):
#        print(ch)


# Probably an interface to reading and writing blocks in a nominated
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
        self.ip     = 0
        self.parent = parent
        self.mem    = parent.mem
        self.sv     = parent.sv
        self.dict   = parent.dict
        self.ds     = parent.ds
        self.rs     = parent.rs

        # dispatch table for rdbyte(addr), wrbyte(addr, byte), call(addr)
        #TODO map in system constants and variables into this table
        #as most variables/consts are 16 bits, how are we going to double-map the addresses? H/L?
        self.dispatch = [
            #name      readfn,      writefn,      execfunction
            ("NOP",    None,        None,         self.n_nop),
            ("STORE",  None,        None,         self.n_store),
            ("FETCH",  None,        None,         self.n_fetch),
            ("STORE8", None,        None,         self.n_store8),
            ("FETCH8", None,        None,         self.n_fetch8),
            ("ADD",    None,        None,         self.n_add),
            ("SUB",    None,        None,         self.n_sub),
            ("AND",    None,        None,         self.n_and),
            ("OR",     None,        None,         self.n_or),
            ("XOR",    None,        None,         self.n_xor),
            ("MULT",   None,        None,         self.n_mult),
            ("DIV",    None,        None,         self.n_div),
            ("MOD",    None,        None,         self.n_mod),
            ("FLAGS",  None,        None,         self.n_flags),
            ("SWAP",   None,        None,         self.ds.swap),
            ("DUP",    None,        None,         self.ds.dup),
            ("OVER",   None,        None,         self.ds.over),
            ("ROT",    None,        None,         self.ds.rot),
            ("DROP",   None,        None,         self.ds.drop),
            ("KEY",    None,        None,         self.n_key),
            ("KEYQ",   None,        None,         self.n_keyq),
            ("EMIT",   None,        None,         self.n_emit),
            ("RDPFA",  None,        None,         self.n_rdpfa),
            ("ADRUV",  None,        None,         self.n_adruv),
            ("BRANCH", None,        None,         self.n_branch),
            ("0BRANCH",None,        None,         self.n_0branch),
            ("NEXT",   None,        None,         self.n_next),
            ("EXIT",   None,        None,         self.n_exit),
            ("DODOES", None,        None,         self.n_dodoes),
            ("RBLK",   None,        None,         self.n_rblk),
            ("WBLK",   None,        None,         self.n_wblk)
        ]

    # functions for memory mapped registers

    def rd_ip(self):
        return self.ip

    def wr_ip(self, number):
        self.ip = number

    # functions for native code

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
        # { cfa=mem[ip]; ip+=2; call(cfa) } ;
        cfa = self.mem[self.ip]
        self.ip += 2
        self.call(cfa)

    def n_exit(self):
        #: n_EXIT   ( -- )
        # { ip=rs_pop() } ;
        self.ip = self.rs.popn()

    def n_dodoes(self):
        #: n_DODOES   ( -- )
        # { while True: n_NEXT} ; / beware of python stack on return?
        while True:
            self.n_next()

    def n_rblk(self): # TODO put in Disk()?
        #: n_RBLK  ( n a -- )
        # { a=ds_pop; n=ds_pop; b=disk_rd(1024*b, mem, a, 1024) } ;
        a = self.ds.popn()
        n = self.ds.popn()
        b = self.disk_rd(1024*n, self.mem, a, 1024)

    def n_wblk(self): # TODO put in Disk()?
        #: n_WBLK  ( n a -- )
        # { a=ds_pop; n=ds_pop; disk_wr(1024*b, mem, a, 1024) } ;
        a = self.ds.popn()
        n = self.ds.popn()
        self.disk_wr(1024*n, self.mem, a, 1024)

    def disk_rd(self, diskaddr, mem, memaddr, size): # TODO put in Disk()?
        Debug.warning("disk_rd not implemented")

    def disk_wr(self, diskaddr, mem, memaddr, size): # TODO put in Disk()?
        Debug.warning("disk_wr not implemented")


    # functions for memory mapped access to registers and routines

    def call(self, addr):
        if addr < len(self.dispatch):
            name, rdfn, wrfn, execfn = self.dispatch[addr]
            Debug.trace("calling native fn:%d %s" % (addr, name))
            if execfn != None:
                execfn()
                return
        Debug.fail("call to unknown native address: %d" % addr)

    def rdbyte(self, addr):
        if addr < len(self.dispatch):
            name, rdfn, wrfn, execfn = self.dispatch[addr]
            Debug.trace("reading native byte:%d %s" % (addr, name))
            if rdfn != None:
                return rdfn()
        Debug.fail("read from unknown native address: %d" % addr)

    def wrbyte(self, addr, byte):
        if addr < len(self.dispatch):
            name, rdfn, wrfn, execfn = self.dispatch[addr]
            Debug.trace("writing native byte:%d %s" % (addr, name))
            if wrfn != None:
                wrfn(byte)
                return
        Debug.fail("write to unknown native address: %d" % addr)


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

        self.mem = Memory(mem)

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
            name, fn = n #TODO: name, rdfn, wrfn, execfn
            #TODO: rdfn and wrfn can be used to memory map consts and variables
            #including to things like: ds.base, ds.ptr, rs.base, rs.ptr, dict.base, dict.ptr
            if name != None:
                # only named items get appended to the DICT
                self.dict.create(nf=name, cf=i, pf=[])

    #def run(self):
    #    #NOTE: can boot() then clone(), and then customise and run() multiple clones
    #    # optionally load app?
    #    # run main interpreter loop (optionally in a thread?)
    #    # only gets here when see a 'BYE' command.
    #    Debug.warning("No interpreter yet")


#----- RUNNER -----------------------------------------------------------------

def test():
    f = Forth().boot()
    #TODO write a 1st unit test, perhaps a series of words to interpret?
    #i.e. could hand define a word in the dict and then execute it to
    #see if it has the correct side effect?

    # unittest would be easier if various data structures had test interfaces
    # for mocking etc?
    #f.run()

if __name__ == "__main__":
    test()

# END
