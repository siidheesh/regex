# Regex

A crap NFA-based regex engine written for fun (beta)

To test:

```shell
python regex.py
```

~~Currently only parses a subset of the POSIX regex spec~~

Supports most of the POSIX BRE spec!

What it doesn't support (yet):

- ~~^ (matching the starting position) \*~~
- ~~$ (matching the ending position) \*~~
- Lookaheads
- Lookbehinds\*\*
- Capture groups
- Backreferences\*\*

~~<sub>\* as the engine currently finds all matching substrings, an interim fix would be to filter them accordingly<sub>~~

<sub>\*\* might not be possible with a FA-based engine<sub>

It's now able to scan text and find substrings :D
