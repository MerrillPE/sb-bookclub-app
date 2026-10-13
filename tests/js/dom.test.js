// @vitest-environment happy-dom
//
// DOM-wiring tests for the page scripts. Each module wires itself up on import (no exported
// init), so each test builds its fixture markup first and then imports the module fresh.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

async function load(markup, module) {
  document.body.innerHTML = markup;
  vi.resetModules();
  await import(module);
}

function submit(form) {
  const event = new Event("submit", { bubbles: true, cancelable: true });
  form.dispatchEvent(event);
  return event;
}

beforeEach(() => {
  document.body.innerHTML = "";
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("data-confirm (main.js)", () => {
  const markup = `
    <div id="page-loading-bar" class="hidden"></div>
    <form data-confirm="Delete this book?"></form>
    <form id="plain"></form>`;

  it("blocks the submit and keeps the loading bar hidden when cancelled", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    await load(markup, "../../app/static/js/main.js");

    const event = submit(document.querySelector("[data-confirm]"));
    expect(confirm).toHaveBeenCalledWith("Delete this book?");
    expect(event.defaultPrevented).toBe(true);
    expect(document.getElementById("page-loading-bar").classList.contains("hidden")).toBe(true);
  });

  it("lets the submit through when confirmed", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    await load(markup, "../../app/static/js/main.js");

    expect(submit(document.querySelector("[data-confirm]")).defaultPrevented).toBe(false);
    expect(document.getElementById("page-loading-bar").classList.contains("hidden")).toBe(false);
  });

  it("never prompts for a form without data-confirm", async () => {
    const confirm = vi.spyOn(window, "confirm");
    await load(markup, "../../app/static/js/main.js");

    expect(submit(document.getElementById("plain")).defaultPrevented).toBe(false);
    expect(confirm).not.toHaveBeenCalled();
  });
});

describe("token panels (auth.js)", () => {
  const markup = `
    <form id="invite-token-form"><input name="token"></form>
    <form id="reset-token-form"><input name="token"></form>`;

  it.each([
    ["#invite-token-form", "  cedar-forest-delta ", "/auth/register/cedar-forest-delta"],
    ["#reset-token-form", "abc/def?x", "/auth/reset-password/abc%2Fdef%3Fx"],
  ])("%s routes a pasted token to the right URL", async (selector, token, path) => {
    await load(markup, "../../app/static/js/auth.js");
    const form = document.querySelector(selector);
    form.elements.token.value = token;

    expect(submit(form).defaultPrevented).toBe(true);
    expect(window.location.pathname).toBe(path);
  });

  it("does nothing for a blank token", async () => {
    await load(markup, "../../app/static/js/auth.js");
    const before = window.location.href;
    const form = document.querySelector("#invite-token-form");
    form.elements.token.value = "   ";

    submit(form);
    expect(window.location.href).toBe(before);
  });
});

describe("star picker (books.js)", () => {
  it("syncs the visual fill and readout when the real <select> changes", async () => {
    await load(`
      <div>
        <select data-score-select>
          <option value="1.0">1.0</option><option value="3.5">3.5</option>
        </select>
        <div data-star-picker><div data-star-fill></div></div>
        <span data-score-display></span>
      </div>`, "../../app/static/js/books.js");

    const select = document.querySelector("[data-score-select]");
    select.value = "3.5";
    select.dispatchEvent(new Event("change", { bubbles: true }));

    expect(document.querySelector("[data-star-fill]").style.width).toBe("70%");
    expect(document.querySelector("[data-score-display]").textContent).toBe("3.5");
  });
});

describe("inline edit toggle (utils.js)", () => {
  it("opens the panel, and cancel resets the form and closes it", async () => {
    document.body.innerHTML = `
      <div data-inline-edit>
        <div data-inline-edit-view><button data-inline-edit-trigger></button></div>
        <div data-inline-edit-panel class="hidden">
          <form><input value="original"><button type="button" data-inline-edit-cancel></button></form>
        </div>
      </div>`;
    vi.resetModules();
    const { initInlineEditToggle } = await import("../../app/static/js/utils.js");
    initInlineEditToggle(document.querySelector("[data-inline-edit]"));

    const view = document.querySelector("[data-inline-edit-view]");
    const panel = document.querySelector("[data-inline-edit-panel]");
    const input = panel.querySelector("input");

    document.querySelector("[data-inline-edit-trigger]").click();
    expect(view.classList.contains("hidden")).toBe(true);
    expect(panel.classList.contains("hidden")).toBe(false);
    expect(document.activeElement).toBe(input);

    input.value = "edited";
    document.querySelector("[data-inline-edit-cancel]").click();
    expect(input.value).toBe("original");
    expect(panel.classList.contains("hidden")).toBe(true);
    expect(view.classList.contains("hidden")).toBe(false);
  });
});
