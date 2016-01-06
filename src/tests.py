# tests.py  06/01/2016  (c) D.J.Whale
#
# Test harness for forth.py

import unittest
import forth

# A small smoke-test - non exhaustive.

class TestForth(unittest.TestCase):

    def setUp(self):
        self.f = forth.Forth().boot()

    def test_01_star(self):
        """Output a single * on stdout"""

        self.f.create_word("TEST", " DOLIT", 42, "EMIT")
        self.f.execute_word("TEST")

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

    def test_03_add(self):
        """Add 1 and 2"""
        self.f.create_word("TEST", " DOLIT", 1, " DOLIT", 2, "+", ".")
        self.f.execute_word("TEST")

    def test_04_sub(self):
        """Subtract"""
        self.f.create_word("TEST", " DOLIT", 2, " DOLIT", 1, "-", ".")
        self.f.execute_word("TEST")

    def test_05_and(self):
        self.f.create_word("TEST", " DOLIT", 0xFFFF, " DOLIT", 0x8000, "AND", ".")
        self.f.execute_word("TEST")

    def test_06_or(self):
        self.f.create_word("TEST", " DOLIT", 0xFFFF, " DOLIT", 0x8000, "OR", ".")
        self.f.execute_word("TEST")

    def test_07_xor(self):
        self.f.create_word("TEST", " DOLIT", 0x0001, " DOLIT", 0x8000, "XOR", ".")
        self.f.execute_word("TEST")

    def test_08_mult(self):
        self.f.create_word("TEST", " DOLIT", 2, " DOLIT", 4, "*", ".")
        self.f.execute_word("TEST")

    def test_09_div(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 3, "/", ".")
        self.f.execute_word("TEST")

    def test_10_mod(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 3, "MOD", ".")
        self.f.execute_word("TEST")

    def test_20_dot(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, ".", ".")
        self.f.execute_word("TEST")

    def test_21_swap(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, "SWAP", ".", ".")
        self.f.execute_word("TEST")

    def test_22_dup(self):
        self.f.create_word("TEST", " DOLIT", 10, "DUP", ".", ".")
        self.f.execute_word("TEST")

    def test_23_over(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, "OVER", ".", ".", ".")
        self.f.execute_word("TEST")

    def test_24_rot(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, " DOLIT", 30, "ROT", ".", ".", ".")
        self.f.execute_word("TEST")

    def test_25_drop(self):
        self.f.create_word("TEST", " DOLIT", 10, " DOLIT", 20, "DROP", ".", ".")
        #TODO should be a 'data stack underflow' exception
        self.f.execute_word("TEST")

    def test_30_wblk_rblk(self):
        # wblk ( n a -- )  i.e. blocknum addr
        #self.f.machine.mem.dump(1024, 16) # TODO capture it

        self.f.create_word("W", " DOLIT", 0, " DOLIT", 1024, "WBLK") # probably DICT
        self.f.create_word("R", " DOLIT", 0, " DOLIT", 65536-1024, "RBLK")
        self.f.execute_word("W")

        # rblk ( n a -- )  i.e. blocknum addr
        self.f.execute_word("R")

        #self.f.machine.mem.dump(65536-1024, 16) # TODO compare it

    def test_40_branch(self):
        """Test unconditional branch feature"""
        self.f.create_word("B", " DOLIT", 42, "EMIT", "BRANCH", -8)
        self.f.machine.limit = 20 # limit to 20 times round DODOES
        self.f.execute_word("B")

    def test_41_0branch_taken(self):
        """Test conditional branch always taken"""
        self.f.create_word("B", " DOLIT", 43, "EMIT", " DOLIT", 1, "0BRANCH", -10)
        self.f.execute_word("B")

    def test_42_0branch_nottaken(self):
        """Test conditional branch always not taken"""
        self.f.create_word("B", " DOLIT", 43, "EMIT", " DOLIT", 0, "0BRANCH", -12)
        self.f.machine.limit = 20 # limit to 10 times round DODOES
        self.f.execute_word("B")

    def test_50_0eq(self):
        """Test 0= relational operator"""
        self.f.create_word("RF", " DOLIT", 10, "0=", ".")
        self.f.execute_word("RF")

        self.f.create_word("RT", " DOLIT", 0, "0=", ".")
        self.f.execute_word("RT")

    def Xtest_51_not(self): #TODO
        """Test NOT boolean operator"""
        self.f.create_word("N")
        self.f.execute_word("N")

    def Xtest_52_0lt(self): #TODO
        """Test 0< relational operator"""
        self.f.create_word("LF")
        self.f.execute_word("LF")
        self.f.create_word("LT")
        self.f.execute_word("LT")

    def Xtest_53_0gt(self): #TODO
        """Test 0> relational operator"""
        self.f.create_word("GF")
        self.f.execute_word("GF")
        self.f.create_word("GT")
        self.f.execute_word("GT")

    def Xtest_54_ult(self): #TODO
        """Test U< relational operator"""
        self.f.create_word("UF")
        self.f.execute_word("UF")
        self.f.create_word("UT")
        self.f.execute_word("UT")


if __name__ == "__main__":
    unittest.main()

# END
