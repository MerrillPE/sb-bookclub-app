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

export function initInlineEditToggle(root) {
    const trigger = root.querySelector("[data-inline-edit-trigger]");
    const view = root.querySelector("[data-inline-edit-view]");
    const panel = root.querySelector("[data-inline-edit-panel]");
    const cancel = root.querySelector("[data-inline-edit-cancel]");
    if (!trigger || !view || !panel) return;

    trigger.addEventListener("click", () => {
        view.classList.add("hidden");
        panel.classList.remove("hidden");
        const focusTarget = panel.querySelector("select, input, textarea");
        if (focusTarget) focusTarget.focus();
    });

    if (cancel) {
        cancel.addEventListener("click", () => {
            const form = panel.querySelector("form");
            if (form) form.reset();
            panel.classList.add("hidden");
            view.classList.remove("hidden");
        });
    }
}
