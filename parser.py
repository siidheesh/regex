from pprint import pprint
from nfa import NFA
import lexer

# FIXME: clean this up


def parse(tree):
    if tree[0] == "UNION_EXPR":
        return union_expr(tree[1])


def union_expr(kids):
    if kids is None or type(kids) is not tuple:
        return None

    res = None
    for kid in kids:
        k, v = kid
        if k != "CONCAT_EXPR":
            raise SyntaxError("expected CONCAT_EXPR")
        r = concat_expr(v)
        if r is not None:
            res = r if res is None else res | r

    return res


def concat_expr(kids):
    if kids is None or type(kids) is not tuple:
        return None

    res = None
    for kid in kids:
        if kid is None or type(kid) is not tuple:
            raise SyntaxError("invalid expr")
        k, v = kid
        r = None
        if k == "EXPR":
            r = expr(v)
        elif k == "KLEENE":
            r = kleene(v)
        elif k == "MATCH":
            r = matchop(v)
        elif k == "OPT":
            r = opt(v)
        elif type(k) is tuple and k[0] == "RANGE":
            r = range_qf(kid)
        else:
            raise SyntaxError(f"unknown expression found in CONCAT_EXPR: {k}")
        if r is not None:
            res = r if res is None else res & r

    return res


def kleene(kid):
    if kid is None or type(kid) is not tuple:
        return None
    k, v = kid
    if k != "EXPR":
        raise SyntaxError("expected EXPR in kleene")
    res = expr(v)
    if res != None:
        return res.kleenefy()
    return None


def matchop(kid):
    if kid is None or type(kid) is not tuple:
        return None
    k, v = kid
    if k != "EXPR":
        raise SyntaxError("expected EXPR in kleene")
    res = expr(v)
    if res != None:
        return res.matchify()
    return None


def opt(kid):
    if kid is None or type(kid) is not tuple:
        return None
    k, v = kid
    if k != "EXPR":
        raise SyntaxError("expected EXPR in opt")
    res = expr(v)
    if res != None:
        return res.optify()
    return None


def range_qf(kid):
    # TODO: clean this up
    if kid is None or type(kid) is not tuple:
        return None
    range_expr, expr_expr = kid
    k, v = range_expr
    if k != "RANGE":
        raise SyntaxError("expected RANGE in range_qf")
    if v is None or type(v) is not tuple:
        raise SyntaxError("invalid range expr")

    expr_tag, expr_inner = expr_expr
    if expr_tag != "EXPR":
        raise SyntaxError("expected EXPR in range_qf")

    res = expr(expr_inner)
    if res is None:
        return None

    range_type = v[0]
    if range_type == "N" and len(v) == 2:
        # range is of type {n}
        n = v[1]
        r = res.clone()
        # match an n-len run of expr
        for _ in range(n-1):
            r = r & res
        return r
    elif range_type == "N," and len(v) == 2:
        # range is of type {n,}
        n = v[1]
        r = res.clone()
        # match an n-len run of expr, followed by expr*
        for _ in range(n-1):
            r = r & res
        return r & res.kleenefy()
    elif range_type == "N,N" and len(v) == 3:
        # range is of type {n,m}
        n, m = v[1], v[2]
        r = NFA()
        # match a union of repeating exprs of length from n to m
        for i in range(n-1, m):
            if i < 0:
                continue
            r1 = res.clone()
            for _ in range(i):
                r1 = r1 & res
            r = r | r1
        return r
    else:
        raise SyntaxError("unknown range type in range_qf")


def expr(kid):
    if kid is None or type(kid) is not tuple:
        return None
    k, v = kid

    def make_nfa(pred):
        a = NFA()
        a.add_transition(NFA.START, pred, NFA.END)
        return a

    res = None
    if k == "EXTENDED_CHAR":
        res = make_nfa(extended_char(v))
    elif k == "CHAR_CLASS":
        res = make_nfa(char_class(v))
    elif k == "UNION_EXPR":
        res = union_expr(v)
    return res


def char_class(kid):
    if kid is None or type(kid) is not tuple:
        return None

    is_neg = False

    if kid[0] == "CHAR_CLASS_INNER_NEG":
        is_neg = True
    elif kid[0] != "CHAR_CLASS_INNER":
        raise SyntaxError("invalid char class type")

    #print("emitting char_class, is_neg:", is_neg)

    # get tuple of lambdas to test against
    lambdas = char_class_expr(kid[1])

    def char_class_helper(x):
        res = False
        for test in lambdas:
            res = res or test(x)
            if not is_neg and res:  # short-circuit if not complementary
                return True
        if is_neg and not res:
            return True
        return False

    # return lambda that tests for at least one match
    return char_class_helper


def char_class_expr(kids):
    if kids is None or type(kids) is not tuple:
        return None

    items = ()
    ranges = ()

    for i in range(len(kids)):
        k, v = kids[i]
        if k == "EXTENDED_CHAR":
            res = extended_char(v)
            if res is None:
                raise SyntaxError()
            items += (res,)
        elif k == "RANGE":
            items += (None,)
            ranges += (i,)

    for i in ranges:
        if i <= 0 or i >= len(kids) - 1:
            raise SyntaxError("invalid range in char class")
        start = kids[i-1][1]
        end = kids[i+1][1]
        items = items[:i] + (extended_char_range(start, end),) + items[i:]

    return tuple(filter(lambda el: el is not None, items))


def extended_char_range(start, end):
    def parse_char(kid):
        if kid is None or type(kid) is not tuple:
            raise SyntaxError("invalid char in char range")
        k, v = kid
        if k == "CHAR":
            return v
        elif k == "ASCII_CP" or k == "UNICODE_CP":
            return chr(int(v, 16))
        else:
            raise SyntaxError("invalid char in char range")
    start = parse_char(start)
    end = parse_char(end)

    if end < start:
        raise SyntaxError("invalid bounds in char range")

    def extended_char_range_helper(x):
        return start <= x and x <= end

    return extended_char_range_helper


def extended_char(kid):
    if kid is None or type(kid) is not tuple:
        return None
    k, v = kid
    #print("emitting extended_char", k, v)
    if k == "CHAR":
        return lambda x: x == v
    elif k == "WILDCARD":
        return lambda x: x != '\n'
    elif k == "ASCII_CP":
        return lambda x: ord(x) == int(v, 16)
    elif k == "UNICODE_CP":
        return lambda x: ord(x) == int(v, 16)
    elif k == "SPECIAL_CHAR":
        if v == "d":
            return lambda x: x.isdigit()
        elif v == "D":
            return lambda x: x.isdigit() == False
        elif v == "w":
            return lambda x: x.isalnum()
        elif v == "W":
            return lambda x: x.isalnum() == False
        elif v == "s":
            return lambda x: x.isspace()
        elif v == "S":
            return lambda x: x.isspace() == False
        elif v == "t":
            return lambda x: x == '\t'
        elif v == "r":
            return lambda x: x == '\r'
        elif v == "n":
            return lambda x: x == '\n'
        elif v == "v":
            return lambda x: x == '\v'
        elif v == "f":
            return lambda x: x == '\f'
        elif v == "0":
            return lambda x: x == '\0'
        else:
            raise SyntaxError("invalid escaped char")
    else:
        raise SyntaxError("invalid extended char")


if __name__ == "__main__":
    #tree = lexer.regex(r"[hcb](a|t)*(hello)*|1")
    regex = input("Enter pattern: ")
    regex = regex if regex != "" else r"\[{3,}\?[hc2-4g-\x707-9]{1,3}(a|t)*(he+llo)*|.\++|(\u1f60B|எழுத்து)*"
    tree = lexer.regex(regex)
    pprint(tree)
    fa = parse(tree)
    while True:
        test = input("test: ")
        print("MATCHED ✔️" if fa.process(test, debug=True) else "NOPE ❌")
