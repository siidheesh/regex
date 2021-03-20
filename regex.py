from timeit import default_timer as timer
import lexer
import parser


class Regex:
    """
    A regex class, for encapsulation
    """

    def __init__(self, pattern):
        # forward nfa looks for match end positions
        self.fa = parser.parse(lexer.lex(pattern))
        lexer.set_reverse(True)
        # reverse nfa looks for match start positions
        self.fa_rev = parser.parse(lexer.lex(pattern))

    def scan(self, input, debug=False):
        """
        Scans the input for matches and returns a list of intervals of matching substrings

        Using a reverse NFA was inspired by 
        https://github.com/BurntSushi/regex-automata/blob/e7bda549a0d49d79c631ded6f47846ad69aa8a3e/src/regex.rs#L14-L19
        """
        if input == "" and self.fa.accepts() and self.fa_rev.accepts():
            # match empty input
            return [(0, 0)]

        # match start position(s)
        start = self.fa_rev.scan(input[::-1])[::-1]
        # match end position(s)
        end = self.fa.scan(input)

        if debug:
            # highlight matching substrings, if debug
            ustart = '\u001b[32;1m\033[4m'
            uend = '\u001b[0m\033[0m'

        matches = []

        """if debug:
            print(input)
            print(start)
            print(end)"""
        # this returns all possible matching substrings
        # to get the longest match, take the smallest starting pos and the largest ending pos and check if valid
        for i in range(len(start)):
            # iterate over start positions
            if not start[i]:
                continue
            for j in range(i, len(start)):
                # iterate over end positions
                if not end[j]:
                    continue
                # confirm the match
                # TODO: confirming the match is necessary for matches with
                # consecutive start and end positions, but is it always necessary?
                if not self.fa.process(input, i, j+1):
                    continue
                matches.append((i, j+1))
                if debug:
                    print(input[:i] + ustart +
                          input[i:j+1] + uend + input[j+1:])
        return matches


if __name__ == "__main__":
    pattern = input("Enter pattern: ")
    if pattern == "":
        pattern = r"^\[{3,}\??[hc2-4g-\x707-9]{,3}((a$|t)*)(gg|wp|lol)?(?<=wp|lol)a(?=he{2,3}llo)(he+llo$)*|^(\s*.\++\s*)+$|^(\u1f60B|எழுத்து$)*|((abc|def)*(?<!^def)ghi)|(abc(?=def$)(ghi|def$|lol)*)+|([\+\-]?(?=\d*[.eE])([0-9]?\.[0-9]+|\.[0-9]+)([eE][\+\-]?[0-9]+)?)"
        # fp pattern: (\+|-)?([0-9]+\.?[0-9]*|\.[0-9]+)([eE](\+|-)?[0-9]+)?
        # fp pattern (no integers): [\+\-]?(?=\d*[.eE])([0-9]?\.[0-9]+|\.[0-9]+)([eE][\+\-]?[0-9]+)?
        print("using def. pattern", pattern)
    reg = Regex(pattern)

    while True:
        test = input("test: ")
        start = timer()
        matches = reg.scan(test, debug=True)
        end = timer()
        print(f"{len(matches)} match(es) ✔️" if matches else "NOPE ❌")
        print("took", end-start, "seconds")
