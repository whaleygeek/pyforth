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
        for a in range(start, start+len):
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
            raise RuntimeError("Address not callable:0x%x" % addr)
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
            raise RuntimeError("must not see -ve size here:0x%x" % size)
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
        raise RuntimeError("Unimplemented") #TODO

    def write(self, rel, bytes):
        """Write a list of bytes, at a specific byte index from TOS"""
        size = len(bytes)
        ptr = self.absaddr(rel, size)
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

    def appendb(self, number):
        pass #TODO: call write

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
            raise RuntimeError("negative growth not dumpable yet")

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
        raise RuntimeError("Byte push on to a Forth stack is not supported")

    def popb(self):
        raise RuntimeError("Byte pop from a Forth stack is not supported")

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
                raise RuntimeError("Could not find word in dict:%s", name)
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
            raise RuntimeError("Could not find word to forget it:%s", name)

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
            self.buf = self.buf[1:]
            return c
        if wait:
            if len(self.buf) == 0:
                raise RuntimeError("WAIT on mock buffer called")
        return None # nothing in buffer


class KeyboardInput(Input):
    """A way to poll and get characters from the keyboard"""

    def waiting(self):
        raise RuntimeError("Not yet implemented")

    def getch(self):
        ch = sys.stdin.read(1) # blocking, line buffered
        if ch == "": # EOF
            raise RuntimeError("EOF on Keyboard input stream")
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
            ("TEST",  0, 2,   parent.rd_test,       parent.wr_test),
            ("IP",    2, 2,   parent.rd_ip,         parent.wr_ip),
            ("H",     4, 2,   parent.dict.rd_p,     parent.dict.wr_p),
            ("SP",    6, 2,   parent.ds.rd_p,       parent.ds.wr_p),
            ("RP",    8, 2,   parent.rs.rd_p,       parent.rs.wr_p),
            ("UVP",  10, 2,   parent.uv.rd_p,       parent.uv.wr_p),

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
            raise RuntimeError("set: NvMem offset 0x%x does not support write function" % offset)
        wr(offset, value)

    def __getitem__(self, offset):
        item = self.find(offset)
        if item == None:
            raise ValueError("Unknown offset in region: 0x%x" % offset)
        name, start, ofs, rd, wr = item
        if rd==None:
            raise RuntimeError("get: NvMem offset 0x%x does not support read function" % offset)
        return rd(offset)


class NvRoutine():
    """Provides access to native routines mapped into memory"""
    def __init__(self, parent, start):
        self.map = [
            ("NOP",        parent.n_nop),      # 00 must always be first entry
            ("ABORT",      parent.n_abort),    # 01
            ("!",          parent.n_store),    # 02
            ("@",          parent.n_fetch),    # 03
            ("C!",         parent.n_store8),   # 04
            ("C@",         parent.n_fetch8),   # 05
            ("EMIT",       parent.n_emit),     # 06
            (".",          parent.n_printtos), # 07
            ("SWAP",       parent.ds.swap),    # 08
            ("DUP",        parent.ds.dup),     # 09
            ("OVER",       parent.ds.over),    # 0A
            ("ROT",        parent.ds.rot),     # 0B
            ("DROP",       parent.ds.drop),    # 0C
            ("NIP",        parent.ds.nip),
            ("TUCK",       parent.ds.tuck),
            ("+",          parent.n_add),
            ("-",          parent.n_sub),
            ("AND",        parent.n_and),
            ("OR",         parent.n_or),
            ("XOR",        parent.n_xor),
            ("*",          parent.n_mult),
            ("/",          parent.n_div),
            ("MOD",        parent.n_mod),
            ("0=",         parent.n_0eq),
            ("NOT",        parent.n_not),
            ("0<",         parent.n_0lt),
            ("0>",         parent.n_0gt),
            ("RBLK",       parent.n_rblk),
            ("WBLK",       parent.n_wblk),
            ("BRANCH",     parent.n_branch),
            ("0BRANCH",    parent.n_0branch),
            (" RDPFA",     parent.n_rdpfa),     # 1D
            (" DODOES",    parent.n_dodoes),    # 1E
            (" DOLIT",     parent.n_dolit),
            ("EXECUTE",    parent.n_execute),
            ("EXIT",       parent.n_exit),
            #(" DOCOL",    parent.n_docol),
            #(" DOCON",     parent.n_docon),
            #(" DOVAR",     parent.n_dovar),
            #(" ADRUV",     parent.n_adruv),
            #(" QUIT",      parent.n_quit),
            #(" BYE",       parent.n_byte),
            #("DOES>",      parent.n_does),
            #(":",          parent.n_colon),
            #(";",          parent.n_semicolon),
            #("VARIABLE",   parent.n_variable),
            #("CONSTANT",   parent.n_constant),
            #("U<",         parent.n_ult),
            #("FLAGS",      parent.n_flags),
            ("KEY",        parent.n_key),
            #("KEYQ",       parent.n_keyq),
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
        raise RuntimeError("native function not found:%s", name)

    def call(self, index):
        """Look up the call index in the dispatch table, and dispatch if known"""
        if index < len(self.map):
            name, execfn = self.map[index]
            #Debug.trace("calling native fn:%d %s" % (addr, name))
            if execfn != None:
                execfn()
                return
        Debug.fail("call to unknown native address offset: 0x%x" % index)
        raise RuntimeError("CALL FAILED")

    def __setitem__(self, key, value):
        raise RuntimeError("Tried to write to NvRoutine memory offset:0x%x value:0x%x" % (key, value))

    def __getitem__(self, key):
        raise RuntimeError("Tried to read from NvRoutine memory offset:0x%x" % key)


class Machine():
    """The inner-interpreter of the lower level/native FORTH words"""

    FALSE = 0x0000
    TRUE  = 0xFFFF #TODO: or -1 (not the same in python, but same in Forth)

    def __init__(self, parent):
        self.ip     = 0
        self.outs   = parent.outs
        self.ins    = parent.ins
        self.disk   = parent.disk

    def boot(self):
        self.build_ds()       # builds memory abstractions
        self.running = False
        self.limit = None     # how many times round DODOES before early terminate?
        return self

    def build_ds(self):
        """Build datastructures in memory"""
        #           base,             dirn/size
        NR_MEM   = (0x0000,          +256)     # native routines
        NV_MEM   = (0x0100,          +256)     # native variables
        DICT_MEM = (0x0400,          +2048)    # dictionary
        DS_MEM   = (0x8000,          -1024)    # data stack
        TIB_MEM  = (0x8000,          +80)      # text input buffer
        RS_MEM   = (0xA000,          -1024)    # return stack
        UV_MEM   = (0xA000,          +1024)    # user variables

        #PAD_MEM   = (2048,            +80       )    # pad
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
        #padstart, padsize = self.mem.region("PAD", PAD_MEM)
        #self.pad = Pad(self.mem, padstart, padptr, padsize)

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
        self.ds.clear()
        self.rs.clear()
        self.running = False

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
        { a=ds_pop; n0=ds_pop8; n1=ds_pop8; mem[a]=n0; mem[a+1]=n1} ;"""
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
        { a=ds_pop; b=ds_pop8; mem[a]=b } ;"""
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

    def n_execute(self):
        """EXECUTE a high level address"""
        # ( pfa -- )
        #Debug.trace("EXECUTE")
        pfa = self.ds.popn()
        #Debug.trace(" pfa:0x%x" % pfa)
        # Don't assume DODOES, just in case it is a low level word!
        cfa = self.dict.pfa2cfa(pfa)
        #Debug.trace(" cfa:0x%x" % cfa)
        cf = self.mem.readn(cfa)
        self.ip = pfa
        #Debug.trace(" calling cf:0x%x" % cf)
        self.call(cf)

    def n_dodoes(self):
        """Repeatedly fetch and execute CFA's until EXIT"""
        #Debug.trace("DODOES")
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
            #Debug.trace(" cfa:0x%x" % cfa)
            cf = self.mem.readn(cfa)
            #Debug.trace(" cf:0x%x" % cf)
            self.rs.pushn(self.ip+2)
            # put something useful in self.ip, i.e. the pfa
            self.ip = cfa+2 # pfa
            self.call(cf)
            sz = self.rs.getused()
            #Debug.trace("RS used: %d" % sz)
            if sz == 0: break # EXIT returned to top level
            self.ip = self.rs.popn()

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

    def n_exit(self):
        """EXIT word - basically a high level Forth return"""
        """: n_EXIT   ( -- )
        { ip=rs_pop() } ;"""
        #Debug.trace("exit")

        self.ip = self.rs.popn()
        # If nothing on stack, STOP
        #if self.rs.getused() >= 2:
        #    #print("rs used:%d" % self.rs.getused())
        #    self.ip = self.rs.popn()
        #    #Debug.trace("popped to IP: 0x%x" % self.ip)
        #else:
        #    Debug.trace("Return stack empty, STOPPING")
        #    self.running = False


#----- FORTH OUTER INTERPRETER ------------------------------------------------

class Forth:
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

    def create_word(self, name, *args):
        """Create a new high level dictionary entry containing a list of words.
             Note this is not a full defining compiler, just a word list
             that also understands numbers."""

        # Build the PF entries (all should contain CFAs)
        plist  = []
        DODOES = self.machine.getNativeRoutineAddress(" DODOES")

        for word in args:
            if type(word) == str:
                # It's a word, so lookup it's address in DICT
                ffa = self.machine.dict.find(word)
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
            raise RuntimeError("var size != 2 not yet supported")

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

    def synthesise(self):
        """Synthesise some high level words, in absence of a compiler and interpreter.
        Note, in a later release, these may be programmed in using the compiler."""

        # CONSTANTS -----------------------------------------------------------

        consts = [
            # name,  value (all size 2)
            ("D0",   self.machine.dict.start),
            ("DZ",   self.machine.dict.size),
            ("S0",   self.machine.ds.start),
            ("SZ",   self.machine.ds.size),
            ("R0",   self.machine.rs.start),
            ("RZ",   self.machine.rs.size),
            ("TIB",  self.machine.tibstart),
            ("TIBZ", self.machine.tibsize),
            #("BB0",  self.machine.bb.start),
            #("BBZ",  self.machine.bb.size),
            #("PADZ", self.machine.pad.size),
            ("FALSE", 0x0000),
            ("TRUE",  0xFFFF),
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
            ("COUNT",),
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

        words = [
            #name      parts                  stack effects
            #----- RELATIONAL
            ("=",      ["-", "0="]),
            ("<>",     ["-", "0=", "NOT"]),
            ("<",      ["-", "0>"]),
            (">",      ["-", "0<"]),
            #----- ALU
            ("/MOD",   ["DUP", "DUP", "/", "ROT", "ROT", "MOD", "SWAP"]),   # ( n1 n2 -- n-rem n-quot)
            ("1+",     [1,  "+"]),                                          # ( n -- n+1)
            ("1-",     [1,  "-"]),                                          # ( n -- n-1)
            ("2+",     [2,  "+"]),                                          # ( n -- n+2)
            ("2-",     [2,  "-"]),                                          # ( n -- n-2)
            ("2*",     [2,  "*"]),                                          # ( n -- n*2)
            ("2/",     [2,  "/"]),                                          # ( n -- n/2)
            ("NEGATE", [-1, "*"]),                                          # ( n -- -n)

            ("ABS",    ["DUP", "0<", "0BRANCH", 2, "NEGATE"]),                          # ( n -- |n|)
            ("MIN",    ["OVER", "OVER", "<", "NOT", "0BRANCH", 2, "SWAP", "DROP"]),     # ( n1 n2 -- min)
            ("MAX",    ["OVER", "OVER", ">", "NOT", "0BRANCH", 2, "SWAP", "DROP"]),     # ( n1 n2 -- max)

            #----- STACK OPS
            (">R",      ["RP", "@", 1, "+", "DUP", "ROT", "!", "RP", "!"]),             # ( n -- )
            ("R>",      ["RP", "DUP", "@", "@", "SWAP", 1, "-", "RP", "!"]),            # ( -- n)
            ("R@",      ["RP", "@", "@"]),                                              # ( -- n)
            ("SP@",     ["SP", "@"]),                                                   # ( -- a)
            ("?DUP",    ["DUP", "0BRANCH", 2, "DUP"]),                                  # ( n -- n n or 0 -- 0)
            ("2SWAP",   ["ROT", ">R", "ROT", "R>"]),                                    # ( d1 d2 -- d2 d1)
            ("2DUP",    ["OVER", "OVER"]),                                              # ( d -- d d)
            ("2OVER",   ["2SWAP", "2DUP", ">R", ">R", "2SWAP", "R>", "R>"]),            # ( d1 d2 -- d1 d2 d1)
            ("2DROP",   ["DROP", "DROP"]),                                              # ( d --)

            #----- GENERAL I/O
            ("HEX",      [16, "BASE", "!"]),                                            #( -- )
            ("OCTAL",    [8,  "BASE", "!"]),                                            #( -- )
            ("DECIMAL",  [10, "BASE", "!"]),                                            #( -- )
            ("CR",       [13, "EMIT"]),                                                 #( -- )
            ("SPACE",    [32, "EMIT"]),                                                 #( -- )
            ("PAGE",     [12, "EMIT"]),                                                 #( -- )

            #---- SIMPLE MEMORY OPS
            ("+!",       ["DUP", "@", "ROT", "+", "!"]),                                #( n a -- )
            ("2!",       ["ROT", "SWAP", "DUP", "ROT", "SWAP", "!", 2, "+", "!"]),      #( d a -- )
            ("2@",       ["DUP", "@", "SWAP", 2, "+", "@"]),                            #( a -- d)


            #TODO if buffer overflows, it goes wrong (i.e. more than 80 chars)
            #----- EXPECT
            ("EXPECT", [                                        # ( a # -- )
                "SPAN", "!",                                    # ( a)        use SPAN as the char counter while in loop
                "DUP",                                          # ( a a)      leave user buffer start on stack, for later cleanup
                ">IN", "!",                                     # ( a)        set INP to start of user buffer, use as write ptr in loop
                # loop                                          # ( a)
                    "KEY", "DUP",                               # ( a c c)    read a char
                    ">IN", "@", "C!",                           # ( a c)        write via INP ptr
                    "OVER",                                     # ( a c a)
                    " DOLIT", 1, "+", ">IN", "!",               # ( a c)     advance write pointer
                    "SPAN", "@", " DOLIT", 1, "-", "SPAN", "!", # ( a c)     dec counter
                    " DOLIT", 10, "=", "NOT",                   # ( a ?)     is char a LF?
                    "0BRANCH", 6,
                    "SPAN", "@", "0=",                          # ( a ?)   span=0 means buffer full
                    "0BRANCH", -31,                             # ( a)       (loop) go round again if it isn't
                # exit                                          # ( a)       address on stack is of start of buffer
                #                                               #            >IN points to char after last written
                #                                               #            a on stack is start of user buffer
                #                                               #            >IN - a is the true SPAN including optional CR
                "DUP",                                          # ( aTIB aTIB)
                ">IN", "@",                                     # ( aTIB aTIB aLASTWR+1)
                "SWAP",                                         # ( aTIB aLASTWR+1 aTIB)
                "-",                                            # ( aTIB #read)
                "SPAN", "!",                                    # ( aTIB)     SPAN holds number of chars read in
                ">IN", "!",                                      # ( )         INP points to first char to read in buffer
            ]),


            #----- SHOW: show a string given address and length
            ("SHOW", [                                      # ( a # -- )
                                                            # target:read
                "DUP", "0=", "NOT", "0BRANCH", 14,          # (exit) ( a #) if counter zero, exit
                "SWAP", "DUP", "C@",                        # ( # a c)      read char at address
                "EMIT",                                     # ( # a)        show char
                " DOLIT", 1, "+",                           # ( # a)        advance address
                "SWAP",                                     # ( a #)
                " DOLIT", 1, "-",                           # ( a #)        dec count
                "BRANCH", -17,                              # (read)        go round for another
                                                            # target:exit
                "DROP", "DROP",
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
    for ch in msg:
        pfa.append(" DOLIT")
        pfa.append(ord(ch))
        pfa.append("EMIT")

    forth.create_word("HELLO", *pfa)
    #forth.machine.dict.dump()

    forth.execute_word("HELLO")

def test_echoloop():
    forth.create_word(
        "RUN",
            "TIB", "TIBZ", "EXPECT",
            #"TIB", "SPAN", "@", "SHOW",
            "TIB", "SPAN", ">IN", ".", ".", ".",
            "BRANCH", -10
    )
    forth.execute_word("RUN")

if __name__ == "__main__":
    #test_hello()
    test_echoloop()
# END
