// Run with `npm test` (Node's built-in runner; no extra dependencies).
import assert from "node:assert/strict";
import { test } from "node:test";

import { compileFormula } from "./formula.ts";

const VARIABLES = ["xg", "xa", "mins", "pts", "price", "g"];
const ROW = { xg: 4.5, xa: 1.5, mins: 450, pts: 45, price: 15, g: 6 };

function value(source: string, row: Record<string, number | null> = ROW): number | null {
  const compiled = compileFormula(source, VARIABLES);
  if (!compiled.ok) throw new Error(compiled.error);
  return compiled.evaluate(row);
}

test("evaluates arithmetic with standard precedence", () => {
  assert.equal(value("xg * xa"), 6.75);
  assert.equal(value("pts / price"), 3);
  assert.equal(value("g - xg"), 1.5);
  assert.equal(value("-xg + 2^3"), 3.5);
  assert.equal(value("2^3^2"), 512); // right-associative
  assert.equal(value("max(xg, xa, 5)"), 5);
});

test("per90 scales by the row's minutes", () => {
  assert.equal(value("per90(xg)"), 0.9);
  assert.ok(Math.abs((value("per90(xg) / xa") ?? 0) - 0.6) < 1e-12);
  assert.equal(value("per90(xg)", { xg: 1, mins: 0 }), null);
});

test("undefined results become null instead of Infinity", () => {
  assert.equal(value("xg / 0"), null);
  assert.equal(value("xg + xa", { xg: 1, xa: null }), null);
});

test("accepts typographic operators and any case", () => {
  assert.equal(value("XG × xa"), 6.75);
  assert.equal(value("xg ÷ xa − 1"), 2);
});

test("rejects malformed formulas with a readable message", () => {
  const cases: [string, RegExp][] = [
    ["", /empty/],
    ["xg *", /ends too early/],
    ["foo + 1", /Unknown stat "foo"/],
    ["bar(xg)", /Unknown function "bar"/],
    ["sqrt(1, 2)", /takes 1 argument/],
    ["(xg", /Expected "\)"/],
    ["xg xa", /Unexpected "xa"/],
    ["xg $ 2", /Unexpected "\$"/],
  ];
  for (const [source, message] of cases) {
    const compiled = compileFormula(source, VARIABLES);
    assert.equal(compiled.ok, false, source);
    if (!compiled.ok) assert.match(compiled.error, message, source);
  }
});
