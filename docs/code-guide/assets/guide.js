(() => {
  document.documentElement.classList.add("js");
  const articles = [...document.querySelectorAll("main article")];
  const navigation = [...document.querySelectorAll(".nav-link")];
  const search = document.querySelector("#file-search");
  const status = document.querySelector("#search-status");
  const toc = document.querySelector("#toc");
  const menu = document.querySelector("#file-menu");
  const notice = document.querySelector("#interaction-status");
  const mobile = window.matchMedia("(max-width: 720px)");
  let current;
  search.disabled = false;
  menu.open = !mobile.matches;
  function announce(text) {
    notice.textContent = text;
  }
  function findArticle(fragment) {
    return (
      articles.find((item) => item.id === fragment) ||
      articles.find((item) =>
        [...item.querySelectorAll("[id]")].some(
          (child) => child.id === fragment,
        ),
      )
    );
  }
  function showPage(focus) {
    let fragment;
    try {
      fragment = decodeURIComponent(location.hash.slice(1));
    } catch {
      fragment = "overview";
    }
    const selected =
      fragment === "main-content"
        ? current || articles[0]
        : findArticle(fragment) || articles[0];
    const changed = current !== selected;
    current = selected;
    articles.forEach((item) => {
      item.hidden = item !== selected;
    });
    navigation.forEach((link) => {
      if (link.hash === "#" + selected.id)
        link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    document.querySelector("#breadcrumb-current").textContent =
      selected.dataset.title;
    document.querySelector("#breadcrumb-group").textContent =
      selected.dataset.group;
    document.title = selected.dataset.title + " · Fynd code guide";
    toc.replaceChildren();
    selected.querySelectorAll("h2[id], h3[id]").forEach((heading) => {
      const a = document.createElement("a");
      a.href = "#" + heading.id;
      a.textContent = heading.textContent;
      toc.append(a);
    });
    if (changed && focus) {
      search.value = "";
      filterFiles();
      if (mobile.matches) menu.open = false;
      selected.querySelector("h1").focus({ preventScroll: true });
      document.querySelector("main").scrollIntoView({ block: "start" });
    }
    if (fragment && fragment !== selected.id) {
      const target = document.getElementById(fragment);
      if (target && selected.contains(target))
        target.scrollIntoView({ block: "start" });
    }
  }
  function filterFiles() {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    navigation.forEach((link) => {
      const matches =
        !query || link.dataset.search.toLowerCase().includes(query);
      link.hidden = !matches;
      if (matches) visible++;
    });
    document.querySelectorAll(".nav-group").forEach((group) => {
      group.hidden = ![...group.querySelectorAll(".nav-link")].some(
        (link) => !link.hidden,
      );
    });
    document.querySelector("#no-results").hidden = visible > 0;
    status.textContent = query
      ? visible + (visible === 1 ? " matching page" : " matching pages")
      : "";
    if (query) menu.open = true;
  }
  search.addEventListener("input", filterFiles);
  search.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      search.value = "";
      filterFiles();
    }
    if (event.key === "Enter") {
      const first = navigation.find((link) => !link.hidden);
      if (first) {
        if (location.hash === first.hash) showPage(true);
        else location.hash = first.hash;
      }
    }
  });
  window.addEventListener("hashchange", () => showPage(true));
  mobile.addEventListener("change", () => {
    menu.open = !mobile.matches;
  });
  document.querySelectorAll(".copy").forEach((button) => {
    button.addEventListener("click", async () => {
      const snippet = button.closest("figure").querySelector("code");
      try {
        if (!navigator.clipboard || !navigator.clipboard.writeText)
          throw new Error("Clipboard unavailable");
        await navigator.clipboard.writeText(snippet.textContent);
        button.textContent = "Copied";
        announce("Example copied.");
      } catch {
        const range = document.createRange();
        range.selectNodeContents(snippet);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        button.textContent = "Selected";
        announce("Example selected. Use your browser’s copy command.");
      }
      setTimeout(() => {
        button.textContent = "Copy";
      }, 1800);
    });
  });
  showPage(false);
})();
