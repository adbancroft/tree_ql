from tree_ql import LarkQuery
from lark  import Lark, Tree
from pathlib  import Path
from tests.test_data.python_indenter import PythonIndenter

# Parse this file
parser = Lark.open(Path(__file__).parent / 'tests' /'test_data'/'python3.lark', start = 'file_input', postlex = PythonIndenter(), parser = 'lalr')
with open(Path(__file__), 'r') as f:
    tree = parser.parse(f.read() +'\n')

# query = LarkQuery('/import_stmt/import_from/dotted_name/[@type="NAME"]/@value')
query = LarkQuery('/import_stmt/import_from//leaf()')
result = query.execute(tree)
for r in result:
    if isinstance(r, Tree):
        print(r.pretty())
    else:
        print(r)