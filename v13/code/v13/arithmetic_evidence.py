"""Source-bound arithmetic expectation for C2 diagnostics, not a tool execution or answer authority.

Only an explicit short numeric expression accepted by the existing proposer is
evaluated. No eval, names, function calls, side effects or Age/tool permission changes.
"""
import ast
import decimal
import operator
import re

OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,
     ast.Div:operator.truediv}
MAX_ABS=decimal.Decimal('1000000000000')

def expectation(text):
    from .toolstep import propose
    p=propose(text)
    if not p or p['tool']!='calc':return None
    expr=p['args']['expression']
    if len(expr)>64 or not re.fullmatch(r'[0-9.+*/()%-]+',expr):return None
    try:
        tree=ast.parse(expr,mode='eval')
        def walk(node,depth=0):
            if depth>8:raise ValueError('depth')
            if isinstance(node,ast.Expression):return walk(node.body,depth+1)
            if isinstance(node,ast.Constant) and type(node.value) in (int,float):
                # Decimal from source lexeme avoids float rounding.
                return decimal.Decimal(ast.get_source_segment(expr,node))
            if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
                v=walk(node.operand,depth+1)
                return v if isinstance(node.op,ast.UAdd) else -v
            if isinstance(node,ast.BinOp) and type(node.op) in OPS:
                a=walk(node.left,depth+1);b=walk(node.right,depth+1)
                if abs(a)>MAX_ABS or abs(b)>MAX_ABS:raise ValueError('size')
                return OPS[type(node.op)](a,b)
            raise ValueError('unsupported')
        with decimal.localcontext() as ctx:
            ctx.prec=24
            result=walk(tree)
        if not result.is_finite() or abs(result)>MAX_ABS:return None
        return {'expression':expr,'expected':format(result.normalize(),'f'),
                'source_span':p['span'],'authority':'SOURCE_EXACT_ARITHMETIC_CHECK_ONLY'}
    except (SyntaxError,ValueError,decimal.DecimalException,ZeroDivisionError,OverflowError):
        return None
