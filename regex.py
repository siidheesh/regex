import lexer
import parser


class Regex:
    """
    A regex class, for encapsulation
    """

    def __init__(self, pattern):
        self.fa = parser.parse(lexer.lex(pattern))
        lexer.set_reverse(True)
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
        start = self.fa_rev.scan(test[::-1])[::-1]
        # match end position(s)
        end = self.fa.scan(test)

        if debug:
            # highlight matching substrings, if debug
            ustart = '\u001b[32;1m\033[4m'
            uend = '\u001b[0m\033[0m'
            count = 1

        matches = []

        """if debug:
            print(input)
            print(start)
            print(end)"""

        for i in range(len(start)):
            # iterate over start positions
            if start[i]:
                for j in range(i, len(start)):
                    # iterate over end positions
                    if end[j]:
                        # confirm the match
                        # TODO: confirming the match is necessary for matches with
                        # consecutive start and end positions, but is it always necessary?
                        if self.fa.process(input[i:j+1]):
                            matches.append((i, j+1))
                            if debug:
                                print(count, '\t', input[:i]+ustart +
                                      input[i:j+1]+uend+input[j+1:])
                                count += 1
        return matches


if __name__ == "__main__":
    pattern = input("Enter pattern: ")
    if pattern == "":
        pattern = r"\[{3,}\??[hc2-4g-\x707-9]{0,3}(a|t)*(he+llo)*|.\++|(\u1f60B|எழுத்து)*"
        print("using def. pattern", pattern)
    reg = Regex(pattern)

    while True:
        test = input("test: ")
        matches = reg.scan(test, debug=True)
        print("MATCHED ✔️" if matches else "NOPE ❌")
