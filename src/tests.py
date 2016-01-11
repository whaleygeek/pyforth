# tests.py  06/01/2016  (c) D.J.Whale
#
# Test harness for forth.py

import unittest
import forth

#TODO: Split into to suites, one for the full set of tests,
#another for the test being developed
# can then turn all other tests off while developing new test

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


    def Xtest_01_star(self):
        """Output a single * on stdout"""
        self.f.create_word("TEST", " DOLIT", 42, "EMIT") #TODO: need a " DOCHR" otherwise stack will break
        self.f.execute_word("TEST")
        self.assertEquals("*", self.f.outs.get())

    def Xtest_02_hello(self):
        """Output a Hello world! message"""

        msg = "Hello world!\n"
        pfa = []
        for ch in msg:
            pfa.append(" DOLIT") #TODO: need a " DOCHR" otherwise stack will break
            pfa.append(ord(ch))
            pfa.append("EMIT")

        self.f.create_word("TEST", *pfa)
        self.f.execute_word("TEST")
        self.assertEquals(msg, self.f.outs.get())

    def Xtest_03_add(self):
        """Add 1 and 2"""
        self.f.create_word("TEST", " DOLIT", 1, " DOLIT", 2, "+", ".")
        self.f.execute_word("TEST")
        self.assertEquals("3 ", self.f.outs.get())

    def Xtest_04_sub(self):
        """Subtract"""
        self.f.create_word("TEST", " DOLIT", 2, " DOLIT", 1, "-", ".")
        self.f.execute_word("TEST")
        self.assertEquals("1 ", self.f.outs.get())

    def Xtest_05_and(self):
        self.f.create_word("TEST", " DOLIT", 0xFFFF, " DOLIT", 0x8000, "AND", ".")
        self.f.execute_word("TEST")
        self.assertEquals("32768 ", self.f.outs.get())

    def Xtest_06_or(self):
        self.f.create_word("TEST", " DOLIT", 0xFFFF, " DOLIT", 0x8000, "OR", ".")
        self.f.execute_word("TEST")
        self.assertEquals("65535 ", self.f.outs.get())

    def Xtest_07_xor(self):
        self.f.create_word("TEST", " DOLIT", 0x0001, " DOLIT", 0x8000, "XOR", ".")
        self.f.execute_word("TEST")
        self.assertEquals("32769 ", self.f.outs.get())

    def Xtest_08_mult(self):
        self.f.create_word("TEST", " DOLIT", 2, " DOLIT", 4, "*", ".")
        self.f.execute_word("TEST")
        self.assertEquals("8 ", self.f.outs.get())

    def Xtest_09_div(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 3, "/", ".")
        self.f.execute_word("TEST")
        self.assertEquals("3 ", self.f.outs.get())

    def Xtest_10_mod(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 3, "MOD", ".")
        self.f.execute_word("TEST")
        self.assertEquals("1 ", self.f.outs.get())

    def Xtest_20_dot(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, ".", ".") #TODO: . should have space after it
        self.f.execute_word("TEST")
        self.assertEquals("20 10 ", self.f.outs.get())

    def Xtest_21_swap(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, "SWAP", ".", ".")
        self.f.execute_word("TEST")
        self.assertEquals("10 20 ", self.f.outs.get()) # . shoudl have space after it

    def Xtest_22_dup(self):
        self.f.create_word("TEST", " DOLIT", 10, "DUP", ".", ".")
        self.f.execute_word("TEST")
        self.assertEquals("10 10 ", self.f.outs.get())

    def Xtest_23_over(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, "OVER", ".", ".", ".")
        self.f.execute_word("TEST")
        self.assertEquals("10 20 10 ", self.f.outs.get())

    def Xtest_24_rot(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, " DOLIT", 30, "ROT", ".", ".", ".")
        self.f.execute_word("TEST")
        self.assertEquals("10 30 20 ", self.f.outs.get())

    def Xtest_25_drop(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, "DROP", ".", ".")
        #should be a 'data stack underflow' exception
        #TODO try/catch this exception and expect it.
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

    def Xtest_40_branch(self):
        """Test unconditional branch feature"""
        self.f.create_word("B", " DOLIT", 42, "EMIT", "BRANCH", -4) #TODO DOCHR
        self.f.machine.limit = 20 # limit number of times round execute loop
        self.f.execute_word("B")
        self.assertEquals("******", self.f.outs.get())

    def Xtest_41_0branch_taken(self):
        """Test conditional branch always taken"""
        self.f.create_word("B", " DOLIT", 43, "EMIT", " DOLIT", 1, "0BRANCH", -6) # TODO DOCHR
        self.f.machine.limit = 20 # limit number of times round execute loop
        self.f.execute_word("B")
        self.assertEquals("+", self.f.outs.get())

    def Xtest_42_0branch_nottaken(self):
        """Test conditional branch always not taken"""
        self.f.create_word("B", " DOLIT", 44, "EMIT", " DOLIT", 0, "0BRANCH", -6) # TODO DOCHR
        self.f.machine.limit = 20 # limit to 10 times round DODOES
        self.f.execute_word("B")
        self.assertEquals(",,,,,", self.f.outs.get())

    def Xtest_50_0eq(self):
        """Test 0= relational operator"""
        self.f.create_word("RF", " DOLIT", 10, "0=", ".")
        self.f.execute_word("RF")
        self.assertEquals("0 ", self.f.outs.get())
        self.f.outs.clear()

        self.f.create_word("RT", " DOLIT", 0, "0=", ".")
        self.f.execute_word("RT")
        self.assertEquals("65535 ", self.f.outs.get())

    def Xtest_51_not(self):
        """Test NOT boolean operator"""
        self.f.create_word("NF", " DOLIT", 0, "NOT", ".")
        self.f.execute_word("NF")
        self.assertEquals("65535 ", self.f.outs.get())
        self.f.outs.clear()

        self.f.create_word("NT", " DOLIT", 1, "NOT", ".")
        self.f.execute_word("NT")
        self.assertEquals("0 ", self.f.outs.get())

    def Xtest_52_0lt(self):
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

    def Xtest_70_key(self):
        self.f.create_word("KEYS", "KEY", "EMIT") # TODO DOCHR
        self.f.create_word("KEYS", "KEY", "EMIT") # TODO DOCHR
        self.f.ins.set("*")
        self.f.execute_word("KEYS")
        #self.f.outs.flush() # does a print # TODO have a get() and clear()
        self.assertEquals("*", self.f.outs.get())

    #def test_99_dumpdict(self):
    #    self.f.machine.dict.dump()

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
    ##: 2DUP   ( d -- d d)                 OVER OVER ;
    #: 2OVER   ( d1 d2 -- d1 d2 d1)       2SWAP 2DUP >R >R 2SWAP R> R> ;
    #: 2DROP   ( d --)                    DROP DROP ;
    #----- GENERAL I/O
    #: HEX   ( -- )                       16 BASE ! ;
    ##: OCTAL   ( -- )                     8 BASE ! ;
    #: DECIMAL   ( -- )                   10 BASE ! ;
    #: CR   ( -- )                        13 EMIT ;
    #: SPACE   ( -- )                     32 EMIT ;
    #: PAGE   ( -- )                      12 EMIT ;
    #---- SIMPLE MEMORY OPS
    #: +!   ( n a -- )                    DUP @ ROT + ! ;
    #: 2!   ( d a -- )                    ROT SWAP DUP ROT SWAP ! 2 + ! ;
    #: 2@   ( a -- d)                     DUP @ SWAP 2 + @ ;

    def test_80_show(self):
        # fill TIB with some test data
        self.f.create_word("TEST",
            " DOLIT", 0x30, "SPAN", "C!",                   # init value to 48
            "TIB", ">IN", "!",                              # init ptr to TIB
            " DOLIT", 10, "COUNT", "!",                     # init count to 9
                                                            # target:loop
            "COUNT", "@", "0=", "NOT", "0BRANCH", 29,       # if count 0, exit
            "SPAN", "C@", ">IN", "@", "C!",                 # store value at addr
            ">IN", "@", " DOLIT", 1, "+", ">IN", "!",       # inc ptr
            "COUNT", "@", " DOLIT", 1, "-", "COUNT", "!",   # dec count
            "SPAN", "C@", " DOLIT", 1, "+", "SPAN", "C!",   # add one to char
            "BRANCH", -33,                                  # to:loop
                                                            # target:exit
            "TIB", ">IN", "!",
            " DOLIT", 10, "COUNT", "!"
            )

        self.f.execute_word("TEST")
        #self.f.machine.tib.dump(self.f.machine.tibstart, 10)

        # Now use: TIB COUNT SHOW to test show works
        self.f.create_word("TEST2", "TIB", "COUNT", "@", "SHOW")
        #self.f.machine.limit=20
        self.f.execute_word("TEST2")
        self.assertEquals("0123456789", self.f.outs.get())


    def XXtest_81_expect(self):
        """EXPECT a line"""
        self.f.create_word("TEST", "TIB", "TIBZ", "EXPECT", "TIB", "SPAN", "SHOW")
        self.f.ins.set("HELLO")
        self.f.execute_word("TEST")
        self.assertEquals("xxx", self.f.outs.get())


if __name__ == "__main__":
    unittest.main()

# END
