import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

import { scoreFromFraction, spineHeight, spineWidth, titleSeed } from "../../app/static/js/shelf.js";

// Shared with tests/test_spine_parity.py, which checks the Jinja side against the same values.
const cases = JSON.parse(readFileSync(new URL("../fixtures/spine_cases.json", import.meta.url), "utf-8"));

describe("spine parity with the Jinja spine macro", () => {
  it.each(cases)("$title", ({ title, seed, width, height }) => {
    expect(titleSeed(title)).toBe(seed);
    expect(spineWidth(title)).toBe(width);
    expect(spineHeight(titleSeed(title))).toBe(height);
  });
});

describe("titleSeed", () => {
  it("is 0 for an empty title", () => {
    expect(titleSeed("")).toBe(0);
  });

  it("sums code points, not UTF-16 units", () => {
    // "📚" is one code point (0x1F4DA) but two UTF-16 units; Python's ord() sees one.
    expect(titleSeed("📚")).toBe(0x1f4da);
  });
});

describe("spineWidth", () => {
  it("counts an emoji as one character", () => {
    expect(spineWidth("📚".repeat(9))).toBe("2.7rem");
    expect(spineWidth("📚".repeat(10))).toBe("3.1rem");
  });
});

describe("scoreFromFraction", () => {
  it.each([
    [0, 1],       // clamped up to the 1-star minimum
    [0.09, 1],
    [0.15, 1],
    [0.25, 1.5],
    [0.5, 2.5],
    [0.69, 3.5],
    [1, 5],
    [-0.5, 1],    // pointer dragged off the left edge
    [1.5, 5],     // pointer dragged off the right edge
  ])("fraction %f -> %f stars", (fraction, expected) => {
    expect(scoreFromFraction(fraction)).toBe(expected);
  });
});
