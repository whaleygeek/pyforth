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

        self.f.create_word("TEST", 42, "EMIT") #TODO: "DOLIT", 42
        self.f.execute_word("TEST")

    def Xtest_02_hello(self):
        """Output a Hello world! message"""

        msg = "Hello world!\n"
        pfa = []
        for ch in msg:
            pfa.append(ord(ch)) #TODO: "DOLIT" ord(ch)
            pfa.append("EMIT")

        self.f.create_word("TEST", *pfa)
        self.f.execute_word("TEST")

    def Xtest_03_add(self):
        """Add 1 and 2"""
        self.f.create_word("TEST", 1, 2, "+", ".") #TODO: DOLIT, 1, DOLIT, 2, + .
        self.f.execute_word("TEST")

    def Xtest_04_sub(self):
        """Subtract"""
        self.f.create_word("TEST", 2, 1, "-", ".")
        self.f.execute_word("TEST")

    def Xtest_05_and(self):
        self.f.create_word("TEST", 0xFFFF, 0x8000, "AND", ".") #TODO: DOLIT, 0xFFFF, DOLIT, 0x8000, AND
        self.f.execute_word("TEST")

    def Xtest_06_or(self):
        self.f.create_word("TEST", 0xFFFF, 0x8000, "OR", ".") #TODO
        self.f.execute_word("TEST")

    def Xtest_07_xor(self):
        self.f.create_word("TEST", 0x0001, 0x8000, "XOR", ".") #TODO
        self.f.execute_word("TEST")

    def Xtest_08_mult(self):
        self.f.create_word("TEST", 2, 4, "*", ".") # TODO
        self.f.execute_word("TEST")

    def Xtest_09_div(self):
        self.f.create_word("TEST", 10, 3, "/", ".") # TODO
        self.f.execute_word("TEST")

    def Xtest_10_mod(self):
        self.f.create_word("TEST", 10, 3, "MOD", ".") #TODO
        self.f.execute_word("TEST")

    def Xtest_20_dot(self):
        self.f.create_word("TEST", 10, 20, ".", ".") #TODO
        self.f.execute_word("TEST")

    def Xtest_21_swap(self):
        self.f.create_word("TEST", 10, 20, "SWAP", ".", ".") #TODO
        self.f.execute_word("TEST")

    def Xtest_22_dup(self):
        self.f.create_word("TEST", 10, "DUP", ".", ".") #TODO
        self.f.execute_word("TEST")

    def Xtest_23_over(self):
        self.f.create_word("TEST", 10, 20, "OVER", ".", ".", ".") #TODO
        self.f.execute_word("TEST")

    def Xtest_24_rot(self):
        self.f.create_word("TEST", 10, 20, 30, "ROT", ".", ".", ".") #TODO
        self.f.execute_word("TEST")

    def Xtest_25_drop(self):
        self.f.create_word("TEST", 10, 20, "DROP", ".", ".") #TODO
        #TODO should be a 'data stack underflow' exception
        self.f.execute_word("TEST")

    def Xtest_30_wblk_rblk(self):
        # wblk ( n a -- )  i.e. blocknum addr
        #self.f.machine.mem.dump(1024, 16)

        self.f.create_word("W", 0, 1024, "WBLK") # probably DICT #TODO
        self.f.create_word("R", 0, 65536-1024, "RBLK") #TODO
        self.f.execute_word("W")

        # rblk ( n a -- )  i.e. blocknum addr
        self.f.execute_word("R")

        #self.f.machine.mem.dump(65536-1024, 16)

    def test_40_branch(self):
        """Test unconditional branch feature"""
        self.f.create_word("B", " DOLIT", 42, "EMIT", "BRANCH", -8)
        self.f.machine.limit = 10 #limit to 10 times round DODOES
        self.f.execute_word("B")

if __name__ == "__main__":
    unittest.main()

# END
