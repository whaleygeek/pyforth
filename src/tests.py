# tests.py  06/01/2016  (c) D.J.Whale
#
# Test harness for forth.py

import unittest
import forth


class x:#Experiment(unittest.TestCase):
    """A small smoke test - non exhaustive"""
    def setUp(self):
        #print("setup")
        self.f = forth.Forth(outs=forth.Output()).boot()

    def tearDown(self):
        #print("teardown")
        self.f = None

    #def test_dumpdict(self):
    #    self.f.machine.dict.dump()


class TestForth(unittest.TestCase):
    """A small smoke test - non exhaustive"""
    def setUp(self):
        #print("setup")
        self.f = forth.Forth(outs=forth.Output()).boot()

    def tearDown(self):
        #print("teardown")
        self.f = None

    # very basic test of stack
    def Xtest_000_stack_pushpop(self):
        EXPECTED = 42
        self.f.machine.ds.pushn(EXPECTED)
        actual = self.f.machine.ds.popn()
        self.assertEquals(EXPECTED, actual)

        EXPECTED = 42
        self.f.machine.rs.pushn(EXPECTED)
        actual = self.f.machine.rs.popn()
        self.assertEquals(EXPECTED, actual)


    def test_01_star(self):
        """Output a single * on stdout"""
        self.f.create_word("TEST", " DOLIT", 42, "EMIT")
        self.f.execute_word("TEST")
        self.assertEquals("*", self.f.outs.get())

    def test_02_hello(self):
        """Output a Hello world! message"""

        msg = "Hello world!\n"
        pfa = []
        for ch in msg:
            pfa.append(" DOLIT")
            pfa.append(ord(ch))
            pfa.append("EMIT")

        self.f.create_word("TEST", *pfa)
        self.f.execute_word("TEST")
        self.assertEquals(msg, self.f.outs.get())

    def test_03_add(self):
        """Add 1 and 2"""
        self.f.create_word("TEST", " DOLIT", 1, " DOLIT", 2, "+", ".")
        self.f.execute_word("TEST")
        self.assertEquals("3 ", self.f.outs.get())

    def test_04_sub(self):
        """Subtract"""
        self.f.create_word("TEST", " DOLIT", 2, " DOLIT", 1, "-", ".")
        self.f.execute_word("TEST")
        self.assertEquals("1 ", self.f.outs.get())

    def test_05_and(self):
        self.f.create_word("TEST", " DOLIT", 0xFFFF, " DOLIT", 0x8000, "AND", ".")
        self.f.execute_word("TEST")
        self.assertEquals("32768 ", self.f.outs.get())

    def test_06_or(self):
        self.f.create_word("TEST", " DOLIT", 0xFFFF, " DOLIT", 0x8000, "OR", ".")
        self.f.execute_word("TEST")
        self.assertEquals("65535 ", self.f.outs.get())

    def test_07_xor(self):
        self.f.create_word("TEST", " DOLIT", 0x0001, " DOLIT", 0x8000, "XOR", ".")
        self.f.execute_word("TEST")
        self.assertEquals("32769 ", self.f.outs.get())

    def test_08_mult(self):
        self.f.create_word("TEST", " DOLIT", 2, " DOLIT", 4, "*", ".")
        self.f.execute_word("TEST")
        self.assertEquals("8 ", self.f.outs.get())

    def test_09_div(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 3, "/", ".")
        self.f.execute_word("TEST")
        self.assertEquals("3 ", self.f.outs.get())

    def test_10_mod(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 3, "MOD", ".")
        self.f.execute_word("TEST")
        self.assertEquals("1 ", self.f.outs.get())

    def test_20_dot(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, ".", ".")
        self.f.execute_word("TEST")
        self.assertEquals("20 10 ", self.f.outs.get())

    def test_21_swap(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, "SWAP", ".", ".")
        self.f.execute_word("TEST")
        self.assertEquals("10 20 ", self.f.outs.get()) # . shoudl have space after it

    def test_22_dup(self):
        self.f.create_word("TEST", " DOLIT", 10, "DUP", ".", ".")
        self.f.execute_word("TEST")
        self.assertEquals("10 10 ", self.f.outs.get())

    def test_23_over(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, "OVER", ".", ".", ".")
        self.f.execute_word("TEST")
        self.assertEquals("10 20 10 ", self.f.outs.get())

    def test_24_rot(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, " DOLIT", 30, "ROT", ".", ".", ".")
        self.f.execute_word("TEST")
        self.assertEquals("10 30 20 ", self.f.outs.get())

    def test_25_drop(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, "DROP", ".", ".")
        #should be a 'data stack underflow' exception
        try:
            self.f.execute_word("TEST")
            self.fail("Did not get expected BufferUnderflow exception")
        except forth.BufferUnderflow:
            pass # expected
        self.assertEquals("10 ", self.f.outs.get())


    #def test_30_wblk_rblk(self):
    #    # wblk ( n a -- )  i.e. blocknum addr
    #    #self.f.machine.mem.dump(1024, 16) # TODO capture it
    #
    #   #TODO Addresses must not be manifsets, they must be related to actual spare space
    #   otherwise we trash our dictionary between each test
    #    self.f.create_word("W", " DOLIT", 0, " DOLIT", 1024, "WBLK") # probably DICT
    #    self.f.create_word("R", " DOLIT", 0, " DOLIT", 65536-1024, "RBLK")
    #    self.f.execute_word("W")
    #
    #    # rblk ( n a -- )  i.e. blocknum addr
    #    self.f.execute_word("R")
    #
    #    #self.f.machine.mem.dump(65536-1024, 16) # TODO compare it
    #    #TODO: assertEquals self.f.outs.get()

    def test_40_branch(self):
        """Test unconditional branch feature"""
        self.f.create_word("B", " DOLIT", 42, "EMIT", "BRANCH", -4)
        self.f.machine.limit = 20 # limit number of times round execute loop
        self.f.execute_word("B")
        self.assertEquals("******", self.f.outs.get())

    def test_41_0branch_taken(self):
        """Test conditional branch always taken"""
        self.f.create_word("B", " DOLIT", 43, "EMIT", " DOLIT", 1, "0BRANCH", -6)
        self.f.machine.limit = 20 # limit number of times round execute loop
        self.f.execute_word("B")
        self.assertEquals("+", self.f.outs.get())

    def test_42_0branch_nottaken(self):
        """Test conditional branch always not taken"""
        self.f.create_word("B", " DOLIT", 44, "EMIT", " DOLIT", 0, "0BRANCH", -6)
        self.f.machine.limit = 20 # limit to 10 times round DODOES
        self.f.execute_word("B")
        self.assertEquals(",,,,,", self.f.outs.get())

    def test_50_0eq(self):
        """Test 0= relational operator"""
        self.f.create_word("RF", " DOLIT", 10, "0=", ".")
        self.f.execute_word("RF")
        self.assertEquals("0 ", self.f.outs.get())
        self.f.outs.clear()

        self.f.create_word("RT", " DOLIT", 0, "0=", ".")
        self.f.execute_word("RT")
        self.assertEquals("65535 ", self.f.outs.get())

    def test_51_not(self):
        """Test NOT boolean operator"""
        self.f.create_word("NF", " DOLIT", 0, "NOT", ".")
        self.f.execute_word("NF")
        self.assertEquals("65535 ", self.f.outs.get())
        self.f.outs.clear()

        self.f.create_word("NT", " DOLIT", 1, "NOT", ".")
        self.f.execute_word("NT")
        self.assertEquals("0 ", self.f.outs.get())

    def test_52_0lt(self):
        """Test 0< relational operator"""
        self.f.create_word("LF", " DOLIT", 0, "0<", ".") #TODO: which way round is this?
        self.f.execute_word("LF")
        self.assertEquals("0 ", self.f.outs.get())
        self.f.outs.clear()

        #TODO: This fails due to incorrect handling of -1 in Machine
        #it comes out as 0xFFFF which is not less than 0.
        #This should be a SIGNED COMPARISON
        self.f.create_word("LT", " DOLIT", -1, "0<", ".") #TODO: which way round is this?
        self.f.execute_word("LT")
        self.assertEquals("0 ", self.f.outs.get())

    def XXXXtest_53_0gt(self): #TODO
        """Test 0> relational operator"""
        #TODO: needs a SIGNED COMPARISON
        self.f.create_word("GF")
        self.f.execute_word("GF")
        self.assertEquals("xxx ", self.f.outs.get())
        self.f.outs.clear()

        self.f.create_word("GT")
        self.f.execute_word("GT")
        self.assertEquals("xxx ", self.f.outs.get())

    def XXXXtest_54_ult(self): #TODO
        """Test U< relational operator"""
        #TODO: needs an UNSIGNED COMPARISON
        self.f.create_word("UF")
        self.f.execute_word("UF")
        self.assertEquals("xxx ", self.f.outs.get())
        self.f.outs.clear()

        self.f.create_word("UT")
        self.f.execute_word("UT")
        self.assertEquals("xxx ", self.f.outs.get())

    def Xtest_60_var_rdwr(self):
        # TEST is an NvMem var that increments the value on every read
        #print("HERE**********")
        self.f.create_word("VADD", "TEST", "@", ".")
        #This exercises the 8/16 bit read issue
        #because TEST increments on every byte read
        self.f.execute_word("VADD") # returns 0x0001
        self.f.execute_word("VADD") # returns 0x0003
        self.assertEquals("1 3 ", self.f.outs.get())

    def test_70_key(self):
        self.f.create_word("KEYS", "KEY", "EMIT")
        self.f.create_word("KEYS", "KEY", "EMIT")
        self.f.ins.set("*")
        self.f.execute_word("KEYS")
        self.assertEquals("*", self.f.outs.get())

    def test_80_show(self): #TODO should rename as TYPE?? (check relationship with PAD though)
        """SHOW what is in a buffer"""
        # fill TIB with some test data
        data = [i for i in range(ord('0'), ord('9')+1)]
        self.f.machine.tib.fwd(len(data))
        self.f.machine.tib.write(0, data)
        #self.f.machine.tib.dump(self.f.machine.tibstart, 10)

        self.f.create_word("TEST", "TIB", " DOLIT", 10, "SHOW")
        self.f.execute_word("TEST")
        self.assertEquals("0123456789", self.f.outs.get())

    def test_81_expect(self):
        """EXPECT a line"""
        self.f.create_word("TEST", "TIB", "TIBZ", "EXPECT" , "TIB", "SPAN", "@", "SHOW" )
        self.f.ins.set("HELLO\n")
        self.f.execute_word("TEST")
        #self.f.machine.tib.dump(self.f.machine.tibstart, 10)
        self.assertEquals("HELLO\n", self.f.outs.get())

    def test_82_count(self):
        """Convert counted string into address and count"""
        # create a counted string
        TESTDATA = "MyString"
        data = [len(TESTDATA)]
        for ch in TESTDATA:
            data.append(ord(ch))
        self.f.machine.tib.fwd(len(data))
        self.f.machine.tib.write(0, data)
        #self.f.machine.tib.dump(self.f.machine.tibstart, len(data)+4)

        self.f.create_word("TEST", "TIB", "COUNT", ".", ".")
        self.f.execute_word("TEST")
        self.assertEquals("8 32769 ", self.f.outs.get())

    def test_83_spaces(self):
        """Output a number of spaces"""
        self.f.create_word("TEST", " DOLIT", 20, "SPACES")
        self.f.execute_word("TEST")
        self.assertEquals("                    ", self.f.outs.get())



    #TODO: need smoke tests for
    #native NIP, TUCK
    #---- CONST
    #: FALSE   ( -- 0)                    0 ;
    #: TRUE   ( -- -1)                    -1 ;
    #----- ALU
    #: /MOD   ( n1 n2 -- n-rem n-quot)    DUP DUP / ROT ROT MOD SWAP ;
    #: 1+   ( n -- n+1)                   1 + ;
    #: 1-   ( n -- n-1)                   1 - ;
    #: 2+   ( n -- n+2)                   2 + ;
    #: 2-   ( n -- n-2)                   2 - ;
    #: 2*   ( n -- n*2)                   2 * ;
    #: 2/   ( n -- n/2)                   2 / ;
    #: NEGATE   ( n -- -n)                -1 * ;
    #: ABS   ( n -- |n|)                  DUP 0< 0BRANCH 2 NEGATE ;
    #: MIN   ( n1 n2 -- min)              OVER OVER < NOT 0BRANCH 2 SWAP DROP ;
    #: MAX   ( n1 n2 -- max)              OVER OVER > NOT 0BRANCH 2 SWAP DROP ;
    #----- STACK OPS
    #: >R   ( n -- )                      RP @ 1 + DUP ROT ! RP ! ;
    #: R>   ( -- n)                       RP DUP @ @ SWAP 1 - RP ! ;
    #: R@   ( -- n)                       RP @ @ ;
    #: SP@   ( -- a)                      SP @ ;
    #: ?DUP   ( n -- n n or 0 -- 0)       DUP 0BRANCH 2 DUP ;
    #: 2SWAP   ( d1 d2 -- d2 d1)          ROT >R ROT R> ;
    #: 2DUP   ( d -- d d)                 OVER OVER ;
    #: 2OVER   ( d1 d2 -- d1 d2 d1)       2SWAP 2DUP >R >R 2SWAP R> R> ;
    #: 2DROP   ( d --)                    DROP DROP ;
    #----- GENERAL I/O
    #: HEX   ( -- )                       16 BASE ! ;
    #: OCTAL   ( -- )                      8 BASE ! ;
    #: DECIMAL   ( -- )                   10 BASE ! ;
    #: CR   ( -- )                        13 EMIT ;
    #: SPACE   ( -- )                     32 EMIT ;
    #: PAGE   ( -- )                      12 EMIT ;
    #---- SIMPLE MEMORY OPS
    #: +!   ( n a -- )                    DUP @ ROT + ! ;
    #: 2!   ( d a -- )                    ROT SWAP DUP ROT SWAP ! 2 + ! ;
    #: 2@   ( a -- d)                     DUP @ SWAP 2 + @ ;


if __name__ == "__main__":
    unittest.main()

# END
