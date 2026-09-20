// Safari's native <input type="date"> renders today's date as its unset state and offers
// no reliable in-UI way to clear it back to empty, so an explicit Clear button is needed
// for a field that's meant to be optional.
document.querySelectorAll("[data-clear-target]").forEach((button) => {
  button.addEventListener("click", () => {
    const target = document.getElementById(button.dataset.clearTarget);
    if (target) target.value = "";
  });
});

document.querySelectorAll("[data-copy-value]").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(button.dataset.copyValue);
      const original = button.textContent;
      button.textContent = "Copied!";
      setTimeout(() => { button.textContent = original; }, 1500);
    } catch (err) {
      // Clipboard API unavailable (e.g. insecure context) -- text is still visible to select manually.
    }
  });
});
