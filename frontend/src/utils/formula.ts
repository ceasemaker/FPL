// Chart Lab formula engine.
//
// A small recursive-descent parser for user-written stat formulas such as
// `xg * xa` or `per90(xg) / xa`. It never calls eval: input is tokenised,
// parsed into an AST, and evaluated against a map of stat values.
//
// Grammar:
//   expr   := term (("+" | "-") term)*
//   term   := power (("*" | "/") power)*
//   power  := unary ("^" power)?
//   unary  := "-" unary | atom
//   atom   := number | name | name "(" args ")" | "(" expr ")"

export type FormulaNode =
  | { kind: "num"; value: number }
  | { kind: "var"; name: string }
  | { kind: "neg"; arg: FormulaNode }
  | { kind: "bin"; op: "+" | "-" | "*" | "/" | "^"; left: FormulaNode; right: FormulaNode }
  | { kind: "call"; name: string; args: FormulaNode[] };

export type StatValues = Record<string, number | null | undefined>;

export class FormulaError extends Error {}

// per90 is the reason this engine exists: it scales any expression by the
// row's minutes. Its arity is 1; it reads `mins` from the same row.
const FUNCTIONS: Record<string, { arity: [number, number]; fn: (args: number[], values: StatValues) => number | null }> = {
  per90: {
    arity: [1, 1],
    fn: ([x], values) => {
      const minutes = values.mins;
      return minutes ? (x / minutes) * 90 : null;
    },
  },
  sqrt: { arity: [1, 1], fn: ([x]) => (x < 0 ? null : Math.sqrt(x)) },
  log: { arity: [1, 1], fn: ([x]) => (x <= 0 ? null : Math.log(x)) },
  abs: { arity: [1, 1], fn: ([x]) => Math.abs(x) },
  min: { arity: [2, 8], fn: (args) => Math.min(...args) },
  max: { arity: [2, 8], fn: (args) => Math.max(...args) },
};

export const FORMULA_FUNCTIONS = Object.keys(FUNCTIONS);

type Token = { type: "num" | "name" | "op" | "lparen" | "rparen" | "comma"; text: string; pos: number };

function tokenize(source: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  while (i < source.length) {
    const ch = source[i];
    if (/\s/.test(ch)) { i += 1; continue; }
    if (/[0-9.]/.test(ch)) {
      const match = /^(\d+\.?\d*|\.\d+)/.exec(source.slice(i));
      if (!match) throw new FormulaError(`Unexpected "${ch}" at position ${i + 1}`);
      tokens.push({ type: "num", text: match[0], pos: i });
      i += match[0].length;
      continue;
    }
    if (/[A-Za-z_]/.test(ch)) {
      const match = /^[A-Za-z_][A-Za-z0-9_]*/.exec(source.slice(i))!;
      tokens.push({ type: "name", text: match[0].toLowerCase(), pos: i });
      i += match[0].length;
      continue;
    }
    // Accept the typographic operators people paste from notes.
    const op = ({ "×": "*", "÷": "/", "−": "-" } as Record<string, string>)[ch] ?? ch;
    if ("+-*/^".includes(op)) { tokens.push({ type: "op", text: op, pos: i }); i += 1; continue; }
    if (ch === "(") { tokens.push({ type: "lparen", text: ch, pos: i }); i += 1; continue; }
    if (ch === ")") { tokens.push({ type: "rparen", text: ch, pos: i }); i += 1; continue; }
    if (ch === ",") { tokens.push({ type: "comma", text: ch, pos: i }); i += 1; continue; }
    throw new FormulaError(`Unexpected "${ch}" at position ${i + 1}`);
  }
  return tokens;
}

export function parseFormula(source: string, knownVariables: Iterable<string>): FormulaNode {
  const variables = new Set(knownVariables);
  const tokens = tokenize(source);
  if (!tokens.length) throw new FormulaError("Formula is empty");
  let index = 0;

  const peek = () => tokens[index];
  const take = () => tokens[index++];
  const expect = (type: Token["type"], what: string) => {
    const token = take();
    if (!token || token.type !== type) {
      throw new FormulaError(token ? `Expected ${what} at position ${token.pos + 1}` : `Expected ${what} at the end`);
    }
    return token;
  };

  function expr(): FormulaNode {
    let node = term();
    while (peek()?.type === "op" && (peek().text === "+" || peek().text === "-")) {
      const op = take().text as "+" | "-";
      node = { kind: "bin", op, left: node, right: term() };
    }
    return node;
  }

  function term(): FormulaNode {
    let node = power();
    while (peek()?.type === "op" && (peek().text === "*" || peek().text === "/")) {
      const op = take().text as "*" | "/";
      node = { kind: "bin", op, left: node, right: power() };
    }
    return node;
  }

  function power(): FormulaNode {
    const base = unary();
    if (peek()?.type === "op" && peek().text === "^") {
      take();
      return { kind: "bin", op: "^", left: base, right: power() };
    }
    return base;
  }

  function unary(): FormulaNode {
    if (peek()?.type === "op" && peek().text === "-") {
      take();
      return { kind: "neg", arg: unary() };
    }
    return atom();
  }

  function atom(): FormulaNode {
    const token = take();
    if (!token) throw new FormulaError("Formula ends too early");
    if (token.type === "num") return { kind: "num", value: Number(token.text) };
    if (token.type === "lparen") {
      const inner = expr();
      expect("rparen", '")"');
      return inner;
    }
    if (token.type === "name") {
      if (peek()?.type === "lparen") {
        const spec = FUNCTIONS[token.text];
        if (!spec) throw new FormulaError(`Unknown function "${token.text}"`);
        take();
        const args: FormulaNode[] = [];
        if (peek()?.type !== "rparen") {
          args.push(expr());
          while (peek()?.type === "comma") { take(); args.push(expr()); }
        }
        expect("rparen", '")"');
        const [lo, hi] = spec.arity;
        if (args.length < lo || args.length > hi) {
          throw new FormulaError(`${token.text}() takes ${lo === hi ? lo : `${lo}-${hi}`} argument${hi === 1 ? "" : "s"}`);
        }
        return { kind: "call", name: token.text, args };
      }
      if (!variables.has(token.text)) throw new FormulaError(`Unknown stat "${token.text}"`);
      return { kind: "var", name: token.text };
    }
    throw new FormulaError(`Unexpected "${token.text}" at position ${token.pos + 1}`);
  }

  const node = expr();
  if (index < tokens.length) {
    const extra = tokens[index];
    throw new FormulaError(`Unexpected "${extra.text}" at position ${extra.pos + 1}`);
  }
  return node;
}

/** Evaluate a parsed formula. Returns null when the value is undefined
 *  (missing stat, division by zero, per90 with no minutes). */
export function evaluateFormula(node: FormulaNode, values: StatValues): number | null {
  const result = evaluate(node, values);
  return result === null || !Number.isFinite(result) ? null : result;
}

function evaluate(node: FormulaNode, values: StatValues): number | null {
  switch (node.kind) {
    case "num":
      return node.value;
    case "var": {
      const value = values[node.name];
      return value === null || value === undefined ? null : value;
    }
    case "neg": {
      const value = evaluate(node.arg, values);
      return value === null ? null : -value;
    }
    case "bin": {
      const left = evaluate(node.left, values);
      const right = evaluate(node.right, values);
      if (left === null || right === null) return null;
      switch (node.op) {
        case "+": return left + right;
        case "-": return left - right;
        case "*": return left * right;
        case "/": return right === 0 ? null : left / right;
        case "^": return left ** right;
      }
      return null;
    }
    case "call": {
      const args = node.args.map((arg) => evaluate(arg, values));
      if (args.some((arg) => arg === null)) return null;
      return FUNCTIONS[node.name].fn(args as number[], values);
    }
  }
}

/** Parse once; return an evaluator or the parse error message. */
export function compileFormula(
  source: string,
  knownVariables: Iterable<string>,
): { ok: true; evaluate: (values: StatValues) => number | null } | { ok: false; error: string } {
  try {
    const node = parseFormula(source, knownVariables);
    return { ok: true, evaluate: (values) => evaluateFormula(node, values) };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error.message : String(error) };
  }
}
