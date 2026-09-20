import "./auth.js"
import "./books.js"
import "./admin.js"
import { initDropdown, initInlineEditToggle } from "./utils.js";

initDropdown("[data-user-menu-toggle]", "[data-user-menu]");
// data-inline-edit is a generic view/panel toggle used by more than one blueprint's templates
// (books' rating panel, auth's token-entry panels), so it's wired up here once rather than
// duplicated in each blueprint file -- see docs/js-architecture.md.
document.querySelectorAll("[data-inline-edit]").forEach(initInlineEditToggle);
