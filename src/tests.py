# tests.py  06/01/2016  (c) D.J.Whale
#
# Test harness for forth.py

import unittest
import forth

# A small smoke-test - non exhaustive.

class TestForth(unittest.TestCase):

    def setUp(self):
        self.f = forth.Forth().boot()

    # very basic test of stack
    def test_00_stack_pushpop(self):
        EXPECTED = 42
        self.f.machine.ds.pushn(EXPECTED)
        actual = self.f.machine.ds.popn()
        self.assertEquals(EXPECTED, actual)

    def Xtest_01_star(self):
        """Output a single * on stdout"""

        self.f.create_word("TEST", " DOLIT", 42, "EMIT")
        self.f.execute_word("TEST")

    def Xtest_02_hello(self):
        """Output a Hello world! message"""

        msg = "Hello world!\n"
        pfa = []
        for ch in msg:
            pfa.append(" DOLIT")
            pfa.append(ord(ch))
            pfa.append("EMIT")

        self.f.create_word("TEST", *pfa)
        self.f.execute_word("TEST")

    def Xtest_03_add(self):
        """Add 1 and 2"""
        self.f.create_word("TEST", " DOLIT", 1, " DOLIT", 2, "+", ".")
        self.f.execute_word("TEST")

    def Xtest_04_sub(self):
        """Subtract"""
        self.f.create_word("TEST", " DOLIT", 2, " DOLIT", 1, "-", ".")
        self.f.execute_word("TEST")

    def Xtest_05_and(self):
        self.f.create_word("TEST", " DOLIT", 0xFFFF, " DOLIT", 0x8000, "AND", ".")
        self.f.execute_word("TEST")

    def Xtest_06_or(self):
        self.f.create_word("TEST", " DOLIT", 0xFFFF, " DOLIT", 0x8000, "OR", ".")
        self.f.execute_word("TEST")

    def Xtest_07_xor(self):
        self.f.create_word("TEST", " DOLIT", 0x0001, " DOLIT", 0x8000, "XOR", ".")
        self.f.execute_word("TEST")

    def Xtest_08_mult(self):
        self.f.create_word("TEST", " DOLIT", 2, " DOLIT", 4, "*", ".")
        self.f.execute_word("TEST")

    def Xtest_09_div(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 3, "/", ".")
        self.f.execute_word("TEST")

    def Xtest_10_mod(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 3, "MOD", ".")
        self.f.execute_word("TEST")

    def Xtest_20_dot(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, ".", ".")
        self.f.execute_word("TEST")

    def Xtest_21_swap(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, "SWAP", ".", ".")
        self.f.execute_word("TEST")

    def Xtest_22_dup(self):
        self.f.create_word("TEST", " DOLIT", 10, "DUP", ".", ".")
        self.f.execute_word("TEST")

    def Xtest_23_over(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, "OVER", ".", ".", ".")
        self.f.execute_word("TEST")

    def Xtest_24_rot(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, " DOLIT", 30, "ROT", ".", ".", ".")
        self.f.execute_word("TEST")

    def Xtest_25_drop(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, "DROP", ".", ".")
        #TODO should be a 'data stack underflow' exception
        self.f.execute_word("TEST")

    def Xtest_30_wblk_rblk(self):
        # wblk ( n a -- )  i.e. blocknum addr
        #self.f.machine.mem.dump(1024, 16) # TODO capture it

        self.f.create_word("W", " DOLIT", 0, " DOLIT", 1024, "WBLK") # probably DICT
        self.f.create_word("R", " DOLIT", 0, " DOLIT", 65536-1024, "RBLK")
        self.f.execute_word("W")

        # rblk ( n a -- )  i.e. blocknum addr
        self.f.execute_word("R")

        #self.f.machine.mem.dump(65536-1024, 16) # TODO compare it

    def Xtest_40_branch(self):
        """Test unconditional branch feature"""
        self.f.create_word("B", " DOLIT", 42, "EMIT", "BRANCH", -4)
        self.f.machine.limit = 20 # limit number of times round execute loop
        self.f.execute_word("B")

    def Xtest_41_0branch_taken(self):
        """Test conditional branch always taken"""
        self.f.create_word("B", " DOLIT", 43, "EMIT", " DOLIT", 1, "0BRANCH", -6)
        self.f.machine.limit = 20 # limit number of times round execute loop
        self.f.execute_word("B")

    def Xtest_42_0branch_nottaken(self):
        """Test conditional branch always not taken"""
        self.f.create_word("B", " DOLIT", 44, "EMIT", " DOLIT", 0, "0BRANCH", -6)
        self.f.machine.limit = 20 # limit to 10 times round DODOES
        self.f.execute_word("B")

    def Xtest_50_0eq(self):
        """Test 0= relational operator"""
        self.f.create_word("RF", " DOLIT", 10, "0=", ".")
        self.f.execute_word("RF")

        self.f.create_word("RT", " DOLIT", 0, "0=", ".")
        self.f.execute_word("RT")

    def Xtest_51_not(self):
        """Test NOT boolean operator"""
        self.f.create_word("NF", " DOLIT", 0, "NOT", ".")
        self.f.execute_word("NF")

        self.f.create_word("NT", " DOLIT", 1, "NOT", ".")
        self.f.execute_word("NT")

    def Xtest_52_0lt(self):
        """Test 0< relational operator"""
        self.f.create_word("LF", " DOLIT", 0, "0<", ".")
        self.f.execute_word("LF")

        #TODO: This fails due to incorrect handling of -1 in Machine
        #it comes out as 0xFFFF which is not less than 0.
        #This should be a SIGNED COMPARISON
        self.f.create_word("LT", " DOLIT", -1, "0<", ".")
        self.f.execute_word("LT")

    def Xtest_53_0gt(self): #TODO
        """Test 0> relational operator"""
        #TODO: needs a SIGNED COMPARISON
        self.f.create_word("GF")
        self.f.execute_word("GF")

        self.f.create_word("GT")
        self.f.execute_word("GT")

    def Xtest_54_ult(self): #TODO
        """Test U< relational operator"""
        #TODO: needs an UNSIGNED COMPARISON
        self.f.create_word("UF")
        self.f.execute_word("UF")

        self.f.create_word("UT")
        self.f.execute_word("UT")


if __name__ == "__main__":
    unittest.main()

# END
