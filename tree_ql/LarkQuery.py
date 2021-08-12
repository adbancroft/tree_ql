from .tree_ql import create_tree_parser

class LarkQuery():
    _query_parser = create_tree_parser('data', 'children')

    def __init__(self, query_str):
        self._compiled_query = self.__class__._query_parser.parse(query_str)

    def execute(self, tree):
        return self._compiled_query([tree])   
        