from lark.visitors import Transformer
import more_itertools
import operator
import logging
from .utils import logger
from python_log_indenter import IndentedLoggerAdapter

logger = IndentedLoggerAdapter(logger)

class query_context:
    def __init__(self, root, working_set):
        self.root = root
        self.working_set = working_set

    def update_working_set(self, new_set):
        self.working_set = list(new_set)
        return self

    def __bool__(self):
        """For predicates - anything in the workinf set implies True"""
        return True if self.working_set else False

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
    def INDEX_PREDICATE_TAG(self, token):
        return token.update(value=int(token.value.lstrip('[').rstrip(']')))

#endregion

    # 'Compiles' the query
#region rule_processing

    def start(self, children):
        def _to_result(context):
            result = list(context.working_set)
            if result:
                if len(result)==1:
                    return result[0]
                return result 
            return None

        return lambda context: _to_result(children[0](context))

    def absolutelocation_path(self, children):
        """Reset to use the root of the tree"""
        remaining_terms = self.__class__._chain_functions(children)
        func = lambda context: remaining_terms(query_context(context.root, [context.root]))
        return self._log_wrapper(func, 'absolutelocation_path')

    def relativelocation_path(self, children):
        """Apply this tree to the working set"""
        func = self.__class__._chain_functions(children)
        return self._log_wrapper(func, 'relativelocation_path')
    
    def child_step(self, children):
        """Navigate one level down the tree I.e. "\". 
        We need to apply the default axes (child) if not explicitly set"""
        def _step(context):
            context = self._apply_axis_specifier(context, children[0], self.child_axis_specifier([]))
            return self.__class__._chain_functions(children[1:])(context)
            
        return self._log_wrapper(self._log_indent_wrapper(_step), 'child_step')

    def descendent_step(self, children):
        """Navigate to all items in the tree starting at from teh workign set I.e."\\"
        We need to apply the default axes (descendant) if not explicitly set"""
        def _descendent_step(context):
            context = self._apply_axis_specifier(context, children[0], self.descendant_axis_specifier([]))
            return self.__class__._chain_functions(children[1:])(context)            
            
        return self._log_wrapper(self._log_indent_wrapper(_descendent_step), 'descendent_step')

    def default_axis_specifier(self, children):
        """Set in the grammar as a gudie for this transformer"""
        # Use ourself as a flag value
        return self.default_axis_specifier

    def null_axis_specifier(self, children):
        """Set in the grammar as a gudie for this transformer"""
        # Use ourself as a flag value
        return self.null_axis_specifier

    def child_axis_specifier(self, children):
        """Swap the working set for all child nodes of the working set"""
        func = lambda context: context.update_working_set(self._to_children(context.working_set))
        return self._log_wrapper(func, 'child::')

    def descendant_axis_specifier(self, children):
        """Swap the working set for all descendants of the working set"""
        func = lambda context: context.update_working_set(self._all_nodes(self._to_children(context.working_set)))
        return self._log_wrapper(func, 'descendant::')             

    def self_axis_specifier(self, children):
        """Reference self - so-op"""
        func = lambda context: context
        return self._log_wrapper(func, 'self::') 

    def descendant_or_self(self, children):
        """Add all descendants of the working set to it"""
        func = lambda context: context.update_working_set(self._all_nodes(context.working_set))
        return self._log_wrapper(func, 'descendant-or-self::') 

    def attribute_step(self, children):
        """Get an attribute value as part of a path. I.e. /@foo"""
        func = lambda context: context.update_working_set(getattr(item, children[0].value, None) for item in context.working_set)
        return self._log_wrapper(func, '@')

    def slice_expr(self, children):
        """Python slice of the working set"""
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
        return self._log_wrapper(func, f'slice[{start}:{stop}:{step}]]') 

    def predicate_expr(self, children):
        """A non-slice predicate. I.e [some expression]
        This will filter items in the working set"""

        def _item_context(current_context, item):
            """For the recrsive grammar to work, we need a new working set containing
            just the item being tested."""
            return query_context(current_context.root, [item])

        expr = self._log_indent_wrapper(self.__class__._chain_functions(children))
        func = lambda context:context.update_working_set(item for item in context.working_set if expr(_item_context(context, item)))
        return self._log_wrapper(func, 'predicate_expr')

    def index_predicate(self, children):
        """ [<int>] """
        index = children[0].value
        func = lambda context: context.update_working_set([more_itertools.nth(context.working_set, index)] if index>=0 else more_itertools.islice_extended(context.working_set)[index:])
        return self._log_wrapper(func, f'index[{index}]') 

    def tname_test(self, children):
        """Test node (not leafs) names in the working set"""
        compare_name = children[0].value
        compare_func = lambda item: getattr(item, self._tree_node_nameattr, None)==compare_name
        func = lambda context: context.update_working_set(item for item in context.working_set if compare_func(item))
        return self._log_wrapper(func, f'tname_test: "{compare_name}"') 

    def wildcard_name_test(self, children):
        """All items: no-op"""
        func = lambda context: context
        return self._log_wrapper(func, '*') 

    def leaf_node_test(self, children):
        """Keep the leaf nodes in the working set"""
        func = lambda context: context.update_working_set(item for item in context.working_set if not self._is_node(item))
        return self._log_wrapper(func, 'leaf()') 

    def node_node_test(self, children):
        """Keep the tree nodes in the working set"""
        func = lambda context: context.update_working_set(item for item in context.working_set if self._is_node(item))
        return self._log_wrapper(func, 'node()') 

    def equality_expr(self, children):
        """Execute an (in)equality expression"""
        func = lambda context: children[1].value(children[0](context.working_set[0]), children[2](context.working_set[0]))
        return self._log_wrapper(self._log_indent_wrapper(func), f'equality_expr: {children[1].value.__name__}')

    def or_expr(self, children):
        """Boolean or"""
        lhs_func = self._log_indent_wrapper(children[0])
        rhs_func = self._log_indent_wrapper(children[1])
        func = lambda context: lhs_func(context) or rhs_func(context)
        return self._log_wrapper(func, 'or_expr')

    def and_expr(self, children):
        """Boolean and"""
        lhs_func = self._log_indent_wrapper(children[0])
        rhs_func = self._log_indent_wrapper(children[1])
        func = lambda context: lhs_func(context) and rhs_func(context)
        return self._log_wrapper(func, 'and_expr')

    def attribute_accessor(self, children):
        """Get an attribute value as part of an expression"""
        func = lambda item: getattr(item, children[0].value, None)
        return self._log_wrapper(func, f'@{children[0].value}')

    def string_literal(self, children):
        func = lambda item: children[0].value
        return self._log_wrapper(func, children[0].value)

    def integer_literal(self, children):
        func = lambda item: children[0].value
        return self._log_wrapper(func, children[0].value)

    def decimal_literal(self, children):
        func = lambda item: children[0].value
        return self._log_wrapper(func, children[0].value)

#endregion

#region Support methods
    
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

    def _log_indent_wrapper(self, func):
        def indent_func_wrapper(*args, **kwargs):
            logger.add()
            result = func(*args, **kwargs)
            logger.sub()
            return result

        return indent_func_wrapper

    def _log_wrapper(self, func, msg):
        def func_wrapper(*args, **kwargs):
            logger.debug(msg)
            return func(*args, **kwargs)

        if hasattr(func, 'tree_ql_tag'):
            return func

        f = func_wrapper
        f.tree_ql_tag = msg
        return f

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

    def _apply_axis_specifier(self, context, specifier, default):
        if specifier==self.default_axis_specifier:
            return default(context)
        elif specifier==self.null_axis_specifier:
            return context
        else:
            return specifier(context)
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
