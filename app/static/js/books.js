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
    if (field && value) {
      field.value = value;
      // Programmatic value changes don't fire "input" on their own -- dispatch one so the
      // live preview (initBookPreview below) picks up auto-filled values too.
      field.dispatchEvent(new Event("input", { bubbles: true }));
    }
  };
  setValue("title", title);
  setValue("author", author);
  setValue("cover_url", cover_url);
  setValue("isbn", isbn);
}

function createSpinner() {
  const spinner = document.createElement("span");
  spinner.className = "inline-block h-4 w-4 rounded-full border-2 border-border-strong border-t-accent animate-spin";
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
    "block rounded border border-border-subtle overflow-hidden hover:border-accent hover:ring-2 hover:ring-accent/30 transition",
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
      "flex items-center gap-3 w-full text-left rounded-lg border border-border-subtle bg-surface px-3 py-2 text-sm text-text-secondary hover:border-accent hover:text-text-primary transition-colors",
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
      toggle.className = "mt-1 text-xs text-accent hover:underline";
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

// Live cover + spine preview on the add/edit book form (books/form.html). Mirrors the
// book_cover/spine macros in _macros.html: keep titleSeed() in step with the `title_seed`
// Jinja filter (app/__init__.py) and the size rules with the spine macro, so the preview
// matches what the saved book will actually look like on the shelf.
const SPINE_HEIGHTS = ["84%", "90%", "95%", "99%"];
const SPINE_WIDTHS = ["2.7rem", "3.1rem", "3.7rem", "4.2rem"];

function spineWidth(title) {
  const length = [...title].length;
  return SPINE_WIDTHS[length <= 9 ? 0 : length <= 16 ? 1 : length <= 24 ? 2 : 3];
}

function titleSeed(title) {
  let sum = 0;
  for (const ch of title) sum += ch.codePointAt(0); // code points, same as Python's ord()
  return sum;
}

function initBookPreview(preview) {
  const palette = JSON.parse(preview.dataset.palette);
  const titleField = document.getElementById("title");
  const authorField = document.getElementById("author");
  const coverField = document.getElementById("cover_url");
  const generated = preview.querySelector("[data-preview-generated]");
  const img = preview.querySelector("[data-preview-img]");
  const spine = preview.querySelector("[data-preview-spine]");
  if (!titleField || !authorField || !coverField || !generated || !img || !spine) return;

  img.addEventListener("error", () => img.classList.add("hidden"));
  img.addEventListener("load", () => img.classList.toggle("hidden", img.naturalWidth <= 1));

  const update = () => {
    const title = titleField.value.trim();
    const author = authorField.value.trim();
    const seed = titleSeed(title);
    const [bg, fg] = palette[seed % palette.length];

    preview.querySelectorAll("[data-preview-title]").forEach((el) => {
      el.textContent = title || "Your book";
    });
    preview.querySelector("[data-preview-author]").textContent = author || "Author";
    preview.querySelector("[data-preview-spine-author]").textContent = (author || "Author").split(/\s+/).pop();

    generated.style.backgroundColor = bg;
    generated.style.color = fg;
    spine.style.setProperty("--spine-bg", bg);
    spine.style.setProperty("--spine-fg", fg);
    spine.style.height = SPINE_HEIGHTS[Math.floor(seed / 3) % 4];
    spine.style.width = spineWidth(title || "Your book");

    const url = coverField.value.trim();
    if (!url) {
      img.classList.add("hidden");
      img.removeAttribute("src");
    } else if (img.getAttribute("src") !== url) {
      img.src = url; // shown by the load listener once it actually loads
    }
  };

  [titleField, authorField, coverField].forEach((field) => field.addEventListener("input", update));
  update();
}

document.querySelectorAll("[data-book-preview]").forEach(initBookPreview);
