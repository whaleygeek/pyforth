# forth.py  25/12/2015  (c) D.J.Whale
#
# An experiment to write a minimal FORTH language on top of Python.
# The main purpose of this is to study the design of the FORTH language
# by attempting a modern implementation of it.

#TODO: Resolve DOLIT (need a DOLITC for char)
#or check Brodie, how is the following coded:
#  42 EMIT
# because the 42 really should be a number, so EMIT should take a number
# and ignore the high byte??

DISK_FILE_NAME = "forth_disk.bin"

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
    def unimplemented(msg):
        """Display a warning about an unimplemented feature"""
        Debug.out("unimplemented", msg)

    @staticmethod
    def fail(msg):
        """Display a failure message on stdout and stop the progra"""
        Debug.out("fail", msg)
        #TODO need to flush stdout to prevent loosing it?
        #import sys
        #sys.exit(1)


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
    def __init__(self, storage, size=None):
        if size == None:
            size = len(storage)
        self.size = size
        self.bytes = storage
        self.map = []

    def __setitem__(self, key, value):
        self.bytes[key] = value

    def __getitem__(self, key):
        return self.bytes[key]

    def dump(self, start, len):
        """Dump memory to stdout, for debug reasons"""
        #TODO do a proper 8 or 16 column address-prefixed dump
        for a in range(start, start+len):
            print("%4x:%2x" % (a, self.bytes[a]))


    def region(self, name, spec):
        """Define a new memory region in the memory map"""
        # spec=(base, dirn/size)
        addr  = spec[0]
        size  = spec[1]
        if size < 0:
            # grows down towards low memory
            start = addr - -size
        else:
            # grows up towards high memory
            start = addr
        end = start + size

        # check for overlaps with an existing region
        for i in self.map:
            iname, istart, isize = i
            iend = istart + isize-1
            if (start >= istart and start <= iend) or (end >= istart and end <= iend):
                raise ValueError("Region %s overlaps with %s" % (name, iname))

        self.map.append((name, start, abs(size)))
        return start, size

    def show_map(self):
        """Display the memory map on stdout"""
        print("MEMORY MAP")
        last_end = 0
        for i in self.map:
            name, start, size = i
            if start != last_end:
                uname  = "UNUSED"
                ustart = last_end
                uend   = start-1
                usize  = uend-ustart-1
                print("%10s %5x %5x %5x" %(uname, ustart, uend, usize))
            print("%10s %5x %5x %5x" % (name, start, start+size-1, size))
            last_end = start + size
        #TODO: show any final unused space up to FFFF at end

    def readn(self, addr):
        """Read a cell sized 2 byte variable"""
        value = Number.from_bytes((self.bytes[addr], self.bytes[addr+1]))
        return value

    def readb(self, addr):
        """Read a 1 byte variable"""
        value = self.bytes[addr]
        return value

    def readd(self, addr):
        """Read a double length variable (4 byte, 32 bits)"""
        value = Number.from_bytes((self.bytes[addr], self.bytes[addr+1], self.bytes[addr+2], self.bytes[addr+3]))
        return value

    def writen(self, addr, value):
        """Write a cell sized 2 byte variable"""
        b0, b1 = Number.to_bytes(value)
        self.bytes[addr]   = b0
        self.bytes[addr+1] = b1

    def writeb(self, addr, value):
        """Write a 1 byte variable"""
        low = (value & 0xFF)
        self.bytes[addr] = low

    def writed(self, addr, value):
        """Write a double length variable (4 byte, 32 bits)"""
        b0, b1, b2, b3 = Double.to_bytes(value)
        self.bytes[addr]   = b0
        self.bytes[addr+1] = b1
        self.bytes[addr+2] = b2
        self.bytes[addr+3] = b3


#----- STACK ------------------------------------------------------------------

class Stack():
    """A general purpose stack abstraction to wrap around memory storage"""
    # bytes are always stored in the provided order, in increasing memory locations

    # Pointer strategies
    FIRSTFREE = False # ptr points to first free byte
    LASTUSED  = True  # ptr points to last used byte
    TOS = 0 # TOP OF STACK INDEX

    def __init__(self, storage, start, size, growdirn=1, ptrtype=None):

        if growdirn > 0: # growdirn +ve
            growdirn = 1
        else: # growdirn -ve
            growdirn = -1

        if ptrtype == None:
            ptrtype = Stack.FIRSTFREE

        self.storage  = storage
        self.start    = start
        self.size     = size
        self.growdirn = growdirn
        self.ptrtype  = ptrtype

        self.reset()

    def dumpraw(self):
        if self.growdirn != 1:
            raise RuntimeError("negative growth not dumpable yet")

        for addr in range(self.start, self.ptr+1):
            b = self.storage[addr]
            if b > 32 and b < 127:
                ch = chr(b)
            else:
                ch = ' '
            print("%x:%x  (%c)" % (addr, b, ch)) #ERROR, something storing a str?

    #--------------------------------------------------------------------------
    def reset(self):
        """Reset the stack to empty"""
        last = self.start+self.size-1

        if self.growdirn > 0: # growdirn +ve
            if self.ptrtype == Stack.FIRSTFREE:
                self.ptr = self.start
            else: # LASTUSED
                self.ptr = self.start-1

        else: # growdirn -ve
            if self.ptrtype == Stack.FIRSTFREE:
                self.ptr = last
            else: #LASTUSED
                self.ptr = last+1

    def grow(self, bytes):
        """Expand the stack by a number of bytes"""
        self.ptr += bytes * self.growdirn
        return self.ptr

    def shrink(self, bytes):
        """Shrink the stack by a number of bytes"""
        self.ptr -= bytes * self.growdirn
        return self.ptr

    def addr(self, rel, size):
        """Work out correct start address of a rel byte index starting at this position, relative to TOS"""
        #rel should reference the relative distance in bytes back from TOS (0 is TOS for all data sizes)

        if self.growdirn > 0: # +ve growth
            if self.ptrtype == Stack.FIRSTFREE:
                return self.ptr - rel - size
            else: # LASTUSED
                return self.ptr - rel - (size-1)
        else: # -ve growth
            if self.ptrtype == Stack.FIRSTFREE:
                return self.ptr + rel + 1
            else: #LASTUSED
                return self.ptr + rel

    def getused(self):
        """Get the number of bytes used on the stack"""
        if self.growdirn > 0: # +ve growth
            return self.ptr - self.start
        else: # -ve growth
            return (self.start+self.size-1) - self.ptr

    def write(self, rel, bytes):
        """Write a list of bytes, at a specific byte index from TOS"""
        size = len(bytes)
        ptr = self.addr(rel, size)
        for b in bytes:
            self.storage[ptr] = b
            ptr += 1

    def read(self, rel, size):
        """Read a list of bytes, at a specific byte index from TOS"""
        bytes = []
        ptr = self.addr(rel, size)
        for i in range(size):
            b = self.storage[ptr]
            bytes.append(b)
            ptr += 1
        return bytes

    def push(self, bytes):
        """Push a list of bytes"""
        size = len(bytes)
        self.grow(size)
        self.write(rel=0, bytes=bytes)

    def pop(self, size):
        """Pop a list of bytes of required size"""
        bytes = self.read(rel=0, size=size)
        self.shrink(size)
        return bytes
    #--------------------------------------------------------------------------
    def pushb(self, byte):
        """Push an 8 bit byte onto the stack"""
        self.push((byte, ))

    def pushn(self, number):
        """Push a 16 bit number onto the stack"""
        b0, b1 = Number.to_bytes(number)
        self.push((b0, b1))

    def pushd(self, double):
        """Push a 32 bit double onto the stack"""
        b0, b1, b2, b3 = Double.to_bytes(double)
        self.push((b0, b1, b2, b3))

    def popb(self):
        """Pop an 8 bit byte from the stack"""
        bytes = self.pop(1)
        return bytes[0]

    def popn(self):
        """Pop a 16 bit number from the stack"""
        b0, b1 = self.pop(2)
        number = Number.from_bytes((b0, b1))
        return number

    def popd(self):
        """Pop a 32 bit double from the stack"""
        b0, b1, b2, b3 = self.pop(4)
        double = Double.from_bytes((b0, b1, b2, b3))
        return double

    def setb(self, index, byte):
        """Write to an 8 bit number at an 8 bit position relative to top of stack"""
        self.write(rel=index, bytes=(byte,))

    def setn(self, index, number):
        """Write to a 16 bit number at a 16 bit position relative to top of stack"""
        b0, b1 = Number.to_bytes(number)
        self.write(rel=index*2, bytes=(b0, b1))

    def setd(self, index, double):
        """Write to a 32 bit number at a 32 bit position relative to stop of stack"""
        b0, b1, b2, b3 = Double.to_bytes(double)
        self.write(rel=index*4, bytes=(b0, b1, b2, b3))

    def getb(self, index):
        """Get an 8 bit number at an 8 bit position relative to top of stack"""
        bytes = self.read(rel=index, size=1)
        return bytes[0]

    def getn(self, index):
        """Get a 16 bit number at a 16-bit position relative to top of stack"""
        b0, b1 = self.read(rel=index*2, size=2)
        number = Number.from_bytes((b0, b1))
        return number

    def getd(self, index):
        """Get a 32 bit number at a 32 bit position relative to top of stack"""
        b0, b1, b2, b3 = self.read(rel=index*4, size=4)
        double = Double.from_bytes((b0, b1, b2, b3))
        return double
    #--------------------------------------------------------------------------
    def dup(self): # ( n -- n n)
        """Forth DUP top of stack"""
        n = self.getn(self.TOS)
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
    def __init__(self, storage, start, size):
        Stack.__init__(self, storage, start, size, growdirn=1, ptrtype=Stack.LASTUSED)

    def create(self, size=2):
        """Create a new constant or variable of the given size in bytes"""
        addr = self.ptr
        self.pushn(0)
        # A variable is just an address in a managed region, so reading and
        # writing is just done directly via memory using this address.
        return addr


class SysVars(Vars):
    #TODO: not sure yet what system variables are used for
    def __init__(self, storage, start, size):
        Vars.__init__(self, storage, start, size)

    # functions used to implement memory mapped registers
    def rd_sv0(self):
        """Read the SysVars start address"""
        return self.start

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
    def __init__(self, storage, start, size):
        Vars.__init__(self, storage, start, size)

    # functions used to implement memory mapped registers
    def rd_uv0(self):
        """Read the UserVars start address"""
        return self.start

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
#     NFA->NF   (name field) name string
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

    def __init__(self, storage, start, size):
        Stack.__init__(self, storage, start, size, growdirn=1, ptrtype=Stack.LASTUSED)

        self.pushb(0) # first FFA entry is always zero, to mark end of search chain
        self.last_ffa = self.ptr
        self.defining_ffa = None

    def create(self, nf, cf=None, pf=None, immediate=False, finish=False):
        """Create a new dictionary record"""
        #Debug.trace("dict.create: nf:%s cf:%d pf:%s" % (nf, cf, str(pf)))

        # truncate name to maximum length
        if len(nf) > 32:
            nf = nf[:32]

        # work out header
        #   FF: flag field (immediate, defining, unused, 5count)
        if immediate: im=Dictionary.FLAG_IMMEDIATE
        else: im=0
        df = Dictionary.FLAG_DEFINING

        ff = im + df + len(nf)
        #   NF: name field
        # as above, already truncated
        #   LF: link field
        lf = self.last_ffa

        # store header
        self.allot(1)
        self.storeb(ff)
        self.defining_ffa = self.ptr
        for ch in nf:
            self.allot(1)
            self.storeb(ord(ch))
        self.allot(2)
        self.store(lf)

        # if cf/nf provided, fill them in too
        if cf != None:
            self.allot()
            self.store(cf)
        if pf != None:
            for f in pf:
                self.allot()
                self.store(f)

        # if finished, clear the defining flag and advance self.last_ffa
        if finish:
            self.finished()

    def finished(self):
        """Mark the most recently used dictionary record as finished/available"""
        # get FFA
        # clear 'defining' bit
        if self.defining_ffa == None:
            raise RuntimeError("Trying to finish an already finished dict defn at:%d", self.last_ffa)

        ff = self.storage.readb(self.defining_ffa)
        self.storage.writeb(self.defining_ffa, ff & ~ Dictionary.FLAG_DEFINING)
        # advance end pointer
        self.last_ffa = self.defining_ffa
        self.defining_ffa = None

    def dump(self):
        """Dump the dictionary in reverse order from self.last_ffa back to NULL"""
        print("DICTIONARY")
        print("start:       %x" % self.start)
        print("size:        %x" % self.size)
        print("ptr:         %x" % self.ptr)
        print("last_ffa:    %x" % self.last_ffa)
        if self.defining_ffa != None:
            print("defining_ffa:%x" % self.defining_ffa)


        ffa = self.last_ffa
        while True:
            ptr = ffa
            ff = self.storage.readb(ptr)
            if ff == 0:
                return # FINISHED

            print("-" * 40)
            #### FF - Flags Field
            buf = "FF: "
            if ff & Dictionary.FLAG_IMMEDIATE: buf += "immediate "
            if ff & Dictionary.FLAG_DEFINING:  buf += "defining "
            if ff & Dictionary.FLAG_UNUSED:    buf += "unused "
            count = ff & Dictionary.FIELD_COUNT
            buf += "sz:" + str(count)
            print(buf)
            ptr += 1

            #### NF - Name Field
            buf = ""
            for i in range(count):
                buf += chr(self.storage.readb(ptr))
                ptr += 1
            print("NF: %s" % buf)

            #### LF - Link Field
            lf = self.storage.readn(ptr)
            print("LF: %x" % lf)
            ptr += 2

            #### CF - Code Field
            cf = self.storage.readn(ptr)
            print("CF: %x" % cf)
            ptr += 2

            #### PF - Parameter Field
            #TODO:Need to know how to sense the end of this?
            #There is no length byte, so depends on CF value
            #could look for ptr matching prev ptr, close enough, but not guaranteed
            print("PF: (here TODO)")

            # Move to prev
            ffa = self.prev(ffa)

    def allot(self, size=2):
        """Allot some extra space in the presently defining dictionary record"""
        if size == 2:
            self.pushn(0) # note this moves the pointer
        else:
            for i in range(size):
                self.pushb(0) # note this moves the pointer

    def store(self, number):
        """Write a 16 bit number at the present H pointer in the dictionary"""
        self.setn(0, number) # note this does not move the pointer

    def storeb(self, byte):
        """Write an 8 bit number at the present H pointer in the dictionary"""
        self.setb(0, byte) # note this does not move the pointer

    def prev(self, ffa_addr=None):
        """Find the FFA address of the previous dictionary word"""
        if ffa_addr==None:
            ffa_addr = self.last_ffa
        lfa = self.ffa2lfa(ffa_addr)
        lf = self.storage.readn(lfa)
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

    def pfa2cfa(self, pfa):
        return pfa-2 # back skip to cfa

    def ffa2nfa(self, ffa):
        """relative skip from ffa to nfa"""
        return ffa+1

    def ffa2lfa(self, ffa=None):
        """relative skip from ffa to lfa"""
        if ffa == None:
            ffa = self.last_ffa
        ff = self.storage.readb(ffa)
        count = ff & Dictionary.FIELD_COUNT # now the count
        lfa = ffa + count + 1
        return lfa

    def ffa2cfa(self, ffa=None):
        """relative skip from ffa to cfa"""
        if ffa == None:
            ffa = self.last_ffa
        return self.ffa2lfa(ffa)+2

    def ffa2pfa(self, ffa=None):
        """relative skip from ffa to pfa"""
        if ffa == None:
            ffa = self.last_ffa
        pfa = self.ffa2lfa(ffa)+4
        return pfa

    def find(self, name, ffa=None):
        """Find a word by it's name, following the chain from ffa backwards"""
        if ffa == None:
            ffa = self.last_ffa

        while True:
            # check if FFA is zero
            ff = self.storage.readb(ffa)
            if ff == 0:
                raise RuntimeError("Could not find word in dict:%s", name)
            # check if still defining
            if ff & Dictionary.FLAG_DEFINING == 0:
                # check if name in NFA matches
                nfa = self.ffa2nfa(ffa)
                count = ff & Dictionary.FIELD_COUNT
                this_name = ""
                for i in range(count):
                    this_name += chr(self.storage.readb(nfa+i))
                if this_name == name:
                    return ffa # FOUND

            # Still definining, or did not match, move to previous entry
            ffa = self.prev(ffa)

    def forget(self, name):
        """Forget all words up to and including this name"""

        ffa = self.find(name)
        if ffa == 0:
            raise RuntimeError("Could not find word to forget it:%s", name)

        # ffa is the FFA of the first item to delete (the new dict ptr)
        prev = self.prev(ffa) # addr of FFA of the item we want to be the last defined item

        # Adjust the pointers
        self.last_ffa = prev # the last defined word in the dictionary
        self.ptr      = ffa  # the H pointer, next free byte in dictionary


    #TODO: might be some functions for address calculations exposed as natives too!
    #beware, we might not be able to pass parameters to them, so defaults should be good?

    # functions for memory mapped registers

    def rd_d0(self):
        """Read the dictionary start address"""
        return self.start

    def rd_h(self):
        """Read the present H value"""
        return self.ptr

    def wr_h(self, number):
        """Write to the present H value"""
        self.ptr = number


class DataStack(Stack):
    """A stack for pushing application data on to """
    def __init__(self, mem, start, size):
        Stack.__init__(self, mem, start, size, growdirn=1, ptrtype=Stack.LASTUSED)

    # functions to allow memory mapped registers
    def rd_s0(self):
        """Read the DataStack start address"""
        return self.start

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
    def __init__(self, mem, start, size):
        Stack.__init__(self, mem, start, size, growdirn=-1, ptrtype=Stack.LASTUSED)

    # functions to allow memory mapped registers
    def rd_r0(self):
        """Read the ReturnStack start address"""
        return self.start

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
#    def __init__(self, mem, start, size, ptr, limit):
#        pass
#    # addr, erase, read, write, advance, retard


#class Pad():
#    def __init__(self, mem, start, size, ptr, limit):
#        pass
#    # addr, clear, read, write, advance, retard, reset, move?


#class BlockBuffers():
#    def __init__(self, mem, start, size, ptr, limit):
#        pass
#    # addr, read, write, erase
#    # cache index


#---- I/O ---------------------------------------------------------------------

#TODO: KeyboardInput
#class Input():
#    def __init__(self):
#        pass
#
#    def check(self):
#        return True
#
#    def read(self):
#        return '*'


#TODO: ScreenOutput
#class Output():
#    def __init__(self):
#        pass
#
#    def writech(self, ch):
#        print(ch)


class Disk():
    """An interface to reading and writing blocks in a nominated binary file"""

    BLOCK_SIZE = 1024
    def __init__(self, name):
        self.filename = name

    def read(self, blocknum):
        f = open(self.filename, "rb")
        f.seek(Disk.BLOCK_SIZE * blocknum)
        buf = f.read(Disk.BLOCK_SIZE)
        f.close()
        return buf

    def write(self, blocknum, bytes):
        f = open(self.filename, "wb")
        f.seek(Disk.BLOCK_SIZE * blocknum)
        f.write(bytes) # must be string or buffer, not list
        f.close()


#----- FORTH MACHINE INNER INTERPRETER ----------------------------------------

class Machine():
    """The inner-interpreter of the lower level/native FORTH words"""
    def __init__(self, parent):
        self.ip     = 0
        #self.outs   = parent.outs
        #self.ins   = parent.ins # TODO: Will need this eventually
        self.disk = parent.disk

    def boot(self):
        self.build_ds()       # builds memory abstractions
        self.build_dispatch() # builds magic routine/register dispatch table
        self.build_native()   # puts native routines/registers into DICT
        self.running = False
        return self

    def build_ds(self):
        """Build datastructures in memory"""

        MEM_SIZE  = 65536
        #          base,             dirn/size
        SV_MEM   = (0,               +1024      )
        EL_MEM   = (1024,            +0         )
        DICT_MEM = (1024,            +1024      )
        PAD_MEM  = (2048,            +80        )
        DS_MEM   = (8192,            -1024      ) # grows downwards
        TIB_MEM  = (8192,            +80        )
        RS_MEM   = (16384,           -1024      ) # grows downwards
        UV_MEM   = (16384,           +1024      )
        BB_MEM   = (65536-(1024*2),  +(1024*2)  )

        self.mem = Memory(mem)

        #   init sysvars
        svstart, svsize = self.mem.region("SV", SV_MEM)
        self.sv = SysVars(self.mem, svstart, svsize)

        #   init elective space??
        #elstart, elsize  = self.region("EL", at=, EV_MEM)
        #self.el = Elective(self.mem, elstart, elsize)

        #   init dictionary
        dictstart, dictsize = self.mem.region("DICT", DICT_MEM)
        self.dict = Dictionary(self.mem, dictstart, dictsize)

        #   init pad
        #padstart, padsize = self.mem.region("PAD", PAD_MEM)
        #self.pad = Pad(self.mem, padstart, padptr, padsize)

        #   init data stack
        dsstart, dssize = self.mem.region("DS", DS_MEM)
        self.ds = DataStack(self.mem, dsstart, dssize)

        #   init text input buffer
        #tibstart, tibsize = self.mem.region("TIB", TIB_MEM)
        #self.tib = TextInputBuffer(self.mem, tibstart, tibsize)

        #   init return stack
        rsstart, rssize = self.mem.region("RS", RS_MEM)
        self.rs = ReturnStack(self.mem, rsstart, rssize)

        #   init user variables (BASE, S0,...)
        #uvstart, uvsize = self.mem.region("UV", UV_MEM)
        #self.uv = UserVars(self.mem, uvstart, uvsize)

        #   init block buffers
        #bbstart, bbsize = self.mem.region("BB", BB_MEM)
        #self.bb = BlockBuffers(self.mem, bbstart, bbsize)

        #self.mem.show_map()

    def build_dispatch(self):
        """Build the dispatch table"""
        # dispatch table for rdbyte(addr), wrbyte(addr, byte), call(addr)
        #TODO: as most variables/consts are 16 bits, how are we going to double-map the addresses? H/L?
        #how will the forth machine access these, using two 8-bit memory accesses, or one
        #16 bit memory access (preferred)
        #in which case, we need to know that it *is* a 16 bit read, and generate a 'bus error' like thing
        #if it is not.

        self.dispatch = [
            #name      readfn,      writefn,      execfunction
            # 'NOP' should always be 0'th item
            ("NOP",    None,        None,         self.n_nop),       # CODE
            ("EMIT",   None,        None,         self.n_emit),      # CODE
            (".",      None,        None,         self.n_printtos),  # CODE
            ("SWAP",   None,        None,         self.ds.swap),     # CODE
            ("DUP",    None,        None,         self.ds.dup),      # CODE
            ("OVER",   None,        None,         self.ds.over),     # CODE
            ("ROT",    None,        None,         self.ds.rot),      # CODE
            ("DROP",   None,        None,         self.ds.drop),     # CODE
            ("+",      None,        None,         self.n_add),       # CODE
            ("-",      None,        None,         self.n_sub),       # CODE
            ("AND",    None,        None,         self.n_and),       # CODE
            ("OR",     None,        None,         self.n_or),        # CODE
            ("XOR",    None,        None,         self.n_xor),       # CODE
            ("*",      None,        None,         self.n_mult),      # CODE
            ("/",      None,        None,         self.n_div),       # CODE
            ("MOD",    None,        None,         self.n_mod),       # CODE
            #("FLAGS",  None,        None,         self.n_flags),     # CODE
            #("KEY",    None,        None,         self.n_key),       # CODE
            #("KEYQ",   None,        None,         self.n_keyq),      # CODE
            ("RBLK",   None,        None,         self.n_rblk),      # CODE
            ("WBLK",   None,        None,         self.n_wblk),      # CODE

            #("STORE",  None,        None,         self.n_store),     # CODE
            #("FETCH",  None,        None,         self.n_fetch),     # CODE
            #("STORE8", None,        None,         self.n_store8),    # CODE
            #("FETCH8", None,        None,         self.n_fetch8),    # CODE
            #("RDPFA",  None,        None,         self.n_rdpfa),     # CODE
            #("ADRUV",  None,        None,         self.n_adruv),     # CODE
            #("BRANCH", None,        None,         self.n_branch),    # CODE
            #("0BRANCH",None,        None,         self.n_0branch),   # CODE

            # DICT registers
            #("D0",     self.dict.rd_d0, None,     None),             # CONST
            #("H",      self.dict.rd_h, self.dict.wr_h, None),        # VAR

            # DATA STACK registers
            #("S0",     self.ds.rd_s0,  None,      None),             # CONST
            #("SP",     self.ds.rd_sp,  self.ds.wr_sp, None),         # VAR

            # RETURN STACK registers
            #("R0",     self.rs.rd_r0,  None,      None),             # CONST
            #("RP",     self.rs.rd_rp,  self.rs.wr_rp, None),         # VAR

            # SYSTEM VARS registers
            # start and ptr for sys vars (SV0, SVP)

            # USER VARS registers
            # start and ptr for user vars (UV0, UVP)

            # BLOCK BUFFER registers
            # start and size for block buffers (BB0, BBZ)

            # MISC
            #("IP",    self.rd_ip, self.wr_ip, None),               # VAR

            # Compiler support routines that can be called by high-level forth
            #("DOES>"),
            #(":"),
            #(";")
            #("VARIABLE")
            #("CONSTANT")

            # Compiler support routines that cannot be called by high-level forth
            # but can be destinations in a CFA.
            # Not registered in dictionary, this is flagged by first char of name=space
            # But this table can still be searched for addresses for internal use.
            (" DODOES",    None,   None,   self.n_dodoes),
            (" DOLIT",     None,   None,   self.n_dolit),
            #(" DOCOL")
            #(" DOCON",    None,   None,   self.n_docon),
            #(" DOVAR",    None,   None,   self.n_dovar),

            ("EXECUTE",    None,   None,   self.n_execute),
            ("EXIT",       None,   None,   self.n_exit),
            #(" QUIT")
            #(" BYE")
        ]

    def build_native(self):
        """Build the native dispatch table and machine"""

        #iterate through native.index and register all DICT entries for them
        for i in range(len(self.dispatch)):
            n = self.dispatch[i]
            name, rdfn, wrfn, execfn = n
            if name != None:
                # only named items get appended to the DICT
                # read only (a constant)
                # write only (not supported??)
                # read and write (a variable)
                if rdfn != None and wrfn == None:
                    DOCON = self.getIndex(" DOCON")
                    self.dict.create(nf=name, cf=DOCON, pf=[0], finish=True)
                if rdfn != None and wrfn != None:
                    DOVAR = self.getIndex(" DOVAR")
                    self.dict.create(nf=name, cf=DOVAR, pf=[0], finish=True)
                # other R/W combinations not created in the dict.

                if execfn != None:
                    # It's a native code call, with no parameters
                    self.dict.create(nf=name, cf=i, pf=[], finish=True)

    def getIndex(self, name):
        """Get the index address of a native routine.
        Note that hidden names are preceeded by a space"""
        for i in range(len(self.dispatch)):
            n = (self.dispatch[i])[0]
            if n == name:
                return i
        raise RuntimeError("native function not found:%s", name)

    # functions for memory mapped access to registers and routines

    #TODO: byte or number?
    def rdbyte(self, addr):
        """Look up read address in dispatch table, and dispatch if known"""
        if addr < len(self.dispatch):
            name, rdfn, wrfn, execfn = self.dispatch[addr]
            Debug.trace("reading native byte:%d %s" % (addr, name))
            if rdfn != None:
                return rdfn()
        Debug.fail("read from unknown native address: %x" % addr)

    #TODO: byte or number?
    def wrbyte(self, addr, byte):
        """Look up write address in dispatch table, and dispatch if known"""
        if addr < len(self.dispatch):
            name, rdfn, wrfn, execfn = self.dispatch[addr]
            Debug.trace("writing native byte:%d %s" % (addr, name))
            if wrfn != None:
                wrfn(byte)
                return
        Debug.fail("write to unknown native address: %x" % addr)

    def call(self, addr):
        """Look up the call address in the dispatch table, and dispatch if known"""
        if addr < len(self.dispatch):
            name, rdfn, wrfn, execfn = self.dispatch[addr]
            #Debug.trace("calling native fn:%d %s" % (addr, name))
            if execfn != None:
                execfn()
                return
        Debug.fail("call to unknown native address: %x" % addr)

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

    def n_docon(self):
        """Reads the 16 bit constant pointed to by PFA and pushes onto DS"""
        #TODO: The PFA of the current word needs to be accessible implicitly somewhere
        #the parser would have read out the CFA of the word to execute,
        #CFA+2 is the PFA for it, and that parameter is the constant value
        #which needs to be pushed onto the DS
        pass #TODO:
        Debug.unimplemented("n_docon")

    def n_dovar(self):
        """Reads the address of the variable, i.e. PFA, and pushes onto DS"""
        #TODO: The PFA of the current word needs to be accessible implicitly somewhere
        #the parser would have read out the CFA of the word to execute,
        #CFA+2 is the PFA for it, and that parameter is the variable address
        #which needs to be pushed onto the DS
        pass # TODO:
        Debug.unimplemented("n_dovar")

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
        #print("n1 %x n2 %x" % (n1, n2))
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
        Debug.unimplemented("n_flags")

    def n_keyq(self):
        """: n_KEYQ   ( -- ?)
        { ds_push8(kbhit) } ;"""
        pass #TODO: knit to Input()
        Debug.unimplemented("n_keyq")

    def n_key(self):
        """: n_KEY   ( -- c)
        { ds_push8(getch) } ;"""
        pass #TODO: knit to Input()
        Debug.unimplemented("n_key")

    def n_emit(self):
        """: n_EMIT   ( c -- )
        { putch(ds_pop8) } ;"""
        import sys
        ch = chr(self.ds.popn() & 0xFF) # TODO check Brodie
        sys.stdout.write(ch) # TODO use Output()
        #sys.stdout.flush()

    def n_printtos(self):
        """: n_PRINTTOS ( n --)
        { printnum(ds_pop16) } ;"""
        n = self.ds.popn()
        print("%d" % n) # TODO use Output()

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

    def n_rblk(self):
        """: n_RBLK  ( n a -- )
        { a=ds_pop; n=ds_pop; b=disk_rd(1024*b, mem, a, 1024) } ;"""
        addr = self.ds.popn()
        blocknum = self.ds.popn()

        bytes = self.disk.read(blocknum)
        if len(bytes) != Disk.BLOCK_SIZE:
            Debug.fail("Malformed disk response buffer")

        for b in bytes:
            self.mem.writeb(addr, ord(b))
            addr += 1

    def n_wblk(self):
        """: n_WBLK  ( n a -- )
        { a=ds_pop; n=ds_pop; disk_wr(1024*b, mem, a, 1024) } ;"""
        addr = self.ds.popn()
        blocknum = self.ds.popn()

        bytes = ""
        for i in range(Disk.BLOCK_SIZE):
            bytes += chr(self.mem.readb(addr))
            addr += 1

        self.disk.write(blocknum, bytes)

    #---- INTERFACE FOR HIGH-LEVEL FORTH WORDS -----

    def n_execute(self):
        """EXECUTE a high level address"""
        # ( pfa -- )
        #Debug.trace("EXECUTE")
        pfa = self.ds.popn()
        #Debug.trace(" pfa:%x" % pfa)
        # Don't assume DODOES, just in case it is a low level word!
        cfa = self.dict.pfa2cfa(pfa)
        #Debug.trace(" cfa:%x" % cfa)
        cf = self.mem.readn(cfa)
        self.ip = pfa
        #Debug.trace(" calling cf:%x" % cf)
        self.call(cf)

    def n_dodoes(self):
        """Repeatedly fetch and execute CFA's until EXIT"""
        #Debug.trace("DODOES")
        while self.running:
            #NEXT
            #Debug.trace("NEXT")
            # ip points to the cfa of the word to execute
            #Debug.trace(" fetch from ip:%x" % self.ip)
            cfa = self.mem.readn(self.ip)
            #Debug.trace(" cfa:%x" % cfa)
            cf = self.mem.readn(cfa)
            #Debug.trace(" cf:%x" % cf)
            self.rs.pushn(self.ip+2)
            self.call(cf)
            self.ip = self.rs.popn()

    def n_dolit(self):
        """Process an inline 16 bit literal and put it on DS"""
        #: n_DOLIT  ( -- )
        #{ip=rs_pop; n=mem_readn(ip); ds.pushn(n) ip+=2}
        #Debug.trace("dolit")
        ip = self.rs.popn()
        n = self.mem.readn(ip)
        self.ds.pushn(n)
        #Debug.trace("found literal: %d" % n)
        ip += 2
        self.rs.pushn(ip)

    def n_exit(self):
        """EXIT word - basically a high level Forth return"""
        """: n_EXIT   ( -- )
        { ip=rs_pop() } ;"""
        #Debug.trace("exit")

        # If nothing on stack, STOP #TODO need a cleaner way to stop
        if self.rs.getused() >= 2:
            self.ip = self.rs.popn()
            #Debug.trace("popped to IP: %x" % self.ip)
        else:
            #Debug.trace("Return stack empty, STOPPING ########")
            self.running = False


#----- FORTH OUTER INTERPRETER ------------------------------------------------

class Forth:
    def boot(self):
        #TODO: Forth or Machine, who owns the streams??
        #TODO how do ins and outs streams get redirected?
        #e.g. printer functions redirect outs to printing routines
        #e.g. input stream can come from a disk block when using LOAD
        #They are both encapsulated as classes, so they can just be
        #re-mapped by the appropriate routines, but who are their parent?

        #self.outs = Output()
        self.disk = Disk(DISK_FILE_NAME)
        self.machine = Machine(self).boot()

        return self


    # High level forth actions

    def create_word(self, name, *args):
        """Create a new high level dictionary entry containing a list of words.
             Note this is not a full defining compiler, just a word list
             that also understands numbers."""

        # Build the PF entries (all should contain CFAs)
        plist  = []
        DOLIT  = self.machine.dict.ffa2cfa(self.machine.dict.find(" DOLIT"))
        DODOES = self.machine.getIndex(" DODOES")

        for word in args:
            if type(word) == str:
                # It's a word, so lookup it's address in DICT
                ffa = self.machine.dict.find(word)
                cfa = self.machine.dict.ffa2cfa(ffa)
                plist.append(cfa)
            elif type(word) == int:
                # It's a number, so insert a DOLIT
                plist.append(DOLIT)
                plist.append(word)
        exit_cfa = self.machine.dict.ffa2cfa(self.machine.dict.find("EXIT"))
        plist.append(exit_cfa)

        # Now create the dictionary entry
        # CF=DODOES is implied for all high level word definitions
        #print(plist)
        self.machine.dict.create(
            nf=name,
            cf=DODOES,
            pf=plist,
            finish=True
        )
        #self.machine.dict.dumpraw()

    def execute_word(self, word):
        """Equivalent to ' word EXECUTE"""

        # Push PFA of word to execute on stack (equivalent to TICK)
        word_ffa = self.machine.dict.find(word)
        word_pfa = self.machine.dict.ffa2pfa(word_ffa)
        self.machine.ds.pushn(word_pfa)

        # Execute word who's PFA is on the stack (actually, EXECUTE)
        exec_ffa = self.machine.dict.find("EXECUTE")
        exec_cfa = self.machine.dict.ffa2cfa(exec_ffa)
        exec_cf  = self.machine.mem.readn(exec_cfa)
        self.machine.running = True
        self.machine.call(exec_cf)

        import sys
        sys.stdout.flush()


    #word parser      - parses a word from an input stream
    #output formatter - formats numbers etc
    #interpreter      - interprets words on an input stream
    #compiler         - compiles new high level definitions into the dictionary
    #assembler        - compiles new inline assembly code into the dictionary
    #editor           - text editor
    #language         - outer layers of language support


#----- RUNNER -----------------------------------------------------------------

forth = Forth().boot()

def create_word(*args):
    forth.create_word(*args)

def execute_word(*args):
    forth.execute_word(*args)

def test_hello():
    """output a "Hello world!" on stdout"""

    msg = "Hello world!\n"
    pfa = []
    for ch in msg:
        pfa.append(ord(ch))
        pfa.append("EMIT")

    forth.create_word("HELLO", *pfa)
    forth.execute_word("HELLO")

if __name__ == "__main__":
    test_hello()

# END
