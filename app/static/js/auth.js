function wireTokenRedirect(formSelector, urlPrefix) {
  const form = document.querySelector(formSelector);
  if (!form) return;
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const token = form.elements.token.value.trim();
    if (token) {
      window.location.href = urlPrefix + encodeURIComponent(token);
    }
  });
}

wireTokenRedirect("#invite-token-form", "/auth/register/");
wireTokenRedirect("#reset-token-form", "/auth/reset-password/");
