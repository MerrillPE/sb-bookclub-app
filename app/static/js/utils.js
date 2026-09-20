export function initDropdown(toggleSelector, menuSelector) {
    const toggle = document.querySelector(toggleSelector);
    const menu = document.querySelector(menuSelector);
    if (!toggle || !menu) return;

    toggle.addEventListener("click", (event) => {
        event.stopPropagation();
        menu.classList.toggle("hidden");
        toggle.setAttribute("aria-expanded", String(!menu.classList.contains("hidden")));
    });
    document.addEventListener("click", (event) => {
        if (!menu.classList.contains("hidden") && !menu.contains(event.target) && event.target !== toggle) {
            menu.classList.add("hidden");
            toggle.setAttribute("aria-expanded", "false");
        }
    });
}
