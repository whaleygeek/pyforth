# forth.py  25/12/2015  (c) D.J.Whale
#
# An experiment to write a minimal FORTH language on top of Python.
# The main purpose of this is to study the design of the FORTH language
# by attempting a modern implementation of it.

import sys

#----- CONFIGURATION ----------------------------------------------------------

DISK_FILE_NAME = "forth_disk.bin"


#----- DEBUG ------------------------------------------------------------------

class Debug():
    """All debug messages should be routed via here"""
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
        raise RuntimeError("FAIL:"+ str(msg))


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


#----- BUFFER -----------------------------------------------------------------

class Buffer():
    """A general purpose memory buffer abstraction"""
    def __init__(self, storage, start=0, size=None):
        if size==None:
            size = len(storage)-start
        self.bytes   = storage
        self.start   = start
        self.size    = size

    #---- LOW LEVEL (overridable) storage access
    def __setitem__(self, key, value):
        self.bytes[key] = value

    def __getitem__(self, key):
        return self.bytes[key]

    #---- HIGH LEVEL storage access (always uses lower level)
    def readn(self, addr):
        """Read a cell sized 2 byte variable"""
        value = Number.from_bytes((self[addr], self[addr+1]))
        return value

    def readb(self, addr):
        """Read a 1 byte variable"""
        value = self[addr]
        return value

    def readd(self, addr):
        """Read a double length variable (4 byte, 32 bits)"""
        value = Number.from_bytes((self[addr], self[addr+1], self[addr+2], self[addr+3]))
        return value

    def writen(self, addr, value):
        """Write a cell sized 2 byte variable"""
        b0, b1 = Number.to_bytes(value)
        self[addr]   = b0
        self[addr+1] = b1

    def writeb(self, addr, value):
        """Write a 1 byte variable"""
        low = (value & 0xFF)
        self[addr] = low

    def writed(self, addr, value):
        """Write a double length variable (4 byte, 32 bits)"""
        b0, b1, b2, b3 = Double.to_bytes(value)
        self[addr]   = b0
        self[addr+1] = b1
        self[addr+2] = b2
        self[addr+3] = b3

    def dump(self, start, len):
        """Dump memory to stdout, for debug reasons"""
        #TODO do a proper 8 or 16 column address-prefixed dump
        for a in range(self.start+start, self.start+start+len):
            print("%4x:%2x" % (a, self[a]))


#----- MEMORY -----------------------------------------------------------------
#
# Access to a block of memory, basically a Python list.

MEMSIZE = 65536
mem = [0 for i in range(MEMSIZE)]

class Memory(Buffer):
    """An abstraction around a block of memory, with named and mapped regions"""
    def __init__(self, storage, size=None):
        Buffer.__init__(self, storage, start=0, size=size)
        self.map = []

    #---- LOW LEVEL (override) storage access
    #this routes via handler if a handler is provided for that region
    #if there is no handler, it calls back to the Buffer.__setitem__ and Buffer.__getitem__
    #for default handling

    def __setitem__(self, key, value):
        handler, start = self.handlerfor(key)
        if handler == None:
            # use default list access
            self.bytes[key] = value
        else:
            # use handler override
            handler[key-start] = value

    def __getitem__(self, key):
        handler, start = self.handlerfor(key)
        if handler == None:
            # use default handler
            return self.bytes[key]
        else:
            # use override handler
            return handler[key-start]

    def call(self, addr):
        handler, start = self.handlerfor(addr)
        if handler == None:
            Debug.fail("Address not callable:0x%x" % addr)
        handler.call(addr-start)

    def handlerfor(self, addr):
        for i in self.map:
            name, start, size, handler = i
            if addr >= start and addr <= start+size-1:
                #found the region
                #Debug.trace("hander:%s" % str(handler))
                return handler, start
        return None, None # use default handler

    def region(self, name, spec, handler=None):
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
        end = start + size - 1

        # check for overlaps with an existing region
        for i in self.map:
            iname, istart, isize, h = i
            iend = istart + isize - 1
            if (start >= istart and start <= iend) or (end >= istart and end <= iend):
                Debug.info("name:%s start:0x%x size:0x%x end:0x%x"     % (name, start, size, end))
                Debug.info("iname:%s istart:0x%x isize:0x%x iend:0x%x" % (iname, istart, isize, iend))

                raise ValueError("Region %s overlaps with %s" % (name, iname))

        size = abs(size)
        self.map.append((name, start, size, handler))
        return start, size

    def show_map(self):
        """Display the memory map on stdout"""

        #TODO must sort by real start address first, otherwise unused region calcs are wrong!
        print("MEMORY MAP")
        last_end = 0
        for i in self.map:
            name, start, size, handler = i
            if start != last_end:
                uname  = "UNUSED"
                ustart = last_end
                uend   = start-1
                usize  = uend-ustart-1
                print("%10s %5x %5x %5x" % (uname, ustart, uend, usize))
            print("%10s %5x %5x %5x %s" % (name, start, start+size-1, size, str(handler)))
            last_end = start + size
        #TODO: show any final unused space up to FFFF at end

    #TODO override low level read and write to check the handler


#----- INDEXED BUFFER ---------------------------------------------------------

class IndexedBufferException(Exception):
    pass #TODO: add reason message

class BufferUnderflow(IndexedBufferException):
    pass

class BufferOverflow(IndexedBufferException):
    pass


class IndexedBuffer(Buffer):
    """A memory mapped buffer that has an index pointer"""
    # Pointer strategies
    FIRSTFREE = False # ptr points to first free byte
    LASTUSED  = True  # ptr points to last used byte

    def __init__(self, storage, start, size, growdirn=1, ptrtype=None):
        Buffer.__init__(self, storage, start, size)
        if size < 0:
            Debug.fail("must not see -ve size here:0x%x" % size)
        # IndexedBuffer
        if growdirn > 0: # growdirn +ve
            growdirn = 1
        else: # growdirn -ve
            growdirn = -1

        if ptrtype == None:
            ptrtype = IndexedBuffer.FIRSTFREE

        self.growdirn = growdirn
        self.ptrtype  = ptrtype

        self.reset()

    def reset(self):
        """Reset the stack to empty"""
        last = self.start+self.size-1

        if self.growdirn > 0: # growdirn +ve
            if self.ptrtype == IndexedBuffer.FIRSTFREE:
                self.ptr = self.start
            else: # LASTUSED
                self.ptr = self.start-1

        else: # growdirn -ve
            if self.ptrtype == IndexedBuffer.FIRSTFREE:
                self.ptr = last
            else: #LASTUSED
                self.ptr = last+1

    def assertPtrValid(self, ptr):
        #TODO: This is a reason to subclass pointer behaviour,
        #TODO: all these different checks at runtime is painful!

        if self.ptrtype == IndexedBuffer.FIRSTFREE:
            if self.growdirn > 0:
                if ptr > self.start + (self.size): # one extra allowed at right hand side
                    #Debug.trace("firstfree,+ve-grow,overflow")
                    raise BufferOverflow
                elif ptr < self.start:
                    #Debug.traceprint("firstfree,+ve-grow,underflow")
                    raise BufferUnderflow
            else: # growdirn -ve
                if ptr < self.start-1: # one extra allowed at left hand side
                    #Debug.traceprint("firstfree,-ve-grow,overflow")
                    raise BufferOverflow
                elif ptr > self.start + (self.size-1):
                    #Debug.traceprint("firstfree,-ve-grow,underflow")
                    raise BufferUnderflow

        else: # LASTUSED
            if self.growdirn > 0:
                if ptr > self.start + (self.size-1): # must not exceed buffer
                    #Debug.trace("lastused,+ve-grow,overflow start:0x%x size:0x%x ptr:0x%x" % (self.start, self.size, ptr))
                    raise BufferOverflow
                elif ptr < (self.start-1): # one extra at left hand side
                    #Debug.trace("lastused,+ve-grow,underflow")
                    raise BufferUnderflow
            else: # growdirn -ve
                if ptr < self.start:
                    #Debug.trace("lastused,-ve-grow,overflow")
                    raise BufferOverflow
                elif ptr > self.start + (self.size):
                    Debug.trace("lastused,-ve-grow,underflow ptr:0x%x start:0x%x size:0x%x" % (ptr, self.start, self.size))
                    raise BufferUnderflow


    def fwd(self, bytes):
        rel = bytes * self.growdirn
        new = self.ptr + rel
        self.assertPtrValid(new)
        self.ptr = new
        return self.ptr

    def back(self, bytes):
        rel = bytes * self.growdirn
        new = self.ptr - rel
        self.assertPtrValid(new)
        self.ptr = new
        return self.ptr

    def absaddr(self, rel, size):
        """Work out correct start address of a rel byte index starting at this position, relative to TOS"""
        #rel should reference the relative distance in bytes back from TOS (0 is TOS for all data sizes)

        if self.growdirn > 0: # +ve growth
            if self.ptrtype == IndexedBuffer.FIRSTFREE:
                return self.ptr - rel - size
            else: # LASTUSED
                return self.ptr - rel - (size-1)

        else: # -ve growth
            if self.ptrtype == IndexedBuffer.FIRSTFREE:
                return self.ptr + rel + 1
            else: #LASTUSED
                return self.ptr + rel

    def getused(self):
        """Get the number of bytes used on the stack"""
        if self.growdirn > 0: # +ve growth
            if self.ptrtype == IndexedBuffer.FIRSTFREE:
                u = self.ptr - self.start
            else: # LASTUSED
                u = (self.ptr+1) - self.start

        else: # -ve growth
            if self.ptrtype == IndexedBuffer.FIRSTFREE:
                u = (self.start+self.size-1) - self.ptr
            else: # LASTUSED
                u = (self.start+self.size) - self.ptr

        return u

    def getfree(self):
        Debug.fail("Unimplemented") #TODO

    def write(self, rel, bytes):
        """Write a list of bytes, at a specific byte index from TOS"""
        size = len(bytes)
        ptr = self.absaddr(rel, size) # is sensitive to ptr growdirn
        for b in bytes:
            self.bytes[ptr] = b
            ptr += 1

    def read(self, rel, size):
        """Read a list of bytes, at a specific byte index from TOS"""
        bytes = []
        ptr = self.absaddr(rel, size)
        for i in range(size):
            b = self.bytes[ptr]
            bytes.append(b)
            ptr += 1
        return bytes

    def appendn(self, number):
        pass #TODO: call write
        Debug.fail("unimplemented")

    def appendb(self, number):
        pass #TODO: call write
        Debug.fail("unimplemented")

    def appends(self, string):
        """Append a string to the buffer"""
        l = len(string)
        self.fwd(l)
        bytes = []
        for ch in string:
            bytes.append(ord(ch))
        self.write(0, bytes)


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

    # Helpful routines for memory mapping pointer register

    def rd_p(self, offset):
        if offset not in [0,1]:
            raise ValueError("Out of range offset:0x%x" % offset)
        bytes = Number.to_bytes(self.ptr)
        return bytes[offset]

    def wr_p(self, offset, byte):
        if offset not in [0,1]:
            raise ValueError("Out of range offset:0x%x" % offset)
        b0, b1 = Number.to_bytes(self.ptr)
        bytes = [b0, b1]
        bytes[offset] = byte
        self.ptr = Number.from_bytes(bytes)

#----- PAD --------------------------------------------------------------------

#class Pad(IndexedBuffer): # Note this is dynamically positioned relative to some other structure
#what other value does this class add? Is it the dynamic moving nature?
#i.e. it's pointer is always relative to some pointer of some other Buffer
#Perhaps it's a general concept, a BrotherBuffer?? RelativeBuffer?
#    def __init__(self, storage, start, size):
#       #TODO need a brother Buffer, for the pointer to be relative to.
#        IndexedBuffer.__init__(self, storage, start, size)
#
#   get/set pointer (knit up to a brother buffer and it's pointer)


#----- BLOCK BUFFERS ----------------------------------------------------------

class BlockBuffers(Buffer):
    """An abstraction in memory for disk block buffers"""
    def __init__(self, storage, start, size, numbuffers, buffersize):
        Buffer.__init__(storage, start, size)
        #TODO: surely this is related to 'size'?
        self.numbuffers = numbuffers
        self.buffersize = buffersize
        #TODO: dirty/clean flags, 1 for each buffer
        #TODO: which block is in which buffer, number for each buffer

    def is_dirty(self, bufidx):
        pass

    def is_clean(self, bufidx):
        pass

    def set_dirty(self, bufidx):
        pass

    def set_clean(self, bufidx):
        pass

    def loadinto(self, bufidx, blockidx):
        # block 0 means not loaded
        # Note that FORTH does not allow block 0 to be loaded.
        # this is usually ok, as it's usually a boot track on native systems.
        pass

    def holds(self, bufidx):
        pass


#----- STACK ------------------------------------------------------------------

class Stack(IndexedBuffer):
    """A general purpose stack abstraction to wrap around memory storage"""
    # bytes are always stored in the provided order, in increasing memory locations

    TOS = 0 # TOP OF STACK INDEX

    def __init__(self, storage, start, size, growdirn, ptrtype):
        IndexedBuffer.__init__(self, storage, start, size, growdirn, ptrtype)

    def grow(self, bytes):
        """Expand the stack by a number of bytes"""
        self.fwd(bytes)

    def shrink(self, bytes):
        """Shrink the stack by a number of bytes"""
        self.back(bytes)

    def dumpraw(self):
        if self.growdirn != 1:
            Debug.fail("negative growth not dumpable yet")

        for addr in range(self.start, self.ptr+1):
            b = self.storage[addr]
            if b > 32 and b < 127:
                ch = chr(b)
            else:
                ch = '?'
            print("0x%x:0x%x  (%c)" % (addr, b, ch)) #ERROR, something storing a str?

    def push(self, bytes):
        """Push a list of bytes"""
        size = len(bytes)
        self.grow(size)
        self.write(rel=0, bytes=bytes)
        return self.absaddr(self.TOS, size)

    def pop(self, size):
        """Pop a list of bytes of required size"""
        bytes = self.read(rel=0, size=size)
        self.shrink(size)
        return bytes

    def pushb(self, byte):
        """Push an 8 bit byte onto the stack"""
        return self.push((byte, ))

    def pushn(self, number):
        """Push a 16 bit number onto the stack"""
        b0, b1 = Number.to_bytes(number)
        return self.push((b0, b1))

    def pushd(self, double):
        """Push a 32 bit double onto the stack"""
        b0, b1, b2, b3 = Double.to_bytes(double)
        return self.push((b0, b1, b2, b3))

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


class ForthStack(Stack):
    """A Forth stack, which has additional useful operations"""
    def __init__(self, storage, start, size, growdirn, ptrtype):
        Stack.__init__(self, storage, start, size, growdirn, ptrtype)

    # All entries on a ForthStack are at least 1 cell in size.
    def pushb(self, byte):
        Debug.fail("Byte push on to a Forth stack is not supported")

    def popb(self):
        Debug.fail("Byte pop from a Forth stack is not supported")

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

    def nip(self):
        """Remove item just under TOS"""
        # ( n1 n2 -- n2)
        n = self.getn(0)
        self.setn(1, n)
        self.popn()

    def tuck(self):
        """TUCK copies TOS to under what it is on top of"""
        # ( n2 n1 -- n1 n2 n1)
        n1 = self.getn(0)
        n2 = self.getn(1)
        self.setn(1, n1)
        self.setn(0, n2)
        self.pushn(n1)


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


#class SysVars(Vars):
#    #TODO: not sure yet what system variables are used for
#    def __init__(self, storage, start, size):
#        Vars.__init__(self, storage, start, size)


class UserVars(Vars):
    """An abstraction for user accessible variables"""
    #TODO: should be one copy per user task.
    #e.g. BASE
    def __init__(self, storage, start, size):
        Vars.__init__(self, storage, start, size)


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

        # for easy debug
        self.cfa_cache = {}
        self.pfa0_cache = {}

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

        # if cf/pf provided, fill them in too
        if cf != None:
            self.allot()
            self.store(cf)
            #for fast debug
            cfa = (self.ptr-1)
            self.cfa_cache[cfa] = nf

        #for fast debug
        pfa0 = self.ptr+1
        self.pfa0_cache[pfa0] = nf

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
            Debug.fail("Trying to finish an already finished dict defn at:%d", self.last_ffa)

        ff = self.bytes.readb(self.defining_ffa)
        self.bytes.writeb(self.defining_ffa, ff & ~ Dictionary.FLAG_DEFINING)
        # advance end pointer
        self.last_ffa = self.defining_ffa
        self.defining_ffa = None

    def readname(self, addr, count):
        buf = ""
        for i in range(count):
            buf += chr(self.bytes.readb(addr))
            addr += 1
        return buf

    def cfa2name(self, cfa):
        return self.cfa_cache[cfa]

    def pfa02name(self, pfa0):
        return self.pfa0_cache[pfa0]

    def dump(self):
        """Dump the dictionary in reverse order from self.last_ffa back to NULL"""
        print("\nDICTIONARY")
        buf = "start:0x%x size:0x%x ptr:0x%x last_ffa:0x%x" % (self.start, self.size, self.ptr, self.last_ffa)
        if self.defining_ffa != None:
            buf += " defining_ffa:0x%x" % self.defining_ffa
        print(buf)

        ffa = self.last_ffa
        while True:
            ptr = ffa
            ff = self.bytes.readb(ptr)
            if ff == 0:
                return # FINISHED

            #print("-" * 40)
            #### FF - Flags Field
            ff_buf = "ffa:0x%x " % ffa
            if ff & Dictionary.FLAG_IMMEDIATE: buf += "im "
            if ff & Dictionary.FLAG_DEFINING:  buf += "def "
            if ff & Dictionary.FLAG_UNUSED:    buf += "un "
            count = ff & Dictionary.FIELD_COUNT
            ff_buf += "sz:" + str(count)
            #print(ff_buf)
            ptr += 1

            #### NF - Name Field
            nfa = ptr
            nf = self.readname(nfa, count)
            nf_buf = "nfa:0x%x (%s)" % (nfa, nf)
            #print(nf_buf)
            ptr += count

            #### LF - Link Field
            lfa = ptr
            lf = self.bytes.readn(lfa)
            prev_nf = self.readname(lf+1, self.bytes.readb(lf) & Dictionary.FIELD_COUNT)
            lf_buf = "lfa:0x%x=0x%x->(%s)" % (lfa, lf, prev_nf)
            #print(lf_buf)
            ptr += 2

            #### CF - Code Field
            cfa = ptr
            cf = self.bytes.readn(cfa)
            #TODO: cf_name comes from machine.dispatch
            cf_buf = "cfa:0x%x=0x%x" % (cfa, cf)
            #print(cf_buf)
            ptr += 2

            #### PF - Parameter Field
            #TODO:Need to know how to sense the end of this?
            #There is no length byte, so depends on CF value
            #could look for ptr matching prev ptr, close enough, but not guaranteed
            pfa = ptr
            # dump first one for now
            pf = self.bytes.readn(pfa)
            #note, this is the CFA of the item. How do we back-step to it's NF?
            #-2 is the LF
            #but before that is arbitrary ascii chars, and a single FF field which
            #might actually be a printable ascii char, so it's ambiguous.
            #Can't assume LF's are sequential, when vocabularies in use.
            #TODO: could always store a zero after FF (PAD) then we would be able to
            #backscan for start of string.
            pf_buf = "pfa:0x%x=0x%x" % (pfa, pf)
            #print(pf_buf)

            # Print a single line dump of dict record
            print(ff_buf + " " + nf_buf + " " + lf_buf + " " + cf_buf + " " + pf_buf)
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
        lf = self.bytes.readn(lfa)
        return lf

    def nfa(self, ffa):
        """relative skip from ffa to nfa"""
        return ffa+1

    def lfa(self, nfa):
        """relative skip from nfa to lfa"""
        ff = self.bytes.readb(nfa)
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

    def cfa2pfa(self, cfa):
        return cfa+2 # forward skip to pfa

    def ffa2nfa(self, ffa):
        """relative skip from ffa to nfa"""
        return ffa+1

    def ffa2lfa(self, ffa=None):
        """relative skip from ffa to lfa"""
        if ffa == None:
            ffa = self.last_ffa
        ff = self.bytes.readb(ffa)
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
            ff = self.bytes.readb(ffa)
            if ff == 0:
                #Debug.trace("Could not find word in dict:'%s'" % name)
                return 0 # NOT FOUND
            # check if still defining
            if ff & Dictionary.FLAG_DEFINING == 0:
                # check if name in NFA matches
                nfa = self.ffa2nfa(ffa)
                count = ff & Dictionary.FIELD_COUNT
                this_name = ""
                for i in range(count):
                    this_name += chr(self.bytes.readb(nfa+i))
                if this_name == name:
                    return ffa # FOUND

            # Still definining, or did not match, move to previous entry
            ffa = self.prev(ffa)

    def forget(self, name):
        """Forget all words up to and including this name"""

        ffa = self.find(name)
        if ffa == 0:
            Debug.fail("Could not find word to forget it:%s", name)

        # ffa is the FFA of the first item to delete (the new dict ptr)
        prev = self.prev(ffa) # addr of FFA of the item we want to be the last defined item

        # Adjust the pointers
        self.last_ffa = prev # the last defined word in the dictionary
        self.ptr      = ffa  # the H pointer, next free byte in dictionary


    #TODO: might be some functions for address calculations exposed as natives too!
    #beware, we might not be able to pass parameters to them, so defaults should be good?


class DataStack(ForthStack):
    """A stack for pushing application data on to """
    def __init__(self, mem, start, size):
        ForthStack.__init__(self, mem, start, size, growdirn=1, ptrtype=Stack.LASTUSED)

    #def pushn(self, number):
    #    ForthStack.pushn(self, number)
    #    print("DS PUSH, size 0x%x " % self.getused())


class ReturnStack(ForthStack):
    """A stack for high level forth call/return addresses"""
    def __init__(self, mem, start, size):
        ForthStack.__init__(self, mem, start, size, growdirn=-1, ptrtype=Stack.LASTUSED)

    #def pushn(self, number):
    #    ForthStack.pushn(self, number)
    #    print("RS PUSH, size 0x%x " % self.getused())



#---- I/O ---------------------------------------------------------------------

class Input():
    def __init__(self):
        self.buf = ""

    def clear(self):
        self.buf = ""

    def set(self, string):
        self.buf = string

    def append(self, ch):
        self.buf += ch

    def waiting(self):
        return len(self.buf)

    def getch(self, wait=True):
        if len(self.buf) > 0:
            c = self.buf[0]
            #print("getch returns:%s" % c)
            self.buf = self.buf[1:]
            return c
        if wait:
            if len(self.buf) == 0:
                Debug.fail("WAIT on mock buffer called")
        return None # nothing in buffer


class KeyboardInput(Input):
    """A way to poll and get characters from the keyboard"""

    def waiting(self):
        Debug.fail("Not yet implemented")

    eof = False

    def getch(self):
        if self.eof:
            Debug.fail("EOF followed by another getch()")
        while True:
            ch = sys.stdin.read(1) # blocking, line buffered
            if ch == "": # EOF
                #Debug.trace("EOF on Keyboard input stream")
                self.eof = True
                return chr(4) # CTRL-D
            if ch == '\r':
                #print("strip return char")
                pass # strip return(13), interpret newline(10) #TODO: is this correct?
            return ch

class Output():
    def __init__(self):
        self.buf = ""

    def writech(self, ch):
        self.buf += ch

    def writen(self, number):
        self.buf += str(number)

    def get(self):
        return self.buf

    def clear(self):
        s = self.buf
        self.buf = ""
        #print("%s" % s)


class ScreenOutput():
    """A way to output characters to the screen"""

    def __init__(self):
        pass

    def writech(self, ch):
        import sys
        sys.stdout.write(ch)

    def writen(self, number):
        import sys
        sys.stdout.write(str(number))


class Disk(): #TODO: DiskFile(Disk) - to allow mocking
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

class NvMem():
    """Provides access to native variables mapped into memory"""

    def __init__(self, parent, start):
        self.map = [
            # name,   o, l,   rd,                   wr
            #("TREG",  0, 2,   parent.rd_test,       parent.wr_test),
            ("IP",    2, 2,   parent.rd_ip,         parent.wr_ip),
            ("H",     4, 2,   parent.dict.rd_p,     parent.dict.wr_p),
            ("SP",    6, 2,   parent.ds.rd_p,       parent.ds.wr_p),
            ("RP",    8, 2,   parent.rs.rd_p,       parent.rs.wr_p),
            ("UVP",  10, 2,   parent.uv.rd_p,       parent.uv.wr_p),
            ("BASE", 12, 1,   parent.rd_base,       parent.wr_base),
            #13

            #("SVP",  12, 2,   parent.sv.rd_p,       parent.sv.wr_p),
            #example of a large buffer
            #("BUF",  2, 100,   parent.rd_buf,        parent.wr_buf),
            # : FLAGS  ( -- n)                     /ADD  n_RDPFA  VAR    Address of flags variable
        ]
        self.register_in_dict(parent, start)

    def register_in_dict(self, parent, start):
        """Register any native routines that want a DICT entry"""

        RDPFA = parent.getNativeRoutineAddress(" RDPFA")
        # iterate through map and register all DICT entries for them
        for item in self.map:
            name, ofs, size, rd, wr = item
            if name != None:
                # only named items get appended to the DICT
                addr = start + ofs
                parent.dict.create(nf=name, cf=RDPFA, pf=[addr], finish=True)

    def find(self, offset):
        """Search through map and find the region entry that holds this offset"""
        for item in self.map:
            name, ofs, size, rd, wr = item
            if offset >= ofs and offset <= (ofs+size-1):
                return item
        return None

    def __setitem__(self, offset, value):
        item = self.find(offset)
        if item == None:
            raise ValueError("Unknown offset in region: 0x%x" % offset)
        name, start, ofs, rd, wr = item
        if wr==None:
            Debug.fail("set: NvMem offset 0x%x does not support write function" % offset)
        wr(offset, value)

    def __getitem__(self, offset):
        item = self.find(offset)
        if item == None:
            raise ValueError("Unknown offset in region: 0x%x" % offset)
        name, start, ofs, rd, wr = item
        if rd==None:
            Debug.fail("get: NvMem offset 0x%x does not support read function" % offset)
        return rd(offset)


class NvRoutine():
    """Provides access to native routines mapped into memory"""
    def __init__(self, parent, start):
        self.map = [
            ("NOP",        parent.n_nop),       # 00 must always be first entry
            ("ABORT",      parent.n_abort),     # 01
            ("!",          parent.n_store),     # 02
            ("@",          parent.n_fetch),     # 03
            ("C!",         parent.n_store8),    # 04
            ("C@",         parent.n_fetch8),    # 05
            ("EMIT",       parent.n_emit),      # 06
            (".",          parent.n_printtos),  # 07
            ("SWAP",       parent.ds.swap),     # 08
            ("DUP",        parent.ds.dup),      # 09
            ("OVER",       parent.ds.over),     # 0A
            ("ROT",        parent.ds.rot),      # 0B
            ("DROP",       parent.ds.drop),     # 0C
            ("NIP",        parent.ds.nip),      # 0D
            ("TUCK",       parent.ds.tuck),     # 0E
            ("+",          parent.n_add),       # 0F
            ("-",          parent.n_sub),       # 10
            ("AND",        parent.n_and),       # 11
            ("OR",         parent.n_or),        # 12
            ("XOR",        parent.n_xor),       # 13
            ("*",          parent.n_mult),      # 14
            ("/",          parent.n_div),       # 15
            ("MOD",        parent.n_mod),       # 16
            ("0=",         parent.n_0eq),       # 17
            ("NOT",        parent.n_not),       # 18
            ("0<",         parent.n_0lt),       # 19
            ("0>",         parent.n_0gt),       # 1A
            ("RBLK",       parent.n_rblk),      # 1B
            ("WBLK",       parent.n_wblk),      # 1C
            ("BRANCH",     parent.n_branch),    # 1D
            ("0BRANCH",    parent.n_0branch),   # 1E
            (" RDPFA",     parent.n_rdpfa),     # 1F
            (" DODOES",    parent.n_dodoes),    # 20
            (" DOLIT",     parent.n_dolit),     # 21
            (" DOSTR",     parent.n_dostr),     # 22
            ("EXECUTE",    parent.n_execute),   # 23
            ("EXIT",       parent.n_exit),      # 24
            ("KEY",        parent.n_key),       # 25
            ("FIND",       parent.n_find),      # 26
            ("NUMBER",     parent.n_number),    # 27
            ("BYE",        parent.n_bye),       # 28
            #("KEYQ",       parent.n_keyq),
            #(" DOCOL",    parent.n_docol),
            #(" DOCON",     parent.n_docon),
            #(" DOVAR",     parent.n_dovar),
            #(" ADRUV",     parent.n_adruv),
            #(" QUIT",      parent.n_quit),
            #("DOES>",      parent.n_does),
            #(":",          parent.n_colon),
            #(";",          parent.n_semicolon),
            #("VARIABLE",   parent.n_variable),
            #("CONSTANT",   parent.n_constant),
            #("U<",         parent.n_ult),
            #("FLAGS",      parent.n_flags),
        ]
        
        self.register_in_dict(parent, start)

    def register_in_dict(self, parent, start):
        """Register any native routines that want a DICT entry"""

        # iterate through map and register all DICT entries for them
        for i in range(len(self.map)):
            n = self.map[i]
            name, execfn = n
            if name != None:
                # only named items get appended to the DICT
                if execfn != None:
                    # It's a native code call, with no parameters
                    addr = i + start
                    parent.dict.create(nf=name, cf=addr, pf=[], finish=True)

    def getIndex(self, name):
        """Get the offset index of a native routine."""
        # Note: Hidden names are preceeded by a space
        # Note: This is an index into the table, not an absolute address
        for i in range(len(self.map)):
            n = (self.map[i])[0]
            if n == name:
                return i
        Debug.fail("native function not found:%s", name)

    def call(self, index):
        """Look up the call index in the dispatch table, and dispatch if known"""
        if index < len(self.map):
            name, execfn = self.map[index]
            #Debug.trace("calling native fn:%d %s" % (addr, name))
            if execfn != None:
                execfn()
                return
        Debug.fail("call to unknown native address offset: 0x%x" % index)

    def __setitem__(self, key, value):
        Debug.fail("Tried to write to NvRoutine memory offset:0x%x value:0x%x" % (key, value))

    def __getitem__(self, key):
        Debug.fail("Tried to read from NvRoutine memory offset:0x%x" % key)


class Machine():
    """The inner-interpreter of the lower level/native FORTH words"""

    FALSE = 0x0000
    TRUE  = 0xFFFF #TODO: or -1 (not the same in python, but same in Forth)

    def __init__(self, parent):
        self.ip     = 0
        self.outs   = parent.outs
        self.ins    = parent.ins
        self.disk   = parent.disk
        self.base   = 10

    def boot(self):
        self.build_ds()       # builds memory abstractions
        self.running = False
        self.limit = None     # how many times round DODOES before early terminate?
        self.exits_pending = 0
        return self

    def build_ds(self):
        """Build datastructures in memory"""
        #           base,             dirn/size
        NR_MEM   = (0x0000,          +256)     # native routines
        NV_MEM   = (0x0100,          +256)     # native variables
        DICT_MEM = (0x0400,          +4096)    # dictionary
        DS_MEM   = (0x8000,          -1024)    # data stack
        TIB_MEM  = (0x8000,          +80)      # text input buffer
        RS_MEM   = (0xA000,          -1024)    # return stack
        UV_MEM   = (0xA000,          +1024)    # user variables

        # static buffer for now, eventually it will have to float dynamically
        PAD_MEM  = (0xB000,          +80       )    # pad

        #BB_MEM   = (65536-(1024*2),  +(1024*2)  )    # block buffers
        #SV_MEM    = (0,               +1024     )    # system variables
        #EL_MEM    = (1024,            +0        )    # electives

        self.mem = Memory(mem)

        # Init sysvars
        #svstart, svsize = self.mem.region("SV", SV_MEM)
        #self.sv = SysVars(self.mem, svstart, svsize)

        # Init elective space??
        #elstart, elsize  = self.region("EL", at=, EV_MEM)
        #self.el = Elective(self.mem, elstart, elsize)

        # Init dictionary
        self.dictstart, self.dictsize = self.mem.region("DICT", DICT_MEM)
        self.dict = Dictionary(self.mem, self.dictstart, self.dictsize)

        # Init pad
        self.padstart, self.padsize = self.mem.region("PAD", PAD_MEM)
        self.pad = Buffer(self.mem, self.padstart, self.padsize)

        # Init data stack
        self.dsstart, self.dssize = self.mem.region("DS", DS_MEM)
        self.ds = DataStack(self.mem, self.dsstart, self.dssize)

        # Init text input buffer
        self.tibstart, self.tibsize = self.mem.region("TIB", TIB_MEM)
        self.tib = IndexedBuffer(self.mem, self.tibstart, self.tibsize)

        # Init return stack
        self.rsstart, self.rssize = self.mem.region("RS", RS_MEM)
        self.rs = ReturnStack(self.mem, self.rsstart, self.rssize)

        # Init user variables (BASE, S0,...)
        self.uvstart, self.uvsize = self.mem.region("UV", UV_MEM)
        self.uv = UserVars(self.mem, self.uvstart, self.uvsize)

        # Init block buffers
        #bbstart, bbsize = self.mem.region("BB", BB_MEM)
        #self.bb = BlockBuffers(self.mem, bbstart, bbsize)

        # Init Native Routines (last so that they can refer to other data structures)
        self.nr_handler = NvRoutine(self, NR_MEM[0])
        self.nrstart, self.nrsize = self.mem.region("NR", NR_MEM, handler=self.nr_handler)

        # Init Native Variables (last so they can refer to other data structures)
        self.nv_handler = NvMem(self, NV_MEM[0])
        self.nvstart, self.nvsize = self.mem.region("NV", NV_MEM, handler=self.nv_handler)

        #self.mem.show_map()

    def getNativeRoutineAddress(self, name):
        # Note: This will fail with an exception if it can't find the name
        addr = self.nr_handler.getIndex(name)
        addr += self.nrstart
        return addr

    def call(self, addr):
        self.mem.call(addr)

    # functions for memory mapped registers

    def rd_ip(self, offset):
        if offset not in [0,1]:
            raise ValueError("Out of range offset:0x%x" % offset)
        bytes = Number.to_bytes(self.ip)
        return bytes[offset]

    def wr_ip(self, offset, byte):
        if offset not in [0,1]:
            raise ValueError("Out of range offset:0x%x" % offset)
        b0, b1 = Number.to_bytes(self.ip)
        bytes = [b0, b1]
        bytes[offset] = byte
        self.ip = Number.from_bytes(bytes)

    def rd_base(self):
        return self.base

    def wr_base(self, value):
        self.base = value

    # temporary testing
    testvalue = 0

    def rd_test(self, offset):
        if offset not in [0,1]:
            raise ValueError("Out of range offset:0x%x" % offset)

        # Every read increments the counter
        prev = self.testvalue
        self.testvalue = (self.testvalue + 1) & 0xFF

        bytes = Number.to_bytes(prev)
        byte = bytes[offset]
        #Debug.trace("rd_test ofs 0x%x byte 0x%x" % (offset, byte))
        return byte

    def wr_test(self, offset, byte):
        #Debug.trace("wr_test ofs 0x%x byte 0x%x" % (offset, byte))
        if offset not in [0,1]:
            raise ValueError("Out of range offset:0x%x" % offset)
        b0, b1 = Number.to_bytes(self.testvalue)
        bytes = [b0, b1]
        bytes[offset] = byte
        self.testvalue = Number.from_bytes(bytes)

    # functions for native code

    def n_nop(self):
        """Do nothing"""
        pass

    def n_abort(self):
        """Empty RS and DS and finish"""
        self.ds.reset()
        self.rs.reset()
        self.running = False #TODO: should return to top level interpreter, not stop the whole machine

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
        pass # TODO:
        Debug.unimplemented("n_dovar")

    def n_store(self):
        """: n_STORE   ( n a -- )
        { a=ds_pop; n=ds_pop mem[a]=n0; mem[a+1]=n1} ;"""
        a = self.ds.popn()
        n = self.ds.popn()
        #print("STORE a:0x%x n:0x%x" % (a, n))
        self.mem.writen(a, n)

    def n_fetch(self):
        """: n_FETCH  ( a -- n)
        { a=ds_pop; n0=mem[a]; n1=mem[a+1]; ds_push8(n0); ds_push8(n1) } ;"""
        #Debug.trace("###FETCH")
        a = self.ds.popn()
        n = self.mem.readn(a)
        #print("FETCH a:0x%x n:0x%x" % (a, n))
        self.ds.pushn(n)

    def n_store8(self):
        #TODO check brodie, what does this get from stack, a 16bit or an 8bit?
        """: n_STORE8  ( b a -- )
        { a=ds_pop; b=ds_pop; mem[a]=b } ;"""
        a = self.ds.popn()
        b = self.ds.popn() & 0xFF
        #print("STORE8 a:0x%x b:0x%x" % (a, b))
        self.mem.writeb(a, b)

    def n_fetch8(self):
        #TODO check brodie, what does this put on stack, a 16 bit or an 8 bit?
        """: n_FETCH8   ( a -- b)
        { a=ds_pop; b=mem[a]; ds_push8(b) } ;"""
        a = self.ds.popn()
        b = self.mem.readb(a)
        #print("FETCH8 a:0x%x b:0x%x" % (a, b))
        self.ds.pushn(b)

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

    def n_0eq(self):
        """: 0=   ( n -- ?)
        { n=popn; if n==0: pushn(FORTH_TRUE) else: pushn(FORTH_FALSE) } ;"""
        n = self.ds.popn()
        if n==0:
            self.ds.pushn(Machine.TRUE)
        else:
            self.ds.pushn(Machine.FALSE)

    def n_not(self):
        """: NOT  ( ? -- ?)
        { f=popn; if n==FORTH_FALSE: pushn(FORTH_TRUE) else: pushn(FORTH_FALSE) } ;"""
        f=self.ds.popn()
        if f==Machine.FALSE:
            self.ds.pushn(Machine.TRUE)
        else:
            self.ds.pushn(Machine.FALSE)

    def n_0lt(self):
        """: 0<   ( n -- ?)
        { n=popn; if n<0: pushn(FORTH_TRUE) else: pushn(FORTH_FALSE) } ;"""
        n = self.ds.popn()
        #TODO: Needs a SIGNED COMPARISON
        if n<0:
            self.ds.pushn(Machine.TRUE)
        else:
            self.ds.pushn(Machine.FALSE)

    def n_0gt(self):
        """: 0>   ( n -- ?)
        { n=popn; if n>0: pushn(FORTH_TRUE) else: pushn(FORTH_FALSE) } ;"""
        #TODO: Needs a SIGNED COMPARISON
        n = self.ds.popn()
        if n>0:
            self.ds.pushn(Machine.TRUE)
        else:
            self.ds.pushn(Machine.FALSE)

    def n_ult(self):
        """: U<   ( u1 u2 -- ?)
        { u2=popn; u1=popn; u2&=0xFFFF; u1&=0xFFFF; if u1<u2: pushn(FORTH_TRUE) else: pushn(FORTH_FALSE) } ;"""
        Debug.fail("Not implemented")
        #TODO: Needs an UNSIGNED COMPARISON

    def n_flags(self):
        """: n_FLAGS   ( -- )
        # { mem[FLAGS]=flags } ;"""
        pass # TODO:
        Debug.unimplemented("n_flags")

    def n_keyq(self):
        """: n_KEYQ   ( -- ?)
        # { ds_pushn(kbhit) } ;"""
        n = self.ins.waiting()
        self.ds.pushn(n)

    def n_key(self):
        """: n_KEY   ( -- c)
        { ds_pushn(getch) } ;"""
        ch = self.ins.getch()
        b = ord(ch)
        self.ds.pushn(b)

    def n_emit(self):
        """: n_EMIT   ( c -- )
        { putch(ds_popn) } ;"""
        ch = chr(self.ds.popn() & 0xFF)
        self.outs.writech(ch)

    def n_printtos(self):
        """: n_PRINTTOS ( n --)
        { printnum(ds_pop16) } ;"""
        n = self.ds.popn()
        self.outs.writen(n)
        self.outs.writech(' ')

    def n_rdpfa(self):
        """: n_RDPFA   ( -- n)
        { pfa=ip; r=mem[pfa]; ds_push(r) } ;"""
        #Debug.trace("ip 0x%x" % self.ip)
        pfa = self.ip
        r = self.mem.readn(pfa)
        self.ds.pushn(r)

    def n_adruv(self):
        """: n_ADRUV   ( a-pfa -- a)
        { pfa=ds_pop; rel=mem[pfa]; a=uservars+rel; ds_push(a) } ;"""
        pfa = self.ds.popn()
        rel = self.mem.readn(pfa)
        uservars = 0 # TODO: per-task offset to uservars
        a = uservars + rel
        self.ds.pushn(a)

    def n_branch(self):
        """: n_BRANCH   ( -- )
        { rel=memn[ip]; ip+=2; abs=ip-rel; ip=abs } ;"""
        #print("BRANCH")
        ip = self.rs.popn() # points to REL
        #print("  ip on entry:0x%x" % ip)
        rel = 2 * self.mem.readn(ip) # each cell is two bytes
        #print("  rel:0x%x" % rel)
        abs = (ip + rel) & 0xFFFF # 2's complement
        #print("  to:0x%x" % abs)
        self.rs.pushn(abs)

    def n_0branch(self):
        """: n_0BRANCH   ( ? -- )
        { f=ds_pop; r=mem[ip]; if f==0:ip=ip+(2*r) else: ip+=2 } ;"""
        #print("0BRANCH")
        f = self.ds.popn()
        #print("  flag:0x%x" % f)
        ip = self.rs.popn() # points to REL
        #print("  ip on entry:0x%x" % ip)
        rel = 2 * self.mem.readn(ip) # each cell is two bytes
        #print("  rel:%d dec" % rel)

        if f == 0:
            abs = (ip + rel) & 0xFFFF # 2's complement
        else:
            abs = ip+2

        #print("  to:0x%x" % abs)
        self.rs.pushn(abs)

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

    def read_counted_string(self, addr):
        count = self.mem.readb(addr)
        addr  = addr+1
        name = ""
        for i in range(count):
            name += chr(self.mem.readb(addr+i))
        #print("FIND name: %s" % name)
        return name

    def n_find(self):
        """Given address of a counted string, find CFA of word, 0 if not found"""
        addr = self.ds.popn()
        #print("find popped address:%x" % addr)
        #for a in range(addr, addr+10, 2):
        #    n = self.mem.readn(a)
        #    print("%x" % n)
        name = self.read_counted_string(addr)
        ffa = self.dict.find(name)
        #print("ffa:0x%x" % ffa)
        if ffa == 0: # NOT FOUND
            self.ds.pushn(0) # NOT FOUND
            #print("NOT FOUND")
            return

        cfa = self.dict.ffa2cfa(ffa)
        #print("cfa:0x%x" % cfa)
        #self.dict.dump()
        self.ds.pushn(cfa)

    def n_number(self):
        """Parse a number using the current BASE"""
        # ( a -- n) or ( a -- d)
        # a is address of a counted string

        addr = self.ds.popn()
        count = self.mem.readb(addr)
        addr += 1

        #print("NUMBER %d %s" % (count, self.mem.readb(addr)))

        base = self.base
        index = 0
        negate = False
        double = False
        accumulator = 0

        while count > 0:
            c = self.mem.readb(addr+index)
            ch = chr(c)
            if ch == '-':
                if index == 0:
                    negate = True
                else:
                    double = True

            elif ch in [',', '/', '.', ';']:
                double = True

            elif ch >= '0' and ch <= '9':
                accumulator *= base
                v = c - 48
                if v < base:
                    accumulator += v
                else:
                    Debug.trace("Conversion error in NUMBER, out of range digit for base")
                    self.n_abort() #TODO: need a way to abort with a message
            else:
                Debug.trace("Parse error in NUMBER, non digit found")
                self.n_abort() #TODO: need a way to abort with a message
            index += 1
            count -= 1

        if negate:
            accumulator = -accumulator
        if double:
            self.ds.pushd(accumulator & 0xFFFFFFFF)
        else:
            self.ds.pushn(accumulator & 0xFFFF)

    def n_bye(self):
        self.running = False

    def n_execute(self):
        """EXECUTE a high level address"""
        # ( cfa -- )
        #Debug.trace("EXECUTE")
        cfa = self.ds.popn()
        #Debug.trace(" cfa:0x%x" % cfa)
        pfa = self.dict.cfa2pfa(cfa)
        #Debug.trace(" pfa:0x%x" % pfa)
        cf = self.mem.readn(cfa)
        self.ip = pfa
        #Debug.trace(" calling cf:0x%x" % cf)
        self.call(cf)

    depth = 0
    def n_dodoes(self):
        """Repeatedly fetch and execute CFA's until EXIT"""
        self.depth += 1
        thisname = self.dict.pfa02name(self.ip)
        #Debug.trace("DODOES enter, depth:%d word:%x %s" % (self.depth, self.ip, thisname))
        #DODOES = self.getNativeRoutineAddress(" DODOES")
        #EXIT   = self.getNativeRoutineAddress("EXIT")

        # TODO when this executes an EXIT, it MUST return in python land
        # otherwise the python stack will fill up and overflow.

        while self.running:
            #NEXT
            #Debug.trace("NEXT")
            if self.limit != None:
                self.limit -= 1
                if self.limit <= 0:
                    self.running = False
                    break

            # ip points to the cfa of the word to execute
            #Debug.trace(" fetch from ip:0x%x" % self.ip)
            cfa = self.mem.readn(self.ip)
            #print(" exec: %s" % self.dict.cfa2name(cfa))
            #Debug.trace(" cfa:0x%x" % cfa)
            cf = self.mem.readn(cfa)
            #Debug.trace(" cf:0x%x" % cf)
            self.rs.pushn(self.ip+2)
            # put something useful in self.ip, i.e. the pfa
            self.ip = cfa+2 # pfa
            #print("calling cf:%x" % cf)
            #if cf == DODOES:
            #    print("dodoes %s calling dodoes, word:%x %s" % (thisname, self.ip, self.dict.pfa02name(self.ip)))
            #elif cf == EXIT:
            #    print("dodoes %s calling exit" % thisname)
            self.call(cf) # if this called n_exit, we must now exit this level of the dodoes loop.
            self.ip = self.rs.popn() # this still needs to happen after call()

            if self.exits_pending > 0:
                #print("dodoes %s EXITS pending %d" % (thisname, self.exits_pending))
                self.exits_pending -= 1
                #print("dodoes %s exits now pending %d" % (thisname, self.exits_pending))
                break

        #self.ip = self.rs.popn()

        self.depth -= 1
        #print("returning from DODOES %s, depth now %d" % (thisname, self.depth))

    def n_dolit(self):
        """Process an inline 16 bit literal and put it on DS"""
        #: n_DOLIT  ( -- )
        #{ip=rs_pop; n=mem_readn(ip); ds.pushn(n) ip+=2}
        ip = self.rs.popn()
        n = self.mem.readn(ip)
        self.ds.pushn(n)
        #Debug.trace("found literal: %d" % n)
        ip += 2
        self.rs.pushn(ip)

    def n_dostr(self):
        """Get the address of a string encoded inline in the pf"""
        # Get the address of the PFA, which is the start of the count preceded string
        ip = self.rs.popn()
        pfa = ip
        self.ds.pushn(pfa)

        # work out how many cells of data to jump for the return point
        # This includes an optional pad byte at the end, which is not accounted
        # for in the length byte, but required to 16-bit align all cells.

        l = self.mem.readb(ip)
        cellbytes = (l/2)+1 # account for length byte, and optional pad at end
        #for a in range(pfa+1, pfa+l+1):
        #    ch = chr(self.mem.readb(a))
        #    sys.stdout.write(ch)

        ip += cellbytes*2
        self.rs.pushn(ip)

    def n_exit(self):
        """EXIT word - basically a high level Forth return"""
        #print("****EXIT")
        self.exits_pending += 1

#----- FORTH OUTER INTERPRETER ------------------------------------------------

class Forth():
    """The outer interpreter"""
    def __init__(self, ins=None, outs=None, disks=None):
        self.ins   = ins
        self.outs  = outs
        self.disks = disks

    def boot(self):
        if self.outs==None:
            self.outs = Output() # Mock
        if self.ins==None:
            self.ins  = Input() # Mock
        if self.disks==None:
            self.disk = Disk(DISK_FILE_NAME) #Mock

        self.machine = Machine(self).boot()
        self.synthesise()

        #self.machine.dict.dump()
        return self

    # High level forth actions
    @staticmethod
    def flatten(args):
        #print("flatten:%s" % str(args))
        r = []
        for a in args:
            if type(a) == list or type(a) == tuple:
                a = Forth.flatten(a)
                for i in a:
                    r.append(i)
            elif type(a) == str or type(a) == int:
                r.append(a)
            else:
                Debug.fail("Unhandled arg type:%s %s" % (str(type(a)), str(a)))
        #print("flattened:%s" % str(r))
        return r

    def create_word(self, name, *args):
        """Create a new high level dictionary entry containing a list of words.
             Note this is not a full defining compiler, just a word list
             that also understands numbers."""

        # Build the PF entries (all should contain CFAs)
        plist  = []
        DODOES = self.machine.getNativeRoutineAddress(" DODOES")

        args = self.flatten(args)

        for word in args:
            if type(word) == str:
                # It's a word, so lookup it's address in DICT
                ffa = self.machine.dict.find(word)
                if ffa == 0:
                    Debug.fail("Word not in dictionary:%s" % word)
                #TODO if not found, should pass to NUMBER to see if it parses,
                # and then just append it if it does.
                cfa = self.machine.dict.ffa2cfa(ffa)
                plist.append(cfa)
            elif type(word) == int:
                plist.append(word)

        exit_cfa = self.machine.dict.ffa2cfa(self.machine.dict.find("EXIT"))
        plist.append(exit_cfa)

        # Now create the dictionary entry
        # CF=DODOES is implied for all high level word definitions
        #Debug.trace(plist)
        self.machine.dict.create(
            nf=name,
            cf=DODOES,
            pf=plist,
            finish=True
        )
        #self.machine.dict.dumpraw()

    @staticmethod
    def CHARACTER(ch):
        return Forth.LITERAL(ord(ch))

    @staticmethod
    def LITERAL(number):
        return " DOLIT", (number & 0xFFFF)

    @staticmethod
    def STRING(string):
        # Length is stored in a byte, so can't be too big. But it can be zero.
        #print("STR:%s" % string)
        l = len(string)
        if l > 255:
            Debug.fail("Cannot encode strings longer than 255 characters")

        # first should be the length
        s = chr(l) + string
        # List should be an even number of bytes long
        if (len(s) % 2) != 0: # odd length including length byte
            s = s + chr(0) # pad byte
            l += 1

        # Encode bytestream, two bytes per cell, note first byte encoded is length
        # last byte encoded might be last char, or a pad char of 0
        nlist = []
        for i in range(0, l, 2): # encode pairs of numbers
            # Using from_bytes means it works with any endianness
            n = Number.from_bytes((ord(s[i]), ord(s[i+1])))
            nlist.append(n)

        # build a list of 16 bit numbers, numbers ready for word encoding
        wlist = [" DOSTR"]
        wlist.append(nlist)
        #x = ""
        #for n in nlist:
        #    x += "%x " % n
        #print("Will encode as:%s" % x)
        #print(wlist)
        return wlist


    def create_const(self, name, number):
        """Create a constant with a given 16 bit value"""
        RDPFA = self.machine.getNativeRoutineAddress(" RDPFA")

        # Now create the dictionary entry
        self.machine.dict.create(
            nf=name,
            cf=RDPFA,
            pf=[number],
            finish=True
        )
        #self.machine.dict.dumpraw()

    def create_var(self, name, size=2, init=0):
        """Create a variable with a given 16 bit default value"""
        if size!=2:
            Debug.fail("var size != 2 not yet supported")

        addr=self.machine.uv.pushn(init)
        RDPFA = self.machine.getNativeRoutineAddress(" RDPFA")

        # Now create the dictionary entry
        self.machine.dict.create(
            nf=name,
            cf=RDPFA, #TODO: something goes wrong with this at runtime
            pf=[addr],
            finish=True
        )
        #self.machine.dict.dumpraw()

    def execute_word(self, word):
        """Equivalent to ' word EXECUTE"""

        # Push PFA of word to execute on stack (equivalent to TICK)
        word_ffa = self.machine.dict.find(word)
        word_cfa = self.machine.dict.ffa2cfa(word_ffa)
        self.machine.ds.pushn(word_cfa)

        # Execute word who's CFA is on the stack (actually, EXECUTE)
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

    def synthesise(self):
        """Synthesise some high level words, in absence of a compiler and interpreter.
        Note, in a later release, these may be programmed in using the compiler."""

        # CONSTANTS -----------------------------------------------------------

        consts = [
            # name,  value (all size 2)
            ("D0",    self.machine.dict.start),
            ("DZ",    self.machine.dict.size),
            ("S0",    self.machine.ds.start),
            ("SZ",    self.machine.ds.size),
            ("R0",    self.machine.rs.start),
            ("RZ",    self.machine.rs.size),
            ("TIB",   self.machine.tibstart),
            ("TIBZ",  self.machine.tibsize),
            ("PAD",   self.machine.padstart),
            ("PADZ",  self.machine.padsize),
            ("FALSE", 0x0000),
            ("TRUE",  0xFFFF),
            ("BL",    32),
            # No number parser yet, so pre-seed a few
            #("0",     0),
            #("1",     1),
            #("10",    10),
            #("42",    42),
            #("BB0",  self.machine.bb.start),
            #("BBZ",  self.machine.bb.size),
        ]

        for c in consts:
            name, value = c
            self.create_const(name, value)

        #TODO PAD is dynamic
        #: PAD   ( -- a)                      /ADD  n_RDPFA  CONST  Address of start of user vars
        #self.create_const("PAD", self.machine.uvstart)


        # VARIABLES -----------------------------------------------------------

        vars = [
            #name     size,   init
            (">IN",),
            ("BLK",),
            #("BINDEX", 2*2),
            ("BASE",    2,    10),
            ("SPAN",),
        ]
        for v in vars:
            name = v[0]
            size = 2
            init = 0
            if len(v) > 1:
                size = v[1]
                if len(v) > 2:
                    init = v[2]

            self.create_var(name, size=size, init=init)


        # CODE WORDS ----------------------------------------------------------

        # aliases, for brevity
        LIT = Forth.LITERAL
        CHR = Forth.CHARACTER
        STR = Forth.STRING

        words = [
            #name      parts                  stack effects
            #----- RELATIONAL
            ("=",      ["-", "0="]),
            ("<>",     ["-", "0=", "NOT"]),
            ("<",      ["-", "0>"]),
            (">",      ["-", "0<"]),
            #----- ALU
            ("/MOD",   ["DUP", "DUP", "/", "ROT", "ROT", "MOD", "SWAP"]),   # ( n1 n2 -- n-rem n-quot)
            ("1+",     [LIT(1),  "+"]),                                          # ( n -- n+1)
            ("1-",     [LIT(1),  "-"]),                                          # ( n -- n-1)
            ("2+",     [LIT(2),  "+"]),                                          # ( n -- n+2)
            ("2-",     [LIT(2),  "-"]),                                          # ( n -- n-2)
            ("2*",     [LIT(2),  "*"]),                                          # ( n -- n*2)
            ("2/",     [LIT(2),  "/"]),                                          # ( n -- n/2)
            ("NEGATE", [LIT(-1), "*"]),                                          # ( n -- -n)

            ("ABS",    ["DUP", "0<", "0BRANCH", +2, "NEGATE"]),                          # ( n -- |n|)
            ("MIN",    ["OVER", "OVER", "<", "NOT", "0BRANCH", +2, "SWAP", "DROP"]),     # ( n1 n2 -- min)
            ("MAX",    ["OVER", "OVER", ">", "NOT", "0BRANCH", +2, "SWAP", "DROP"]),     # ( n1 n2 -- max)

            #----- STACK OPS
            (">R",      ["RP", "@", LIT(1), "+", "DUP", "ROT", "!", "RP", "!"]),             # ( n -- )
            ("R>",      ["RP", "DUP", "@", "@", "SWAP", LIT(1), "-", "RP", "!"]),            # ( -- n)
            ("R@",      ["RP", "@", "@"]),                                              # ( -- n)
            ("SP@",     ["SP", "@"]),                                                   # ( -- a)
            ("?DUP",    ["DUP", "0BRANCH", +2, "DUP"]),                                  # ( n -- n n or 0 -- 0)
            ("2SWAP",   ["ROT", ">R", "ROT", "R>"]),                                    # ( d1 d2 -- d2 d1)
            ("2DUP",    ["OVER", "OVER"]),                                              # ( d -- d d)
            ("2OVER",   ["2SWAP", "2DUP", ">R", ">R", "2SWAP", "R>", "R>"]),            # ( d1 d2 -- d1 d2 d1)
            ("2DROP",   ["DROP", "DROP"]),                                              # ( d --)

            #----- GENERAL I/O
            ("HEX",      [LIT(16), "BASE", "!"]),                                            #( -- )
            ("OCTAL",    [LIT(8),  "BASE", "!"]),                                            #( -- )
            ("DECIMAL",  [LIT(10), "BASE", "!"]),                                            #( -- )
            ("CR",       [LIT(13), "EMIT", LIT(10), "EMIT"]),                                #( -- )
            ("SPACE",    [LIT(32), "EMIT"]),                                                 #( -- )
            ("PAGE",     [LIT(12), "EMIT"]),                                                 #( -- )

            #---- SIMPLE MEMORY OPS
            ("+!",       ["DUP", "@", "ROT", "+", "!"]),                                    #( n a -- )
            ("2!",       ["ROT", "SWAP", "DUP", "ROT", "SWAP", "!", LIT(2), "+", "!"]),     #( d a -- )
            ("2@",       ["DUP", "@", "SWAP", 2, "+", "@"]),                                #( a -- d)


            #-----
            ("EXPECT", [                                        # ( a # -- )
                "SPAN", "!",                                    # ( a)          use SPAN as the char counter while in loop
                "DUP",                                          # ( a a)        leave user buffer start on stack, for later cleanup
                ">IN", "!",                                     # ( a)          set INP to start of user buffer, use as write ptr in loop
                # loop                                          # ( a)
                    "KEY",                                      # ( a c)        read a char
                    "DUP", LIT(4), "=", "0BRANCH", +2, "BYE",   # ( a c)        is it EOF? If it is, BYE
                    "DUP", LIT(10), "=", "NOT", "0BRANCH", +23, # ( a c ?)      is it LF?, to:done
                    ">IN", "@", "C!",                           # ( a)          write via INP ptr
                    ">IN", "@", LIT(1), "+", ">IN", "!",        # ( a)          advance write pointer
                    "SPAN", "@", LIT(1), "-", "SPAN", "!",      # ( a)          dec counter
                    "SPAN", "@", "0=",                          # ( a ?)        is span=0 (buffer full)
                    "0BRANCH", -36,                             # ( a)          to:loop go round again if it isn't
                # done                                          # ( a c)        address on stack is of start of buffer
                #                                               #               >IN points to char after last written
                #                                               #               a on stack is start of user buffer
                #                                               #               >IN - a is the true SPAN including optional CR
                "DROP",                                         # ( aTIB)
                "DUP",                                          # ( aTIB aTIB)
                ">IN", "@",                                     # ( aTIB aTIB aLASTWR+1)
                "SWAP",                                         # ( aTIB aLASTWR+1 aTIB)
                "-",                                            # ( aTIB #read)
                "SPAN", "!",                                    # ( aTIB)       SPAN holds number of chars read in
                ">IN", "!",                                     # ( )           INP points to first char to read in buffer
            ]),
            #-----
            ("TYPE", [                                      # ( a # -- )
                                                            # target:read
                "DUP", "0=", "NOT", "0BRANCH", +14,         # (exit) ( a #) if counter zero, exit
                "SWAP", "DUP", "C@",                        # ( # a c)      read char at address
                "EMIT",                                     # ( # a)        show char
                LIT(1), "+",                                # ( # a)        advance address
                "SWAP",                                     # ( a #)
                LIT(1), "-",                                # ( a #)        dec count
                "BRANCH", -17,                              # (read)        go round for another
                                                            # target:exit
                "DROP", "DROP",
            ]),
            #-----
            ("COUNT", [                                     # ( a)
                "DUP",                                      # ( a a)
                "C@",                                       # ( a #)
                "SWAP",                                     # ( # a)
                LIT(1), "+",                                # ( # a)
                "SWAP",                                     # ( a #)
            ]),
            #-----
            ("SPACES", [                                    # ( n -- )
                # loop                                      # ( n)
                    "DUP",                                  # ( n n)
                    "0BRANCH", +9,                          # ( n)      to:exit
                    LIT(32), "EMIT",                        # ( n)
                    LIT(1), "-",                            # ( n-1)
                    "BRANCH", -10,                          # ( n)      to:loop
                # exit                                      # ( n)
                "DROP"                                      # ( )
            ]),
            #-----
            ("IN@+", [                                          # ( -- c)
                "TIB", "SPAN", "@", "+",                        # ( a)          address of first unused byte at end of buffer
                ">IN", "@", "=",                                # ( ?)          is IN ptr at end of buffer?  TRUE if at end
                LIT(0), "SWAP", "NOT", "0BRANCH", +12, "DROP",  # ( -- or 0)    to:exit with 0 on stack if end, stack empty if chars
                ">IN", "@", "C@",                               # ( c)          read next char at ptr
                ">IN", "@", LIT(1), "+", ">IN", "!",            # ( c)          advance IN ptr
                # exit                                          # ( c or 0)
            ]),
            #-----
            ("SKIP", [                                  # ( s)                  skip until end or not c
            # skip                                      # ( s)
                "IN@+",                                 # ( s c or c 0)         read next from input stream, returns 0 if empty
                "DUP", "0BRANCH", +14,                  # ( s c) to:exitskip    exit if at end of buffer??
                "OVER", "=", "NOT", "0BRANCH", -8,      # ( s )  to:skip        if matches separator
            ">IN", "@", LIT(1), "-", ">IN", "!",        # ( s )                 just seen non separator, wind back to first non sep char
            "DUP",                                      # ( s s)                two items on stack
            # exitskip                                  # ( s c)
            "DROP", "DROP",                             # ( )
            ]),
            #-----
            ("0PAD>", [                                 # ( -- )
                LIT(0), "PAD", "C!"                     # ( )          write zero to first entry in PAD buffer
            ]),
            #-----
            ("PAD>+", [                                 # ( c -- )
                "PAD", "C@", LIT(1), "+", "PAD", "C!",  # ( c )         advance count by 1 (no range check? PADZ??)
                "PAD", "C@", "PAD", "+", "C!"           # ( )           write char to next free location
            ]),
            #-----
            ("WORD", [                                      # ( cs -- a)
                "0PAD>",                                    # ( cs)             reset PAD pointer/count
                "DUP", "SKIP",                              # ( cs)             leave separator on stack, need it later
                # copy                                      # ( cs)
                    "IN@+",                                 # ( cs c or cs 0)   try to consume next char
                    "DUP", "0BRANCH", +17,                  # ( cs c)  to:exit  zero marks end of buffer
                    "DUP", "PAD>+",                         # ( cs c)           write char to next pad, advance ptr
                    "OVER", "=", "0BRANCH", -9,             # ( cs)  to:copy    if not separator, go round again
                    "DROP",                                 # ( )
                    "PAD", "C@", LIT(1), "-", "PAD","C!",   # ( )               take one off count value
                    "BRANCH", +3,                           # ( )
                # exit                                      # ( c c)
                "DROP", "DROP",                             # ( )
                # ret                                       # ( )
                "PAD"                                       # ( a)              address of PAD (count in ofs 0) returned on stack
            ]),
            #-----
            ("STAR", [CHR('*')]), # could do as a CONSTANT
            #-----
            ("INTERPRET", [
                # getword                                   # ( )
                "BL", "WORD", "COUNT",                      # ( a #)
                "0=", "0BRANCH", +4,                        # ( a)          to: findword
                "DROP",                                     # ( )
                "BRANCH", +19,                              # ( )           to: exit

                # findword                                  # ( a)
                LIT(1), "-",                                # ( a)          litcells=2: subtract one to point to count byte for FIND
                "DUP",                                      # ( a:t a:t)    save addr in case we want to print ?name on not found
                "FIND",                                     # ( a:t a:cfa)  0 if not found, cfa if found
                "DUP", "NOT", "0BRANCH", +5,                # ( a:t a:cfa)  to: run

                # notword                                   # ( a:t a:cfa)
                "DROP",                                     # ( a:t)
                "NUMBER",                                   # ( n or u or d or ud) note: will ABORT if cannot parse
                "BRANCH", -21,                              # ( ) to:getword

                #TODO: might have to put this in REPL loop, with a way to trap ABORT??
                # notnumber
                #CHR("?"), "EMIT",                           # ( a:t)        chrcells=2
                #"COUNT", "TYPE",                            # ( )
                #"BRANCH", +6,                               # ( )           to: exit

                # run                                       # ( a:t a:cfa)  addr is cfa of word to exec
                "SWAP", "DROP",                             # ( a:cfa)
                "EXECUTE",                                  # ( )           execute the word whose address info is on the DS
                "BRANCH", -26,                              # ( )           to: getword
            ]),
            #-----
            ("REPL", [
                #TODO clear return stack
                LIT(0), "SPAN", "!",                        # ( )       clear span so we don't get repeat on blank line
                "TIB", "TIBZ", "EXPECT",                    # ( )       read in a whole line up to CR
                "TIB", ">IN", "!",                          # ( )       set IN read ptr to start of TIB
                "INTERPRET",                                # ()
                STR("Ok"), "COUNT", "TYPE",                 # ()        strcells=3 (dostr)(count,O)(k,-)
                "CR",
                "BRANCH", -18                               # ()        to:start
            ]),
        ]

        for w in words:
            name, parts = w
            self.create_word(name, *parts)

        #self.machine.dict.dump()



#----- RUNNER -----------------------------------------------------------------

forth = Forth(ins=KeyboardInput(), outs=ScreenOutput()).boot()

def create_word(*args):
    forth.create_word(*args)

def execute_word(*args):
    forth.execute_word(*args)

def test_hello():
    """output a "Hello world!" on stdout"""

    msg = "Hello world!\n"
    pfa = []
    #TODO: Use Forth.STRING here
    for ch in msg:
        pfa.append(" DOLIT")
        pfa.append(ord(ch))
        pfa.append("EMIT")

    forth.create_word("HELLO", *pfa)
    #forth.machine.dict.dump()

    forth.execute_word("HELLO")

def test_echoloop():
    #forth.create_word(
    #    "RUN",
    #        "TIB", "TIBZ", "EXPECT",
    #        #"TIB", "SPAN", "@", "TYPE",
    #        "BRANCH", -4
    #)
    forth.create_word("TEST", "TIB", "TIBZ", "EXPECT" , "TIB", "SPAN", "@", "TYPE", "BRANCH", -8 )
    #forth.machine.dict.dump()
    forth.execute_word("TEST")

def repl():
    forth.execute_word("REPL")

if __name__ == "__main__":
    #test_hello()
    #test_echoloop()
    repl()

# END
