import "./auth.js"
import "./books.js"
import "./admin.js"
import { initDropdown, initInlineEditToggle } from "./utils.js";

initDropdown("[data-user-menu-toggle]", "[data-user-menu]");
// data-inline-edit is a generic view/panel toggle used by more than one blueprint's templates
// (books' rating panel, auth's token-entry panels), so it's wired up here once rather than
// duplicated in each blueprint file -- see docs/js-architecture.md.
document.querySelectorAll("[data-inline-edit]").forEach(initInlineEditToggle);

// Site-wide chrome (the #page-loading-bar element lives in base.html), so it's initialized
// here rather than in a blueprint file -- see docs/js-architecture.md.
function initPageLoadingBar() {
  const bar = document.getElementById("page-loading-bar");
  if (!bar) return;

  const show = () => {
    bar.classList.remove("hidden");
    bar.style.transition = "none";
    bar.style.width = "0%";
    bar.offsetWidth; // force reflow so the reset above applies before the transition starts
    bar.style.transition = "width 4s ease-out";
    bar.style.width = "90%";
    // Safety net: if navigation never actually completes (offline, cancelled), don't
    // leave the bar stuck forever -- a real navigation unloads the page before this fires.
    setTimeout(hide, 15000);
  };
  const hide = () => {
    bar.classList.add("hidden");
    bar.style.transition = "";
    bar.style.width = "0%";
  };

  document.addEventListener("click", (event) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const link = event.target.closest("a[href]");
    if (!link || link.target === "_blank" || link.hasAttribute("download")) return;
    const href = link.getAttribute("href");
    if (href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) return;
    if (new URL(link.href, window.location.href).origin !== window.location.origin) return;
    show();
  });

  document.addEventListener("submit", (event) => {
    if (!event.defaultPrevented) show();
  });

  // Covers back/forward-cache restores, where the browser could otherwise redisplay
  // a page with the bar left visible from just before the user navigated away.
  window.addEventListener("pageshow", hide);
}

initPageLoadingBar();

// Site-wide chrome (the toggle button lives in base.html's navbar), so it's initialized
// here rather than in a blueprint file -- see docs/js-architecture.md. The initial theme
// itself is set by a blocking inline script in base.html's <head> to avoid a flash of the
// wrong theme on load; this just wires up the toggle click and persists the choice.
function initThemeToggle() {
  const toggle = document.querySelector("[data-theme-toggle]");
  if (!toggle) return;

  toggle.addEventListener("click", () => {
    const dark = !document.documentElement.classList.contains("dark");
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  });
}

initThemeToggle();
