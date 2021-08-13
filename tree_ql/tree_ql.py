from lark.visitors import Transformer
import more_itertools
import operator
import logging
from .utils import logger

class EnterExitLog():
    def __init__(self, funcName):
        self.funcName = funcName

    def __enter__(self):
        logger.debug('Started: %s' % self.funcName)
        return self

    def __exit__(self, type, value, tb):
        pass

class query_context:
    def __init__(self, root, working_set):
        self.root = root
        self.working_set = working_set

    def update_working_set(self, new_set):
        self.working_set = new_set
        return self

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
    def ADD_OP(self, token):
        return token.update(value=operator.add)       
    def MINUS_OP(self, token):
        return token.update(value=operator.sub)       
    def MUL_OP(self, token):
        return token.update(value=operator.mul)       
    def DIV_OP(self, token):
        return token.update(value=operator.truediv)       
    def MOD_OP(self, token):
        return token.update(value=operator.mod)       
    # def NODE_TEST_TAG(self, token):
    #     return token.update(value=token.value.lstrip('@'))
    def ATTRIBUTE_SELECTOR_TAG(self, token):
        return token.update(value=token.value.lstrip('@'))
    def INDEX_PREDICATE_TAG(self, token):
        return token.update(value=int(token.value.lstrip('[').rstrip(']')))

#endregion

    # 'Compiles' the query
#region rule_processing

    # def or_expression(self, children):
    #     lhs_func = children[0]
    #     rhs_func = children[1]
    #     return lambda context: lhs_func(context) or rhs_func(context)

    # def and_expression(self, children):
    #     lhs_func = children[0]
    #     rhs_func = children[1]
    #     return lambda context: lhs_func(context) and rhs_func(context)

    # def node_test_expression(self, children):
    #     comparison_attr = children[0].value
    #     compare_op = children[1].value
    #     compare_value = children[2].value
    #     return lambda node: hasattr(node, comparison_attr) and compare_op(getattr(node, comparison_attr), compare_value)

    # def filter_expression(self, children):
    #     return lambda context: (node for node in context if children[0](node)) 

    # def attribute_selector(self, children):
    #     attribute = children[0].value
    #     return lambda context: (getattr(node, attribute) for node in context if hasattr(node, attribute))

    # def tree_data_selector(self, children):
    #     return lambda context: (node for node in context if hasattr(node, self._tree_node_nameattr) and getattr(node, self._tree_node_nameattr)==children[0].value)

    # def child_context(self, children):
    #     return lambda context: more_itertools.collapse((self._to_children(item) for item in context.working_set))

    # def child_index(self, children):
    #     index = children[0].value
    #     return lambda context: [more_itertools.nth(context, index)] if index>=0 else more_itertools.islice_extended(context)[index:]

    # def child_selector(self, children):
    #     return self.__class__._chain_functions(children)

    def start(self, children):
        def _to_result(context):
            result = list(context.working_set)
            if result:
                if len(result)==1:
                    return result[0]
                return result 
            return None

        return lambda context: _to_result(children[0](context))
        
#endregion

#region Rule processing support

    def _is_node(self, item):
        return hasattr(item, self._tree_node_childattr)

    def _all_nodes(self, context):
        return self._scan_nodes(context, lambda c : c)

    def _scan_nodes(self, context, pred):
        """Return all values in the tree that evaluate pred(value) as true."""
        for item in context:
            if pred(item):
                yield item
            yield from self._scan_nodes(self._to_children([item]), pred)   

    def _to_children(self, working_set):
        return more_itertools.collapse((getattr(item, self._tree_node_childattr) for item in working_set if self._is_node(item)))

    def _wrap_function(self, func, tag):
        def func_wrapper(*args, **kwargs):
            with EnterExitLog(tag):
                return func(*args, **kwargs)

        if hasattr(func, 'tree_ql_tag'): return func

        f = func_wrapper
        f.tree_ql_tag = tag
        return f

    def _evaluate(lhs, op, rhs, item):
        def to_value(maybe_value, item):
            if callable(maybe_value):
                return maybe_value(item)
            else:
                return maybe_value.children[0].value
        return op(to_value(lhs, item), to_value(rhs, item))

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

#endregion

# ================= NEW

#region Context rules

    def absolutelocation_path(self, children):
        remaining_terms = self.__class__._chain_functions(children)
        func = lambda context: remaining_terms(query_context(context.root, [context.root]))
        return self._wrap_function(func, 'absolutelocation_path')

    def relativelocation_path(self, children):
        func = self.__class__._chain_functions(children)
        return self._wrap_function(func, 'relativelocation_path')
    
    def child_step(self, children):
        def _step(context):
            mutable_children = children
            if mutable_children[0]==self.default_axis_specifier:
                context = self.child_axis_specifier([])(context)
                mutable_children = mutable_children[1:]
            return self.__class__._chain_functions(mutable_children)(context)
            
        return self._wrap_function(_step, 'child_step')

    def descendent_step(self, children):
        def _descendent_step(context):
            mutable_children = children
            if mutable_children[0]==self.default_axis_specifier:
                context = self.descendant_axis_specifier([])(context)
                mutable_children = mutable_children[1:]
            return self.__class__._chain_functions(mutable_children)(context)
            
        return self._wrap_function(_descendent_step, 'descendent_step')

    def default_axis_specifier(self, children):
        # Use ourself as a flag value
        return self.default_axis_specifier

    def child_axis_specifier(self, children):
        func = lambda context: context.update_working_set(self._to_children(context.working_set))
        return self._wrap_function(func, 'child_axis_specifier')

    def descendant_axis_specifier(self, children):
        func = lambda context: context.update_working_set(self._all_nodes(self._to_children(context.working_set)))
        return self._wrap_function(func, 'descendant_axis_specifier')             

    def self_axis_specifier(self, children):
        func = lambda context: context
        return self._wrap_function(func, 'self_axis_specifier') 

    def descendant_or_self(self, children):
        func = lambda context: context.update_working_set(self._all_nodes(context.working_set))
        return self._wrap_function(func, 'descendant_or_self') 

    def attribute_step(self, children):
        func = lambda context: context.update_working_set(getattr(item, children[0].value, None) for item in context.working_set)
        return self._wrap_function(func, 'attribute_step')

    def slice_expr(self, children):
        def _get_first_int(children):
            if children and children[0].type=='INTEGER_LITERAL':
                return children[0].value
            return None

        start = _get_first_int(children)
        children = children[(2 if start else 1):]
        stop = _get_first_int(children)
        children = children[(2 if stop else 1):]
        step = _get_first_int(children)

        func = lambda context: context.update_working_set(more_itertools.islice_extended(context.working_set, start, stop, step))
        return self._wrap_function(func, 'slice_expr') 

    def predicate_expr(self, children):
        expr = self.__class__._chain_functions(children)
        func = lambda context:context.update_working_set(item for item in context.working_set if expr(item))
        return self._wrap_function(func, 'predicate_expr')

    def index_predicate(self, children):
        index = children[0].value
        func = lambda context: context.update_working_set([more_itertools.nth(context.working_set, index)] if index>=0 else more_itertools.islice_extended(context.working_set)[index:])
        return self._wrap_function(func, 'index_predicate') 

#end region

#region item tests

    def tname_test(self, children):
        compare_name = children[0].value
        compare_func = lambda item: getattr(item, self._tree_node_nameattr, None)==compare_name
        func = lambda context: context.update_working_set(item for item in context.working_set if compare_func(item))
        return self._wrap_function(func, 'tname_test') 

    def wildcard_name_test(self, children):
        func = lambda context: context
        return self._wrap_function(func, 'wildcard_name_test') 

    def leaf_node_test(self, children):
        func = lambda context: context.update_working_set(item for item in context.working_set if not self._is_node(item))
        return self._wrap_function(func, 'leaf_node_test') 

    def node_node_test(self, children):
        func = lambda context: context.update_working_set(item for item in context.working_set if self._is_node(item))
        return self._wrap_function(func, 'leaf_node_test') 

    def equality_expr(self, children):      
        func = lambda item: self.__class__._evaluate(children[0], children[1].value, children[2], item)
        return self._wrap_function(func, 'equality_expr')

    def attribute_accessor(self, children):
        func = lambda item: getattr(item, children[0].value, None)
        return self._wrap_function(func, 'attribute_accessor')

#endregion

from pathlib import Path
from lark import Lark

_GRAMMAR = Path(__file__).parent / 'tree_ql.lark'
_GRAMMAR_CACHE = _GRAMMAR.with_suffix('.lark.cache')

def create_tree_parser(tree_node_nameattr, tree_node_childattr):
    """
    tree_node_nameattr is the name of the attribute that provides the tree node name
    tree_node_childattr is the name of the attribute that accesses a tree nodes children
    """    
    return Lark.open(_GRAMMAR, parser = 'lalr', maybe_placeholders=True, transformer = _inline_transformer(tree_node_nameattr, tree_node_childattr), cache=str(_GRAMMAR_CACHE))
