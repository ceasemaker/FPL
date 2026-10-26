// Shared sidebar for the mockups. The page sets <body data-page="players">.
(function () {
  const icon = (d) => `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
  const groups = [
    { links: [
      ["home", "Home", '<path d="M3.5 9.2L10 3.5l6.5 5.7"/><path d="M5 8v8.5h3.5v-4.5h3v4.5H15V8"/>'],
      ["matches", "Matches", '<circle cx="10" cy="10" r="6.5"/><path d="M10 6.2l2.6 1.9-1 3.1H8.4l-1-3.1z"/>'],
      ["teams", "Teams", '<path d="M10 3l5.5 2v4.6c0 3.4-2.3 5.9-5.5 7.4-3.2-1.5-5.5-4-5.5-7.4V5z"/><path d="M10 6.5v7"/>'],
      ["players", "Players", '<circle cx="10" cy="6.5" r="3"/><path d="M4.5 16.5c.6-3 2.9-4.8 5.5-4.8s4.9 1.8 5.5 4.8"/>', "players.html"],
      ["chart-lab", "Chart Lab", '<path d="M3.5 16.5h13M3.5 16.5V3.5"/><circle cx="7.5" cy="12" r="1.2"/><circle cx="11" cy="8" r="1.2"/><circle cx="14.5" cy="10.5" r="1.2"/>'],
    ] },
    { title: "My FPL", links: [
      ["planner", "Transfer planner", '<rect x="3.5" y="4.5" width="13" height="12" rx="2"/><path d="M3.5 8.5h13M7 3v3M13 3v3"/><path d="M7 12.2h3.5m0 0-1.6-1.5m1.6 1.5-1.6 1.5"/>', "planner.html"],
      ["watchlist", "Watchlist", '<path d="M6 3.5h8v13l-4-3-4 3z"/>'],
      ["rate", "Rate my team", '<path d="M10 3.5l1.9 4 4.4.5-3.3 3 .9 4.3L10 13.1l-3.9 2.2.9-4.3-3.3-3 4.4-.5z"/>'],
      ["decision", "Decision Lab", '<path d="M7.5 3.5h5M8.5 3.5v4.2l-4.3 7.2a1.1 1.1 0 001 1.6h9.6a1.1 1.1 0 001-1.6l-4.3-7.2V3.5"/>'],
      ["analyse", "Analyse Manager", '<circle cx="8.5" cy="8.5" r="4.5"/><path d="M12 12l4.5 4.5"/>'],
      ["price", "Price Monitor", '<path d="M3.5 14l4-4.5 3 2.5 5.5-6"/><path d="M12.5 6h3.5v3.5"/>'],
    ] },
    { title: "Data rooms", links: [
      ["stats", "Stats Explorer", '<rect x="3" y="3.5" width="14" height="13" rx="2"/><path d="M3 7.5h14M7.5 7.5v9M3 12h14"/>'],
      ["defcon", "DEFCON", '<path d="M10 3l6 2.2v4.3c0 3.6-2.4 6.2-6 7.5-3.6-1.3-6-3.9-6-7.5V5.2z"/><path d="M7.2 10.2l2 2 3.8-4"/>'],
      ["model", "Model Lab", '<path d="M3.5 14.5a6.5 6.5 0 0113 0"/><path d="M10 14.5l3-4.5"/><path d="M3.5 17h13"/>'],
    ] },
  ];
  const page = document.body.dataset.page;
  const html = groups.map((g) => `<div class="nav-group" role="group" aria-label="${g.title ?? "Sections"}">${g.title ? `<h2>${g.title}</h2>` : ""}${g.links.map(([key, label, d, href]) =>
    `<a href="${href ?? "#"}"${key === page ? ' aria-current="page"' : ""}>${icon(d)}<span>${label}</span></a>`).join("")}</div>`).join("");
  const nav = document.createElement("nav");
  nav.className = "nav";
  nav.setAttribute("aria-label", "Primary navigation");
  nav.innerHTML = `<a class="brand" href="#">AeroFPL</a>${html}<button class="menu-button" type="button" aria-label="Open menu"><svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M3 6h12M3 12h12"/></svg></button>`;
  document.body.prepend(nav);
})();
