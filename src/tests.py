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

        self.f.create_word("TEST", 42, "EMIT")
        self.f.execute_word("TEST")

    def test_02_hello(self):
        """Output a Hello world! message"""

        msg = "Hello world!\n"
        pfa = []
        for ch in msg:
            pfa.append(ord(ch))
            pfa.append("EMIT")

        self.f.create_word("TEST", *pfa)
        self.f.execute_word("TEST")

    def test_03_add(self):
        """Add 1 and 2"""
        self.f.create_word("TEST", 1, 2, "+", ".")
        self.f.execute_word("TEST")

    def test_04_sub(self):
        """Subtract"""
        self.f.create_word("TEST", 2, 1, "-", ".")
        self.f.execute_word("TEST")

    def test_05_and(self):
        self.f.create_word("TEST", 0xFFFF, 0x8000, "AND", ".")
        self.f.execute_word("TEST")

    def test_06_or(self):
        self.f.create_word("TEST", 0xFFFF, 0x8000, "OR", ".")
        self.f.execute_word("TEST")

    def test_07_xor(self):
        self.f.create_word("TEST", 0x0001, 0x8000, "XOR", ".")
        self.f.execute_word("TEST")

    def test_08_mult(self):
        self.f.create_word("TEST", 2, 4, "*", ".")
        self.f.execute_word("TEST")

    def test_09_div(self):
        self.f.create_word("TEST", 10, 3, "/", ".")
        self.f.execute_word("TEST")

    def test_10_mod(self):
        self.f.create_word("TEST", 10, 3, "MOD", ".")
        self.f.execute_word("TEST")

    def test_20_dot(self):
        self.f.create_word("TEST", 10, 20, ".", ".")
        self.f.execute_word("TEST")

    def test_21_swap(self):
        self.f.create_word("TEST", 10, 20, "SWAP", ".", ".")
        self.f.execute_word("TEST")

    def test_22_dup(self):
        self.f.create_word("TEST", 10, "DUP", ".", ".")
        self.f.execute_word("TEST")

    def test_23_over(self):
        self.f.create_word("TEST", 10, 20, "OVER", ".", ".", ".")
        self.f.execute_word("TEST")

    def test_24_rot(self):
        self.f.create_word("TEST", 10, 20, 30, "ROT", ".", ".", ".")
        self.f.execute_word("TEST")

    def test_25_drop(self):
        self.f.create_word("TEST", 10, 20, "DROP", ".", ".")
        #TODO should be a 'data stack underflow' exception
        self.f.execute_word("TEST")


    def test_30_wblk_rblk(self):
        # wblk ( n a -- )  i.e. blocknum addr
        #self.f.machine.mem.dump(1024, 16)

        self.f.create_word("W", 0, 1024, "WBLK") # probably DICT
        self.f.create_word("R", 0, 65536-1024, "RBLK")
        self.f.execute_word("W")

        # rblk ( n a -- )  i.e. blocknum addr
        self.f.execute_word("R")

        #self.f.machine.mem.dump(65536-1024, 16)

if __name__ == "__main__":
    unittest.main()

# END
