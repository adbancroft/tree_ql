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
        return lambda context: lhs_func(context) or rhs_func(context)

    def and_expression(self, children):
        lhs_func = children[0]
        rhs_func = children[1]
        return lambda context: lhs_func(context) and rhs_func(context)

    def slice(self, children):
        slice_object = children[0]
        return lambda context: more_itertools.islice_extended(context)[slice_object]

    def node_test_expression(self, children):
        comparison_attr = children[0].value
        compare_op = children[1].value
        compare_value = children[2].value
        return lambda node: hasattr(node, comparison_attr) and compare_op(getattr(node, comparison_attr), compare_value)

    def filter_expression(self, children):
        return lambda context: (node for node in context if children[0](node)) 

    def attribute_selector(self, children):
        attribute = children[0].value
        return lambda context: (getattr(node, attribute) for node in context if hasattr(node, attribute))

    def tree_data_selector(self, children):
        return lambda context: (node for node in context if hasattr(node, self._tree_node_nameattr) and getattr(node, self._tree_node_nameattr)==children[0].value)

    def child_context(self, children):
        return lambda context: more_itertools.collapse((getattr(item, self._tree_node_childattr) for item in context if hasattr(item, self._tree_node_childattr)))

    def child_index(self, children):
        index = children[0].value
        return lambda context: [more_itertools.nth(context, index)] if index>=0 else more_itertools.islice_extended(context)[index:]

    def child_selector(self, children):
        return self.__class__._chain_functions(children)

    def start(self, children):
        def _to_result(context):
            result = list(context)
            if result:
                if len(result)==1:
                    return result[0]
                return result 
            return None

        func = self.__class__._chain_functions(children)
        return lambda context: _to_result(func(context))
        
#endregion

    @staticmethod
    def _chain_functions(children):
        def _chain_functions_inner(context):
            for func in children:
                context = func(context)
            return context        

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
