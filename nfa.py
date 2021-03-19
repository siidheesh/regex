
from timeit import default_timer as timer
from pprint import pprint


class NFA:
    """
    A class representing an NFA

    See below for examples of use
    """

    START = "s"  # start state
    END = "e"    # final state

    def __init__(self):
        # the NFA's current state(s)
        self.state = {NFA.START}
        # flags pertinent to the input being processed
        self.flags = {}
        self.transitions = {}
        # transitions that are taken when a predicate is satisfied
        self.predicates = {}
        # list of conditions to be checked before accepting a state
        self.invariants = {}

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

    # add an invariant to be upheld when in a particular state
    def add_invariant(self, state, cond):
        if not callable(input):
            raise ValueError("cond must be function-like")
        if state not in self.invariants:
            self.invariants[state] = {cond}
        else:
            self.invariants[state].add(cond)

    # check if the state upholds the invariants, if any
    def check_invariant(self, state):
        if state not in self.invariants:
            return True
        for cond in self.invariants[state]:
            if not cond(self.flags):
                return False
        return True

    # invoke transition if applicable
    def transition(self, input):
        new_state = set()
        for state in self.state:
            idx = (state, input)
            if idx in self.transitions:
                for to_state in self.transitions[idx]:
                    if self.check_invariant(to_state):
                        new_state.add(to_state)
            if state in self.predicates:
                for pred, to_state in self.predicates[state]:
                    if pred(input) and self.check_invariant(to_state):
                        new_state.add(to_state)

        self.state = self.resolve_et(new_state)

    # non-deterministically follow empty transitions
    def resolve_et(self, state_list=None):
        if state_list is None:
            state_list = self.state

        visited = set()
        queue = list(state_list)
        while queue:
            # keep traversing till we've either seen the state or it doesn't have any empty transitions
            state = queue.pop(0)
            if state in visited or not self.check_invariant(state):
                continue
            visited.add(state)
            idx = (state, None)
            if idx in self.transitions:
                queue.extend(self.transitions[idx])
        return visited

    # returns True if at least one state is accepted
    def accepts(self):
        return NFA.END in self.state

    # Create a shallow clone
    def clone(self):
        res = NFA()
        res.transitions = self.transitions.copy()
        res.predicates = self.predicates.copy()
        return res

    # Embed the rhs NFA into the target NFA, marking rhs' states
    #
    # it's the caller's responsibility to ensure that if multiple NFAs
    # are embedded into the same target, each NFA is marked differently
    def embed_nfa(self, rhs, mark):
        # add transitions
        for idx in rhs.transitions:
            from_state, input = idx
            for to_state in rhs.transitions[idx]:
                self.add_transition(mark(from_state), input, mark(to_state))
        # add predicates
        for from_state in rhs.predicates:
            for predicate, to_state in rhs.predicates[from_state]:
                self.add_transition(
                    mark(from_state), predicate, mark(to_state))
        # add invariants
        for state in rhs.invariants:
            for cond in rhs.invariants[state]:
                self.add_invariant(mark(state), cond)
        return self

    # union op
    def __or__(self, rhs):
        # prefer having RHS be a list of NFAs, as it leads to less transient states added

        union = (self,)
        if type(rhs) not in [list, tuple]:
            union += (rhs,)
        else:
            union += tuple(rhs)  # FIXME: replace with itertools.chain maybe?

        res = NFA()
        union_len = len(union)
        markers = list(map(_gen_mark, range(union_len)))

        for i in range(union_len):
            mark = markers[i]
            # embed union[i] into res
            res.embed_nfa(union[i], mark)
            # connect start and end states
            res.add_transition(NFA.START, None, mark(NFA.START))
            res.add_transition(mark(NFA.END), None, NFA.END)

        return res

    # concatenation op
    def __and__(self, rhs):
        concat = (self,)
        if type(rhs) not in [list, tuple]:
            concat += (rhs,)
        else:
            concat += tuple(rhs)

        res = NFA()
        concat_len = len(concat)
        markers = list(map(_gen_mark, range(concat_len)))

        for i in range(concat_len):
            res.embed_nfa(concat[i], markers[i])
            if i < concat_len - 1:
                # connect adjacent inner start and end states
                res.add_transition(markers[i](NFA.END),
                                   None, markers[i+1](NFA.START))

        # connect start and end states
        res.add_transition(NFA.START, None, markers[0](NFA.START))
        res.add_transition(markers[-1](NFA.END), None, NFA.END)

        return res

    # match op (match >=1 times)
    # the use of predicates requires embedding the NFA in another one, and linking the start/end states within
    def matchify(self):
        clone = self.clone()

        mark = _gen_mark('m')
        clone.embed_nfa(self, mark)

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
        # we could call optify on clone, but it'd add extra states
        clone.add_transition(NFA.START, None, NFA.END)
        return clone

    # Optional op (match 0 or 1 time(s))
    def optify(self):
        fallthrough = NFA()
        fallthrough.add_transition(NFA.START, None, NFA.END)
        return self | fallthrough

    # Run automaton on input[start:end]
    def process(self, input, start, end, debug=False, short_circuit=False):
        # resolve empty transitions first in case of empty input
        input_len = len(input)
        self.flags["pos"] = start
        self.flags["input"] = input
        self.flags["input_len"] = input_len
        # set flags before calling reset as empty transitions may involve invariant checking
        self.reset()
        if debug:
            print("proc: input", input)
        for i in range(start, end):
            self.flags["pos"] = i
            self.transition(input[i])
            if debug:
                print("proc:", input[i], self.accepts(), self.state)
            if not len(self.state):
                # no active branches left
                break
            if short_circuit and self.accepts():
                return True
        return self.accepts()

    def reset(self):
        """
        Reset NFA to initial state
        """
        self.state = self.resolve_et({NFA.START})

    def scan(self, input):
        """
        Runs the NFA on an input and returns a list indicating if the NFA was in an accepting state after each transition
        """
        input_len = len(input)
        self.flags["pos"] = 0
        self.flags["input"] = input
        self.flags["input_len"] = input_len
        self.reset()
        res = []
        for i in range(input_len):
            self.flags["pos"] = i
            if not len(self.state):
                # reset NFA if no longer active
                self.reset()
            self.transition(input[i])
            res.append(self.accepts())
        return res


# returns a lambda that marks states with a suffix
def _gen_mark(suffix):
    return lambda state: str(state)+str(suffix)


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
    print(a.state)
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
