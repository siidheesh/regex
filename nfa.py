
from pprint import pprint


class NFA:
    # _START = "_start"   # the internal start node
    START = "start"     # start node for the user
    END = "end"         # default final state

    def __init__(self):
        self.state = {NFA.START}
        self.accept = {NFA.END}
        self.transitions = {}
        self.predicates = {}
        # self.add_transition(NFA._START, None, NFA.START)

    # add to set of accepted states
    # def add_accept(self, state):
    #    self.accept.add(state)

    # Add a transition from state fr to state to, on input
    # Input can be callable
    def add_transition(self, fr, input, to):
        if callable(input):
            # input is function-like
            if fr not in self.predicates:
                self.predicates[fr] = ((input, to),)
            else:
                self.predicates[fr] += ((input, to),)
        else:
            idx = (fr, input)
            # NFAs allow for multiple transition targets
            if idx not in self.transitions:
                self.transitions[idx] = (to,)
            else:
                self.transitions[idx] += (to,)

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

    # union op
    def __add__1(self, other):
        if self is other:
            return self

        # add an 'r' to the RHS nfa's states
        def append_r(state):
            return str(state)+'r'

        # self.state += tuple(map(append_r, other.state))
        # for other_start_state in map(append_r, other.state):
        #    self.add_transition(NFA.START, None, other_start_state)

        for start_transition in other.transitions[(NFA.START, None)]:
            self.add_transition(NFA.START, None, append_r(start_transition))

        # add RHS' accepted states to LHS
        self.accept.update(map(append_r, other.accept))

        # add RHS' transitions to LHS
        for idx in other.transitions:
            from_state, input = idx
            if from_state is NFA.START:
                continue
            new_idx = (append_r(from_state), input)
            self.transitions[new_idx] = set(
                map(append_r, other.transitions[idx]))

        for state in other.predicates:
            self.predicates[append_r(state)] = tuple(
                map(lambda pair: (pair[0], append_r(pair[1])), other.predicates[state]))

        # clear RHS
        other.transitions = None
        other.predicates = None

        return self

    def __add__(self, rhs):
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
                # leave START and END unchanged
                if from_state is not NFA.START:
                    from_state = mark(from_state)
                for to_state in hs.transitions[idx]:
                    if to_state is not NFA.END:
                        to_state = mark(to_state)
                    res.add_transition(from_state, input, to_state)
            # add predicates
            for from_state in hs.predicates:
                for predicate, to_state in hs.predicates[from_state]:
                    if from_state is not NFA.START:
                        from_state = mark(from_state)
                    if to_state is not NFA.END:
                        to_state = mark(to_state)
                    res.add_transition(from_state, predicate, to_state)

        return res

    # concatenation op
    def __mul__1(self, other):
        if self is other:
            return self

        # add a 'c' to the RHS nfa's states
        def append_c(state):
            return str(state)+'c'

        # add RHS' transitions to LHS
        for idx in other.transitions:
            from_state, input = idx
            new_idx = (append_c(from_state), input)
            self.transitions[new_idx] = set(
                map(append_c, other.transitions[idx]))

        for state in other.predicates:
            self.predicates[append_c(state)] = tuple(
                map(lambda pred, to: (pred, append_c(to)), other.predicates[state]))

        # add empty transitions from each of LHS' accept states to RHS' start states
        for final_state in self.accept:
            for start_state in map(append_c, other.state):
                self.add_transition(final_state, None, start_state)

        # set LHS' accept states to be RHS' accept states
        self.accept = set(map(append_c, other.accept))

        # clear RHS
        other.transitions = None
        other.predicates = None

        return self

    def __mul__(self, rhs):
        res = NFA()

        def mark_lhs(state):
            return str(state)+'a'

        def mark_rhs(state):
            return str(state)+'b'

        # clone self
        # lhs = self + NFA()

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

    # match op
    def matchify(self):
        # for final_state in self.accept:
        # add an empty transition between each state and the start state
        #self.add_transition(final_state, None, NFA.START)
        for idx in self.transitions:
            if NFA.END in self.transitions[idx]:
                # link every state, that transits to END, to START
                self.add_transition(*idx, NFA.START)
        return self

    # Kleene op
    def kleenefy(self):
        self.matchify()
        # accept the starting state
        # self.accept.add(NFA.START)
        self.add_transition(NFA.START, None, NFA.END)
        return self


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
    '''
    b.add_transition(NFA.START, lambda x: x == 'b', 1)
    b.add_transition(1, lambda x: x == 'l', 2)
    b.add_transition(2, lambda x: x == 'u', 3)
    b.add_transition(3, lambda x: x == 'e', NFA.END)
    '''
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

    # a.add_transition(1, 'a', 3)
    # a.add_transition(3, None, 1)
    # a.add_transition(4, 'b', 2)

    '''
  print(a.transitions)
  print(a.state, a.accepts())
  a.empty_transitions()
  print(a.state, a.accepts())
  a.transition('c')
  print(a.state, a.accepts())
  # a.transition('i')
  print(a.state, a.accepts())

  print("-----")

  print(b.transitions)
  print(b.state, b.accepts())
  b.empty_transitions()
  print(b.state, b.accepts())
  b.transition('b')
  print(b.state, b.accepts())
  b.transition('l')
  print(b.state, b.accepts())
  b.transition('u')
  print(b.state, b.accepts())
  b.transition('e')
  print(b.state, b.accepts())
  '''

    #b += c
    #a += b
    #a *= d.kleenefy()
    #a *= e
    a = (b + c) * d.kleenefy() * e

    pprint(a.transitions)
    print(a.state, a.accept)
    a.transition('b')
    print(a.state, a.accepts())
    a.transition('l')
    print(a.state, a.accepts())
    a.transition('u')
    print(a.state, a.accepts())
    a.transition('e')
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
