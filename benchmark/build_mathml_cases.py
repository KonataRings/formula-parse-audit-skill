#!/usr/bin/env python3
"""Build benchmark/mathml_cases.jsonl: MathML in, expected LaTeX out.

These exercise the reconstruction path (no publisher annotation), including the
cases that break naive converters: invisible operators U+2061/U+2062, a function
application, nested fractions under a root, subscript-plus-superscript, a
piecewise definition, an uppercase Greek letter, and an alttext-only formula.
"""
import json

M = "http://www.w3.org/1998/Math/MathML"


def math(inner, alttext=None):
    attr = ' alttext="%s"' % alttext.replace('"', "&quot;") if alttext else ""
    return '<math xmlns="%s"%s>%s</math>' % (M, attr, inner)


CASES = [
    {
        "id": "mass-energy",
        "mathml": math("<mi>E</mi><mo>=</mo><mi>m</mi><msup><mi>c</mi><mn>2</mn></msup>"),
        "expected_latex": r"E=m{c}^{2}",
        "note": "superscript on a single letter",
    },
    {
        "id": "invisible-times",
        "mathml": math("<mn>2</mn><mo>&#x2062;</mo><mi>&#x3c0;</mi><mo>&#x2062;</mo>"
                       "<mi>m</mi><msup><mi>k</mi><mn>2</mn></msup>"),
        "expected_latex": r"2\pi m{k}^{2}",
        "note": "U+2062 must vanish, not become an operator",
    },
    {
        "id": "function-application",
        "mathml": math("<mi>sin</mi><mo>&#x2061;</mo><mfenced><mi>x</mi></mfenced>"),
        "expected_latex": r"\mathrm{sin}(x)",
        "note": "U+2061 is function application; sin(x) is not sin*(x)",
    },
    {
        "id": "root-of-fraction",
        "mathml": math("<mi>&#x3c9;</mi><mo>=</mo><msqrt><mfrac><mi>k</mi><mi>m</mi>"
                       "</mfrac></msqrt>"),
        "expected_latex": r"\omega=\sqrt{\frac{k}{m}}",
        "note": "square root wrapping a fraction",
    },
    {
        "id": "subscript-superscript",
        "mathml": math("<msubsup><mi>x</mi><mi>i</mi><mn>2</mn></msubsup><mo>+</mo>"
                       "<msubsup><mi>x</mi><mi>j</mi><mn>2</mn></msubsup>"),
        "expected_latex": r"{x}_{i}^{2}+{x}_{j}^{2}",
        "note": "msubsup keeps both scripts on the same base",
    },
    {
        "id": "piecewise",
        "mathml": math("<mi>f</mi><mo>(</mo><mi>x</mi><mo>)</mo><mo>=</mo>"
                       "<mfenced open=\'{\' close=\'\'><mtable>"
                       "<mtr><mtd><mi>x</mi></mtd><mtd><mi>x</mi><mo>&gt;</mo><mn>0</mn></mtd></mtr>"
                       "<mtr><mtd><mo>-</mo><mi>x</mi></mtd><mtd><mi>x</mi><mo>&#x2264;</mo><mn>0</mn></mtd></mtr>"
                       "</mtable></mfenced>"),
        "expected_latex": r"f(x)=\begin{cases}x & x>0 \\ -x & x\le 0\end{cases}",
        "note": "braced table becomes cases; rows are two columns",
    },
    {
        "id": "uppercase-greek",
        "mathml": math("<mi>&#x398;</mi><mo>=</mo><mfrac><mrow><mi>h</mi><msub><mi>&#x3bd;</mi>"
                       "<mi>D</mi></msub></mrow><msub><mi>k</mi><mi>B</mi></msub></mfrac>"),
        "expected_latex": r"\Theta=\frac{h{\nu}_{D}}{{k}_{B}}",
        "note": "uppercase Greek and two subscripted factors",
    },
    {
        "id": "alttext-only",
        "mathml": math("<mrow><mi>a</mi><mo>+</mo><mi>b</mi></mrow>", alttext="a + b"),
        "expected_latex": r"a+b",
        "note": "when the publisher gives alttext LaTeX, prefer it over reconstruction",
    },
]

if __name__ == "__main__":
    for c in CASES:
        print(json.dumps(c, ensure_ascii=False))

