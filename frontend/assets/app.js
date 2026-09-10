/* Role-aware dashboard. Loaded by app.html. */
(function () {
const { api, session, getLocation, logout } = window.FW;

if (!session.token) { location.href = "login.html"; return; }

const root = document.getElementById("root");
document.getElementById("logout").onclick = logout;

// ---------- small helpers ----------
const h = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; };
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt = (d) => d ? new Date(d).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "—";
const dist = (d) => d.distance_km != null ? `${d.distance_km} km away` : "";

function notice(msg, kind = "err") {
  const n = h(`<div class="notice ${kind}">${esc(msg)}</div>`);
  root.prepend(n);
  setTimeout(() => n.remove(), 5000);
}

async function run(btn, fn) {
  const label = btn.textContent;
  btn.disabled = true; btn.textContent = "…";
  try { await fn(); }
  catch (e) { notice(e.message); }
  finally { btn.disabled = false; btn.textContent = label; }
}

function donationCard(d, actionsHtml = "") {
  const parties = [
    d.restaurant && `From: ${esc(d.restaurant.name)}${d.restaurant.phone ? " · " + esc(d.restaurant.phone) : ""}`,
    d.ngo && `NGO: ${esc(d.ngo.name)}`,
    d.delivery_partner && `Delivery: ${esc(d.delivery_partner.name)}`,
  ].filter(Boolean).map((p) => `<div class="row"><span>${p}</span></div>`).join("");
  const events = (d.events || []).map((e) => `<li><span>${esc(e.status)}${e.note ? " — " + esc(e.note) : ""}</span><span>${fmt(e.created_at)}</span></li>`).join("");
  return h(`
    <div class="card" data-id="${d.id}">
      <div class="row" style="align-items:flex-start">
        <h3>${esc(d.food_name)}</h3>
        <span class="status ${d.status}">${d.status.replace("_", " ")}</span>
      </div>
      <div class="meta">${[d.meal_type, d.category, d.quantity].filter(Boolean).map(esc).join(" · ")}</div>
      ${d.notes ? `<div class="meta">“${esc(d.notes)}”</div>` : ""}
      <div class="row"><span>📍 ${esc(d.pickup_address)}${d.city ? ", " + esc(d.city) : ""}</span><span>${dist(d)}</span></div>
      ${d.best_before ? `<div class="row"><span>Best before</span><span>${fmt(d.best_before)}</span></div>` : ""}
      ${parties}
      ${actionsHtml ? `<div class="actions">${actionsHtml}</div>` : ""}
      ${events ? `<ul class="timeline">${events}</ul>` : ""}
    </div>`);
}

function tabs(items, initial) {
  const bar = h(`<div class="tabs">${items.map((t, i) => `<button data-k="${t.key}" class="${i === 0 ? "active" : ""}">${t.label}</button>`).join("")}</div>`);
  const panel = h(`<div></div>`);
  const render = (key) => {
    [...bar.children].forEach((b) => b.classList.toggle("active", b.dataset.k === key));
    panel.innerHTML = "<p class='empty'>Loading…</p>";
    items.find((t) => t.key === key).render(panel);
  };
  bar.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) render(b.dataset.k); });
  setTimeout(() => render(initial || items[0].key), 0);
  const frag = document.createDocumentFragment();
  frag.append(bar, panel);
  return frag;
}

function list(target, rows, makeCard) {
  target.innerHTML = "";
  if (!rows.length) { target.append(h(`<p class="empty">Nothing here yet.</p>`)); return; }
  const grid = h(`<div class="grid cards"></div>`);
  rows.forEach((r) => grid.append(makeCard(r)));
  target.append(grid);
}

// ---------- header ----------
const u = session.user;
document.getElementById("role-pill").textContent = u.role;
document.getElementById("who").textContent = u.name;

const DASHBOARDS = { restaurant: restaurantView, ngo: ngoView, delivery: deliveryView, admin: adminView };
(DASHBOARDS[u.role] || (() => notice("Unknown role")))();

// =====================================================================
// RESTAURANT
// =====================================================================
function restaurantView() {
  root.innerHTML = `<h1 class="page-title">Restaurant dashboard</h1>
    <p class="page-sub">Post leftover food — nearby NGOs will claim it and a delivery partner brings it to them.</p>`;
  root.append(tabs([
    { key: "new", label: "Post food", render: renderNewDonation },
    { key: "mine", label: "My donations", render: renderMyDonations },
  ]));
}

function renderNewDonation(panel) {
  const f = h(`
    <form class="stack">
      <div><label>Food name</label><input name="food_name" required /></div>
      <div class="field-row">
        <div><label>Meal type</label><select name="meal_type"><option value="">—</option><option>veg</option><option>non-veg</option></select></div>
        <div><label>Category</label><select name="category"><option value="">—</option><option>raw-food</option><option>cooked-food</option><option>packed-food</option></select></div>
      </div>
      <div><label>Quantity</label><input name="quantity" placeholder="e.g. 40 people / 5 kg" /></div>
      <div><label>Notes (optional)</label><textarea name="notes"></textarea></div>
      <div class="field-row">
        <div><label>Contact name</label><input name="contact_name" value="${esc(u.name)}" /></div>
        <div><label>Contact phone</label><input name="contact_phone" value="${esc(u.phone || "")}" /></div>
      </div>
      <div><label>Pickup address</label><input name="pickup_address" value="${esc(u.address || "")}" required /></div>
      <div class="field-row">
        <div><label>City</label><input name="city" value="${esc(u.city || "")}" /></div>
        <div><label>Best before (optional)</label><input type="datetime-local" name="best_before" /></div>
      </div>
      <div class="field-row">
        <div><label>Latitude</label><input type="number" step="any" name="lat" value="${u.lat ?? ""}" required /></div>
        <div><label>Longitude</label><input type="number" step="any" name="lng" value="${u.lng ?? ""}" required /></div>
      </div>
      <button type="button" class="btn ghost sm" id="loc">📍 Use my current location</button>
      <button class="btn" type="submit">Post donation</button>
    </form>`);
  f.querySelector("#loc").onclick = (e) => run(e.target, async () => {
    const loc = await getLocation();
    if (!loc) throw new Error("Couldn't get location");
    f.lat.value = loc.lat; f.lng.value = loc.lng;
  });
  f.onsubmit = async (e) => {
    e.preventDefault();
    const body = {};
    for (const [k, v] of new FormData(f)) {
      if (v === "") continue;
      body[k] = (k === "lat" || k === "lng") ? Number(v) : v;
    }
    if (body.best_before) body.best_before = new Date(body.best_before).toISOString();
    try {
      await api.post("/api/donations", body);
      notice("Donation posted.", "ok");
      f.reset();
    } catch (err) { notice(err.message); }
  };
  panel.innerHTML = ""; panel.append(f);
}

async function renderMyDonations(panel) {
  const rows = await api.get("/api/donations/mine");
  list(panel, rows, (d) => {
    const canCancel = ["available", "claimed", "assigned"].includes(d.status);
    const card = donationCard(d, canCancel ? `<button class="btn danger sm" data-act="cancel">Cancel</button>` : "");
    const btn = card.querySelector('[data-act="cancel"]');
    if (btn) btn.onclick = () => run(btn, async () => {
      await api.post(`/api/donations/${d.id}/cancel`);
      renderMyDonations(panel);
    });
    return card;
  });
}

// =====================================================================
// NGO
// =====================================================================
function ngoView() {
  root.innerHTML = `<h1 class="page-title">NGO dashboard</h1>
    <p class="page-sub">Browse leftover food near you and claim it for the people you serve.</p>`;
  root.append(tabs([
    { key: "avail", label: "Available near me", render: renderAvailable },
    { key: "claims", label: "My claims", render: renderClaims },
  ]));
}

async function renderAvailable(panel) {
  panel.innerHTML = "";
  const controls = h(`<form class="stack" style="max-width:none;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));display:grid">
      <div><label>Latitude</label><input name="lat" type="number" step="any" value="${u.lat ?? ""}" /></div>
      <div><label>Longitude</label><input name="lng" type="number" step="any" value="${u.lng ?? ""}" /></div>
      <div><label>Radius (km)</label><input name="radius_km" type="number" value="25" /></div>
      <div style="display:flex;align-items:flex-end;gap:8px">
        <button class="btn" type="submit">Search</button>
        <button class="btn ghost" type="button" id="here">📍</button>
      </div>
    </form>`);
  const out = h(`<div></div>`);
  panel.append(controls, out);
  controls.querySelector("#here").onclick = (e) => run(e.target, async () => {
    const loc = await getLocation(); if (!loc) throw new Error("no location");
    controls.lat.value = loc.lat; controls.lng.value = loc.lng;
  });
  const search = async () => {
    out.innerHTML = "<p class='empty'>Loading…</p>";
    const q = new URLSearchParams();
    for (const [k, v] of new FormData(controls)) if (v !== "") q.set(k, v);
    try {
      const rows = await api.get(`/api/ngo/donations/available?${q}`);
      list(out, rows, (d) => {
        const card = donationCard(d, `<button class="btn sm" data-act="claim">Claim</button>`);
        const b = card.querySelector('[data-act="claim"]');
        b.onclick = () => run(b, async () => {
          const res = await api.post(`/api/ngo/donations/${d.id}/claim`);
          notice(res.delivery_partner
            ? `Claimed. ${res.delivery_partner.name} is assigned to deliver.`
            : "Claimed. Waiting for a delivery partner to pick it up.", "ok");
          search();
        });
        return card;
      });
    } catch (e) { out.innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  };
  controls.onsubmit = (e) => { e.preventDefault(); search(); };
  search();
}

async function renderClaims(panel) {
  const rows = await api.get("/api/ngo/donations/claimed");
  list(panel, rows, (d) => {
    let acts = "";
    if (["assigned", "picked_up", "claimed"].includes(d.status)) acts += `<button class="btn sm" data-act="rcv">Confirm received</button>`;
    if (["claimed", "assigned"].includes(d.status)) acts += `<button class="btn ghost sm" data-act="rel">Release</button>`;
    const card = donationCard(d, acts);
    const rcv = card.querySelector('[data-act="rcv"]');
    const rel = card.querySelector('[data-act="rel"]');
    if (rcv) rcv.onclick = () => run(rcv, async () => { await api.post(`/api/ngo/donations/${d.id}/confirm-received`); renderClaims(panel); });
    if (rel) rel.onclick = () => run(rel, async () => { await api.post(`/api/ngo/donations/${d.id}/release`); renderClaims(panel); });
    return card;
  });
}

// =====================================================================
// DELIVERY
// =====================================================================
function deliveryView() {
  root.innerHTML = `<h1 class="page-title">Delivery dashboard</h1>
    <p class="page-sub">Go on shift to get auto-assigned the nearest pickups, or grab jobs from the pool.</p>`;
  const av = h(`<div class="card" style="margin-bottom:20px">
      <div class="row"><h3>Shift status</h3>
        <label style="display:flex;gap:8px;align-items:center;font-weight:600">
          <input type="checkbox" id="avail" style="width:auto" ${u.is_available ? "checked" : ""}/> Available
        </label>
      </div>
      <div class="meta">Location: <span id="loc-txt">${u.lat != null ? `${u.lat}, ${u.lng}` : "not set"}</span></div>
      <div class="actions"><button class="btn ghost sm" id="upd-loc">📍 Update my location</button></div>
    </div>`);
  root.append(av);
  const save = async (extra) => {
    const body = { is_available: av.querySelector("#avail").checked, ...extra };
    const me = await api.patch("/api/delivery/availability", body);
    session.patchUser(me);
    av.querySelector("#loc-txt").textContent = me.lat != null ? `${me.lat}, ${me.lng}` : "not set";
  };
  av.querySelector("#avail").onchange = (e) => run(e.target, () => save({}));
  av.querySelector("#upd-loc").onclick = (e) => run(e.target, async () => {
    const loc = await getLocation(); if (!loc) throw new Error("no location");
    await save(loc); notice("Location updated.", "ok");
  });

  root.append(tabs([
    { key: "tasks", label: "My tasks", render: renderTasks },
    { key: "pool", label: "Open pool", render: renderPool },
  ]));
}

async function renderTasks(panel) {
  const rows = await api.get("/api/delivery/tasks?active_only=false");
  list(panel, rows, (d) => {
    let acts = "";
    if (d.status === "assigned") acts = `<button class="btn sm" data-act="pickup">Mark picked up</button><button class="btn ghost sm" data-act="decline">Decline</button>`;
    else if (d.status === "picked_up") acts = `<button class="btn sm" data-act="deliver">Mark delivered</button>`;
    const card = donationCard(d, acts);
    card.querySelectorAll("[data-act]").forEach((b) => {
      b.onclick = () => run(b, async () => {
        await api.post(`/api/delivery/donations/${d.id}/${b.dataset.act}`);
        renderTasks(panel);
      });
    });
    return card;
  });
}

async function renderPool(panel) {
  const q = u.lat != null ? "" : "";
  try {
    const rows = await api.get(`/api/delivery/pool${q}`);
    list(panel, rows, (d) => {
      const card = donationCard(d, `<button class="btn sm" data-act="accept">Accept job</button>`);
      const b = card.querySelector("[data-act]");
      b.onclick = () => run(b, async () => { await api.post(`/api/delivery/donations/${d.id}/accept`); renderPool(panel); });
      return card;
    });
  } catch (e) {
    panel.innerHTML = `<p class="empty">${esc(e.message)}<br/>Set your location above to see the pool.</p>`;
  }
}

// =====================================================================
// ADMIN
// =====================================================================
async function adminView() {
  root.innerHTML = `<h1 class="page-title">Admin</h1><p class="page-sub">Oversee donations, accounts and feedback.</p>`;
  try {
    const s = await api.get("/api/admin/stats");
    const grid = h(`<div class="stat-grid"></div>`);
    Object.entries(s.users).forEach(([k, n]) => grid.append(h(`<div class="stat"><div class="n">${n}</div><div class="l">${k}s</div></div>`)));
    Object.entries(s.donations).forEach(([k, n]) => grid.append(h(`<div class="stat"><div class="n">${n}</div><div class="l">${k.replace("_", " ")}</div></div>`)));
    grid.append(h(`<div class="stat"><div class="n">${s.feedback_count}</div><div class="l">feedback</div></div>`));
    root.append(grid);
  } catch (e) { notice(e.message); }

  root.append(tabs([
    { key: "don", label: "Donations", render: renderAdminDonations },
    { key: "usr", label: "Users", render: renderAdminUsers },
    { key: "fb", label: "Feedback", render: renderAdminFeedback },
  ]));
}

async function renderAdminDonations(panel) {
  panel.innerHTML = "";
  const bar = h(`<div style="margin-bottom:14px">
    <select id="st"><option value="">All statuses</option>
      ${["available", "claimed", "assigned", "picked_up", "delivered", "cancelled", "expired"].map((s) => `<option>${s}</option>`).join("")}
    </select></div>`);
  const out = h(`<div></div>`);
  panel.append(bar, out);
  const load = async () => {
    out.innerHTML = "<p class='empty'>Loading…</p>";
    const st = bar.querySelector("#st").value;
    const rows = await api.get(`/api/admin/donations${st ? `?status=${st}` : ""}`);
    list(out, rows, (d) => {
      let acts = "";
      if (["claimed", "assigned"].includes(d.status)) acts = `<button class="btn sm" data-act="assign">Assign nearest delivery</button>`;
      const card = donationCard(d, acts);
      const b = card.querySelector("[data-act]");
      if (b) b.onclick = () => run(b, async () => {
        const near = await api.get(`/api/admin/donations/${d.id}/nearest-delivery`);
        if (!near) throw new Error("No delivery partner available nearby");
        if (!confirm(`Assign ${near.name} (${near.vehicle_type || "—"})?`)) return;
        await api.post(`/api/admin/donations/${d.id}/assign/${near.id}`);
        load();
      });
      return card;
    });
  };
  bar.querySelector("#st").onchange = load;
  load();
}

async function renderAdminUsers(panel) {
  const rows = await api.get("/api/admin/users");
  panel.innerHTML = "";
  const grid = h(`<div class="grid cards"></div>`);
  rows.forEach((usr) => {
    const card = h(`<div class="card">
      <div class="row"><h3>${esc(usr.name)}</h3><span class="pill">${usr.role}</span></div>
      <div class="meta">${esc(usr.email)}${usr.phone ? " · " + esc(usr.phone) : ""}</div>
      <div class="meta">${esc(usr.city || "")} ${usr.lat != null ? "· located" : "· no location"}</div>
      <div class="actions">
        <button class="btn ghost sm" data-act="approve">${usr.is_approved ? "Un-approve" : "Approve"}</button>
        <button class="btn ${usr.is_active ? "danger" : ""} sm" data-act="active">${usr.is_active ? "Deactivate" : "Reactivate"}</button>
      </div>
    </div>`);
    card.querySelector('[data-act="approve"]').onclick = (e) => run(e.target, async () => {
      await api.patch(`/api/admin/users/${usr.id}`, { is_approved: !usr.is_approved });
      renderAdminUsers(panel);
    });
    card.querySelector('[data-act="active"]').onclick = (e) => run(e.target, async () => {
      await api.patch(`/api/admin/users/${usr.id}`, { is_active: !usr.is_active });
      renderAdminUsers(panel);
    });
    grid.append(card);
  });
  panel.append(grid);
}

async function renderAdminFeedback(panel) {
  const rows = await api.get("/api/feedback");
  list(panel, rows, (fb) => h(`<div class="card">
    <div class="row"><h3>${esc(fb.name || "Anonymous")}</h3><span class="meta">${fmt(fb.created_at)}</span></div>
    <div class="meta">${esc(fb.email || "")}</div>
    <p style="margin-top:8px">${esc(fb.message)}</p>
  </div>`));
}
})();
