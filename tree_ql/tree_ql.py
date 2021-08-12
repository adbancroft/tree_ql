from lark.visitors import Transformer
import more_itertools
import operator

class _inline_transformer(Transformer):
    
    def __init__(self, tree_node_nameattr, tree_node_childattr):
        """
        tree_node_nameattr is the name of the attribute that provides the tree node name
        tree_node_childattr is the name of the attribute that accesses a tree nodes children
        """
        self._tree_node_nameattr = tree_node_nameattr
        self._tree_node_childattr = tree_node_childattr

    # Converts or adjusts terminals
#region terminal_processing
    def INTEGER_LITERAL(self, token):
        return token.update(value=int(token.value))
    def DECIMAL_LITERAL(self, token):
        return token.update(value=float(token.value))
    def STRING_LITERAL(self, token):
        return token.update(value=token.value.strip('"\''))
    def OP_EQUAL(self, token):
        return token.update(value=operator.eq)
    def OP_NOT_EQUAL(self, token):
        return token.update(value=operator.ne)
    def OP_LESS_THAN(self, token):
        return token.update(value=operator.lt)
    def OP_GREATER_THAN(self, token):
        return token.update(value=operator.gt)
    def OP_LESS_THAN_EQUAL(self, token):
        return token.update(value=operator.le)
    def OP_GREATER_THAN_EQUAL(self, token):
        return token.update(value=operator.ge)
    def NODE_TEST_TAG(self, token):
        return token.update(value=token.value.lstrip('@'))
    def ATTRIBUTE_SELECTOR_TAG(self, token):
        return token.update(value=token.value.lstrip('/@'))      
#endregion

    # 'Compiles' the query
#region rule_processing
    def slice_op(self, children):
        def _get_first_int(children):
            if children and children[0].type=='INTEGER_LITERAL':
                return children[0].value
            return None

        start = _get_first_int(children)
        children = children[(2 if start else 1):]
        stop = _get_first_int(children)
        children = children[(2 if stop else 1):]
        step = _get_first_int(children)

        return slice(start, stop, step)

    def or_expression(self, children):
        lhs_func = children[0]
        rhs_func = children[1]
        func = lambda input: lhs_func(input) or rhs_func(input)
        return self.__class__._skip_if_emptyinput(func)

    def and_expression(self, children):
        lhs_func = children[0]
        rhs_func = children[1]
        func = lambda input: lhs_func(input) and rhs_func(input)
        return self.__class__._skip_if_emptyinput(func)

    def slice(self, children):
        slice_object = children[0]
        func = lambda input: more_itertools.islice_extended(input)[slice_object]
        return self.__class__._skip_if_emptyinput(func)

    def node_test_expression(self, children):
        comparison_attr = children[0].value
        compare_op = children[1].value
        compare_value = children[2].value
        func = lambda node: hasattr(node, comparison_attr) and compare_op(getattr(node, comparison_attr), compare_value)
        return self.__class__._skip_if_emptyinput(func)

    def filter_expression(self, children):
        func = lambda input: (node for node in input if children[0](node)) 
        return self.__class__._skip_if_emptyinput(func)

    def attribute_selector(self, children):
        attribute = children[0].value
        func = lambda input: (getattr(node, attribute) for node in input if hasattr(node, attribute))
        return self.__class__._skip_if_emptyinput(func)

    def tree_data_selector(self, children):
        func = lambda input: (node for node in input if hasattr(node, self._tree_node_nameattr) and getattr(node, self._tree_node_nameattr)==children[0].value)
        return self.__class__._skip_if_emptyinput(func)

    def all_children(self, children):
        func = lambda input: more_itertools.collapse((getattr(item, self._tree_node_childattr) for item in input if hasattr(item, self._tree_node_childattr)))
        return self.__class__._skip_if_emptyinput(func)

    def child_index(self, children):
        index = children[0].value
        func = lambda input: [more_itertools.nth(input, index)] if index>=0 else more_itertools.islice_extended(input)[index:]
        return self.__class__._skip_if_emptyinput(func)

    def child_selector(self, children):
        func = self.__class__._chain_functions(children)
        return self.__class__._skip_if_emptyinput(func)

    def start(self, children):
        def _to_result(input):
            result = list(input)
            if result:
                if len(result)==1:
                    return result[0]
                return result 
            return None

        func = self.__class__._chain_functions(children)
        return lambda input: _to_result(func(input))
        
#endregion

    @staticmethod
    def _skip_if_emptyinput(func):
        """Optimization: do no further processing if there is no input"""
        def __skip_if_emptyinput(input):
            return func(input) if input else input
        return __skip_if_emptyinput

    @staticmethod
    def _chain_functions(children):
        def _chain_functions_inner(input):
            for func in children:
                input = func(input)
            return input        

        if len(children)==1:
            return children[0]
        else:
            return _chain_functions_inner

from pathlib import Path
from lark import Lark

_GRAMMAR = Path(__file__).parent / 'tree_ql.lark'
_GRAMMAR_CACHE = _GRAMMAR.with_suffix('.lark.cache')

def create_tree_parser(tree_node_nameattr, tree_node_childattr):
    """
    tree_node_nameattr is the name of the attribute that provides the tree node name
    tree_node_childattr is the name of the attribute that accesses a tree nodes children
    """    
    return Lark.open(_GRAMMAR, parser = 'lalr', transformer = _inline_transformer(tree_node_nameattr, tree_node_childattr), cache=str(_GRAMMAR_CACHE))
