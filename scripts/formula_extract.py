#!/usr/bin/env python3
"""Extract formulas from MathML / publisher XML into structure-preserving LaTeX.

Usage:
    python formula_extract.py --input <xml-or-dir> [--output formulas.jsonl]
    python formula_extract.py --pdf <file.pdf> [--output pdf_text.txt]

Design notes
- Uses only the standard library (xml.etree) so it runs in a bare container.
- Preserves element ids so every formula can be traced back to its source node.
- Falls back to regex extraction when the document is not well-formed XML.
"""
import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

MATHML = "{http://www.w3.org/1998/Math/MathML}"

GREEK = {
    "alpha": r"\alpha", "beta": r"\beta", "gamma": r"\gamma", "delta": r"\delta",
    "epsilon": r"\epsilon", "varepsilon": r"\varepsilon", "zeta": r"\zeta",
    "eta": r"\eta", "theta": r"\theta", "vartheta": r"\vartheta", "iota": r"\iota",
    "kappa": r"\kappa", "lambda": r"\lambda", "mu": r"\mu", "nu": r"\nu", "xi": r"\xi",
    "pi": r"\pi", "rho": r"\rho", "sigma": r"\sigma", "tau": r"\tau",
    "upsilon": r"\upsilon", "phi": r"\phi", "varphi": r"\varphi", "chi": r"\chi",
    "psi": r"\psi", "omega": r"\omega", "Gamma": r"\Gamma", "Delta": r"\Delta",
    "Theta": r"\Theta", "Lambda": r"\Lambda", "Xi": r"\Xi", "Pi": r"\Pi",
    "Sigma": r"\Sigma", "Upsilon": r"\Upsilon", "Phi": r"\Phi", "Psi": r"\Psi",
    "Omega": r"\Omega",
}

OPS = {
    "\u00d7": r"\times", "\u22c5": r"\cdot", "\u00b7": r"\cdot", "\u2212": "-",    "\u2264": r"\le", "\u2265": r"\ge", "\u2260": r"\neq", "\u2248": r"\approx",
    "\u221d": r"\propto", "\u2202": r"\partial", "\u2207": r"\nabla",
    "\u2211": r"\sum", "\u220f": r"\prod", "\u222b": r"\int", "\u221e": r"\infty",
    "\u2208": r"\in", "\u2192": r"\to", "\u00b1": r"\pm", "\u2213": r"\mp",
    "\u27e8": r"\langle", "\u27e9": r"\rangle", "\u2026": r"\ldots",
    "\u2032": "'", "\u2033": "''", "\u2300": r"\varnothing", "\u00b0": r"^{\circ}",
    "\u2103": r"^{\circ}\mathrm{C}", "\u2030": r"\text{\textperthousand}",
    "\u2245": r"\simeq", "\u2243": r"\simeq", "\u2261": r"\equiv", "\u2217": "*",
    "\u22a5": r"\perp", "\u2225": r"\parallel", "\u2297": r"\otimes", "\u2295": r"\oplus",
    "\u2282": r"\subset", "\u2286": r"\subseteq", "\u222a": r"\cup", "\u2229": r"\cap",
    "\u2200": r"\forall", "\u2203": r"\exists", "\u2205": r"\varnothing",
    "\u03b1": r"\alpha", "\u03b2": r"\beta", "\u03b3": r"\gamma", "\u03b4": r"\delta",
    "\u03b5": r"\epsilon", "\u03b8": r"\theta", "\u03bb": r"\lambda", "\u03bc": r"\mu",
    "\u03c0": r"\pi", "\u03c1": r"\rho", "\u03c3": r"\sigma", "\u03c4": r"\tau",
    "\u03c6": r"\phi", "\u03c9": r"\omega", "\u0394": r"\Delta", "\u03a9": r"\Omega",
    "\u03a3": r"\Sigma", "\u0398": r"\Theta", "\u03bd": r"\nu", "\u03b7": r"\eta",
    "\u03ba": r"\kappa", "\u03be": r"\xi", "\u03c8": r"\psi", "\u03c7": r"\chi",
    "\u03c5": r"\upsilon", "\u03b9": r"\iota", "\u03b6": r"\zeta", "\u039b": r"\Lambda",
    "\u03a6": r"\Phi", "\u03a8": r"\Psi", "\u03a0": r"\Pi",
}


INVISIBLE = {
    "\u2061": "",      # function application: sin(x), not sin*(x)
    "\u2062": "",      # invisible times: implicit product
    "\u2063": "",      # invisible separator
    "\u200b": "",      # zero width space
    "\u00a0": " ",     # non-breaking space
    "\u2009": r"\,",   # thin space
    "\u200a": r"\,",   # hair space
    "\u2044": "/",     # fraction slash
    "\u2212": "-",     # minus sign
    "\u2013": "-",
}


def clean_text(s):
    for k, v in INVISIBLE.items():
        s = s.replace(k, v)
    return s


def _tag(el):
    return el.tag.replace(MATHML, "") if isinstance(el.tag, str) else ""


def _attr_id(el):
    for key in ("id", "xml:id", "{http://www.w3.org/XML/1998/namespace}id"):
        if key in el.attrib:
            return el.attrib[key]
    return None


def _txt(el):
    return (el.text or "") + "".join(
        (c.tail or "") for c in el)


def clean_texmath(raw):
    """JATS <tex-math> often wraps a full LaTeX document from the typesetter."""
    s = re.sub(r"<\?.*?\?>", " ", raw, flags=re.S)
    s = s.replace("<![CDATA[", " ").replace("]]>", " ")
    if "\\begin{document}" in s:
        s = s.split("\\begin{document}", 1)[1]
    if "\\end{document}" in s:
        s = s.split("\\end{document}", 1)[0]
    s = re.sub(r"\s+", " ", s).strip()
    for a, b in (("$$", "$$"), ("$", "$"), ("\\[", "\\]"), ("\\(", "\\)")):
        if len(s) > len(a) + len(b) and s.startswith(a) and s.endswith(b):
            s = s[len(a):-len(b)].strip()
    if not s or "\\documentclass" in s or "\\usepackage" in s:
        return None
    return s


def find_texmath(el, parents, depth=3):
    """The publisher's LaTeX may sit next to the MathML inside <alternatives>.

    Only direct siblings are inspected: walking a whole ancestor subtree would
    hand one formula the LaTeX of its neighbour further down the page.
    """
    cur = el
    for _ in range(depth):
        cur = parents.get(cur)
        if cur is None:
            break
        for node in list(cur):
            if _tag(node) == "tex-math":
                text = clean_texmath("".join(node.itertext()))
                if text:
                    return text
    return None


def source_tex(el, parents=None):
    """Return (latex, method) for the publisher's own LaTeX, if any."""
    for node in el.iter():
        if _tag(node) in ("annotation", "annotation-xml"):
            enc = (node.attrib.get("encoding") or "").lower()
            if "tex" in enc:
                text = "".join(node.itertext()).strip()
                if text:
                    return text, "source_annotation"
    if parents:
        tex = find_texmath(el, parents)
        if tex:
            return tex, "source_texmath"
    alt = el.attrib.get("alttext")
    if alt and "\\" in alt:
        return alt.strip(), "source_alttext"
    return None, None


def find_label(el, parents, depth=4):
    """JATS keeps the equation number in <label> next to the formula."""
    cur = el
    for _ in range(depth):
        cur = parents.get(cur)
        if cur is None:
            break
        for child in cur:
            if _tag(child) == "label":
                text = "".join(child.itertext()).strip()
                if text:
                    return text
    return None


def convert(el):
    """Convert one MathML node to LaTeX (recursively)."""
    t = _tag(el)
    kids = list(el)

    if t in ("math", "mrow", "mstyle", "semantics", "mtd", "mpadded"):
        parts = []
        if el.text and el.text.strip():
            parts.append(_escape_text(el.text))
        for c in kids:
            if _tag(c) == "annotation" or _tag(c) == "annotation-xml":
                continue
            parts.append(convert(c))
            if c.tail and c.tail.strip():
                parts.append(_escape_text(c.tail))
        return "".join(parts)

    if t == "mi":
        name = clean_text((el.text or "").strip())
        if not name:
            return ""
        if name in OPS:            # a Greek character kept as a literal
            return OPS[name]
        if len(name) > 1 and name in GREEK:
            return GREEK[name]
        if len(name) > 1:
            return r"\mathrm{%s}" % name
        return name

    if t == "mn":
        return clean_text((el.text or "").strip())

    if t == "mo":
        raw_orig = (el.text or "").strip()
        if raw_orig in INVISIBLE and INVISIBLE[raw_orig] == "":
            return ""              # U+2061/U+2062 and friends must not reach LaTeX
        raw = clean_text(raw_orig)
        if not raw:
            return ""
        return OPS.get(raw, raw)

    if t == "mtext":
        return r"\text{%s}" % clean_text((el.text or "").strip())

    if t == "mfrac":
        num = convert(kids[0]) if len(kids) > 0 else ""
        den = convert(kids[1]) if len(kids) > 1 else ""
        return r"\frac{%s}{%s}" % (num, den)

    if t == "msup":
        base = convert(kids[0]) if kids else ""
        sup = convert(kids[1]) if len(kids) > 1 else ""
        return "{%s}^{%s}" % (base, sup)

    if t == "msub":
        base = convert(kids[0]) if kids else ""
        sub = convert(kids[1]) if len(kids) > 1 else ""
        return "{%s}_{%s}" % (base, sub)

    if t == "msubsup":
        base = convert(kids[0]) if kids else ""
        sub = convert(kids[1]) if len(kids) > 1 else ""
        sup = convert(kids[2]) if len(kids) > 2 else ""
        return "{%s}_{%s}^{%s}" % (base, sub, sup)

    if t == "msqrt":
        return r"\sqrt{%s}" % "".join(convert(c) for c in kids)

    if t == "mroot":
        base = convert(kids[0]) if kids else ""
        deg = convert(kids[1]) if len(kids) > 1 else ""
        return r"\sqrt[%s]{%s}" % (deg, base)

    if t == "mfenced":
        open_ = el.attrib.get("open", "(")
        close = el.attrib.get("close", ")")
        body = ",".join(convert(c) for c in kids)
        if kids and _tag(kids[0]) == "mtable" and open_ in ("{", "\\{"):
            return r"\begin{cases}%s\end{cases}" % _cases_body(kids[0])
        return open_ + body + close

    if t == "munderover":
        base = convert(kids[0]) if kids else ""
        under = convert(kids[1]) if len(kids) > 1 else ""
        over = convert(kids[2]) if len(kids) > 2 else ""
        return "%s_{%s}^{%s}" % (base, under, over)

    if t == "munder":
        base = convert(kids[0]) if kids else ""
        under = convert(kids[1]) if len(kids) > 1 else ""
        return "%s_{%s}" % (base, under)

    if t == "mover":
        base = convert(kids[0]) if kids else ""
        over = convert(kids[1]) if len(kids) > 1 else ""
        return "%s^{%s}" % (base, over)

    if t == "mspace":
        return " "

    if t == "mtable":
        rows = []
        for tr in kids:
            cells = [convert(td) for td in list(tr)]
            rows.append(" & ".join(cells))
        return r"\begin{array}{%s}%s\end{array}" % ("c" * 3, r" \\ ".join(rows))

    # unknown node: keep children so nothing silently disappears
    body = "".join(convert(c) for c in kids)
    return body if body else _escape_text(el.text or "")


SIMPLE = {r"\frac", r"\sqrt", r"\mathrm", r"\text", r"\begin", r"\end", r"\left", r"\right",
          r"\sum", r"\int", r"\prod", r"\partial", r"\nabla", r"\infty", r"\approx",
          r"\le", r"\ge", r"\neq", r"\pm", r"\mp", r"\sim", r"\to", r"\langle", r"\rangle",
          r"\mathbb", r"\mathcal", r"\hat", r"\bar", r"\vec", r"\dot", r"\ddot", r"\times",
          r"\cdot", r"\log", r"\ln", r"\exp", r"\sin", r"\cos", r"\tan", r"\max", r"\min",
          r"\operatorname", r"\mathrm{d}", r"\mid", r"\vert", r"\Vert"}
COMMANDS = sorted({c for c in list(GREEK.values()) + list(OPS.values()) + list(SIMPLE)
                   if c.startswith("\\")}, key=len, reverse=True)
KNOWN = set(COMMANDS)


def separate_commands(latex):
    """`\\pi` followed by a letter would be read as a longer control word.

    Only the reconstructed path goes through here; publisher LaTeX is left alone.
    The scan takes the longest known command so that `\\left` is never cut to `\\le`.
    """
    out, i, n = [], 0, len(latex)
    while i < n:
        ch = latex[i]
        if ch == "\\" and i + 1 < n and latex[i + 1].isalpha():
            j = i + 1
            while j < n and latex[j].isalpha():
                j += 1
            word = latex[i:j]
            if word in KNOWN:
                out.append(word)
                i = j
                continue
            best = None
            for k in range(j - 1, i + 1, -1):
                if latex[i:k] in KNOWN:
                    best = latex[i:k]
                    break
            if best:
                out.append(best + " ")
                i += len(best)
                continue
            out.append(word)
            i = j
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def brace_balance(latex):
    """Escaped braces \\{ \\} are literals, not grouping, so they do not count."""
    s = latex.replace(r"\{", "").replace(r"\}", "")
    return s.count("{") - s.count("}")


def _cells(row):
    return [convert(td).strip() for td in list(row)]


def _cases_body(table):
    lines = []
    for row in list(table):
        cells = _cells(row)
        if len(cells) >= 2:
            lines.append("%s & %s" % (cells[0], cells[1]))
        elif cells:
            lines.append(cells[0])
    return r" \\ ".join(lines)


def _escape_text(s):
    return s.replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")


def _depth(latex):
    return latex.count(r"\frac") + latex.count("^{") + latex.count("_{")


def scan_file(path):
    """Return list of {id, latex, kind, depth, source} for one file."""
    raw = open(path, encoding="utf-8", errors="replace").read()
    out = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        # regex fallback: grab <math ...>...</math> blocks and their ids
        for m in re.finditer(r"<math\b[^>]*>.*?</math>", raw, re.S):
            block = m.group(0)
            idm = re.search(r'\bid="([^"]+)"', block)
            text = re.sub(r"<[^>]+>", " ", block)
            text = re.sub(r"\s+", " ", text).strip()
            out.append({"id": idm.group(1) if idm else None,
                        "latex": None,
                        "plain": text,
                        "kind": "xml_fallback_text",
                        "depth": 0,
                        "source": os.path.basename(path)})
        return out

    nodes = [el for el in root.iter() if _tag(el) in ("math",)]
    parents = {}
    for p in root.iter():
        for c in p:
            parents[c] = p

    def inherited_id(el):
        """Walk up until an element carries an id (MathML or disp-formula)."""
        cur, container = el, None
        while cur is not None:
            tag = _tag(cur)
            if container is None and tag not in ("math", "mrow", "semantics"):
                container = tag or None
            own = _attr_id(cur)
            if own:
                return own, container
            cur = parents.get(cur)
        return None, container

    for el in nodes:
        annotation, method = source_tex(el, parents)
        if annotation:
            # publisher LaTeX is authoritative: leave it byte for byte
            latex = re.sub(r"\s+", " ", annotation).strip()
        else:
            latex = convert(el).strip()
            # a control word followed by a letter would be read as a longer command:
            # \pim is an error, \pi m is not
            latex = separate_commands(latex)
        fid, container = inherited_id(el)
        balance = brace_balance(latex)
        out.append({"id": fid,
                    "latex": latex,
                    "plain": re.sub(r"\s+", " ", latex),
                    "kind": classify(latex),
                    "depth": _depth(latex),
                    "method": method or "reconstructed",
                    "container": container,
                    "label": find_label(el, parents),
                    "truncated": balance != 0,
                    "source": os.path.basename(path)})
    return out


def classify(latex):
    if not latex:
        return "empty"
    if r"\frac" in latex and (r"\sum" in latex or r"\int" in latex):
        return "summed_fraction"
    if r"\frac" in latex:
        return "fraction"
    if "^{" in latex and "_{" in latex:
        return "subscript_superscript"
    if "_{" in latex:
        return "subscripted"
    return "inline"


INLINE = [
    (re.compile(r"\$\$(.+?)\$\$", re.S), "display_math"),
    (re.compile(r"\\\[(.+?)\\\]", re.S), "display_bracket"),
    (re.compile(r"\\begin\{(equation\*?|align\*?|eqnarray\*?)\}(.+?)\\end\{\1\}", re.S), "latex_env"),
    (re.compile(r"(?<!\$)\$(?!\$)([^$\n]{4,})\$(?!\$)", re.S), "inline_math"),
]


def scan_text(path):
    """Extract formulas from LaTeX-bearing text (id = file#line)."""
    raw = open(path, encoding="utf-8", errors="replace").read()
    out = []
    for pattern, kind in INLINE:
        for m in pattern.finditer(raw):
            body = m.group(m.lastindex).strip()
            if not body:
                continue
            line = raw[:m.start()].count("\n") + 1
            out.append({"id": "%s#L%d" % (os.path.basename(path), line),
                        "latex": re.sub(r"\s+", " ", body),
                        "plain": re.sub(r"\s+", " ", body),
                        "kind": kind,
                        "depth": _depth(body),
                        "method": "text_latex",
                        "container": None,
                        "truncated": body.count("{") != body.count("}"),
                        "source": os.path.basename(path)})
    # de-duplicate identical latex extracted by overlapping patterns
    seen, uniq = set(), []
    for r in out:
        key = r["latex"]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    return uniq


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="xml file or directory")
    ap.add_argument("--pdf", help="pdf file; extracted text is written verbatim")
    ap.add_argument("--output", default="formulas.jsonl")
    a = ap.parse_args()

    if a.pdf:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(a.pdf)
            text = "\n".join(page.get_text() for page in doc)
            method = "pymupdf"
        except Exception as e:  # pragma: no cover - environment dependent
            text = ""
            method = "unavailable: %s" % e
        with open(a.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(json.dumps({"pdf": a.pdf, "method": method, "chars": len(text)}, ensure_ascii=False))
        return

    files = []
    if a.input and os.path.isdir(a.input):
        for name in sorted(os.listdir(a.input)):
            if name.lower().endswith((".xml", ".mathml", ".html")):
                files.append(os.path.join(a.input, name))
    elif a.input:
        files = [a.input]

    rows = []
    for p in files:
        for r in scan_file(p):
            rows.append(r)

    text_paths = []
    if a.input and os.path.isdir(a.input):
        text_paths = [os.path.join(a.input, n) for n in sorted(os.listdir(a.input))
                      if n.lower().endswith((".tex", ".txt", ".md"))]
    elif a.input and a.input.lower().endswith((".tex", ".txt", ".md")):
        text_paths = [a.input]
    for p in text_paths:
        rows.extend(scan_text(p))

    with open(a.output, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"files": [os.path.basename(p) for p in files],
                      "formulas": len(rows),
                      "with_id": sum(1 for r in rows if r["id"]),
                      "output": a.output}, ensure_ascii=False))


if __name__ == "__main__":
    main()
