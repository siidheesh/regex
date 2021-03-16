
from timeit import default_timer as timer
from pprint import pprint


class NFA:
    """
    A class representing an NFA

    See below for examples of use
    """

    START = "start"     # start state
    END = "end"         # final state

    def __init__(self):
        self.state = {NFA.START}
        self.accept = {NFA.END}
        self.transitions = {}
        self.predicates = {}

    # Add a transition from state fr to state to, on input
    # Input can be callable
    def add_transition(self, fr, input, to):
        if callable(input):
            # input is function-like
            if fr not in self.predicates:
                self.predicates[fr] = {(input, to)}
            else:
                self.predicates[fr].add((input, to))
        else:
            idx = (fr, input)
            # NFAs allow for multiple transition targets
            if idx not in self.transitions:
                self.transitions[idx] = {to}
            else:
                self.transitions[idx].add(to)

    # invoke transition if applicable
    def transition(self, input):
        self.resolve_et()

        new_state = set()
        for state in self.state:
            idx = (state, input)
            if idx in self.transitions:
                for to_state in self.transitions[idx]:
                    new_state.add(to_state)
            if state in self.predicates:
                for pred, to_state in self.predicates[state]:
                    if pred(input):
                        new_state.add(to_state)
        self.state = new_state

        self.resolve_et()

    # non-deterministically follow empty transitions
    def resolve_et(self):
        visited = set()
        queue = list(self.state)
        while queue:
            # keep traversing till we've either seen the state or it doesn't have any empty transitions
            state = queue.pop(0)
            if state in visited:
                continue
            visited.add(state)
            idx = (state, None)
            if idx in self.transitions:
                queue.extend(self.transitions[idx])
        self.state = visited

    # returns True if at least one state is accepted
    def accepts(self):
        return len(self.state & self.accept) > 0

    # Create a shallow clone
    def clone(self):
        res = NFA()
        res.transitions = self.transitions.copy()
        res.predicates = self.predicates.copy()
        return res

    # union op
    def __or__(self, rhs):
        res = NFA()

        def mark_lhs(state):
            return str(state)+'l'

        def mark_rhs(state):
            return str(state)+'r'

        # iterate over lhs and rhs
        for hs, mark in ((self, mark_lhs), (rhs, mark_rhs)):
            # add transitions
            for idx in hs.transitions:
                from_state, input = idx
                for to_state in hs.transitions[idx]:
                    res.add_transition(mark(from_state), input, mark(to_state))
            # add predicates
            for from_state in hs.predicates:
                for pred, to_state in hs.predicates[from_state]:
                    res.add_transition(mark(from_state), pred, mark(to_state))
            # connect start and end states
            res.add_transition(NFA.START, None, mark(NFA.START))
            res.add_transition(mark(NFA.END), None, NFA.END)
        return res

    # concatenation op
    def __and__(self, rhs):
        res = NFA()

        def mark_lhs(state):
            return str(state)+'a'

        def mark_rhs(state):
            return str(state)+'b'

        for hs, mark in ((self, mark_lhs), (rhs, mark_rhs)):
            # add transitions
            for idx in hs.transitions:
                from_state, input = idx
                if from_state is not NFA.START or hs is rhs:
                    from_state = mark(from_state)
                for to_state in hs.transitions[idx]:
                    if to_state is not NFA.END or hs is self:
                        to_state = mark(to_state)
                    res.add_transition(from_state, input, to_state)
            # add predicates
            for from_state in hs.predicates:
                for predicate, to_state in hs.predicates[from_state]:
                    if from_state is not NFA.START or hs is rhs:
                        from_state = mark(from_state)
                    if to_state is not NFA.END or hs is self:
                        to_state = mark(to_state)
                    res.add_transition(from_state, predicate, to_state)

        res.add_transition(mark_lhs(NFA.END), None, mark_rhs(NFA.START))

        return res

    # FIXME: remove this?
    def __invert__(self):
        res = NFA()
        for idx in self.transitions:
            for to_state in self.transitions[idx]:
                if to_state is not NFA.END:
                    # only accept states that weren't originally accepted
                    res.add_transition(*idx, to_state)
                    res.add_transition(*idx, NFA.END)
        return res

    # match op (match >=1 times)
    # the use of predicates requires embedding the NFA in another one, and linking the start/end states within
    def matchify(self):
        clone = self.clone()

        def mark(state):
            return str(state)+'m'

        # add transitions
        for idx in self.transitions:
            from_state, input = idx
            for to_state in self.transitions[idx]:
                clone.add_transition(mark(from_state), input, mark(to_state))

        # add predicates
        for from_state in self.predicates:
            for predicate, to_state in self.predicates[from_state]:
                clone.add_transition(
                    mark(from_state), predicate, mark(to_state))

        # connect start and end states
        clone.add_transition(NFA.START, None, mark(NFA.START))
        clone.add_transition(mark(NFA.END), None, NFA.END)

        # connect inner end state to inner start state
        clone.add_transition(mark(NFA.END), None, mark(NFA.START))

        return clone

    # Kleene op (match >=0 times)
    def kleenefy(self):
        clone = self.matchify()
        # accept the starting state
        clone.add_transition(NFA.START, None, NFA.END)
        return clone

    # Optional op (match 0 or 1 time(s))
    def optify(self):
        fallthrough = NFA()
        fallthrough.add_transition(NFA.START, None, NFA.END)
        return self | fallthrough

    # Run automaton on an input string
    def process(self, input, debug=False):
        self.state = {NFA.START}
        if debug:
            print("proc: input", input)
        for char in input:
            self.transition(char)
            if debug:
                print("proc:", char, self.accepts(), self.state)
            if not len(self.state):
                # no active branches left
                break
        return self.accepts()


if __name__ == "__main__":
    a = NFA()
    a.add_transition(NFA.START, 'b', NFA.END)
    a.add_transition(NFA.START, 'h', 3)
    a.add_transition(NFA.START, 'c', NFA.END)
    a.add_transition(3, 'i', NFA.END)
    a.add_transition(NFA.START, lambda x: x.isspace(), 10)

    b = NFA()
    b.add_transition(NFA.START, lambda x: x == 'b', 2)
    b.add_transition(2, lambda x: x == 'l', 3)
    b.add_transition(3, lambda x: x == 'u', 4)
    b.add_transition(4, lambda x: x == 'e', NFA.END)

    c = NFA()
    c.add_transition(NFA.START, 'b', 2)
    c.add_transition(2, 'l', 3)
    c.add_transition(3, 'u', 4)
    c.add_transition(4, 'd', NFA.END)

    d = NFA()
    d.add_transition(NFA.START, 'c', 2)
    d.add_transition(2, 'l', 3)
    d.add_transition(3, 'u', 4)
    d.add_transition(4, 'e', NFA.END)

    e = NFA()
    e.add_transition(NFA.START, ' ', NFA.END)

    # a => (a|b|c)d*(ed)*
    a = (a | b | c) & d.kleenefy() & (e & d).kleenefy()

    pprint(a.transitions)
    print(a.state, a.accept)
    a.transition('b')
    print(a.state, a.accepts())
    a.transition('l')
    print(a.state, a.accepts())
    a.transition('u')
    print(a.state, a.accepts())
    a.transition('f')
    print('e', a.state, a.accepts())

    a.transition('c')
    print(a.state, a.accepts())
    a.transition('l')
    print(a.state, a.accepts())
    a.transition('u')
    print(a.state, a.accepts())
    a.transition('e')
    print('e', a.state, a.accepts())

    a.transition(' ')
    print(' ', a.state, a.accepts())

    a.transition('c')
    print('c', a.state, a.accepts())
    a.transition('l')
    print(a.state, a.accepts())
    a.transition('u')
    print(a.state, a.accepts())
    a.transition('e')
    print(a.state, a.accepts())

    a.transition(' ')
    print(a.state, a.accepts())

    a.transition('c')
    print('c', a.state, a.accepts())
    a.transition('l')
    print(a.state, a.accepts())
    a.transition('u')
    print(a.state, a.accepts())
    a.transition('e')
    print(a.state, a.accepts())

    start = timer()
    res = a.process("b clue clue")
    end = timer()
    print("accepted: ", res, "time:", end-start)
