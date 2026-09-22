import { initDropdown } from "./utils.js";

initDropdown("[data-filter-toggle]", "[data-filter-menu]");

document.querySelectorAll("[data-star-picker]").forEach((picker) => {
  const wrapper = picker.parentElement;
  const select = wrapper.querySelector("[data-score-select]");
  const fill = picker.querySelector("[data-star-fill]");
  const display = wrapper.querySelector("[data-score-display]");
  if (!select || !fill || !display) return;

  const applyValue = (value) => {
    const clamped = Math.max(1, Math.min(5, value));
    select.value = clamped.toFixed(1);
    select.dispatchEvent(new Event("change", { bubbles: true }));
  };

  const valueFromPointer = (clientX) => {
    const rect = picker.getBoundingClientRect();
    const fraction = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    return Math.round(fraction * 5 * 2) / 2;
  };

  picker.addEventListener("pointerdown", (event) => {
    picker.setPointerCapture(event.pointerId);
    applyValue(valueFromPointer(event.clientX));
  });
  picker.addEventListener("pointermove", (event) => {
    if (!picker.hasPointerCapture(event.pointerId)) return;
    applyValue(valueFromPointer(event.clientX));
  });
  picker.addEventListener("pointerup", (event) => {
    if (picker.hasPointerCapture(event.pointerId)) picker.releasePointerCapture(event.pointerId);
  });

  // Keeps the visual widget in sync whether the change came from a pointer drag above
  // (which dispatches "change" itself) or from native keyboard interaction with the
  // still-real, still-focusable (but visually sr-only) <select>.
  select.addEventListener("change", () => {
    const value = parseFloat(select.value);
    fill.style.width = `${(value / 5) * 100}%`;
    display.textContent = value.toFixed(1);
  });
});

function fillBookFields({ title, author, cover_url, isbn }) {
  const setValue = (id, value) => {
    const field = document.getElementById(id);
    if (field && value) field.value = value;
  };
  setValue("title", title);
  setValue("author", author);
  setValue("cover_url", cover_url);
  setValue("isbn", isbn);
}

function createSpinner() {
  const spinner = document.createElement("span");
  spinner.className = "inline-block h-4 w-4 rounded-full border-2 border-stone-300 border-t-amber-600 animate-spin";
  spinner.setAttribute("aria-hidden", "true");
  return spinner;
}

function makeCandidateButton(candidateData, className, label, onPick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.addEventListener("click", () => onPick(candidateData));
  return button;
}

function addCoverThumb(thumbs, candidate, coverEntry, pick) {
  const thumbButton = makeCandidateButton(
    { ...candidate, cover_url: coverEntry.cover_url, isbn: coverEntry.isbn },
    "block rounded border border-stone-200 dark:border-stone-600 overflow-hidden hover:border-amber-500",
    "",
    pick,
  );
  const img = document.createElement("img");
  img.src = coverEntry.cover_url;
  img.loading = "lazy";
  img.alt = `${candidate.title} cover option`;
  img.className = "w-full aspect-[2/3] object-cover";
  // Open Library can still return a 200 with a 1x1 placeholder GIF for an edition
  // its own metadata claims has a cover, so a load error alone won't catch it --
  // check actual pixel size as a defense-in-depth backstop.
  img.addEventListener("load", () => {
    if (img.naturalWidth <= 1) thumbButton.remove();
  });
  thumbButton.appendChild(img);
  thumbs.appendChild(thumbButton);
}

function renderLookupCandidates(container, candidates) {
  container.innerHTML = "";
  const pick = (candidateData) => {
    fillBookFields(candidateData);
    container.classList.add("hidden");
  };

  candidates.forEach((candidate) => {
    const row = document.createElement("div");

    const year = candidate.year ? ` (${candidate.year})` : "";
    const mainButton = makeCandidateButton(
      candidate,
      "flex items-center gap-3 w-full text-left rounded-md border border-stone-200 dark:border-stone-600 px-3 py-2 text-sm text-text-secondary hover:bg-surface-muted",
      "",
      pick,
    );
    if (candidate.cover_url) {
      const thumb = document.createElement("img");
      thumb.src = candidate.cover_url;
      thumb.loading = "lazy";
      thumb.alt = "";
      thumb.className = "h-12 w-auto flex-none rounded";
      // Same 1x1-placeholder guard used for the "more covers" thumbnails below.
      thumb.addEventListener("load", () => {
        if (thumb.naturalWidth <= 1) thumb.remove();
      });
      mainButton.appendChild(thumb);
    }
    const label = document.createElement("span");
    label.textContent = `${candidate.title} — ${candidate.author}${year}`;
    mainButton.appendChild(label);
    row.appendChild(mainButton);

    if (candidate.work_key) {
      const thumbs = document.createElement("div");
      thumbs.className = "hidden mt-1 grid grid-cols-6 gap-2";

      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "mt-1 text-xs text-amber-700 hover:underline";
      toggle.textContent = "Show more covers";

      let loaded = false;
      toggle.addEventListener("click", async () => {
        thumbs.classList.toggle("hidden");
        if (loaded || thumbs.classList.contains("hidden")) return;
        loaded = true;
        toggle.disabled = true;
        const spinner = createSpinner();
        toggle.after(spinner);
        try {
          const response = await fetch(`/books/api/lookup/covers?work=${encodeURIComponent(candidate.work_key)}`);
          const data = await response.json();
          const covers = data.covers || [];
          if (!covers.length) {
            toggle.textContent = "No other covers found";
            return; // stays disabled -- nothing more to load
          }
          covers.forEach((coverEntry) => addCoverThumb(thumbs, candidate, coverEntry, pick));
          toggle.disabled = false;
        } catch (err) {
          loaded = false;
          toggle.disabled = false;
        } finally {
          spinner.remove();
        }
      });

      row.appendChild(toggle);
      row.appendChild(thumbs);
    }

    container.appendChild(row);
  });
  container.classList.remove("hidden");
}

document.querySelectorAll("[data-book-lookup]").forEach((button) => {
  const form = button.closest("form");
  const errorMessage = form?.querySelector("[data-book-lookup-error]");
  const candidatesContainer = form?.querySelector("[data-book-lookup-candidates]");
  if (!form || !errorMessage || !candidatesContainer) return;

  button.addEventListener("click", async () => {
    errorMessage.classList.add("hidden");
    candidatesContainer.classList.add("hidden");

    const isbn = document.getElementById("isbn")?.value.trim() ?? "";
    const title = document.getElementById("title")?.value.trim() ?? "";
    const author = document.getElementById("author")?.value.trim() ?? "";
    const params = new URLSearchParams();
    if (isbn) params.set("isbn", isbn);
    if (title) params.set("title", title);
    if (author) params.set("author", author);

    button.disabled = true;
    const spinner = createSpinner();
    button.after(spinner);
    try {
      const response = await fetch(`/books/api/lookup?${params.toString()}`);
      const data = await response.json();
      if (data.match) {
        fillBookFields(data.match);
      } else if (data.candidates && data.candidates.length) {
        renderLookupCandidates(candidatesContainer, data.candidates);
      } else {
        errorMessage.classList.remove("hidden");
      }
    } catch (err) {
      errorMessage.classList.remove("hidden");
    } finally {
      spinner.remove();
      button.disabled = false;
    }
  });
});
