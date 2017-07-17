from .context import dataquery

import unittest

class TestQueries(unittest.TestCase):
    queries = []

    def setUp(self):
        print ""

    def test_parse_period(self):
        parse_period('1 week')

def main():
    unittest.main()

if __name__ == '__main__':
    main()
