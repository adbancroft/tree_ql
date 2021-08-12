
# TreeQL: a query language for Tree structures
## What
A query language for Tree structures, modeled after [XPath](https://en.wikipedia.org/wiki/XPath#Syntax_and_semantics_%28XPath_1.0%29).

Provides a concrete implementation for [Lark](https://github.com/lark-parser/lark) parse trees. Can be extended to other tree structures.

Example:

    from tree_ql import LarkQuery
    from lark  import Lark
    from pathlib  import Path
    from tests.test_data.python_indenter import PythonIndenter
    
    parser = Lark.open(Path(__file__).parent / 'tests' /'test_data'/'python3.lark', start = 'file_input', postlex = PythonIndenter(), parser = 'lalr')
    with open(Path(__file__), 'r') as f:
        tree = parser.parse(f.read() +'\n')
    
    query = LarkQuery('/import_stmt/import_from/dotted_name/[@type="NAME"]/@value')
    result = query.execute(tree)
    print(result)

Prints:

    ['tree_ql', 'lark', 'pathlib', 'tests', 'test_data', 'python_indenter']

Full grammar is [here](https://github.com/adbancroft/tree_ql/blob/master/tree_ql/tree_ql.lark).

Install via pip:

    pip install git+https://github.com/adbancroft/tree_ql.git

## Why
Lark parse trees can already be navigated using:

 1. The provided hooks for [visitation &
    transformation](https://lark-parser.readthedocs.io/en/latest/visitors.html#). These are comprehensive and type safe, but result in a lot of code if you need to query the tree in many different ways.
    
 2. Native Python approaches such as list comprehensions. Simple to use if processing a limited set of nodes (such a `Tree.children`), but complicated to write to be fully aware of the entire tree.

This module provides a 3rd method,  positioned between these 2. It takes account of the tree hierarchy while providing the flexibility of a query language.