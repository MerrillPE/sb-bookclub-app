import { initDropdown, initInlineEditToggle } from "./utils.js";

initDropdown("[data-filter-toggle]", "[data-filter-menu]");
document.querySelectorAll("[data-inline-edit]").forEach(initInlineEditToggle);
