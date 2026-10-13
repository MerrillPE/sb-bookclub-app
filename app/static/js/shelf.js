// Pure helpers shared by books.js -- no DOM access or side effects on import, so they can be
// unit-tested directly (tests/js/shelf.test.js).
//
// The spine/seed rules mirror the `title_seed` Jinja filter (app/__init__.py) and the `spine`
// macro in _macros.html, so the add/edit form's live preview matches what the saved book
// will look like on the shelf. tests/fixtures/spine_cases.json pins both sides to the same
// expected values -- change one side and the other side's test will fail.
const SPINE_HEIGHTS = ["84%", "90%", "95%", "99%"];
const SPINE_WIDTHS = ["2.7rem", "3.1rem", "3.7rem", "4.2rem"];

export function titleSeed(title) {
  let sum = 0;
  for (const ch of title) sum += ch.codePointAt(0); // code points, same as Python's ord()
  return sum;
}

export function spineWidth(title) {
  const length = [...title].length;
  return SPINE_WIDTHS[length <= 9 ? 0 : length <= 16 ? 1 : length <= 24 ? 2 : 3];
}

export function spineHeight(seed) {
  return SPINE_HEIGHTS[Math.floor(seed / 3) % 4];
}

// Star-picker score for a pointer position given as a 0..1 fraction of the widget's width:
// rounded to the nearest half star and clamped to the form's 1.0-5.0 range.
export function scoreFromFraction(fraction) {
  const clampedFraction = Math.max(0, Math.min(1, fraction));
  const score = Math.round(clampedFraction * 5 * 2) / 2;
  return Math.max(1, Math.min(5, score));
}
