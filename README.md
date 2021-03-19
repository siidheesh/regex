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
- ~~Lookaheads~~ <sup>beta<sup>
- ~~Lookbehinds~~ <sup>beta\*\*\*<sup>
- Capture groups
- Backreferences\*\*

~~<sub>\* as the engine currently finds all matching substrings, an interim fix would be to filter them accordingly<sub>~~

<sub>\*\* might not be possible with a FA-based engine<sub>

<sub>\*\*\* -ve lookaheads and -ve lookbehinds don't currently work properly<sub>
