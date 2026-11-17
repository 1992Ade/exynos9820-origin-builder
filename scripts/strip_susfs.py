#!/usr/bin/env python3
"""Remove an in-tree SuSFS integration from a kernel tree (mini "unifdef").

Every SuSFS hook in the kernel is wrapped in #if/#ifdef on CONFIG_KSU_SUSFS*. This treats those
symbols as undefined and resolves the conditionals that only depend on them, leaving every other
conditional untouched (tri-state evaluation: False / True / unknown). Used to get a SuSFS-free
tree on which a newer SuSFS patch (e.g. JackA1ltman's 4.14 v2.4.0 port) can be applied.

Usage: strip_susfs.py <kernel-root> <file> [<file> ...]   (paths relative to the root)
Prints the files changed and any leftover 'susfs' reference (to be handled by hand).
"""
import re
import sys
from pathlib import Path

SUSFS = re.compile(r"^CONFIG_KSU_SUSFS\w*$")
UNKNOWN = None


def ev(expr):
    """Evaluate a preprocessor expression with SuSFS symbols = 0, others unknown."""
    toks = re.findall(r"defined\s*\(\s*\w+\s*\)|defined\s+\w+|&&|\|\||!|\(|\)|\w+|\S", expr)
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else None

    def take():
        nonlocal pos
        pos += 1
        return toks[pos - 1]

    def atom():
        t = take()
        if t == "!":
            v = atom()
            return UNKNOWN if v is UNKNOWN else (not v)
        if t == "(":
            v = orx()
            if peek() == ")":
                take()
            return v
        m = re.match(r"defined\s*\(?\s*(\w+)", t)
        name = m.group(1) if m else t
        if SUSFS.match(name):
            return False
        if name == "0":
            return False
        if name == "1":
            return True
        return UNKNOWN

    def andx():
        v = atom()
        while peek() == "&&":
            take()
            w = atom()
            v = False if (v is False or w is False) else (True if (v and w) else UNKNOWN)
        return v

    def orx():
        v = andx()
        while peek() == "||":
            take()
            w = andx()
            v = True if (v is True or w is True) else (False if (v is False and w is False) else UNKNOWN)
        return v

    try:
        return orx()
    except IndexError:
        return UNKNOWN


DIRECTIVE = re.compile(r"^\s*#\s*(ifdef|ifndef|if|elif|else|endif)\b(.*)$")


def strip(text):
    lines = text.split("\n")
    out = []
    # stack entries: dict(mode, taken) ; mode: 'keep' (unknown, keep directives),
    # 'resolved' (known; emit nothing for directives)
    stack = []

    def emitting():
        return all(s["emit"] for s in stack)

    i = 0
    while i < len(lines):
        line = lines[i]
        # join continued directive lines
        full = line
        j = i
        while full.endswith("\\") and DIRECTIVE.match(line) and j + 1 < len(lines):
            j += 1
            full = full[:-1] + " " + lines[j]
        m = DIRECTIVE.match(full)
        raw = lines[i:j + 1]
        i = j + 1
        if not m:
            if emitting():
                out.append(line)
            continue
        kw, rest = m.group(1), re.sub(r"/\*.*?\*/|//.*$", "", m.group(2)).strip()
        if kw in ("ifdef", "ifndef", "if"):
            if kw == "ifdef":
                v = False if SUSFS.match(rest) else UNKNOWN
            elif kw == "ifndef":
                v = True if SUSFS.match(rest) else UNKNOWN
            else:
                v = ev(rest)
            parent = emitting()
            if v is UNKNOWN:
                stack.append({"known": False, "emit": True, "done": False})
                if parent:
                    out.extend(raw)
            else:
                stack.append({"known": True, "emit": bool(v), "done": bool(v)})
        elif kw == "elif":
            s = stack[-1]
            v = ev(rest)
            if s["known"]:
                if s["done"]:
                    s["emit"] = False
                elif v is UNKNOWN:
                    # previous branches were all false: turn this elif into an #if
                    s.update(known=False, emit=True)
                    stack.pop()
                    parent = emitting()
                    stack.append(s)
                    if parent:
                        out.append(re.sub(r"#\s*elif", "#if", raw[0], count=1))
                        out.extend(raw[1:])
                else:
                    s["emit"] = bool(v)
                    s["done"] = bool(v)
            else:
                # unknown chain: a false elif branch is dropped, a true one becomes #else
                if v is False:
                    s["skip_branch"] = True
                    s["emit"] = False
                else:
                    s["emit"] = True
                    s.pop("skip_branch", None)
                    stack.pop()
                    parent = emitting()
                    stack.append(s)
                    if parent:
                        if v is True:
                            out.append("#else")
                            s["closed"] = True
                        else:
                            out.extend(raw)
        elif kw == "else":
            s = stack[-1]
            if s["known"]:
                s["emit"] = not s["done"]
                s["done"] = True
            else:
                s["emit"] = not s.get("closed", False)
                stack.pop()
                parent = emitting()
                stack.append(s)
                if parent and not s.get("closed"):
                    out.extend(raw)
        elif kw == "endif":
            s = stack.pop()
            if not s["known"] and emitting():
                out.extend(raw)
    return "\n".join(out)


def main():
    root = Path(sys.argv[1])
    for rel in sys.argv[2:]:
        p = root / rel
        if not p.exists():
            continue
        old = p.read_text(errors="surrogateescape")
        new = strip(old)
        if new != old:
            p.write_text(new, errors="surrogateescape")
            print(f"stripped: {rel}")
        for n, l in enumerate(new.split("\n"), 1):
            if "susfs" in l.lower():
                print(f"  leftover {rel}:{n}: {l.strip()[:110]}")


if __name__ == "__main__":
    main()
