#!/usr/bin/env python3
"""Build benchmark/cases.jsonl.

Each case stores a LaTeX string plus an INDEPENDENT Python expression for the
same physical formula. The skill's converter is scored against the value the
independent expression produces, so a conversion mistake (dropped exponent,
merged subscript, wrong bracket level) shows up as a numeric mismatch instead of
being silently accepted.

Run: python build_cases.py > cases.jsonl
"""
import json
import math

CASES = [
    {
        "id": "debye-lowT-heat-capacity",
        "latex": r"C_p=\frac{12}{5}\pi^4 N k_B (\frac{T}{\Theta})^3",
        "independent_expr": "(12/5)*math.pi**4*N*k_B*(T/Theta)**3",
        "values": {"N": 1.0, "k_B": 1.380649e-23, "T": 10.0, "Theta": 1000.0},
        "expected_symbols": ["C_p", "N", "k_B", "T", "Theta"],
        "note": "Debye low-temperature limit; exponent 3 must stay on (T/Theta)",
    },
    {
        "id": "ideal-gas-pressure",
        "latex": r"p=\frac{n R T}{V}",
        "independent_expr": "n*R*T/V",
        "values": {"n": 1.0, "R": 8.314462618, "T": 300.0, "V": 0.024},
        "expected_symbols": ["p", "n", "R", "T", "V"],
        "note": "nested fraction; every symbol appears once",
    },
    {
        "id": "arrhenius-rate",
        "latex": r"k=A\exp(-\frac{E_a}{R T})",
        "independent_expr": "A*math.exp(-E_a/(R*T))",
        "values": {"A": 1e13, "E_a": 50000.0, "R": 8.314462618, "T": 300.0},
        "expected_symbols": ["k", "A", "E_a", "R", "T"],
        "note": "minus sign inside the exponential and a subscripted activation energy",
    },
    {
        "id": "einstein-heat-capacity",
        "latex": r"C=3Nk_B(\frac{\Theta}{T})^2\frac{\exp(\Theta/T)}{(\exp(\Theta/T)-1)^2}",
        "independent_expr": "3*N*k_B*(Theta/T)**2*math.exp(Theta/T)/(math.exp(Theta/T)-1)**2",
        "values": {"N": 1.0, "k_B": 1.380649e-23, "T": 300.0, "Theta": 300.0},
        "expected_symbols": ["C", "N", "k_B", "Theta", "T"],
        "note": "powers on a bracketed ratio plus a squared denominator",
    },
    {
        "id": "debye-length",
        "latex": r"\lambda_D=\sqrt{\frac{\epsilon_0 k_B T}{n e^2}}",
        "independent_expr": "math.sqrt(epsilon_0*k_B*T/(n*e**2))",
        "values": {"epsilon_0": 8.8541878128e-12, "k_B": 1.380649e-23,
                   "T": 300.0, "n": 1e20, "e": 1.602176634e-19},
        "expected_symbols": ["lambda_D", "epsilon_0", "k_B", "T", "n", "e"],
        "note": "square root of a fraction; charge appears squared",
    },
    {
        "id": "fermi-energy",
        "latex": r"E_F=\frac{\hbar^2}{2m}(3\pi^2 n)^{2/3}",
        "independent_expr": "hbar**2/(2*m)*(3*math.pi**2*n)**(2/3)",
        "values": {"hbar": 1.054571817e-34, "m": 9.1093837015e-31, "n": 8.47e28},
        "expected_symbols": ["E_F", "hbar", "m", "n"],
        "note": "fractional exponent 2/3 on a bracketed product",
    },
    {
        "id": "larmor-frequency",
        "latex": r"\omega=\gamma B",
        "independent_expr": "gamma*B",
        "values": {"gamma": 2.67522128e8, "B": 1.5},
        "expected_symbols": ["omega", "gamma", "B"],
        "note": "implicit product of two symbols; Greek letter must survive",
    },
    {
        "id": "diffusion-length",
        "latex": r"L=\sqrt{D \tau}",
        "independent_expr": "math.sqrt(D*tau)",
        "values": {"D": 1e-9, "tau": 1e-3},
        "expected_symbols": ["L", "D", "tau"],
        "note": "square root of a product; no numeric coefficient",
    },
    {
        "id": "stefan-boltzmann-flux",
        "latex": r"j=\sigma T^4",
        "independent_expr": "sigma*T**4",
        "values": {"sigma": 5.670374419e-8, "T": 300.0},
        "expected_symbols": ["j", "sigma", "T"],
        "note": "single-power term; catches a dropped exponent",
    },
    {
        "id": "thermal-de-broglie",
        "latex": r"\lambda=\frac{h}{\sqrt{2\pi m k_B T}}",
        "independent_expr": "h/math.sqrt(2*math.pi*m*k_B*T)",
        "values": {"h": 6.62607015e-34, "m": 1.67262192369e-27, "k_B": 1.380649e-23, "T": 300.0},
        "expected_symbols": ["lambda", "h", "m", "k_B", "T"],
        "note": "square root in the denominator; constants under the root",
    },
]

if __name__ == "__main__":
    for c in CASES:
        env = {"math": math}
        env.update(c["values"])
        c["expected_value"] = eval(c["independent_expr"], {"__builtins__": {}}, env)
        print(json.dumps(c, ensure_ascii=False))
