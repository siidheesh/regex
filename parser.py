from nfa import NFA

# FIXME: clean this up


def parse(tree):
    if tree[0] == "UNION_EXPR":
        return union_expr(tree[1])
    raise SyntaxError("expected a union expression at the root")


def union_expr(kids):
    if kids is None or type(kids) is not tuple:
        return None

    union = []

    for kid in kids:
        k = kid[0]
        if k == "CONCAT_EXPR":
            r = concat_expr(kid[1])
        elif k == "ANCHORED_EXPR":
            k, anchor_type, v = kid
            r = anchored_expr(v, anchor_type)
        else:
            raise SyntaxError("expected ANCHORED_EXPR")

        if r is not None:
            union.append(r)

    return union[0] | union[1:] if len(union) > 1 else union[0]


def anchored_expr(kid, anchor_type):
    if kid is None or type(kid) is not tuple:
        return None
    k, v = kid

    if k != "CONCAT_EXPR":
        raise SyntaxError("expected CONCAT_EXPR in ANCHORED_EXPR")

    concat_list = [concat_expr(v)]

    if '^' in anchor_type:
        start = NFA()
        start.add_transition(NFA.START, None, NFA.END)
        # guard: at the start of input or after a newline
        start.add_guard(
            NFA.START, lambda f: f['pos'] <= 0 or f["input"][f['pos'] - 1] == '\n')
        concat_list = [start] + concat_list

    if '$' in anchor_type:
        end = NFA()
        end.add_transition(NFA.START, None, NFA.END)
        # guard: at the end of input or before a newline
        end.add_guard(
            NFA.START, lambda f: f['pos'] == f["input_len"] - 1 or f["input"][f['pos'] + 1] == '\n')
        concat_list += [end]

    if len(concat_list) > 1:
        return concat_list[0] & concat_list[1:]
    return concat_list[0]


def concat_expr(kids):
    if kids is None or type(kids) is not tuple:
        return None

    concat = []

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
        # FIXME: lookaheads and lookbehinds don't currently work if the fa is later kleenefied etc.
        elif k == "LOOKAHEAD" or k == "LOOKAHEAD_NEG":
            is_neg = k == "LOOKAHEAD_NEG"
            k, lookahead_tree = v
            if k != "UNION_EXPR":
                raise SyntaxError(f"expected UNION_EXPR in lookahead")
            la_fa = union_expr(lookahead_tree)

            # run the lookbehind fa against the input ahead of the current pos
            def lookahead_guard(f):
                pos = f["pos"]
                input = f["input"]
                inlen = f["input_len"]
                if pos + 1 > inlen:
                    return is_neg
                res = la_fa.process(input, pos+1, inlen, short_circuit=True)
                return (is_neg and not res) or (not is_neg and res)

            # if the expr is successfully matched, check if the lookahead is satisfied
            r = NFA()
            r.add_transition(NFA.START, None, NFA.END)
            r.add_guard(NFA.START, lookahead_guard)

        elif k == "LOOKBEHIND" or k == "LOOKBEHIND_NEG":
            is_neg = k == "LOOKBEHIND_NEG"
            # the lookbehind expr is inverted by the lexer
            k, lookbehind_tree = v
            if k != "UNION_EXPR":
                raise SyntaxError(f"expected UNION_EXPR in lookbehind")
            lb_fa = union_expr(lookbehind_tree)

            # run the lookbehind fa against the reverse of the input before the current
            def lookbehind_guard(f):
                pos = f["pos"]
                input = f["input"][pos::-1]
                if len(input) < pos + 1:
                    return is_neg
                res = lb_fa.process(input, 0, pos+1, short_circuit=True)
                return (is_neg and not res) or (not is_neg and res)

            # before the expr is tested, check if the lookbehind is satisfied
            r = NFA()
            r.add_transition(NFA.START, None, NFA.END)
            r.add_guard(NFA.START, lookbehind_guard)

        else:
            raise SyntaxError(f"unknown expression found in CONCAT_EXPR: {k}")

        if r is not None:
            concat.append(r)

    return concat[0] & concat[1:] if len(concat) > 1 else concat[0]


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
        raise SyntaxError("expected RANGE in range quantifier")
    if v is None or type(v) is not tuple:
        raise SyntaxError("invalid range expr")

    expr_tag, expr_inner = expr_expr
    if expr_tag != "EXPR":
        raise SyntaxError("expected EXPR in range quantifier")

    res = expr(expr_inner)
    if res is None:
        return None

    range_type = v[0]
    if range_type == "N" and len(v) == 2:
        # range is of type {n}
        n = v[1]
        # match an n-len run of expr
        if n > 1:
            return res & [res for _ in range(n-1)]
        elif n == 1:
            return res
        elif n == 0:
            return None
        else:
            raise SyntaxError("invalid bound in range quantifier")
    elif range_type == "N," and len(v) == 2:
        # range is of type {n,}
        n = v[1]
        if n > 1:
            # match an n-len run of exprs, followed by expr*
            concat = [res] * (n-1) + [res.kleenefy()]
            return res & concat
        elif n == 1:
            # match expr atleast once
            return res.matchify()
        elif n == 0:
            # basically the kleene star op
            return res.kleenefy()
        else:
            raise SyntaxError("invalid bound in range quantifier")
    elif range_type == ",N" and len(v) == 2:
        # range is of type {,n} (eq. to {0,n})
        return range_qf_n_m(0, v[1], res)
    elif range_type == "N,N" and len(v) == 3:
        # range is of type {n,m}
        return range_qf_n_m(v[1], v[2], res)
    else:
        raise SyntaxError("unknown bound type in range quantifier")


def range_qf_n_m(n, m, expr_fa):
    if not (n >= 0 and m >= 0 and m >= n):
        raise SyntaxError("invalid bounds in range quantifier")
    if m == 0:
        # skip if upper bound is 0
        return None
    union = []
    for run_len in range(n, m+1):
        if run_len > 1:
            union.append(expr_fa & [expr_fa] * (run_len - 1))
        elif run_len == 1:
            union.append(expr_fa)
        else:  # run_len is 0
            fallthrough = NFA()
            fallthrough.add_transition(NFA.START, None, NFA.END)
            union.append(fallthrough)
    return union[0] | union[1:] if len(union) > 1 else union[0]


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

    # print("emitting char_class, is_neg:", is_neg)

    # get tuple of lambdas to test against
    lambdas = char_class_expr(kid[1])

    def char_class_helper(x):
        res = False
        for test in lambdas:
            res = res or test(x)
            if not is_neg and res:  # short-circuit if not complementary
                return True
        return is_neg and not res

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
    # print("emitting extended_char", k, v)
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
            raise SyntaxError("invalid special char")
    elif k == "DOLLAR":
        return lambda x: x == '\n'
    elif k == "CARET":
        return lambda x: x == '\x02'  # STX, FIXME
    else:
        raise SyntaxError("invalid extended char")


"""
if __name__ == "__main__":
    # tree = lexer.regex(r"[hcb](a|t)*(hello)*|1")
    regex = input("Enter pattern: ")
    regex = regex if regex != "" else r"\[{,3}\??[hc2-4g-\x707-9]{0,3}(a|t)*(he+llo)*|.\++|(\u1f60B|?????????????????????)*"
    tree = lexer.lex(regex)
    lexer.set_reverse(True)
    tree_rev = lexer.lex(regex)
    pprint(tree)
    pprint(tree_rev)
    fa = parse(tree)
    fa_rev = parse(tree_rev)
    while True:
        test = input("test: ")
        print("MATCHED ??????" if fa.process(test, debug=False) else "NOPE ???")
        print(test)
        print(fa_rev.scan(test[::-1])[::-1])  # each 1 is a start of a match
        print(fa.scan(test))  # each 1 is an end of a match
"""
