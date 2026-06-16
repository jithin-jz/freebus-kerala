(function () {
  const cache = {};
  const supported = new Set(["en", "ml"]);

  function chooseLanguage(requested) {
    if (supported.has(requested)) {
      return requested;
    }
    const browser = (navigator.language || "en").slice(0, 2);
    return supported.has(browser) ? browser : "en";
  }

  async function loadMessages(lang) {
    if (cache[lang]) {
      return cache[lang];
    }
    const response = await fetch(`/static/locales/${lang}.json`);
    if (!response.ok) {
      throw new Error(`Missing locale: ${lang}`);
    }
    cache[lang] = await response.json();
    return cache[lang];
  }

  async function applyLanguage(lang) {
    const chosen = chooseLanguage(lang);
    const messages = await loadMessages(chosen);
    window.PBF_I18N = messages;
    document.documentElement.lang = chosen;
    document.querySelectorAll("[data-i18n]").forEach((node) => {
      const key = node.getAttribute("data-i18n");
      if (messages[key]) {
        node.textContent = messages[key];
      }
    });
    document.querySelectorAll("[data-lang]").forEach((button) => {
      button.setAttribute("aria-pressed", button.getAttribute("data-lang") === chosen ? "true" : "false");
    });
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-lang]");
    if (button) {
      applyLanguage(button.getAttribute("data-lang")).catch(() => {});
    }
  });

  const initial = new URLSearchParams(window.location.search).get("lang");
  applyLanguage(initial).catch(() => {});
})();

