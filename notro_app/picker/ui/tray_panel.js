/* Notro tray popup — own WebView2 UI, no Discord injection or remote assets. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const pages = ["home", "settings", "about"];
  let activePage = "home";
  let busy = false;
  let popupState = null;
  let toastTimer = null;
  const api = () => window.pywebview && window.pywebview.api;

  function setText(id, value) {
    const node = $(id);
    if (node) node.textContent = value == null ? "" : String(value);
  }
  function copy() {
    return popupState && popupState.labels || {};
  }
  function word(key, fallback = "") {
    return copy()[key] || fallback;
  }
  function fillOptions(select, entries, activeValue) {
    const node = $(select);
    node.replaceChildren();
    for (const item of entries) {
      const option = document.createElement("option");
      option.value = String(item.value);
      option.textContent = String(item.label);
      node.appendChild(option);
    }
    node.value = String(activeValue);
  }
  function yes(value) { return value === true; }
  function showToast(message) {
    const node = $("toast");
    node.textContent = String(message || word("failed", "Unable to complete action."));
    node.classList.remove("hidden");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => node.classList.add("hidden"), 3400);
  }
  function showPage(next) {
    activePage = pages.includes(next) ? next : "home";
    for (const page of pages)
      $("page-" + page).classList.toggle("hidden", page !== activePage);
    const first = $("page-" + activePage);
    if (first) first.scrollTop = 0;
  }
  function render() {
    if (!popupState) return;
    const state = popupState, labels = copy(), about = state.about || {};
    document.documentElement.lang = String(state.lang_resolved || "en");
    setText("header-version", "v" + (about.version || ""));
    setText("status-pill", yes(state.monitor_enabled) ?
      word("running", "ACTIVE") : word("paused", "PAUSED"));
    $("status-pill").classList.toggle("paused", !yes(state.monitor_enabled));

    const texts = {
      "txt-picker": "picker",
      "txt-picker-note": "picker_note",
      "home-label": "quick_actions",
      "txt-toggle": yes(state.monitor_enabled) ? "pause" : "resume",
      "txt-library": "open_library",
      "txt-limit": "limit",
      "txt-settings": "settings",
      "txt-about": "about",
      "txt-quit": "quit",
      "home-footnote": "footnote",
      "back-settings": "back",
      "settings-title": "settings",
      "label-limit": "limit",
      "limit-hint": "limit_note",
      "label-hotkey": "hotkey",
      "label-language": "language",
      "txt-startup": "startup",
      "txt-auto-update": "auto_update",
      "txt-check-update": "check_update",
      "txt-restart-update": "restart_update",
      "txt-output": "open_output",
      "txt-settings-library": "open_library",
      "back-about": "back",
      "about-subtitle": "about_note",
      "about-attr-platform": "platform",
      "about-attr-engine": "engine",
      "about-attr-license": "license",
      "about-disclosure": "disclosure",
      "about-repo-label": "links",
      "txt-github": "github",
      "txt-releases": "releases",
      "txt-issues": "issues",
      "txt-license": "license_link"
    };
    for (const [element, key] of Object.entries(texts))
      setText(element, labels[key] || key);

    setText("limit-value", state.limit_mb === 1024 ? "1 GB" :
      state.limit_mb + " MB");
    setText("about-title", about.name || "Notro");
    setText("about-version", "v" + (about.version || "?"));
    $("about-quick-github").setAttribute(
      "aria-label", word("github", "GitHub repository"));
    setText("about-platform", about.platform || "");
    setText("about-engine", about.engine || "");
    setText("about-license", about.license || "");
    $("select-limit").value = String(state.limit_mb);
    fillOptions("select-hotkey", state.hotkeys || [], state.hotkey || "off");
    fillOptions("select-language", state.languages || [], state.language || "auto");
    $("toggle-startup").classList.toggle("enabled", yes(state.startup));
    $("toggle-auto-update").classList.toggle("enabled", yes(state.auto_update));
    $("btn-auto-update").classList.toggle("hidden", !yes(state.updater_present));
    $("btn-check-update").classList.toggle("hidden", !yes(state.updater_present));
    $("btn-restart-update").classList.toggle("hidden", !yes(state.update_ready));
  }
  async function refresh() {
    if (!api()) return;
    try {
      const value = await api().get_state();
      if (value && typeof value === "object") {
        popupState = value;
        render();
      }
    } catch (_) {
      showToast("Notro cannot read the tray state.");
    }
  }
  async function runAction(action, value = "") {
    if (busy || !api()) return;
    busy = true;
    try {
      const result = await api().activate(String(action), String(value));
      if (!result || !result.ok)
        showToast((result && result.error) || word("failed", "Unable to complete action."));
      if (action !== "quit" && action !== "picker" &&
          action !== "output" && action !== "library") await refresh();
    } catch (_) {
      showToast(word("failed", "Unable to complete action."));
    } finally {
      busy = false;
    }
  }
  function setPageAndRefresh(page) {
    showPage(page);
    return refresh();
  }
  for (const button of document.querySelectorAll("[data-action]")) {
    button.addEventListener("click", () => runAction(button.dataset.action));
  }
  for (const button of document.querySelectorAll("[data-nav]")) {
    button.addEventListener("click", () => setPageAndRefresh(button.dataset.nav));
  }
  for (const button of document.querySelectorAll("[data-link]")) {
    button.addEventListener("click", () => runAction("open_link", button.dataset.link));
  }
  $("select-limit").addEventListener("change", e => runAction("limit", e.target.value));
  $("select-hotkey").addEventListener("change", e => runAction("hotkey", e.target.value));
  $("select-language").addEventListener("change", e => runAction("language", e.target.value));

  document.addEventListener("keydown", e => {
    if (e.key === "Escape") {
      e.preventDefault();
      if (activePage !== "home") {
        showPage("home");
      } else if (api()) api().hide();
    }
  });
  window.addEventListener("blur", () => {
    // Clicking elsewhere closes only the custom popup. Leaving it hidden
    // must never alter the selected clipboard or send any keypresses.
    if (api()) api().hide();
  });
  // Invoked by the Python Win32 tray right-click handler after it positions
  // and shows the hidden WebView2 window. No private data in JS literals.
  window.notroPanelOpen = page => {
    showPage(page);
    return refresh();
  };
  window.addEventListener("pywebviewready", async () => {
    try {
      await api().ready();
      await refresh();
    } catch (_) {
      // The native pystray context menu still works until initialization.
    }
  }, {once: true});
})();