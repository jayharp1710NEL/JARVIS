"""Safe calculator tool — AST-based arithmetic, no eval()."""
from __future__ import annotations

import ast
import math
import operator as op

from pydantic import BaseModel, Field

from .base import Tool

_BIN_OPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
    ast.Pow: op.pow, ast.Mod: op.mod, ast.FloorDiv: op.floordiv,
}
_UNARY = {ast.UAdd: op.pos, ast.USub: op.neg}
_FUNCS = {
    "sqrt": math.sqrt, "log": math.log, "log10": math.log10, "log2": math.log2,
    "exp": math.exp, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan, "floor": math.floor,
    "ceil": math.ceil, "abs": abs, "round": round, "factorial": math.factorial,
    "gcd": math.gcd, "max": max, "min": min, "pow": pow,
}
_CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau, "inf": math.inf}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Only numeric constants are allowed.")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Name):
        if node.id in _CONSTS:
            return _CONSTS[node.id]
        raise ValueError(f"Unknown name '{node.id}'.")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            raise ValueError("Unknown or disallowed function call.")
        args = [_eval(a) for a in node.args]
        return _FUNCS[node.func.id](*args)
    raise ValueError("Unsupported expression.")


def safe_calculate(expression: str) -> float:
    tree = ast.parse(expression, mode="eval")
    return _eval(tree)


class CalcInput(BaseModel):
    expression: str = Field(..., description="Arithmetic expression, e.g. '2*(3+4)**2'")


class CalculatorTool(Tool):
    name = "calculator"
    description = "Evaluate a math expression safely (supports sqrt, log, trig, etc.)."
    InputModel = CalcInput

    def execute(self, params: CalcInput):
        value = safe_calculate(params.expression)
        return {"expression": params.expression, "result": value}, f"= {value}"
