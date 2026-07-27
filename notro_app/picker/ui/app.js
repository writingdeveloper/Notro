/* Notro Picker UI. pywebview 부재 시(mock) 브라우저 단독 미리보기 지원. */
const $ = (s) => document.querySelector(s);
const state = { items: [], recent: [], folders: [], collections: [], strings: {}, tab: "emoji", query: "", collection: "__all__", captureCollection: "__notro_captures__", autoCaptureSave: false, pasteSizes: {}, pasteSizeChoices: [0, 32, 48, 64, 96, 128, 160], cursor: -1 };

/* 붙여넣기 크기를 고를 수 있는 탭 (백엔드 resize.TARGETS와 같은 순서) */
const SIZE_TABS = ["emoji", "sticker", "gif"];

const str = (k) => state.strings[k] || k;
const api = () => window.pywebview && window.pywebview.api;

/* ---------- 데이터 ---------- */
async function refresh() {
  if (!api()) { mock(); applyStrings(); renderRail(); render(); renderFolders(); renderSizes(); return; }
  const s = await api().get_state();
  Object.assign(state, { items: s.items, recent: s.recent, folders: s.folders, collections: s.collections || [], strings: s.strings, captureCollection: s.capture_collection || "__notro_captures__", autoCaptureSave: !!s.auto_capture_save, pasteSizes: s.paste_sizes || {}, pasteSizeChoices: (s.paste_size_choices && s.paste_size_choices.length) ? s.paste_size_choices : state.pasteSizeChoices });
  applyStrings(); renderRail(); render(); renderFolders(); renderSizes();
}

function mock() {
  const sq = (c) => "data:image/svg+xml," + encodeURIComponent(
    `<svg xmlns='http://www.w3.org/2000/svg' width='64' height='64'><rect width='64' height='64' rx='12' fill='${c}'/></svg>`);
  state.items = [
    { id: "1", type: "emoji", name: "miku smile", keywords: ["happy"], animated: false, url: sq("#39c5bb"), can_url: true, is_folder: false, convert_warning: false, favorite: true, collection: "miku" },
    { id: "2", type: "emoji", name: "wave", keywords: [], animated: false, url: sq("#eb459e"), can_url: true, is_folder: false, convert_warning: false, favorite: false, collection: "" },
    { id: "3", type: "emoji", name: "miku wink", keywords: [], animated: false, url: sq("#57f287"), can_url: false, is_folder: false, convert_warning: false, favorite: true, collection: "miku" },
    { id: "4", type: "sticker", name: "cat", keywords: [], animated: false, url: sq("#f9a62b"), can_url: false, is_folder: false, convert_warning: true, favorite: false, collection: "" },
    { id: "5", type: "gif", name: "dance", keywords: [], animated: true, url: sq("#5865f2"), can_url: false, is_folder: true, convert_warning: false, favorite: false, collection: "gifs" },
  ];
  state.recent = ["1"];
  state.folders = [{ path: "C:\\mock\\gifs", default_type: "gif", exists: true }];
  state.collections = [{ name: "miku", label: "miku", icon: sq("#39c5bb") }, { name: "gifs", label: "gifs", icon: null }];
  state.autoCaptureSave = false;
  state.pasteSizes = { emoji: 48, sticker: 160, gif: 0 };
  state.strings = {};
}

/* ---------- 렌더 ---------- */
function applyStrings() {
  $("#search").placeholder = str("picker_search");
  $("#btn-capture").title = str("picker_capture_add");
  $("#btn-capture").setAttribute("aria-label", str("picker_capture_add"));
  $("#btn-add").title = str("picker_add_submit");
  $("#btn-settings").title = str("picker_settings");
  document.querySelectorAll(".tab").forEach((b) => {
    b.textContent = str("picker_tab_" + b.dataset.tab);
  });
  $("#hint").textContent = str("picker_hint");
  $("#add-title").textContent = str("picker_add_title");
  $("#add-url").placeholder = str("picker_add_url_ph");
  $("#add-name").placeholder = str("picker_add_name_ph");
  $("#add-kw").placeholder = str("picker_add_kw_ph");
  $("#add-collection-label").textContent = str("picker_add_collection_ph");
  $("#add-collection").placeholder = str("picker_add_collection_new_ph");
  $("#add-note").textContent = str("picker_add_note");
  $("#add-submit").textContent = str("picker_add_submit");
  $("#add-cancel").textContent = str("picker_cancel");
  $("#st-title").textContent = str("picker_settings_title");
  $("#st-auto-capture-label").textContent = str("picker_auto_capture");
  $("#st-auto-capture-note").textContent = str("picker_auto_capture_note");
  $("#st-auto-capture").checked = state.autoCaptureSave;
  $("#st-size-subtitle").textContent = str("picker_paste_size");
  $("#st-size-note").textContent = str("picker_paste_size_note");
  $("#st-folders-subtitle").textContent = str("picker_folders_subtitle");
  $("#st-openlib").textContent = str("picker_open_library");
  $("#st-addfolder").textContent = str("picker_add_folder");
  $("#st-close").textContent = str("picker_cancel");
  $("#dropzone").textContent = str("picker_drop_hint");
}

function inCollection(i) {
  if (state.collection === "__all__") return true;
  if (state.collection === "__fav__") return i.favorite;
  return (i.collection || "") === state.collection;
}

function renderRail() {
  const rail = $("#rail");
  rail.innerHTML = "";
  const add = (key, label, title, icon) => {
    const b = document.createElement("button");
    if (icon) {
      const img = document.createElement("img");
      img.src = icon;
      b.appendChild(img);
    } else {
      b.textContent = label;
    }
    b.title = title;
    if (state.collection === key) b.classList.add("active");
    b.addEventListener("click", () => { state.collection = key; renderRail(); render(); });
    rail.appendChild(b);
  };
  add("__fav__", "★", str("picker_col_favorites"), null);
  add("__all__", "▦", str("picker_col_all"), null);
  for (const col of state.collections) {
    const label = col.label || col.name;
    add(col.name, label.slice(0, 2), label, col.icon);
  }
}

/* 한글 초성 검색 — library.matches_query()의 미러. 규칙이 갈리면 타이핑 중
   결과와 Enter 결과가 달라지므로 양쪽을 같이 고쳐야 한다. */
const CHOSEONG = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ";
function toChoseong(text) {
  let out = "";
  for (const ch of text.toLowerCase()) {
    const c = ch.codePointAt(0);
    out += (c >= 0xac00 && c <= 0xd7a3)
      ? CHOSEONG[Math.floor((c - 0xac00) / 588)] : ch;
  }
  return out;
}
function hasJamo(text) {
  return [...text].some((ch) => {
    const c = ch.codePointAt(0);
    return c >= 0x3131 && c <= 0x314e;
  });
}
function matchesQuery(q, item) {
  if (!q) return true;
  const fields = [item.name.toLowerCase(), ...item.keywords.map((k) => k.toLowerCase())];
  if (fields.some((f) => f.includes(q))) return true;
  if (!hasJamo(q)) return false;
  const cq = toChoseong(q);
  return fields.some((f) => toChoseong(f).includes(cq));
}

// 타이핑 반응성을 위한 클라이언트 미러. 정식 검색 책임은 library.search() (스펙 §3).
function filtered() {
  const q = state.query.trim().toLowerCase();
  return state.items.filter((i) => i.type === state.tab && inCollection(i) &&
    matchesQuery(q, i));
}

function render() {
  const c = $("#content");
  c.innerHTML = "";
  cells = [];          /* 키보드 커서가 훑는 셀 목록 — section()이 채운다 */
  const items = filtered();
  if (!state.query && state.collection !== "__fav__") {
    const favs = items.filter((i) => i.favorite);
    if (favs.length) c.appendChild(section(str("picker_col_favorites"), favs.slice(0, 16)));
  }
  if (!state.query) {
    const rset = new Set(state.recent);
    const rec = items.filter((i) => rset.has(i.id));
    if (rec.length) c.appendChild(section(str("picker_recent"), rec.slice(0, 16)));
  }
  if (!items.length) {
    const d = document.createElement("div");
    d.className = "empty";
    d.textContent = str("picker_empty");
    c.appendChild(d);
    setCursor(-1);
    return;
  }
  c.appendChild(section("", items));
  setCursor(cells.length ? 0 : -1, false);
}

function section(title, items) {
  const wrap = document.createElement("div");
  if (title) {
    const h = document.createElement("h4");
    h.textContent = title;
    wrap.appendChild(h);
  }
  const g = document.createElement("div");
  g.className = "grid " + state.tab;
  for (const item of items) {
    const b = document.createElement("button");
    b.className = "cell";
    b.title = item.name;
    const img = document.createElement("img");
    img.loading = "lazy";
    img.src = item.url;
    b.appendChild(img);
    if (item.convert_warning) {
      const badge = document.createElement("span");
      badge.className = "warn-badge";
      badge.textContent = "!";
      badge.title = str("picker_convert_warn");
      b.title = item.name + " — " + str("picker_convert_warn");
      b.appendChild(badge);
    }
    if (item.favorite) {
      const fb = document.createElement("span");
      fb.className = "fav-badge";
      fb.textContent = "★";
      b.appendChild(fb);
    }
    b.addEventListener("click", () => select(item, "file"));
    b.addEventListener("contextmenu", (e) => { e.preventDefault(); showCtx(e, item); });
    b.__item = item;
    cells.push(b);
    g.appendChild(b);
  }
  wrap.appendChild(g);
  return wrap;
}

function select(item, mode) {
  if (api()) api().select_item(item.id, mode);
}

/* ---------- 키보드 커서 ----------
   핫키로 연 뒤 손을 마우스로 옮기지 않고 끝낼 수 있어야 한다: 검색창에 포커스를
   둔 채 방향키로 그리드를 훑고 Enter로 보낸다 (디스코드 자체 이모지 창과 같은
   조작). 위아래는 열 수를 계산하는 대신 실제 좌표로 "윗줄/아랫줄에서 x가 가장
   가까운 칸"을 고른다 — 즐겨찾기·최근 사용 섹션이 섞여 열 수가 구간마다 달라도
   그대로 동작한다. */
let cells = [];

function setCursor(index, scroll = true) {
  const prev = cells[state.cursor];
  if (prev) prev.classList.remove("cursor");
  state.cursor = index;
  const cur = cells[index];
  if (!cur) return;
  cur.classList.add("cursor");
  if (scroll) cur.scrollIntoView({ block: "nearest" });
}

function moveCursor(dx, dy) {
  if (!cells.length) return;
  if (state.cursor < 0 || !cells[state.cursor]) { setCursor(0); return; }
  if (dx) {
    setCursor(Math.min(Math.max(state.cursor + dx, 0), cells.length - 1));
    return;
  }
  const cur = cells[state.cursor].getBoundingClientRect();
  const cx = cur.left + cur.width / 2;
  let best = -1;
  let bestScore = Infinity;
  for (let i = 0; i < cells.length; i++) {
    if (i === state.cursor) continue;
    const r = cells[i].getBoundingClientRect();
    const drow = r.top - cur.top;
    if (dy > 0 ? drow <= 1 : drow >= -1) continue;   /* 진행 방향의 줄만 본다 */
    const score = Math.abs(drow) * 10000 + Math.abs(r.left + r.width / 2 - cx);
    if (score < bestScore) { bestScore = score; best = i; }
  }
  if (best >= 0) setCursor(best);
}

function selectCursor() {
  const cur = cells[state.cursor];
  if (cur && cur.__item) select(cur.__item, "file");
}

/* ---------- 컨텍스트 메뉴 ---------- */
function showCtx(e, item) {
  const ctx = $("#ctx");
  ctx.innerHTML = "";
  const add = (label, fn, danger) => {
    const b = document.createElement("button");
    b.textContent = label;
    if (danger) b.className = "danger";
    b.addEventListener("click", () => { hideCtx(); fn(); });
    ctx.appendChild(b);
  };
  add(str("picker_ctx_file"), () => select(item, "file"));
  if (item.can_url) add(str("picker_ctx_url"), () => select(item, "url"));
  if (!item.is_folder) {
    add(item.favorite ? str("picker_ctx_unfavorite") : str("picker_ctx_favorite"),
        async () => { await api().toggle_favorite(item.id); refresh(); });
    add(str("picker_ctx_collection"), async () => {
      const shown = item.collection_label || item.collection || "";
      const name = window.prompt(str("picker_ctx_collection"), shown);
      if (name !== null) {
        const trimmed = name.trim();
        const value = item.collection === state.captureCollection && trimmed === shown
          ? state.captureCollection : trimmed;
        await api().set_collection(item.id, value);
        refresh();
      }
    });
    add(str("picker_ctx_delete"), async () => { await api().remove_item(item.id); refresh(); }, true);
  }
  ctx.classList.remove("hidden");
  const x = Math.min(e.clientX, window.innerWidth - 160);
  const y = Math.min(e.clientY, window.innerHeight - ctx.offsetHeight - 8);
  ctx.style.left = x + "px";
  ctx.style.top = y + "px";
}
function hideCtx() { $("#ctx").classList.add("hidden"); }

/* ---------- 등록 모달 ---------- */
/* 세로 바에서 실제 컬렉션을 보고 있으면 그곳을 기본 저장 위치로 쓴다.
   전체(__all__)·즐겨찾기(__fav__)는 컬렉션이 아니므로 미분류. */
function currentCollection() {
  return (state.collection === "__all__" || state.collection === "__fav__")
    ? "" : state.collection;
}

/* 저장 위치 선택: 미분류 + 기존 컬렉션 목록 + "새 컬렉션"(항상 마지막).
   "새 컬렉션"은 값이 아니라 마지막 항목인지로 판별한다 — 어떤 문자열을
   sentinel로 써도 사용자가 같은 이름의 컬렉션을 만들 수 있기 때문이다. */
function renderCollectionOptions(selected) {
  const sel = $("#add-collection-select");
  sel.innerHTML = "";
  const add = (value, label) => {
    const o = document.createElement("option");
    o.value = value;
    o.textContent = label;
    sel.appendChild(o);
  };
  add("", str("picker_col_uncategorized"));
  for (const col of state.collections) add(col.name, col.label || col.name);
  add("", str("picker_add_collection_new"));
  const at = state.collections.findIndex((c) => c.name === selected);
  sel.selectedIndex = at < 0 ? 0 : at + 1;
  syncCollectionInput();
}

function isNewCollection() {
  const sel = $("#add-collection-select");
  return sel.selectedIndex === sel.options.length - 1;
}

/* "새 컬렉션"을 골랐을 때만 이름 입력칸을 보여준다 */
function syncCollectionInput() {
  const isNew = isNewCollection();
  $("#add-collection").classList.toggle("hidden", !isNew);
  if (isNew) $("#add-collection").focus();
}

function chosenCollection() {
  return isNewCollection()
    ? $("#add-collection").value.trim()
    : $("#add-collection-select").value;
}

function openAdd() {
  $("#add-error").classList.add("hidden");
  $("#add-url").value = "";
  $("#add-name").value = "";
  $("#add-kw").value = "";
  $("#add-collection").value = "";
  renderCollectionOptions(currentCollection());
  $("#modal-add").classList.remove("hidden");
  $("#add-url").focus();
}
async function submitAdd() {
  const url = $("#add-url").value.trim();
  if (!url || !api()) return;
  const added = chosenCollection();
  const res = await api().register_url(url, $("#add-name").value.trim(),
    $("#add-kw").value.trim(), added, state.tab);
  if (res.ok) {
    $("#modal-add").classList.add("hidden");
    await refresh();
    if (added && added !== currentCollection()) {
      state.collection = added;  /* 방금 넣은 컬렉션을 바로 보여준다 */
      renderRail();
      render();
    }
  } else {
    const el = $("#add-error");
    el.textContent = str("picker_err_" + res.error);
    el.classList.remove("hidden");
  }
}

function captureErrorKey(error) {
  return ({
    no_image: "picker_capture_no_image",
    read: "picker_capture_read_error",
    register: "picker_capture_register_error",
  })[error] || "picker_capture_register_error";
}

async function addCapture() {
  if (!api()) return;
  const res = await api().register_capture();
  if (!res || !res.ok) {
    flashHint(captureErrorKey(res && res.error));
    return;
  }
  await refresh();
  state.collection = res.collection;
  renderRail();
  render();
  flashHint(res.duplicate ? "picker_capture_duplicate" : "picker_capture_saved");
}

/* ---------- 붙여넣기 크기 설정 ----------
   디스코드는 첨부를 원본 픽셀 크기로 그리므로 여기서 고른 값이 곧 상대에게
   보이는 크기다. 저장된 값이 선택지에 없으면(예전 설정) 그 값도 목록에 남겨
   조용히 다른 크기로 바뀌지 않게 한다. */
function renderSizes() {
  const box = $("#st-sizes");
  box.innerHTML = "";
  for (const type of SIZE_TABS) {
    const current = Number(state.pasteSizes[type]) || 0;
    const row = document.createElement("div");
    row.className = "size-row";
    const label = document.createElement("label");
    label.textContent = str("picker_tab_" + type);
    label.htmlFor = "st-size-" + type;
    const sel = document.createElement("select");
    sel.id = "st-size-" + type;
    const choices = state.pasteSizeChoices.includes(current)
      ? state.pasteSizeChoices : [...state.pasteSizeChoices, current];
    for (const px of choices) {
      const o = document.createElement("option");
      o.value = String(px);
      o.textContent = px ? px + " px" : str("picker_size_original");
      sel.appendChild(o);
    }
    sel.value = String(current);
    sel.addEventListener("change", async () => {
      const px = Number(sel.value);
      if (!api()) { state.pasteSizes[type] = px; return; }
      const res = await api().set_paste_size(type, px);
      const applied = res && typeof res.px === "number" ? res.px : px;
      state.pasteSizes[type] = applied;
      sel.value = String(applied);
    });
    row.appendChild(label);
    row.appendChild(sel);
    box.appendChild(row);
  }
}

/* ---------- 폴더 설정 ---------- */
function renderFolders() {
  const box = $("#st-folders");
  box.innerHTML = "";
  for (const f of state.folders) {
    const row = document.createElement("div");
    row.className = "folder-row" + (f.exists ? "" : " missing");
    const span = document.createElement("span");
    span.textContent = f.path + " (" + str("picker_tab_" + f.default_type) + ")";
    span.title = f.path;
    const del = document.createElement("button");
    del.textContent = "✕";
    del.addEventListener("click", async () => { await api().remove_folder(f.path); refresh(); });
    row.appendChild(span);
    row.appendChild(del);
    box.appendChild(row);
  }
}

/* ---------- 이벤트 배선 ---------- */
$("#search").addEventListener("input", (e) => { state.query = e.target.value; render(); });
document.querySelectorAll(".tab").forEach((b) =>
  b.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    b.classList.add("active");
    state.tab = b.dataset.tab;
    render();
  }));
$("#btn-add").addEventListener("click", openAdd);
$("#btn-capture").addEventListener("click", addCapture);
$("#add-submit").addEventListener("click", submitAdd);
$("#add-url").addEventListener("keydown", (e) => { if (e.key === "Enter") submitAdd(); });
$("#add-collection-select").addEventListener("change", syncCollectionInput);
$("#add-collection").addEventListener("keydown", (e) => { if (e.key === "Enter") submitAdd(); });
$("#add-cancel").addEventListener("click", () => $("#modal-add").classList.add("hidden"));
$("#btn-settings").addEventListener("click", () => {
  $("#st-auto-capture").checked = state.autoCaptureSave;
  $("#modal-settings").classList.remove("hidden");
});
$("#st-close").addEventListener("click", () => $("#modal-settings").classList.add("hidden"));
$("#st-auto-capture").addEventListener("change", async (e) => {
  if (!api()) return;
  state.autoCaptureSave = !!(await api().set_auto_capture_save(e.target.checked));
  e.target.checked = state.autoCaptureSave;
});
$("#st-addfolder").addEventListener("click", async () => {
  if (api()) { await api().add_folder(state.tab); refresh(); }
});
$("#st-openlib").addEventListener("click", () => { if (api()) api().open_data_dir(); });

document.addEventListener("click", (e) => { if (!$("#ctx").contains(e.target)) hideCtx(); });
/* 방향키/Enter는 검색창에 포커스가 있어도 그리드를 조작한다 (캐럿 이동보다
   이쪽이 쓸모 있다 — 검색어는 한 줄이고, 디스코드 이모지 창도 같은 규칙이다).
   Enter는 여기서만 처리한다: 검색창에도 핸들러를 두면 버블링으로 두 번 보낸다. */
const CURSOR_MOVES = {
  ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowDown: [0, 1], ArrowUp: [0, -1],
};
window.addEventListener("keydown", (e) => {
  const modal = [$("#modal-add"), $("#modal-settings")]
    .find((m) => !m.classList.contains("hidden"));
  if (e.key === "Escape") {
    if (modal) { modal.classList.add("hidden"); return; }
    if (!$("#ctx").classList.contains("hidden")) { hideCtx(); return; }
    if (api()) api().hide();
    return;
  }
  if (modal || e.ctrlKey || e.altKey || e.metaKey) return;
  const move = CURSOR_MOVES[e.key];
  if (move) { e.preventDefault(); moveCursor(move[0], move[1]); return; }
  if (e.key === "Enter") { e.preventDefault(); selectCursor(); }
});
window.addEventListener("blur", () => { if (api()) api().hide(); });

/* ---------- 드래그앤드롭 (pywebviewFullPath) ---------- */
let dragDepth = 0;
window.addEventListener("dragenter", (e) => { e.preventDefault(); dragDepth++; $("#dropzone").classList.remove("hidden"); });
window.addEventListener("dragleave", () => { if (--dragDepth <= 0) { dragDepth = 0; $("#dropzone").classList.add("hidden"); } });
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", async (e) => {
  e.preventDefault();
  dragDepth = 0;
  $("#dropzone").classList.add("hidden");
  if (!api()) return;
  const paths = [...e.dataTransfer.files].map((f) => f.pywebviewFullPath).filter(Boolean);
  if (paths.length) {
    const res = await api().register_files(paths, state.tab, currentCollection());
    await refresh();
    if (res.failed && res.count) flashHint("picker_drop_partial", res);
    else if (res.failed) flashHint("picker_drop_failed");
  }
});

/* ---------- 클립보드 이미지 붙여넣기 등록 (스펙 §5) ---------- */
let hintTimer = 0;
function flashHint(key, values) {
  const f = $("#hint");
  let message = str(key);
  for (const [name, value] of Object.entries(values || {})) {
    message = message.replaceAll("{" + name + "}", value);
  }
  f.textContent = message;
  clearTimeout(hintTimer);
  hintTimer = setTimeout(() => { f.textContent = str("picker_hint"); }, 1800);
}
window.addEventListener("paste", async (e) => {
  /* 등록 모달이 열려 있으면 URL 등 네이티브 붙여넣기를 방해하지 않는다 */
  if (!$("#modal-add").classList.contains("hidden")) return;
  if (!api()) return;
  /* MIME이 명확한 이미지만 기본 동작을 막는다. 백엔드 호출 자체는 항상 시도해
     MIME이 빠진 CF_DIB 캡처도 저장하되 텍스트 붙여넣기는 그대로 둔다. */
  const items = (e.clipboardData && e.clipboardData.items) || [];
  const hasImage = [...items].some((it) => it.type && it.type.indexOf("image/") === 0);
  if (hasImage) e.preventDefault();
  const res = await api().register_clipboard(state.tab, currentCollection());
  if (res && res.ok) await refresh();
  else if (hasImage || (res && res.error !== "no_image")) {
    flashHint(captureErrorKey(res && res.error));
  }
});

/* ---------- 표시 훅 (Python이 호출) ---------- */
window.__onShow = () => {
  state.query = "";
  $("#search").value = "";
  hideCtx();
  refresh();
  setTimeout(() => $("#search").focus(), 30);
};

if (window.pywebview) refresh();
else window.addEventListener("pywebviewready", refresh);
setTimeout(() => { if (!window.pywebview) refresh(); }, 60); /* 브라우저 mock */
