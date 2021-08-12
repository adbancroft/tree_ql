import unittest
from logging import DEBUG, StreamHandler, getLogger
from pathlib import Path
from test_data.python_indenter import PythonIndenter

# from lark.lexer import Token
from tree_ql import LarkQuery
from lark import Lark, LarkError, Tree

# We will use a python file as our test tree
_PYTHON_GRAMMAR = Path(__file__).parent /'test_data'/'python3.lark'
_GRAMMAR_CACHE = _PYTHON_GRAMMAR.with_suffix('.lark.cache')
_PYTHON_PARSER = Lark.open(_PYTHON_GRAMMAR, start = 'file_input', postlex = PythonIndenter(), parser = 'lalr', cache = str(_GRAMMAR_CACHE))
test_data_filepath = Path(__file__).parent /'test_data'/'aifc.py'
with open(test_data_filepath, 'r') as f:
    _TEST_TREE = _PYTHON_PARSER.parse(f.read() +'\n')

class test_lark_ql(unittest.TestCase):

    def setUp(self):
        log = getLogger( self.__class__.__name__ )
        log.addHandler(StreamHandler())
        log.setLevel(DEBUG)

    def test_bad_path_fails(self):
        with self.assertRaises(LarkError):
            subject = LarkQuery('')
        with self.assertRaises(LarkError):
            subject = LarkQuery('/')
            
    def test_tree_path(self):
        subject = LarkQuery('/expr_stmt')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(result.data, 'expr_stmt')
        self.assertEqual(len(result.children), 1)

        subject = LarkQuery('/expr_stmt/string')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(result.data, 'string')
        self.assertEqual(len(result.children), 1)

        subject = LarkQuery('/funcdef/parameters')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 13)

    def test_child_index(self):
        subject = LarkQuery('/[6]')
        result = subject.execute(_TEST_TREE)
        self.assertIsInstance(result, Tree)
        self.assertEqual(result.data, 'assign_stmt')

        subject = LarkQuery('/[-1]')
        result = subject.execute(_TEST_TREE)
        self.assertIsInstance(result, Tree)
        self.assertEqual(result.data, 'if_stmt')

    def test_slice(self):
        subject = LarkQuery('/[:]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), len(_TEST_TREE.children))

        subject = LarkQuery('/[1:]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), len(_TEST_TREE.children)-1)

        subject = LarkQuery('/[:-1]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), len(_TEST_TREE.children)-1)

        subject = LarkQuery('/[1:1]')
        result = subject.execute(_TEST_TREE)
        self.assertFalse(result)

        subject = LarkQuery('/[1:2]')
        result = subject.execute(_TEST_TREE)
        self.assertIsInstance(result, Tree)
        self.assertEqual(result.data, 'import_stmt')

        subject = LarkQuery('/[2::2]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), len(_TEST_TREE.children)//2)

        subject = LarkQuery('/[::2]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 1+(len(_TEST_TREE.children)//2))

    def test_attribute_selector(self):
        subject = LarkQuery('/funcdef/[@type="NAME"]@value')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 13)
        self.assertEqual(result[0], '_read_long')
        self.assertEqual(result[12], 'open')

    def test_or(self):
        subject = LarkQuery('/[@data="classdef" or @data="funcdef"]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 16)
        self.assertEqual(result[0].children[0].value, 'Error')
        self.assertEqual(result[15].children[0].value, 'open')

    def test_and(self):
        subject = LarkQuery('/funcdef/parameters/[@type="NAME" and @value="file"]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 5)
        self.assertEqual(result[0].value, 'file')

if __name__ == '__main__':
    unittest.main()
