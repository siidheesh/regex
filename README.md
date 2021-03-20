# Regex

A crap NFA-based text-directed regex engine written for fun (beta)

To test:

```shell
python regex.py
```

~~Currently only parses a subset of the POSIX regex spec~~

Supports most of the POSIX BRE spec, including variable=width lookarounds †

What it doesn't support (yet):

- ~~^ (matching the starting position)~~
- ~~$ (matching the ending position)~~
- ~~Lookaheads~~ †
- ~~Lookbehinds~~ †
- Capture groups
- Backreferences\*

<sub>\* might not be possible with a FA-based engine<sub>

<sub>† negative lookarounds are greedy, i.e they'll reject if the expression is found _anywhere_ ahead of (resp. behind) the current pos<sub>
