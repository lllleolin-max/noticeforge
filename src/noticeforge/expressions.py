"""Use PyPA validation/catalog; validate the human's finite branch selection."""
import re
from packaging.licenses import canonicalize_license_expression, InvalidLicenseExpression
from .contracts import text
from .errors import InputError


def normalize(value):
    text(value, "license expression", 2048)
    try:
        return str(canonicalize_license_expression(value))
    except InvalidLicenseExpression as exc:
        raise InputError(f"invalid SPDX expression: {exc}") from exc


def tree(expression):
    tokens = re.findall(r"\(|\)|[^\s()]+", normalize(expression))
    if len(tokens) > 128:
        raise InputError("expression token allowance exceeded")
    position = 0
    def atom():
        nonlocal position
        token = tokens[position]
        position += 1
        if token == "(":
            node = disjunction()
            if tokens[position] != ")":
                raise InputError("missing expression closing parenthesis")
            position += 1
            return node
        if position < len(tokens) and tokens[position] == "WITH":
            token += " WITH " + tokens[position + 1]
            position += 2
        return ("atom", token)
    def conjunction():
        nonlocal position
        node = atom()
        while position < len(tokens) and tokens[position] == "AND":
            position += 1
            node = ("AND", node, atom())
        return node
    def disjunction():
        nonlocal position
        node = conjunction()
        while position < len(tokens) and tokens[position] == "OR":
            position += 1
            node = ("OR", node, conjunction())
        return node
    try:
        result = disjunction()
    except (IndexError, RecursionError) as exc:
        raise InputError("unsupported bounded expression") from exc
    if position != len(tokens):
        raise InputError("unsupported expression grammar")
    return result


def leaves(node):
    if node[0] == "atom":
        return {node[1]}
    return leaves(node[1]) | leaves(node[2])


def choice_valid(node, selected):
    """Bounded branch union proof, including repeated atoms across AND operands."""
    states = 0
    def branches(part):
        nonlocal states
        if part[0] == "atom":
            return {frozenset([part[1]])} if part[1] in selected else set()
        left, right = branches(part[1]), branches(part[2])
        if part[0] == "OR":
            result = left | right
        else:
            if len(left) * len(right) > 4096:
                raise InputError("license branch proof allowance exceeded")
            result = {a | b for a in left for b in right}
        states += len(result)
        if states > 4096:
            raise InputError("license branch proof allowance exceeded")
        return result
    return frozenset(selected) in branches(node)


def validate_choice(expression, selected):
    selected = [normalize(item) for item in selected]
    for item in selected:
        if tree(item)[0] != "atom":
            raise InputError("each choice must be a simple license or WITH atom")
    if len(set(selected)) != len(selected) or not choice_valid(tree(expression), set(selected)):
        raise InputError("approved choice is not one expression branch")
    return selected
