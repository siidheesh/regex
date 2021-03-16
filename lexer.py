
from pprint import pprint
# r"([^ab-c.\u0ACD1H3\d\n]\uACD1.){1}*+?*abcd"
test = r"[hc\xFFv]?at|1[^ab-c.\u0ACD1H3\d\n]\uACD1."
i = -1


def peek():
    return test[i+1] if i+1 < len(test) else None


def m(a):
    global i, test
    i += 1
    if test[i] != a:
        raise SyntaxError(
            f'expected {a}, found {test[i]} at pos {i} of {test}')


def regex(string):
    global test, i
    test = string
    i = -1
    return union_expr()


def union_expr():
    res = ()
    while True:
        r = concat_expr()
        if not r:
            break
        res += (r,)
        if peek() != '|':
            break
        m('|')

    if res != ():
        return ("UNION_EXPR", res)
    return None


def concat_expr():
    res = ()
    while True:
        r = quantified_expr()
        if r:
            res += (r,)
        else:
            break
    if res != ():
        return ("CONCAT_EXPR", res)
    return None


def quantified_expr():
    res = expr()
    tag = None
    if peek() == '*':
        m('*')
        if peek() == '?':
            m('?')
            tag = "LAZY_KLEENE"
        else:
            tag = "KLEENE"
    elif peek() == '+':
        m('+')
        if peek() == '?':
            m('?')
            tag = "LAZY_MATCH"
        else:
            tag = "MATCH"
    elif peek() == '?':
        m('?')
        if peek() == '?':
            m('?')
            tag = "LAZY_OPT"
        else:
            tag = "OPT"
    elif peek() == '{':
        m('{')
        r = range_expr()
        m('}')
        if r:
            return (r, res)
        raise SyntaxError("invalid range expr")

    if tag:
        return (tag, res)
    return res


def range_expr():
    n1 = num()
    if not n1:
        return None
    if peek() == ',':
        m(',')
        n2 = num()
        if n2:
            return ("RANGE-N,N", n1, n2)
        else:
            return ("RANGE-N,", n1)
    return ("RANGE-N", n1)


def num():
    res = None
    while True:
        unk = peek()
        if unk.isdigit():
            m(unk)
            res = int(unk) if res is None else res*10 + int(unk)
        else:
            return res


def expr():
    res = None
    if peek() == '(':
        m('(')
        res = union_expr()
        m(')')
    else:
        res = enclosed_expr()

    if res:
        return ("EXPR", res)
    return None


'''
ENCLOSED_EXPR -> EXTENDED_CHAR || CHAR_CLASS || ε


ENCLOSED_EXPR -> EXTENDED_CHAR ENCLOSED_EXPR' || CHAR_CLASS ENCLOSED_EXPR' 
ENCLOSED_EXPR' -> ENCLOSED_EXPR ENCLOSED_EXPR' || ε
'''

'''
def enclosed_expr11():
    if not peek():
        return ("ENCLOSED_EXPR", None)
    res = char_class()
    if res:
        return ("ENCLOSED_EXPR", res)
    res = extended_char()
    if res:
        return ("ENCLOSED_EXPR", res)
    raise SyntaxError()
'''


def enclosed_expr():
    '''res = ()
    while True:
        r = extended_char()
        if r:
            res += (r,)
            break  # continue
        r = char_class()
        if r:
            res += (r,)
            break  # continue
        else:
            break

    if res != ():
        return res
    return None'''
    res = extended_char()
    if res:
        return res
    res = char_class()
    if res:
        return res
    return None


def extended_char():
    if peek() == '\\':
        m('\\')
        if peek() in "dDwWsStrnvf0":
            spc_char = peek()
            m(spc_char)
            return ("EXTENDED_CHAR", ("SPECIAL_CHAR", spc_char))
        elif peek() == 'x':
            res = ascii_char()
            if res:
                return ("EXTENDED_CHAR", res)
        elif peek() == 'u':
            res = unicode_char()
            if res:
                return ("EXTENDED_CHAR", res)
        else:
            raise SyntaxError("unrecognised escaped char "+peek())
    else:
        res = char()
        if not res:
            # raise SyntaxError()
            return None
        return ("EXTENDED_CHAR", res)


def char():
    unk_char = peek()
    if not unk_char:
        return None
    if unk_char.isalnum():
        m(unk_char)
        return ("CHAR", unk_char)
    elif unk_char == '.':
        m('.')
        return ("WILDCARD", None)
    # raise SyntaxError("unrecognised char "+unk_char)
    return None


def ascii_char():
    m('x')
    hex_string = ""
    for _ in range(2):
        hex_char = peek()
        if hex_char in "0123456789ABCDEF":
            m(hex_char)
            hex_string += hex_char
        else:
            # return None
            raise SyntaxError("invalid ascii codepoint")
    return ("ASCII_CP", hex_string)


def unicode_char():
    m('u')
    hex_string = ""
    for _ in range(4):
        hex_char = peek()
        if hex_char in "0123456789ABCDEF":
            m(hex_char)
            hex_string += hex_char
        else:
            raise SyntaxError("invalid unicode codepoint")
            # return None
    # optional 5th hex digit
    hex_char = peek()
    if hex_char in "0123456789ABCDEF":
        m(hex_char)
        hex_string += hex_char
    return ("UNICODE_CP", hex_string)


def char_class():
    if peek() == '[':
        m('[')
        res = char_class_inner()
        m(']')
        return ("CHAR_CLASS", res)
    return None


def char_class_inner():
    tag = None
    if peek() == '^':
        m('^')
        tag = "CHAR_CLASS_INNER_NEG"
    else:
        tag = "CHAR_CLASS_INNER"
    res = char_class_expr()
    if res:
        return (tag, res)
    raise SyntaxError()


'''
left-recursive production
CHAR_CLASS_EXPR -> CHAR_CLASS_EXPR EXTENDED_CHAR || CHAR_CLASS_EXPR CHAR_CLASS_RANGE || EXTENDED_CHAR || CHAR_CLASS_RANGE

CHAR_CLASS_EXPR -> EXTENDED_CHAR CHAR_CLASS_EXPR' || CHAR_CLASS_RANGE CHAR_CLASS_EXPR'
CHAR_CLASS_EXPR' -> CHAR_CLASS_EXPR CHAR_CLASS_EXPR' || ε
'''


def char_class_expr():
    res = ()
    while peek() is not None and peek() != ']':
        if peek() == '-':
            m('-')
            res += (("RANGE", None),)
        else:
            r = extended_char()
            if r:
                res += (r,)
            else:
                break
    if res is not None:
        return res
    return None
    # return ("CHAR_CLASS_EXPR", res)


if __name__ == "__main__":
    pprint(regex(r"[hc\xFFv1]?(a|t)|136[^ab-c.\u111111]"))
    # pprint(regex(r"[hc]?(a|t)"))
