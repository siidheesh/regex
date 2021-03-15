import nfa


def expr(kid):
    if kid is None or type(kid) is not tuple:
        return None
    k, v = kid
    res = None
    if k == "EXTENDED_CHAR":
        res = (extended_char(v),)
    elif k == "CHAR_CLASS":
        res = (char_class(v),)
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

    print("emitting char_class, is_neg:", is_neg)

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
        start = kids[i-1]
        end = kids[i+1]
        items = items[:i] + (extended_char_range(start, end),) + items[i:]

    return items


def extended_char_range(start, end):
    pass


def extended_char(kid):
    if kid is None or type(kid) is not tuple:
        return None
    k, v = kid
    print("emitting extended_char", k, v)
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
