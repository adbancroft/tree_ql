import unittest
from logging import DEBUG, StreamHandler, getLogger
from pathlib import Path
from test_data.python_indenter import PythonIndenter

# from lark.lexer import Token
from tree_ql import LarkQuery, logger
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
        logger.addHandler(StreamHandler())
        logger.setLevel(DEBUG)

    def test_bad_path_fails(self):
        with self.assertRaises(LarkError):
            subject = LarkQuery('')
        with self.assertRaises(LarkError):
            subject = LarkQuery('/')
    
    def test_root_absolute_location_path(self):
        pass

    def testdescendent_absolutelocation_path(self):
        subject = LarkQuery('//assign_stmt')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 180)
        for stmt in result:
            self.assertEqual('assign_stmt', stmt.data)

    def testdescendent_relativelocation_path(self):
        subject = LarkQuery('/classdef/suite//assign_stmt')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 131)
        for stmt in result:
            self.assertEqual('assign_stmt', stmt.data)

    def test_wildcard(self):
        subject = LarkQuery('/funcdef/*')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 39)
        self.assertEqual('_read_long', result[0].value)
        self.assertEqual('suite', result[38].data)

    def test_name_node_test(self):
        subject = LarkQuery('/expr_stmt')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(result.data, 'expr_stmt')
        self.assertEqual(len(result.children), 1)

        subject = LarkQuery('/funcdef/parameters')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 13)

    def test_child_axis_specifier(self):
        subject = LarkQuery('/assign_stmt/child::*')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 10)
        for stmt in result:
            self.assertEqual('assign', stmt.data)

    def test_self_axis_specifier(self):
        subject = LarkQuery('/assign_stmt/self::*')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 10) 
        self.assertEqual('assign_stmt', result[0].data)
        self.assertEqual('assign_stmt', result[9].data)

    def test_descendent_axis_specifier(self):
        subject = LarkQuery('/assign_stmt/descendant::*')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 83) 
        self.assertEqual('assign', result[0].data)
        self.assertEqual('"""\\\nA human-readable version of the compression type\n(\'not compressed\' for AIFF files)"""', result[82].value)

        subject = LarkQuery('/assign_stmt/descendant::var')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 11) 
        for stmt in result:
            self.assertEqual('var', stmt.data)

    def test_descendentself_axis_specifier(self):
        subject = LarkQuery('/assign_stmt/descendant-or-self::*')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 93) 
        self.assertEqual('assign_stmt', result[0].data)
        self.assertEqual('"""\\\nA human-readable version of the compression type\n(\'not compressed\' for AIFF files)"""', result[92].value)

        subject = LarkQuery('/assign_stmt/descendant-or-self::string')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 10) 
        for stmt in result:
            self.assertEqual('string', stmt.data)        

    def test_child_index(self):
        subject = LarkQuery('/child::*[6]')
        result = subject.execute(_TEST_TREE)
        self.assertIsInstance(result, Tree)
        self.assertEqual(result.data, 'assign_stmt')

        subject = LarkQuery('/child::*[-1]')
        result = subject.execute(_TEST_TREE)
        self.assertIsInstance(result, Tree)
        self.assertEqual(result.data, 'if_stmt')

    def test_slice(self):
        subject = LarkQuery('/child::*[:]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), len(_TEST_TREE.children))

        subject = LarkQuery('/child::*[1:]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), len(_TEST_TREE.children)-1)

        subject = LarkQuery('/child::*[:-1]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), len(_TEST_TREE.children)-1)

        subject = LarkQuery('/child::*[1:1]')
        result = subject.execute(_TEST_TREE)
        self.assertFalse(result)

        subject = LarkQuery('/child::*[1:2]')
        result = subject.execute(_TEST_TREE)
        self.assertIsInstance(result, Tree)
        self.assertEqual(result.data, 'import_stmt')

        subject = LarkQuery('/child::*[2::2]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), len(_TEST_TREE.children)//2)

        subject = LarkQuery('/child::*[::2]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 1+(len(_TEST_TREE.children)//2))

    def test_equality_op(self):
        subject = LarkQuery('/funcdef/parameters/child::*[@value=="file"]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 5) 
        for r in result:
            self.assertEqual('file', r.value) 

    # def test_contextitem_expr(self):

    def test_attribute_selector(self):
        subject = LarkQuery('/funcdef/child::*[@type=="NAME"]/@value')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 13)
        self.assertEqual(result[0], '_read_long')
        self.assertEqual(result[12], 'open')

    def test_or(self):
        subject = LarkQuery('/child::*[@data=="classdef" or @data=="funcdef"]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 16)
        self.assertEqual(result[0].children[0].value, 'Error')
        self.assertEqual(result[15].children[0].value, 'open')

    def test_and(self):
        subject = LarkQuery('/funcdef/parameters/child::*[@type=="NAME" and @value=="file"]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 5)
        for r in result:
            self.assertEqual('file', r.value) 

    def test_sub_query(self):
        subject = LarkQuery('/classdef/self::*[.//funcdef/descendant::*[@value=="__exit__"]]')# and @value=="__exit__"]]')
        # subject = LarkQuery('/classdef//funcdef//descendant::*[@value=="__exit__"]')# and @value=="__exit__"]]')
        result = subject.execute(_TEST_TREE)
        self.assertEqual(len(result), 2)
        self.assertEqual('classdef', result[0].data)
        self.assertEqual('classdef', result[0].data)
        self.assertEqual('Aifc_read', result[0].children[0].value)
        self.assertEqual('Aifc_write', result[1].children[0].value)

if __name__ == '__main__':
    unittest.main()
