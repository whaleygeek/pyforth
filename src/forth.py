# forth.py  25/12/2015  D.J.Whale
#
# An experiment to write a minimal FORTH language on top of Python.
# The main purpose of this is to study the design of the FORTH language
# by attempting a modern implementation of it.

#----- DEBUG ------------------------------------------------------------------

class Debug():
    @staticmethod
    def out(ty, msg):
        """Display a formatted message on stdout"""
        print("%s:%s" % (str(ty), str(msg)))

    @staticmethod
    def trace(msg):
        """Display an optional trace message on stdout"""
        Debug.out("debug", msg)

    @staticmethod
    def info(msg):
        """Display an informational message on stdout"""
        Debug.out("info", msg)

    @staticmethod
    def warning(msg):
        """Display a warning message on stdout"""
        Debug.out("warning", msg)

    @staticmethod
    def fail(msg):
        """Display a failure message on stdout and stop the progra"""
        Debug.out("fail", msg)
        import sys
        sys.exit()


#----- NUMBER and DOUBLE accessors --------------------------------------------

class NumberBigEndian():
    """A big-endian 16-bit number helper"""
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


class DoubleBigEndian():
    """A big-endian 32-bit number helper"""
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

# The standard says that byte order is not defined. We will use big-endian.

class Number(NumberBigEndian):pass
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
        """Define a new memory region in the memory map"""
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
        """Display the memory map on stdout"""
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


#----- STACK ------------------------------------------------------------------

class Stack():
    """A general purpose stack abstraction to wrap around memory storage"""
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
        """Reset the stack to empty"""
        if self.grows > 0:
            self.ptr = self.base
        else:
            self.ptr = self.base + self.size

    def grow(self, bytes):
        """Expand the stack by a number of bytes"""
        self.ptr += bytes * self.grows

    def shrink(self, bytes):
        """Shrink the stack by a number of bytes"""
        self.ptr -= bytes * self.grows

    def pushn(self, number):
        """Push a 16 bit number onto the stack"""
        b0, b1 = Number.to_bytes(number)
        if self.incwrite: self.grow(2)
        self.mem[self.ptr]   = b0
        self.mem[self.ptr+1] = b1
        if not self.incwrite: self.grow(2)

    def pushb(self, byte):
        """Push an 8 bit byte onto the stack"""
        if self.incwrite: self.grow(1)
        self.mem[self.ptr] = byte & 0xFF
        if not self.incwrite: self.grow(1)

    def pushd(self, double):
        """Push a 32 bit double onto the stack"""
        b0, b1, b2, b3 = Double.to_bytes(double)
        if self.incwrite: self.grow(4)
        self.mem[self.ptr]   = b0
        self.mem[self.ptr+1] = b1
        self.mem[self.ptr+2] = b2
        self.mem[self.ptr+3] = b3
        if not self.incwrite: self.grow(4)

    def popn(self):
        """Pop a 16 bit number from the stack"""
        if self.incwrite: self.grow(2)
        b0 = self.mem[self.ptr]
        b1 = self.mem[self.ptr+1]
        number = Number.from_bytes((b0, b1))
        if not self.incwrite: self.grow(2)
        return number

    def popb(self):
        """Pop an 8 bit byte from the stack"""
        if not self.incwrite: self.shrink(1)
        byte = self.mem[self.ptr]
        if self.incwrite: self.shrink(1)
        return byte

    def popd(self):
        """Pop a 32 bit double from the stack"""
        if not self.incwrite: self.shrink(4)
        b0 = self.mem[self.ptr]
        b1 = self.mem[self.ptr+1]
        b2 = self.mem[self.ptr+2]
        b3 = self.mem[self.ptr+3]
        double = Double.from_bytes((b0, b1, b2, b3))
        if self.incwrite: self.shrink(4)
        return double

    def getn(self, relindex):
        """Get a 16 bit number at a 16-bit position relative to top of stack"""
        ofs = (relindex*2)*self.grow
        b0 = self.mem[self.ptr+ofs]
        b1 = self.mem[self.ptr+ofs+1]
        number = Number.from_bytes((b0, b1))
        return number

    def getb(self, relindex):
        """Get an 8 bit number at an 8 bit position relative to top of stack"""
        ofs = relindex * self.grow
        byte = self.mem[self.ptr+ofs]
        return byte

    def getd(self, relindex):
        """Get a 32 bit number at a 32 bit position relative to top of stack"""
        ofs = (relindex*4)*self.grow
        b0 = self.mem[self.ptr+ofs]
        b1 = self.mem[self.ptr+ofs+1]
        b2 = self.mem[self.ptr+ofs+2]
        b3 = self.mem[self.ptr+ofs+3]
        double = Double.from_bytes((b0, b1, b2, b3))
        return double

    def setn(self, relindex, number):
        """Write to a 16 bit number at a 16 bit position relative to top of stack"""
        ofs = (relindex*2)*self.grow
        b0, b1 = Number.to_bytes(number)
        self.mem[self.ptr+ofs]   = b0
        self.mem[self.ptr+ofs+1] = b1

    def setb(self, relindex, byte):
        """Write to an 8 bit number at an 8 bit position relative to top of stack"""
        ofs = relindex*self.grow
        self.mem[self.ptr+ofs] = byte

    def setd(self, relindex, double):
        """Write to a 32 bit number at a 32 bit position relative to stop of stack"""
        ofs = (relindex*4)*self.grow
        b0, b1, b2, b3 = Double.to_bytes(double)
        self.mem[self.ptr+ofs]   = b0
        self.mem[self.ptr+ofs+1] = b1
        self.mem[self.ptr+ofs+2] = b2
        self.mem[self.ptr+ofs+3] = b3

    def dup(self): # ( n -- n n)
        """Forth DUP top of stack"""
        n = self.getn(0)
        self.pushn(n)

    def swap(self): # ( n1 n2 -- n2 n1)
        """Forth SWAP top two numbers on stack"""
        n0 = self.getn(0)
        n1 = self.getn(1)
        self.setn(0, n1)
        self.setn(1, n0)

    def rot(self): # ( n1 n2 n3 -- n2 n3 n1)
        """Forth 3 way ROTate of top 3 number on stack"""
        n3 = self.getn(0)
        n2 = self.getn(1)
        n1 = self.getn(2)
        self.setn(0, n1)
        self.setn(1, n3)
        self.setn(2, n2)

    def over(self): # ( n1 n2 -- n1 n2 n1)
        """Forth bring second number on stack over on to top of stack"""
        n = self.getn(1)
        self.pushn(n)

    def drop(self): # ( n -- )
        """Forth drop top number on stack"""
        self.popn()


#----- VARS -------------------------------------------------------------------

class Vars(Stack):
    """A generic variable region abstraction"""
    def __init__(self, storage, offset, size):
        Stack.__init__(storage, offset, size)

    def create(self, size=2):
        """Create a new constant or variable of the given size in bytes"""
        addr = self.ptr
        self.pushn(0)
        # A variable is just an address in a managed region, so reading and
        # writing is just done directly via memory using this address.
        return addr


class SysVars(Vars):
    #TODO: not sure yet what system variables are used for
    def __init__(self, storage, base, size):
        Vars.__init__(self, storage, base, size)

    # functions used to implement memory mapped registers
    def rd_sv0(self):
        """Read the SysVars base address"""
        return self.base

    def rd_svz(self):
        """Read the SysVars size in bytes"""
        return self.size

    def rd_svp(self):
        """Read the SysVars current pointer"""
        return self.ptr

    def wr_svp(self, number):
        """Write to the SysVars current pointer"""
        self.ptr = number


class UserVars(Vars):
    #TODO: should be one copy per user task.
    #e.g. BASE
    def __init__(self, storage, base, size):
        Vars.__init__(self, storage, base, size)

    # functions used to implement memory mapped registers
    def rd_uv0(self):
        """Read the UserVars base address"""
        return self.base

    def rd_uvz(self):
        """Read the UserVars size in bytes"""
        return self.size

    def rd_uvp(self):
        """Read the UserVars pointer"""
        return self.ptr

    def wr_uvp(self, number):
        """Write to the UserVars pointer"""
        self.ptr = number


#----- DICTIONARY -------------------------------------------------------------
#
# Structure:
#   HEADER
#     FFA->FF   (flags field) {b7=immediate flag, b6=defining, b5=unused, b4..b0=count 0..31}
#     NFA->NF   (name field) 16 bit padded name string
#          1PAD (optional pad byte to 16 bit align next field)
#     LFA->LF   (link field) {16bit addr of prev entry}
#   BODY
#     CFA->CF (code field) {16bit addr of machine code routine}
#     PFA->PF (parameter field) list of {16 bit parameters specific to CFA type}

class Dictionary(Stack):
    """A dictionary of defined Forth WORDs"""
    FLAG_IMMEDIATE = 0x80
    FLAG_DEFINING  = 0x40
    FLAG_UNUSED    = 0x20
    FIELD_COUNT    = 0x1F # 0..31

    def __init__(self, storage, base, size):
        Stack.__init__(storage, base, size)
        self.pushn(0) # first FFA entry is always zero, to mark end of search chain
        self.last_ffa = self.ptr

    def create(self, nf, cf=None, pf=None, immediate=False, finish=False):
        """Create a new dictionary record"""
        Debug.trace("dict.create: nf:%s cf:%d pf:%s" % (nf, cf, str(pf)))

        # truncate name to maximum length
        if len(nf) > 32:
            nf = nf[:32]

        # work out header
        #   FF: flag field (immediate, defining, unused, 5count)
        if immediate: im=Dictionary.FLAG_IMMEDIATE
        else: im=0
        df = Dictionary.FLAG_DEFINING

        ff = im + df + len(nf)
        # extra pad byte to 16 bit align
        pad = len(nf) % 2
        #   NF: name field
        # as above, already truncated
        #   LF: link field
        lf = self.last_ffa

        # store header
        self.allot(1)
        self.writeb(ff)
        for ch in nf:
            self.allot(1)
            self.writeb(ch)
        if pad: self.allot(1)
        self.allot(2)
        self.write(lf)

        # if cf/nf provided, fill them in too
        if cf != None:
            self.allot()
            self.write(cf)
        if pf != None:
            for f in pf:
                self.allot()
                self.write(f)

        # if finished, clear the defining flag and advance self.last_ffa
        if finish:
            self.finished()

    def finished(self):
        """Mark the most recently used dictionary record as finished/available"""
        # get FFA
        growth = self.ptr - self.last_ffa
        # clear 'defining' bit
        ff = self.getb(-growth)
        self.setb(-growth, ff & ~ Dictionary.FLAG_DEFINING)
        # advance end pointer
        self.last_ffa = self.ptr

    def allot(self, size=2):
        """Allot some extra space in the presently defining dictionary record"""
        if size == 2:
            self.pushn(0) # note this moves the pointer
        else:
            for i in range(size):
                self.pushb(0) # note this moves the pointer

    def write(self, number):
        """Write a 16 bit number at the present H pointer in the dictionary"""
        self.setn(0, number) # note this does not move the pointer

    def writeb(self, byte):
        """Write an 8 bit number at the present H pointer in the dictionary"""
        self.setb(0, byte) # note this does not move the pointer

    def prev(self, ffa_addr=None):
        """Find the FFA address of the previous dictionary word"""
        if ffa_addr==None:
            ffa_addr = self.last_ffa
        lfa = self.ffa2lfa(ffa_addr)
        lf = self.storage.read(lfa)
        return lf

    def nfa(self, ffa):
        """relative skip from ffa to nfa"""
        return ffa+1

    def lfa(self, nfa):
        """relative skip from nfa to lfa"""
        ff = self.storage.readb(nfa)
        count = ff & ~ Dictionary.FIELD_COUNT # now the count
        lfa = nfa + count + (count%2) # optional PAD
        return lfa

    def cfa(self, lfa):
        """relative skip from lfa to cfa"""
        return lfa+2

    def pfa(self, cfa):
        """relative skip from cfa to pfa"""
        return cfa+2

    def ffa2nfa(self, ffa):
        """relative skip from ffa to nfa"""
        return ffa+1

    def ffa2lfa(self, ffa=None):
        """relative skip from ffa to lfa"""
        if ffa == None:
            ffa = self.last_ffa
        ff = self.storage.readb(ffa)
        count = ff & ~ Dictionary.FIELD_COUNT # now the count
        lfa = count + (count % 2) # optional PAD
        return lfa

    def ffa2cfa(self, ffa=None):
        """relative skip from ffa to cfa"""
        if ffa == None:
            ffa = self.last_ffa
        return ffa+2

    def ffa2pfa(self, ffa=None):
        """relative skip from ffa to pfa"""
        if ffa == None:
            ffa = self.last_ffa
        return ffa+4

    def find(self, name, ffa=None):
        """Find a word by it's name, following the chain from ffa backwards"""
        if ffa == None:
            ffa = self.last_ffa

        while True:
            # check if FFA is zero
            ff = self.storage.readb(ffa)
            if ff == 0:
                return 0 # Not found # TODO: Should this be an exception?
            # check if still defining
            if ff & Dictionary.FLAG_DEFINING == 0:
                # check if name in NFA matches
                nfa = self.ffa2nfa(ffa)
                count = ff & Dictionary.FIELD_COUNT
                this_name = ""
                for i in range(count):
                    this_name += self.storage.readb(nfa+i)
                if this_name == name:
                    return ffa # FOUND

            # Still definining, or did not match, move to previous entry
            ffa = self.prev(ffa)

    def forget(self, name):
        """Forget all words up to and including this name"""

        ffa = self.find(name)
        if ffa == 0:
            return # Nothing to delete, name not found
            #TODO: really this should be an exception?

        # ffa is the FFA of the first item to delete (the new dict ptr)
        prev = self.prev(ffa) # addr of FFA of the item we want to be the last defined item

        # Adjust the pointers
        self.last_ffa = prev # the last defined word in the dictionary
        self.ptr      = ffa  # the H pointer, next free byte in dictionary


    #TODO: might be some functions for address calculations exposed as natives too!
    #beware, we might not be able to pass parameters to them, so defaults should be good?

    # functions for memory mapped registers

    def rd_d0(self):
        """Read the dictionary base address"""
        return self.base

    def rd_h(self):
        """Read the present H value"""
        return self.ptr

    def wr_h(self, number):
        """Write to the present H value"""
        self.ptr = number


class DataStack(Stack):
    """A stack for pushing application data on to """
    def __init__(self, mem, base, size):
        Stack.__init__(self, mem, base, size, grows=1, incwrite=False)

    # functions to allow memory mapped registers
    def rd_s0(self):
        """Read the DataStack base address"""
        return self.base

    def rd_sz(self):
        """Read the DataStack size in bytes"""
        return self.size

    def rd_sp(self):
        """Read the DataStack present TOS pointer"""
        return self.ptr

    def wr_sp(self, number):
        """Write to the DataStack present TOS pointer"""
        self.ptr = number


class ReturnStack(Stack):
    """A stack for high level forth call/return addresses"""
    def __init__(self, mem, base, size):
        Stack.__init__(self, mem, base, size, grows=-1, incwrite=False)

    # functions to allow memory mapped registers
    def rd_r0(self):
        """Read the ReturnStack base address"""
        return self.base

    def rd_rz(self):
        """Read the ReturnStack size in bytes"""
        return self.size

    def rd_rp(self):
        """Read the ReturnStack present TOS pointer"""
        return self.ptr

    def wr_rp(self, number):
        """Write to the ReturnStack present TOS pointer"""
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
#
#    def read(self, diskaddr, mem, memaddr, size):
#        Debug.warning("disk_rd not implemented")
#
#    def write(self, diskaddr, mem, memaddr, size);
#        Debug.warning("disk_wr not implemented")


#----- MACHINE ----------------------------------------------------------------

class Machine():
    """A native machine simulation, enough to attach ALU and stack ops to"""
    def __init__(self, parent):
        self.ip     = 0
        self.parent = parent
        self.mem    = parent.mem
        self.sv     = parent.sv
        #TODO: self.uv = parent.uv #user vars (task specific offset?)
        self.dict   = parent.dict
        self.ds     = parent.ds
        self.rs     = parent.rs

        # dispatch table for rdbyte(addr), wrbyte(addr, byte), call(addr)
        #TODO: as most variables/consts are 16 bits, how are we going to double-map the addresses? H/L?
        #how will the forth machine access these, using two 8-bit memory accesses, or one
        #16 bit memory access (preferred)
        #in which case, we need to know that it *is* a 16 bit read, and generate a 'bus error' like thing
        #if it is not.
        self.dispatch = [
            #name      readfn,      writefn,      execfunction
            ("NOP",    None,        None,         self.n_nop),       # CODE
            ("STORE",  None,        None,         self.n_store),     # CODE
            ("FETCH",  None,        None,         self.n_fetch),     # CODE
            ("STORE8", None,        None,         self.n_store8),    # CODE
            ("FETCH8", None,        None,         self.n_fetch8),    # CODE
            ("ADD",    None,        None,         self.n_add),       # CODE
            ("SUB",    None,        None,         self.n_sub),       # CODE
            ("AND",    None,        None,         self.n_and),       # CODE
            ("OR",     None,        None,         self.n_or),        # CODE
            ("XOR",    None,        None,         self.n_xor),       # CODE
            ("MULT",   None,        None,         self.n_mult),      # CODE
            ("DIV",    None,        None,         self.n_div),       # CODE
            ("MOD",    None,        None,         self.n_mod),       # CODE
            ("FLAGS",  None,        None,         self.n_flags),     # CODE
            ("SWAP",   None,        None,         self.ds.swap),     # CODE
            ("DUP",    None,        None,         self.ds.dup),      # CODE
            ("OVER",   None,        None,         self.ds.over),     # CODE
            ("ROT",    None,        None,         self.ds.rot),      # CODE
            ("DROP",   None,        None,         self.ds.drop),     # CODE
            ("KEY",    None,        None,         self.n_key),       # CODE
            ("KEYQ",   None,        None,         self.n_keyq),      # CODE
            ("EMIT",   None,        None,         self.n_emit),      # CODE
            ("RDPFA",  None,        None,         self.n_rdpfa),     # CODE
            ("ADRUV",  None,        None,         self.n_adruv),     # CODE
            ("BRANCH", None,        None,         self.n_branch),    # CODE
            ("0BRANCH",None,        None,         self.n_0branch),   # CODE
            ("NEXT",   None,        None,         self.n_next),      # CODE
            ("EXIT",   None,        None,         self.n_exit),      # CODE
            ("DODOES", None,        None,         self.n_dodoes),    # CODE
            ("RBLK",   None,        None,         self.n_rblk),      # CODE
            ("WBLK",   None,        None,         self.n_wblk),      # CODE

            # DICT registers
            ("D0",     self.dict.rd_d0, None,     None),             # CONST
            ("H",      self.dict.rd_h, self.dict.wr_h, None),        # VAR

            # DATA STACK registers
            ("S0",     self.ds.rd_s0,  None,      None),             # CONST
            ("SP",     self.ds.rd_sp,  self.ds.wr_sp, None),         # VAR

            # RETURN STACK registers
            ("R0",     self.rs.rd_r0,  None,      None),             # CONST
            ("RP",     self.rs.rd_rp,  self.rs.wr_rp, None),         # VAR

            # SYSTEM VARS registers
            # base and ptr for sys vars (SV0, SVP)

            # USER VARS registers
            # base and ptr for user vars (UV0, UVP)

            # BLOCK BUFFER registers
            # base and size for block buffers (BB0, BBZ)

            # MISC
            ("IP",    self.rd_ip, self.wr_ip, None),               # VAR

            #TODO: compiler routines etc
            # DOES>
            # COLON
            # SEMICOLON
            # VARIABLE
            # CONSTANT
            # DODOES
            # DOCOL
            # DOCON
            # DOVAR
            # NEXT
            # QUIT (run interpreter loop)
            # BYE (stop the forth engine)
        ]

    # functions for memory mapped registers

    def rd_ip(self):
        """Read the present high level forth instruction pointer"""
        return self.ip

    def wr_ip(self, number):
        """Write to the present high level forth instruction pointer"""
        self.ip = number

    # functions for native code

    def n_nop(self):
        """Do nothing"""
        pass

    def n_store(self):
        """: n_STORE   ( n a -- )
        { a=ds_pop; n0=ds_pop8; n1=ds_pop8; mem[a]=n0; mem[a+1]=n1} ;"""
        a = self.ds.popn()
        n0 = self.ds.popb()
        n1 = self.ds.popb()
        self.mem[a] = n0
        self.mem[a+1] = n1

    def n_fetch(self):
        """: n_FETCH  ( a -- n)
        { a=ds_pop; n0=mem[a]; n1=mem[a+1]; ds_push8(n0); ds_push8(n1) } ;"""
        a = self.ds.popn()
        n0 = self.mem[a]
        n1 = self.mem[a+1]
        self.ds.pushb(n0)
        self.ds.pushb(n1)

    def n_store8(self):
        """: n_STORE8  ( b a -- )
        { a=ds_pop; b=ds_pop8; mem[a]=b } ;"""
        a = self.ds.popn()
        b = self.ds.popb()
        self.mem[a] = b

    def n_fetch8(self):
        """: n_FETCH8   ( a -- b)
        { a=ds_pop; b=mem[a]; ds_push8(b) } ;"""
        a = self.ds.popn()
        b = self.mem[a]
        self.ds.pushb(b)
        pass

    def n_add(self):
        """: n_ADD   ( n1 n2 -- n-sum)
        { n2=ds_pop; n1=ds_pop; r=n1+n2; flags=zncv; ds_push(r) } ;"""
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 + n2
        flags = 0 # TODO: ZNCV
        self.ds.pushn(r)

    def n_sub(self):
        """: n_SUB   ( n1 n2 -- n-diff)
        { n2=ds_pop; n1=ds_pop; r=n1-n2; flags=zncv; ds_push(r) } ;"""
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 - n2
        flags = 0; # TODO: ZNCV
        self.ds.pushn(r)

    def n_and(self):
        """: n_AND   ( n1 n2 -- n-and)
        { n2=ds_pop; n1=ds_pop; r=n1 and n2; flags=zncv; ds_push(r) } ;"""
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 & n2
        flags = 0 # TODO: ZNCV
        self.ds.pushn(r)

    def n_or(self):
        """: n_OR   ( n1 n2 -- n-or)
        { n2=ds_pop; n1=ds_pop; r=n1 or n2; flags=zncv; ds_push(r) } ;"""
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 | n2
        flags = 0 # TODO: ZNCV
        self.ds.pushn(r)

    def n_xor(self):
        """: n_XOR   ( n1 n2 -- n-xor)
        { n2=ds_pop; n1=ds_pop; r=n1 xor n2; flags=zncv; ds_push(r) } ;"""
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 ^ n2
        flags = 0 # TODO: ZNCV
        self.ds.pushn(r)

    def n_mult(self):
        """: n_MULT   ( n1 n2 -- n-prod)
        { n2=ds_pop; n1=ds_pop; r=n1*n2; flags=zncv; ds_push(r) } ;"""
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 * n2
        flags = 0 # TODO: ZNCV
        self.ds.pushn(r)

    def n_div(self):
        """: n_DIV   ( n1 n2 -- n-quot)
        { n2=ds_pop; n2=ds_pop; r=n1/n2; flags=zncv; ds_push(c) } ;"""
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 / n2
        flags = 0 # TODO: ZNCV
        self.ds.pushn(r)

    def n_mod(self):
        """: n_MOD   ( n1 n2 -- n-rem)
        { n2=ds_pop; n1=ds_pop; r=n1 mod n2; flags=zncv; ds_push(r) } ;"""
        n2 = self.ds.popn()
        n1 = self.ds.popn()
        r = n1 % n2
        flags = 0 # TODO: ZNCV
        self.ds.pushn(r)

    def n_flags(self):
        """: n_FLAGS   ( -- )
        # { mem[FLAGS]=flags } ;"""
        pass # TODO:

    def n_keyq(self):
        """: n_KEYQ   ( -- ?)
        { ds_push8(kbhit) } ;"""
        pass #TODO: knit to Input()

    def n_key(self):
        """: n_KEY   ( -- c)
        { ds_push8(getch) } ;"""
        pass #TODO: knit to Input()

    def n_emit(self):
        """: n_EMIT   ( c -- )
        { putch(ds_pop8) } ;"""
        pass #TODO: knit to Output()

    def n_rdpfa(self):
        """: n_RDPFA   ( a-pfa -- n)
        { pfa=ds_pop; r=mem[pfa]; ds_push(r) } ;"""
        pfa = self.ds.popn()
        r = self.mem[pfa]
        self.ds.pushn(r)

    def n_adruv(self):
        """: n_ADRUV   ( a-pfa -- a)
        { pfa=ds_pop; rel=mem[pfa]; a=uservars+rel; ds_push(a) } ;"""
        pfa = self.ds.popn()
        rel = self.mem[pfa]
        uservars = 0 # TODO: per-task offset to uservars
        a = uservars + rel
        self.ds.pushn(a)

    def n_branch(self):
        """: n_BRANCH   ( -- )
        { rel=mem[ip]; ip+=2; abs=ip-rel; ip=abs } ;"""
        ip = self.ip
        rel = self.mem[ip]
        ip += 2
        abs = ip - rel
        self.ip = abs

    def n_0branch(self):
        """: n_0BRANCH   ( ? -- )
        { f=ds_pop; r=mem[ip]; if f==0:ip=ip-r else: ip+=2 } ;"""
        f = self.ds.popn()
        ip = self.ip
        rel = self.mem[ip]
        if f==0:
            self.ip = ip-rel
        else:
            self.ip += 2

    def n_next(self):
        """: n_NEXT   ( -- )
        { cfa=mem[ip]; ip+=2; call(cfa) } ;"""
        cfa = self.mem[self.ip]
        self.ip += 2
        self.call(cfa)

    def n_exit(self):
        """: n_EXIT   ( -- )
        { ip=rs_pop() } ;"""
        self.ip = self.rs.popn()

    def n_dodoes(self):
        """: n_DODOES   ( -- )
        { while True: n_NEXT} ; / beware of python stack on return? """
        while True:
            self.n_next()

    def n_rblk(self):
        """: n_RBLK  ( n a -- )
        { a=ds_pop; n=ds_pop; b=disk_rd(1024*b, mem, a, 1024) } ;"""
        a = self.ds.popn()
        n = self.ds.popn()
        #TODO: b = self.disk.read(1024*n, self.mem, a, 1024)

    def n_wblk(self):
        """: n_WBLK  ( n a -- )
        { a=ds_pop; n=ds_pop; disk_wr(1024*b, mem, a, 1024) } ;"""
        a = self.ds.popn()
        n = self.ds.popn()
        #TODO: self.disk.write(1024*n, self.mem, a, 1024)


    # functions for memory mapped access to registers and routines

    def call(self, addr):
        """Look up the call address in the dispatch table, and dispatch if known"""
        if addr < len(self.dispatch):
            name, rdfn, wrfn, execfn = self.dispatch[addr]
            Debug.trace("calling native fn:%d %s" % (addr, name))
            if execfn != None:
                execfn()
                return
        Debug.fail("call to unknown native address: %d" % addr)

    def rdbyte(self, addr):
        """Look up read address in dispatch table, and dispatch if known"""
        if addr < len(self.dispatch):
            name, rdfn, wrfn, execfn = self.dispatch[addr]
            Debug.trace("reading native byte:%d %s" % (addr, name))
            if rdfn != None:
                return rdfn()
        Debug.fail("read from unknown native address: %d" % addr)

    def wrbyte(self, addr, byte):
        """Look up write address in dispatch table, and dispatch if known"""
        if addr < len(self.dispatch):
            name, rdfn, wrfn, execfn = self.dispatch[addr]
            Debug.trace("writing native byte:%d %s" % (addr, name))
            if wrfn != None:
                wrfn(byte)
                return
        Debug.fail("write to unknown native address: %d" % addr)


#----- FORTH CONTEXT ----------------------------------------------------------

class Forth:
    """The Forth language - knits everything together into one helpful object"""
    def boot(self):
        self.build_ds()
        self.build_native()
        return self

    def build_ds(self):
        """Build datastructures in memory"""
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
        """Build the native dispatch table and machine"""
        self.machine = Machine(self)

        #iterate through native.index and register all DICT entries for them
        for i in range(len(self.machine.index)):
            n = self.machine.index[i]
            name, rdfn, wrfn, execfn = n
            if name != None:
                # only named items get appended to the DICT
                # read only (a constant)
                # write only (not supported??)
                # read and write (a variable)
                if rdfn != None and wrfn == None:
                    pass # TODO: create a constant record in DICT (DOCON)
                if rdfn != None and wrfn != None:
                    pass # TODO: create a variable record in DICT (DOVAR)
                # other R/W combinations not created in the dict.

                if execfn != None:
                    # It's a native code call, with no parameters
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
    #TODO: write a 1st unit test, perhaps a series of words to interpret?
    #i.e. could hand define a word in the dict and then execute it to
    #see if it has the correct side effect?

    # unittest would be easier if various data structures had test interfaces
    # for mocking etc?
    #f.run()

if __name__ == "__main__":
    test()

# END
