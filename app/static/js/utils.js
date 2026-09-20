const instances = [];

function openDropdown(instance) {
    instances.forEach((other) => {
        if (other !== instance) closeDropdown(other);
    });
    instance.menu.classList.remove("hidden");
    instance.toggle.setAttribute("aria-expanded", "true");
    const focusTarget = instance.menu.querySelector("a, button, input, select, textarea, [tabindex]");
    if (focusTarget) focusTarget.focus();
}

function closeDropdown(instance, { restoreFocus = false } = {}) {
    if (instance.menu.classList.contains("hidden")) return;
    instance.menu.classList.add("hidden");
    instance.toggle.setAttribute("aria-expanded", "false");
    if (restoreFocus) instance.toggle.focus();
}

export function initDropdown(toggleSelector, menuSelector) {
    const toggle = document.querySelector(toggleSelector);
    const menu = document.querySelector(menuSelector);
    if (!toggle || !menu) return;

    const instance = { toggle, menu };
    instances.push(instance);

    toggle.addEventListener("click", (event) => {
        event.stopPropagation();
        if (menu.classList.contains("hidden")) {
            openDropdown(instance);
        } else {
            closeDropdown(instance);
        }
    });

    document.addEventListener("click", (event) => {
        if (!menu.classList.contains("hidden") && !menu.contains(event.target) && event.target !== toggle) {
            closeDropdown(instance);
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !menu.classList.contains("hidden")) {
            closeDropdown(instance, { restoreFocus: true });
        }
    });
}
