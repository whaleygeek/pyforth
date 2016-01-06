# tests.py  06/01/2016  (c) D.J.Whale
#
# Test harness for forth.py

import unittest
import forth

class TestForth(unittest.TestCase):

    def setUp(self):
        self.f = forth.Forth().boot()

    def test_1_star(self):
        """Output a single * on stdout"""

        self.f.create_word("TEST", 42, "EMIT")
        self.f.execute_word("TEST")

    def test_2_hello(self):
        """Output a Hello world! message"""

        msg = "Hello world!\n"
        pfa = []
        for ch in msg:
            pfa.append(ord(ch))
            pfa.append("EMIT")

        self.f.create_word("TEST", *pfa)
        self.f.execute_word("TEST")

    def test_3_add(self):
        """Add 1 and 2"""
        self.f.create_word("TEST", 1, 2, "+", ".")
        self.f.execute_word("TEST")


if __name__ == "__main__":
    unittest.main()

# END
