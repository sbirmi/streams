(() => {
  "use strict";

  const validViews = new Set(["priority", "recent", "manual", "stale"]);
  const dashboardMode = window.location.pathname === "/dashboard";
  const urlState = { hasRoot: false, hasView: false, hasFocus: false, root: null, view: null, focus: null };
  function readUrlState(url = new URL(window.location.href)) {
    const params = url.searchParams;
    urlState.hasRoot = params.has("root"); urlState.hasView = params.has("view"); urlState.hasFocus = params.has("focus");
    urlState.root = params.get("root"); urlState.view = validViews.has(params.get("view")) ? params.get("view") : null; urlState.focus = params.get("focus");
  }
  readUrlState();
  const state = { bundle: null, streams: [], selected: null, selectedIds: [], selecting: false, selectionReady: false, moveMode: null, rootPath: [], focusColumn: "stream", commentIndex: 0, commentId: null, view: urlState.view || "priority", query: "", pendingCommand: [], editing: null, editingPlacement: null, commentEditing: null, deleteTarget: null, shortcuts: {}, presentationLoaded: false, dashboard: dashboardMode };
  const list = document.querySelector("#stream-list");
  const search = document.querySelector("#search");
  const username = document.querySelector("#username");
  const editorDialog = document.querySelector("#editor-dialog");
  const commentDialog = document.querySelector("#comment-dialog");
  const deleteDialog = document.querySelector("#delete-dialog");
  const shortcutsDialog = document.querySelector("#shortcuts-dialog");
  const shortcutList = document.querySelector("#shortcut-list");
  const commandHud = document.querySelector("#command-hud");

  function presentationKey() { return `streams:p:${state.bundle?.id || "bundle"}:${currentRootId() || "index"}`; }
  function readPresentation() { try { return JSON.parse(localStorage.getItem(presentationKey()) || "{}"); } catch (_) { return {}; } }
  function writePresentation() {
    try {
      const expanded = Object.fromEntries(state.streams.map((stream) => [stream.id, stream.expanded !== false]));
      localStorage.setItem(presentationKey(), JSON.stringify({ expanded, selected: state.selected, focusColumn: state.focusColumn, commentId: selectedComment()?.id || null }));
    } catch (_) { /* localStorage may be unavailable in private or restricted contexts. */ }
  }
  function focusParam() {
    const comment = selectedComment();
    return state.focusColumn === "comments" && comment ? `comment:${comment.id}` : state.selected ? `stream:${state.selected}` : null;
  }
  function updateUrl(historyMode = "replace") {
    const url = new URL(window.location.href);
    url.searchParams.delete("root"); url.searchParams.delete("view"); url.searchParams.delete("focus");
    if (state.dashboard) {
      const focus = state.selected ? `stream:${state.selected}` : null;
      if (focus) url.searchParams.set("focus", focus);
      const dashboardCanonical = `${url.pathname}?${url.searchParams.toString()}${url.hash}`;
      window.history[`${historyMode}State`](null, "", dashboardCanonical);
      readUrlState(new URL(window.location.href));
      return;
    }
    const rootId = currentRootId();
    if (rootId) url.searchParams.set("root", rootId);
    url.searchParams.set("view", state.view);
    const focus = focusParam();
    if (focus) url.searchParams.set("focus", focus);
    const canonical = `${url.pathname}?${url.searchParams.toString()}${url.hash}`;
    window.history[`${historyMode}State`](null, "", canonical);
    readUrlState(new URL(window.location.href));
  }
  function savePresentationAndUrl(historyMode = "replace") { writePresentation(); updateUrl(historyMode); }
  function applyPresentation(allowSavedFocus = false) {
    const saved = readPresentation();
    const expanded = saved.expanded || {};
    state.streams.forEach((stream) => { if (typeof expanded[stream.id] === "boolean") stream.expanded = expanded[stream.id]; });
    if ((allowSavedFocus || !urlState.hasFocus) && saved.selected && currentRootItems().some((stream) => stream.id === saved.selected)) {
      state.selected = saved.selected;
      state.focusColumn = "stream";
      state.commentIndex = 0;
      state.commentId = null;
      if (saved.focusColumn === "comments" && saved.commentId) {
        const stream = selectedStream();
        const index = stream?.comments?.findIndex((comment) => comment.id === saved.commentId) ?? -1;
        if (index >= 0) { state.focusColumn = "comments"; state.commentIndex = index; state.commentId = saved.commentId; }
      }
    }
    ensureFocusedTargetVisible();
    state.presentationLoaded = true;
  }
  function ensureFocusedTargetVisible() {
    const rootItems = currentRootItems();
    if (!state.selected || !rootItems.some((stream) => stream.id === state.selected)) state.selected = currentRootId() || rootItems[0]?.id || null;
    let stream = selectedStream();
    const seen = new Set();
    while (stream?.parent_stream_id && !seen.has(stream.parent_stream_id)) {
      seen.add(stream.parent_stream_id);
      const parent = selectedStreamById(stream.parent_stream_id);
      if (!parent) break;
      parent.expanded = true;
      stream = parent;
    }
  }
  function applyUrlState() {
    const root = urlState.root && selectedStreamById(urlState.root);
    state.rootPath = root ? [root.id] : [];
    const rootItems = currentRootItems();
    if (!state.selected || !rootItems.some((stream) => stream.id === state.selected)) state.selected = rootItems[0]?.id || null;
    state.focusColumn = "stream"; state.commentIndex = 0; state.commentId = null;
    if (!urlState.hasFocus) return;
    const focus = urlState.focus || "";
    const [type, id] = focus.split(":", 2);
    if (type === "stream" && currentRootItems().some((stream) => stream.id === id)) { state.selected = id; state.focusColumn = "stream"; state.commentIndex = 0; state.commentId = null; ensureFocusedTargetVisible(); return; }
    if (type === "comment") {
      const stream = currentRootItems().find((item) => (item.comments || []).some((comment) => comment.id === id));
      const index = stream?.comments?.findIndex((comment) => comment.id === id) ?? -1;
      if (stream && index >= 0) { state.selected = stream.id; state.focusColumn = "comments"; state.commentIndex = index; state.commentId = id; }
    }
    ensureFocusedTargetVisible();
  }

  async function api(path, options = {}) {
    const response = await fetch(path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) { const error = new Error(body.message || body.error || `Request failed (${response.status})`); error.status = response.status; error.body = body; throw error; }
    return body;
  }
  function actor() { return username.value.trim() || "anonymous"; }
  function loadUsername() { const cookie = document.cookie.split("; ").find((item) => item.startsWith("stream_username=")); if (cookie) username.value = decodeURIComponent(cookie.slice("stream_username=".length)); }
  function saveUsername() { const value = username.value.trim(); document.cookie = value ? `stream_username=${encodeURIComponent(value)}; Max-Age=31536000; Path=/; SameSite=Lax` : "stream_username=; Max-Age=0; Path=/; SameSite=Lax"; }
  function escapeHtml(value) { return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char])); }
  function markdown(value) { return escapeHtml(value).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/`(.+?)`/g, "<code>$1</code>").replace(/\n/g, "<br>"); }
  function displayDeadline(value) { return value ? String(value).slice(0, 10) : ""; }
  function childrenOf(id, items = state.streams) { return items.filter((stream) => stream.parent_stream_id === id); }
  function selectedStreamById(id) { return state.streams.find((stream) => stream.id === id); }
  function currentRootId() { return state.rootPath[state.rootPath.length - 1] || null; }
  function descendantsOf(id) { const result = []; function visit(parentId) { childrenOf(parentId).forEach((child) => { result.push(child); visit(child.id); }); } visit(id); return result; }
  function currentRootItems() { const rootId = currentRootId(); return rootId ? [selectedStreamById(rootId), ...descendantsOf(rootId)].filter(Boolean) : state.streams; }
  function favoriteStreams() {
    return state.streams.filter((stream) => stream.favorite).sort((a, b) => Number(Boolean(a.closed_at)) - Number(Boolean(b.closed_at)) || b.updated_at.localeCompare(a.updated_at) || a.id.localeCompare(b.id));
  }
  function streamPath(stream) {
    const path = []; const seen = new Set(); let current = stream;
    while (current && !seen.has(current.id)) { path.unshift(current); seen.add(current.id); current = selectedStreamById(current.parent_stream_id); }
    return path;
  }
  function ordered(items) {
    return [...items].sort((a, b) => {
      if (state.view === "recent") return b.updated_at.localeCompare(a.updated_at) || a.id.localeCompare(b.id);
      if (state.view === "manual") return (a.order_key - b.order_key) || a.id.localeCompare(b.id);
      if (state.view === "stale") return Number(Boolean(a.closed_at)) - Number(Boolean(b.closed_at)) || a.updated_at.localeCompare(b.updated_at) || a.id.localeCompare(b.id);
      const aPriority = a.priority == null ? Number.MAX_SAFE_INTEGER : a.priority;
      const bPriority = b.priority == null ? Number.MAX_SAFE_INTEGER : b.priority;
      return Number(Boolean(a.closed_at)) - Number(Boolean(b.closed_at)) || aPriority - bPriority || b.updated_at.localeCompare(a.updated_at) || a.id.localeCompare(b.id);
    });
  }
  function visibleItems() {
    const query = state.query.toLowerCase();
    return currentRootItems().filter((stream) => !query || [stream.summary, stream.description, ...(stream.tags || []), ...(stream.owners || [])].some((value) => String(value).toLowerCase().includes(query)));
  }
  function navigationItems() {
    const items = visibleItems(); const result = [];
    function visit(stream) { result.push(stream); if (stream.expanded !== false) ordered(childrenOf(stream.id, items)).forEach(visit); }
    const rootId = currentRootId();
    ordered(rootId ? items.filter((stream) => stream.id === rootId) : items.filter((stream) => !stream.parent_stream_id)).forEach(visit); return result;
  }
  function navigationEntries() {
    const items = visibleItems(); const result = [];
    function visit(stream, depth) { result.push({ stream, depth }); if (stream.expanded !== false) ordered(childrenOf(stream.id, items)).forEach((child) => visit(child, depth + 1)); }
    const rootId = currentRootId();
    ordered(rootId ? items.filter((stream) => stream.id === rootId) : items.filter((stream) => !stream.parent_stream_id)).forEach((stream) => visit(stream, 0));
    return result;
  }
  function renderComment(comment, index) { return `<article class="comment-card ${state.focusColumn === "comments" && index === state.commentIndex && state.selected === comment.stream_id ? "is-focused" : ""}" data-comment-index="${index}" tabindex="-1"><div class="comment-meta"><strong>${escapeHtml(comment.creator)}</strong><span>${escapeHtml(comment.updated_at)}</span><button class="comment-edit" type="button" data-edit-comment="${comment.id}" aria-label="Edit comment" title="Edit comment">✎</button></div><div class="comment-body">${markdown(comment.body)}</div></article>`; }
  function renderPlaceholder(depth) { return `<article class="stream-row is-placeholder" style="--depth:${depth}" aria-label="New stream insertion point"><div class="stream-gutter"></div><div class="stream-main"><div class="stream-content"><div class="placeholder-pulse" aria-hidden="true"></div></div></div></article>`; }
  function renderChildren(parentId, depth, items) { let markup = ""; const children = ordered(childrenOf(parentId, items)); for (const child of children) { if (state.pendingInsert?.placement === "before" && state.pendingInsert.anchorId === child.id) markup += renderPlaceholder(depth); markup += renderStream(child, depth, items); if (state.pendingInsert?.placement === "after" && state.pendingInsert.anchorId === child.id) markup += renderPlaceholder(depth); } if (state.pendingInsert?.placement === "child" && state.pendingInsert.anchorId === parentId) markup += renderPlaceholder(depth); if (state.pendingInsert?.placement === "root" && parentId === null) markup += renderPlaceholder(depth); return markup; }
  function renderStream(stream, depth, items) {
    const children = ordered(childrenOf(stream.id, items));
    const insertingChild = state.pendingInsert?.placement === "child" && state.pendingInsert.anchorId === stream.id;
    const childMarkup = stream.expanded !== false || insertingChild ? renderChildren(stream.id, depth + 1, items) : "";
    const tags = [...(stream.priority == null ? [] : [`<span class="tag priority-tag">#P${stream.priority}</span>`]), ...(stream.tags || []).map((tag) => `<span class="tag">#${escapeHtml(tag)}</span>`)].join("");
    const comments = (stream.comments || []).map((comment, index) => renderComment(comment, index)).join("");
    const owners = (stream.owners || []).join(", ");
    const deadline = displayDeadline(stream.deadline);
    return `<article class="stream-row ${stream.closed_at ? "is-closed" : ""} ${state.selected === stream.id ? "is-selected" : ""} ${state.selectedIds.includes(stream.id) ? "is-move-selected" : ""} ${state.moveMode?.targetId === stream.id ? "is-move-target" : ""}" style="--depth:${depth}" data-id="${stream.id}" tabindex="-1"><div class="stream-gutter"><button class="disclosure ${children.length ? "" : "is-empty"}" type="button" data-toggle="${stream.id}" aria-label="${stream.expanded !== false ? "Collapse" : "Expand"}">${stream.expanded !== false ? "⌄" : "›"}</button><span class="status-box" aria-label="${stream.closed_at ? "Closed" : "Open"}">${stream.closed_at ? "✓" : ""}</span></div><div class="stream-main"><div class="stream-content"><div class="stream-title-line"><span class="stream-id" title="Stream ${escapeHtml(stream.id)}">${escapeHtml(stream.id.slice(0, 6))}</span><button class="favorite-toggle" type="button" data-favorite-toggle="${stream.id}" aria-label="${stream.favorite ? "Remove" : "Add"} ${escapeHtml(stream.summary)} ${stream.favorite ? "from" : "to"} favorites" title="${stream.favorite ? "Remove from" : "Add to"} favorites">${stream.favorite ? "★" : "☆"}</button><span class="stream-title">${markdown(stream.summary)}</span><button class="stream-move" type="button" data-move="${stream.id}" aria-label="Move stream" title="Move stream">↕</button><button class="stream-edit" type="button" data-edit="${stream.id}" aria-label="Edit stream" title="Edit stream">✎</button><button class="stream-delete" type="button" data-delete="${stream.id}" aria-label="Delete stream" title="Delete stream">⌫</button></div><div class="stream-meta"><span class="updated">${escapeHtml(stream.updated_at)}</span>${owners ? `<span class="owners" title="Owners: ${escapeHtml(owners)}">${escapeHtml(owners)}</span>` : ""}${deadline ? `<span class="deadline" title="Deadline">due ${escapeHtml(deadline)}</span>` : ""}<span class="tag-list">${tags}</span><button class="comment-add" type="button" data-comment="${stream.id}" aria-label="Add comment">＋</button></div>${stream.description ? `<div class="stream-description">${markdown(stream.description)}</div>` : ""}</div>${comments ? `<div class="comment-rail" aria-label="Comments">${comments}</div>` : ""}</div></article>${childMarkup}`;
  }
  function render() {
    if (state.dashboard) { renderDashboard(); return; }
    const items = visibleItems();
    const rootId = currentRootId();
    list.innerHTML = items.length ? (rootId ? renderStream(selectedStreamById(rootId), 0, items) : renderChildren(null, 0, items)) : (state.pendingInsert ? renderPlaceholder(0) : '<div class="empty-filter">No streams match this filter.</div>');
    const viewItems = currentRootItems();
    const open = viewItems.filter((stream) => !stream.closed_at).length;
    document.querySelector("#toolbar-stats").textContent = `${open} open stream${open === 1 ? "" : "s"} · ${viewItems.length} total`;
  }
  function renderDashboard() {
    const favorites = favoriteStreams();
    const count = favorites.length;
    document.querySelector("#toolbar-stats").textContent = `${count} favorite stream${count === 1 ? "" : "s"}`;
    list.innerHTML = count ? favorites.map((stream) => {
      const breadcrumbs = streamPath(stream).map((item, index, path) => `<button class="dashboard-breadcrumb" type="button" data-dashboard-root="${escapeHtml(item.id)}">${escapeHtml(item.summary)}${index < path.length - 1 ? " /" : ""}</button>`).join(" ");
      const owners = (stream.owners || []).join(", ");
      return `<article class="favorite-row ${stream.closed_at ? "is-closed" : ""} ${state.selected === stream.id ? "is-selected" : ""}" data-favorite-row="${escapeHtml(stream.id)}" tabindex="-1"><span class="favorite-status" aria-label="${stream.closed_at ? "Closed" : "Open"}">${stream.closed_at ? "✓" : ""}</span><button class="favorite-star" type="button" data-unfavorite="${escapeHtml(stream.id)}" aria-label="Remove ${escapeHtml(stream.summary)} from favorites" title="Remove from favorites">★</button><div class="favorite-main"><button class="favorite-summary" type="button" data-dashboard-open="${escapeHtml(stream.id)}">${markdown(stream.summary)}</button><div class="favorite-meta"><span class="dashboard-breadcrumbs" aria-label="Hierarchy">${breadcrumbs}</span>${owners ? `<span class="owners" title="Owners: ${escapeHtml(owners)}">${escapeHtml(owners)}</span>` : ""}<span class="updated">${escapeHtml(stream.updated_at)}</span></div></div></article>`;
    }).join("") : '<div class="empty-filter">No favorite streams yet.</div>';
  }
  function selectedStream() { return state.streams.find((stream) => stream.id === state.selected); }
  function selectedComment() { const stream = selectedStream(); if (state.focusColumn !== "comments") return null; return stream?.comments?.find((comment) => comment.id === state.commentId) || stream?.comments?.[state.commentIndex] || null; }
  function restoreCommentFocus() { if (state.focusColumn !== "comments" || !state.selected) return; const stream = selectedStream(); const index = state.commentId ? stream?.comments?.findIndex((comment) => comment.id === state.commentId) ?? -1 : state.commentIndex; if (index >= 0) state.commentIndex = index; const row = document.querySelector(`[data-id="${CSS.escape(state.selected)}"]`); const card = row?.querySelector(`[data-comment-index="${state.commentIndex}"]`); card?.focus(); card?.scrollIntoView({ block: "nearest", inline: "nearest" }); }
  function updateRootLabel() {
    if (state.dashboard) { document.querySelector("#bundle-name").textContent = "Favorites"; return; }
    const path = state.rootPath.map((id) => selectedStreamById(id)?.summary).filter(Boolean);
    document.querySelector("#bundle-name").textContent = path.length ? ["Index", ...path].join(" / ") : state.bundle?.name || "Index";
  }
  function updateChrome() { document.querySelector("#view-select").closest(".compact-control").hidden = state.dashboard; document.querySelector("[data-action=\"dashboard\"]").hidden = state.dashboard; document.querySelector("[data-action=\"index\"]").hidden = !state.dashboard; document.querySelector("#dashboard-label").hidden = !state.dashboard; }
  function select(id, preserveComment = false) { state.selected = id; if (!preserveComment) { state.focusColumn = "stream"; state.commentIndex = 0; state.commentId = null; } render(); savePresentationAndUrl(); document.querySelector(`[data-id="${CSS.escape(id)}"]`)?.scrollIntoView({ block: "nearest" }); }
  function openDashboard(historyMode = "push") { state.dashboard = true; state.rootPath = []; state.focusColumn = "stream"; state.commentId = null; const favorites = favoriteStreams(); state.selected = favorites.some((stream) => stream.id === state.selected) ? state.selected : favorites[0]?.id || null; window.history[`${historyMode}State`](null, "", `/dashboard${state.selected ? `?focus=stream:${encodeURIComponent(state.selected)}` : ""}`); readUrlState(); updateChrome(); updateRootLabel(); render(); }
  function openIndex(historyMode = "push") { state.dashboard = false; state.rootPath = []; state.focusColumn = "stream"; state.commentIndex = 0; state.commentId = null; window.history[`${historyMode}State`](null, "", "/?view=priority"); readUrlState(); state.view = "priority"; updateChrome(); applyUrlState(); updateRootLabel(); render(); }
  function openRootedView(id, historyMode = "push") { state.dashboard = false; state.rootPath = [id]; state.selected = id; state.focusColumn = "stream"; state.commentIndex = 0; state.commentId = null; window.history[`${historyMode}State`](null, "", `/?root=${encodeURIComponent(id)}&view=manual&focus=stream:${encodeURIComponent(id)}`); readUrlState(); updateChrome(); applyUrlState(); updateRootLabel(); render(); document.querySelector(`[data-id="${CSS.escape(id)}"]`)?.scrollIntoView({ block: "nearest" }); }
  function updateSelection(targetId) { const entries = navigationEntries(); const anchor = entries.findIndex(({ stream }) => stream.id === state.selectionAnchor); const target = entries.findIndex(({ stream }) => stream.id === targetId); if (anchor < 0 || target < 0 || entries[anchor].stream.parent_stream_id !== entries[target].stream.parent_stream_id) { showCommandHud("Selection must remain contiguous siblings · [Esc] cancel"); return false; } const low = Math.min(anchor, target); const high = Math.max(anchor, target); state.selectedIds = entries.slice(low, high + 1).map(({ stream }) => stream.id); return true; }
  function moveVertical(direction) { const items = navigationItems(); const index = items.findIndex((stream) => stream.id === state.selected); const target = items[Math.max(0, Math.min(items.length - 1, index + direction))]; if (target) { const preserve = state.focusColumn === "comments" && (target.comments || []).length; state.commentIndex = preserve ? Math.min(state.commentIndex, target.comments.length - 1) : 0; state.commentId = preserve ? target.comments[state.commentIndex]?.id || null : null; state.selected = target.id; if (state.selecting) updateSelection(target.id); else if (!state.selectionReady) { state.selectedIds = []; select(target.id, Boolean(preserve)); } if (state.moveMode) state.moveMode.targetId = target.id; render(); savePresentationAndUrl(); } }
  function moveSibling(direction) { const entries = navigationEntries(); const index = entries.findIndex(({ stream }) => stream.id === state.selected); if (index < 0) return; const depth = entries[index].depth; let target = null; for (let cursor = index + direction; cursor >= 0 && cursor < entries.length; cursor += direction) { if (entries[cursor].depth === depth) { target = entries[cursor].stream; break; } } if (!target) { for (let cursor = index + direction; cursor >= 0 && cursor < entries.length; cursor += direction) { if (entries[cursor].depth < depth) { target = entries[cursor].stream; break; } } } if (!target) return; state.selected = target.id; if (state.selecting) updateSelection(target.id); else if (!state.selectionReady) { state.selectedIds = []; select(target.id); } if (state.moveMode) state.moveMode.targetId = target.id; }
  function moveHorizontal(direction) { const stream = selectedStream(); if (!stream) return; const count = (stream.comments || []).length; if (direction > 0 && state.focusColumn === "stream" && count) { state.focusColumn = "comments"; state.commentIndex = 0; state.commentId = stream.comments[0]?.id || null; } else if (direction > 0 && state.focusColumn === "comments") { state.commentIndex = Math.min(state.commentIndex + 1, count - 1); state.commentId = stream.comments[state.commentIndex]?.id || null; } else if (direction < 0 && state.focusColumn === "comments" && state.commentIndex > 0) { state.commentIndex -= 1; state.commentId = stream.comments[state.commentIndex]?.id || null; } else if (direction < 0) { state.focusColumn = "stream"; state.commentId = null; } render(); savePresentationAndUrl(); document.querySelector(`[data-id="${CSS.escape(state.selected || "")}"]`)?.scrollIntoView({ block: "nearest" }); }
  function setExpanded(stream, expanded, recursive) { stream.expanded = expanded; if (recursive) childrenOf(stream.id).forEach((child) => setExpanded(child, expanded, true)); }
  function fold(action) { const stream = selectedStream(); if (!stream) return; if (action === "fold_open") setExpanded(stream, true, false); if (action === "fold_close") setExpanded(stream, false, false); if (action === "fold_open_all") setExpanded(stream, true, true); if (action === "fold_close_all") setExpanded(stream, false, true); if (action === "fold_toggle") stream.expanded = stream.expanded === false; render(); savePresentationAndUrl(); }
  function showCommandHud(text) { commandHud.textContent = text; commandHud.hidden = !text; }
  const shortcutLabels = { move_left: "Move across stream/comments", move_right: "Move across stream/comments", move_up: "Move selection", move_down: "Move selection", move_previous_sibling: "Previous item at this level", move_next_sibling: "Next item at this level", edit: "Edit the focused stream", add_comment: "Add a comment", open_help: "Show this help", cancel_command: "Cancel a pending command", zoom_enter: "Enter the focused rooted view", zoom_back: "Return to the parent view", delete_stream: "Delete the focused stream", delete_comment: "Delete the focused comment", insert_before: "Insert before the focused stream", insert_after: "Insert after the focused stream", insert_child: "Insert a child stream", fold_open: "Open one level", fold_open_all: "Open descendants", fold_close: "Close one level", fold_close_all: "Close descendants", fold_toggle: "Toggle the focused hierarchy", start_move: "Pick up a stream", start_selection: "Select a sibling block", move_before: "Place before target", move_after: "Place after target", move_child: "Place as first child", move_promote: "Promote after current parent" };
  function renderShortcutHelp() { shortcutList.innerHTML = Object.entries(state.shortcuts).map(([action, bindings]) => `<div><dt>${bindings.map((binding) => `<kbd>${escapeHtml(binding)}</kbd>`).join(" / ")}</dt><dd>${escapeHtml(shortcutLabels[action] || action)}</dd></div>`).join(""); }
  const namedKeys = new Set(["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Enter", "Backspace", "Escape", "PageUp", "PageDown", "Home", "End", "Tab"]);
  const modifierOnlyKeys = new Set(["Shift", "Control", "Alt", "Meta", "CapsLock"]);
  function bindingTokens(binding) { return binding.includes(" ") ? binding.trim().split(/\s+/) : (namedKeys.has(binding) ? [binding] : [...binding]); }
  function isModifierOnlyKey(key) { return modifierOnlyKeys.has(key); }
  function shortcutEntries() { return Object.entries(state.shortcuts).flatMap(([action, bindings]) => bindings.map((binding) => ({ action, tokens: bindingTokens(binding) }))); }
  function matchingShortcuts(tokens) { return shortcutEntries().filter(({ tokens: binding }) => tokens.every((token, index) => binding[index] === token)); }
  function insertionPlacement(action) { return action.startsWith("insert_") ? action.replace("insert_", "") : null; }
  function nextShortcutHints(matches, length) { return [...new Map(matches.map(({ action, tokens }) => [tokens[length], `[${tokens[length]}] ${shortcutLabels[action] || action}`])).values()].join(" · "); }
  function shortcutGroupLabel(matches) { const actions = matches.map(({ action }) => action); if (actions.every((action) => action.startsWith("fold_"))) return "fold"; if (actions.every((action) => action.startsWith("delete_"))) return "delete"; if (actions.every((action) => action.startsWith("insert_"))) return "insert"; if (actions.every((action) => action.startsWith("zoom_"))) return "view"; return "command"; }
  function moveHud() { const count = state.moveMode?.sourceIds.length || 0; const target = selectedStreamById(state.moveMode?.targetId); showCommandHud(`[m] moving ${count} stream${count === 1 ? "" : "s"}${target ? ` → target: ${target.summary}` : " → navigate to a target"} · [p] before · [n] after · [c] child · [u] promote · [Esc] cancel`); }
  function startMove() { const sourceIds = state.selectedIds.length ? [...state.selectedIds] : (state.selected ? [state.selected] : []); if (!sourceIds.length) return; state.selecting = false; state.selectionReady = false; state.moveMode = { sourceIds, targetId: null }; render(); moveHud(); }
  function startSelection() { if (!state.selected) return; if (state.selecting) { state.selecting = false; state.selectionReady = true; showCommandHud(`[v] selection complete (${state.selectedIds.length}) · [m] pick up · [j]/[k] move to target · [Esc] clear`); render(); return; } state.selecting = true; state.selectionReady = false; state.selectionAnchor = state.selected; state.selectedIds = [state.selected]; showCommandHud("[v] selecting a contiguous sibling block · [j]/[k] extend · [v] finish · [m] pick up · [Esc] cancel"); render(); }
  async function completeMove(placement) { if (!state.moveMode) return; const sourceIds = state.moveMode.sourceIds; const targetId = placement === "promote" ? selectedStreamById(sourceIds[0])?.parent_stream_id : state.moveMode.targetId || state.selected; if (!targetId) { showCommandHud("No valid target · navigate to a target or press [Esc] to cancel"); return; } const revisions = Object.fromEntries(sourceIds.map((id) => [id, selectedStreamById(id)?.revision])); const destination = placement === "promote" ? "after" : placement; try { await api("/api/streams/move", { method: "POST", body: JSON.stringify({ actor: actor(), stream_ids: sourceIds, revisions, target_stream_id: targetId, placement: destination, root_stream_id: currentRootId() }) }); state.moveMode = null; state.selecting = false; state.selectionReady = false; state.selectedIds = []; state.selected = sourceIds[0]; await loadStreams(); document.querySelector("#status-message").textContent = "Stream moved"; showCommandHud(""); } catch (error) { showCommandHud(error.status === 409 ? "A selected stream changed elsewhere; refresh and review before moving · [Esc] cancel" : `${error.message} · [Esc] cancel`); } }
  function insertionBlocked(placement) { return (placement === "before" || placement === "after") && currentRootId() && selectedStream()?.id === currentRootId(); }
  function showInsertionBlocked() { showCommandHud("Cannot insert beside the rooted stream; use ic to add a child"); }
  function requestRootInsertion() { if (currentRootId()) { showCommandHud("Cannot add a root stream while viewing a rooted stream"); return; } openEditor(null, "root"); }
  function enterRoot() { const stream = selectedStream(); if (!stream || currentRootId() === stream.id) return; state.rootPath.push(stream.id); state.selected = stream.id; state.focusColumn = "stream"; state.commentIndex = 0; state.commentId = null; applyPresentation(true); updateRootLabel(); render(); savePresentationAndUrl("push"); }
  function popRoot() {
    if (!state.rootPath.length) return;
    const previousSelection = state.selected;
    const leaving = selectedStreamById(state.rootPath.pop());
    const parentItems = currentRootItems();
    const selectionStillVisible = previousSelection && parentItems.some((stream) => stream.id === previousSelection);
    if (!selectionStillVisible) {
      const fallback = currentRootId() || leaving?.parent_stream_id || leaving?.id || navigationItems()[0]?.id || null;
      state.selected = parentItems.some((stream) => stream.id === fallback) ? fallback : parentItems[0]?.id || null;
    } else {
      state.selected = previousSelection;
    }
    state.focusColumn = "stream";
    state.commentIndex = 0;
    state.commentId = null;
    applyPresentation(true);
    updateRootLabel();
    render();
    savePresentationAndUrl("push");
  }
  function restoreFromHistory() {
    readUrlState();
    state.dashboard = window.location.pathname === "/dashboard";
    if (state.dashboard) { state.rootPath = []; const focused = urlState.focus?.startsWith("stream:") ? urlState.focus.slice(7) : null; const favorites = favoriteStreams(); state.selected = favorites.some((stream) => stream.id === focused) ? focused : favorites[0]?.id || null; updateChrome(); updateRootLabel(); render(); requestAnimationFrame(() => document.querySelector(`[data-favorite-row="${CSS.escape(state.selected || "")}"]`)?.scrollIntoView({ block: "nearest" })); return; }
    updateChrome();
    state.view = urlState.view || "priority";
    applyUrlState();
    applyPresentation();
    document.querySelector("#view-select").value = state.view;
    updateRootLabel();
    render();
    writePresentation();
    requestAnimationFrame(() => {
      const row = state.selected && document.querySelector(`[data-id="${CSS.escape(state.selected)}"]`);
      row?.scrollIntoView({ block: "nearest" });
      restoreCommentFocus();
    });
  }
  function openEditor(stream = null, placement = null) { state.editing = stream; state.editingPlacement = placement; state.pendingInsert = stream ? null : { placement: placement || "root", anchorId: state.selected }; render(); document.querySelector("#editor-title").textContent = stream ? "Edit stream" : "Add stream"; document.querySelector("#editor-placement").textContent = stream ? "" : ({ before: "Inserting before the focused stream", after: "Inserting after the focused stream", child: "Inserting as a child of the focused stream", root: "Adding a root stream" }[placement || "root"]); document.querySelector("#editor-summary").value = stream?.summary || ""; document.querySelector("#editor-description").value = stream?.description || ""; document.querySelector("#editor-owners").value = (stream?.owners || []).join(", "); document.querySelector("#editor-priority").value = stream ? (stream.priority ?? "") : ""; document.querySelector("#editor-deadline").value = displayDeadline(stream?.deadline); document.querySelector("#editor-order-key").value = stream?.order_key ?? ""; document.querySelector("#editor-tags").value = (stream?.tags || []).join(", "); document.querySelector("#editor-error").textContent = ""; const placeholder = document.querySelector(".is-placeholder"); placeholder?.scrollIntoView({ block: "center" }); if (!editorDialog.open) editorDialog.showModal(); requestAnimationFrame(() => document.querySelector("#editor-summary").focus()); }
  async function submitStream(event) { event.preventDefault(); const stream = state.editing; const priorityValue = document.querySelector("#editor-priority").value; const owners = document.querySelector("#editor-owners").value.split(",").map((owner) => owner.trim()).filter(Boolean); const deadline = document.querySelector("#editor-deadline").value || null; const tags = document.querySelector("#editor-tags").value.split(/[,\s]+/).map((tag) => tag.trim()).filter(Boolean); const changes = { summary: document.querySelector("#editor-summary").value.trim(), description: document.querySelector("#editor-description").value, owners, priority: priorityValue === "" ? null : Number(priorityValue), deadline, tags }; try { if (stream) await api(`/api/streams/${stream.id}`, { method: "PATCH", body: JSON.stringify({ actor: actor(), revision: stream.revision, changes }) }); else { if (!state.bundle) state.bundle = (await api("/api/bundles", { method: "POST", body: JSON.stringify({ name: "Index", actor: actor() }) })).bundle; const siblingInsertion = state.editingPlacement === "before" || state.editingPlacement === "after"; await api(`/api/bundles/${state.bundle.id}/streams`, { method: "POST", body: JSON.stringify({ actor: actor(), ...changes, parent_stream_id: state.editingPlacement === "child" ? state.selected : siblingInsertion ? selectedStream()?.parent_stream_id : null, anchor_stream_id: siblingInsertion ? state.selected : null, placement: state.editingPlacement === "root" ? null : state.editingPlacement, root_stream_id: currentRootId() }) }); } state.pendingInsert = null; editorDialog.close(); await loadStreams(); document.querySelector("#status-message").textContent = stream ? "Stream saved" : "Stream added"; } catch (error) { document.querySelector("#editor-error").textContent = error.message; } }
  function openComment(stream = selectedStream()) { if (!stream) return; state.editing = stream; state.commentEditing = null; document.querySelector("#comment-title").textContent = "Add comment"; document.querySelector("#comment-submit").textContent = "Add comment"; document.querySelector("#comment-body").value = ""; document.querySelector("#comment-error").textContent = ""; commentDialog.showModal(); document.querySelector("#comment-body").focus(); }
  function openCommentEditor(comment) { if (!comment) return; state.editing = null; state.commentEditing = comment; document.querySelector("#comment-title").textContent = "Edit comment"; document.querySelector("#comment-submit").textContent = "Save"; document.querySelector("#comment-body").value = comment.body || ""; document.querySelector("#comment-error").textContent = ""; commentDialog.showModal(); document.querySelector("#comment-body").focus(); }
  async function submitComment(event) { event.preventDefault(); const body = document.querySelector("#comment-body").value.trim(); const editingComment = state.commentEditing; try { if (editingComment) { await api(`/api/comments/${editingComment.id}`, { method: "PATCH", body: JSON.stringify({ actor: actor(), revision: editingComment.revision, body, sticky_note: Boolean(editingComment.sticky_note) }) }); state.focusColumn = "comments"; state.selected = editingComment.stream_id; state.commentId = editingComment.id; } else { const stream = state.editing; await api(`/api/streams/${stream.id}/comments`, { method: "POST", body: JSON.stringify({ actor: actor(), body }) }); } commentDialog.close(); await loadStreams(); document.querySelector("#status-message").textContent = editingComment ? "Comment saved" : "Comment added"; } catch (error) { document.querySelector("#comment-error").textContent = error.status === 409 ? "This comment changed elsewhere. Review the current comment before saving again." : error.message; } }
  function openDelete(target, type) {
    if (!target) return;
    state.deleteTarget = { target, type };
    document.querySelector("#delete-title").textContent = `Delete ${type}?`;
    document.querySelector("#delete-message").textContent = type === "stream" ? `Delete “${target.summary}”? Its direct children will become root streams, and its comments will be deleted.` : `Delete this comment by ${target.creator}?`;
    document.querySelector("#delete-error").textContent = "";
    deleteDialog.showModal();
  }
  async function submitDelete(event) {
    event.preventDefault();
    const deletion = state.deleteTarget;
    if (!deletion) return;
    const { target, type } = deletion;
    try {
      await api(`/api/${type === "stream" ? "streams" : "comments"}/${target.id}`, { method: "DELETE", body: JSON.stringify({ actor: actor(), revision: target.revision }) });
      deleteDialog.close();
      state.deleteTarget = null;
      if (type === "stream") {
        const parent = target.parent_stream_id;
        state.rootPath = state.rootPath.filter((id) => id !== target.id);
        state.selected = parent || null;
        state.focusColumn = "stream";
        state.commentIndex = 0;
      } else {
        state.focusColumn = "stream";
        state.commentIndex = 0;
      }
      await loadStreams();
      document.querySelector("#status-message").textContent = `${type === "stream" ? "Stream" : "Comment"} deleted`;
    } catch (error) {
      document.querySelector("#delete-error").textContent = error.status === 409 ? "This item changed elsewhere. Close this dialog, refresh, and review the current item before deleting." : error.message;
    }
  }
  async function loadStreams() { if (!state.bundle) { state.streams = []; state.selected = null; render(); return; } const previousExpanded = Object.fromEntries(state.streams.map((stream) => [stream.id, stream.expanded])); const body = await api(`/api/bundles/${state.bundle.id}/streams`); state.streams = body.streams.map((stream) => ({ ...stream, expanded: previousExpanded[stream.id] ?? (stream.expanded !== false) })); if (state.dashboard) { const focused = urlState.focus?.startsWith("stream:") ? urlState.focus.slice(7) : null; state.selected = focused && favoriteStreams().some((stream) => stream.id === focused) ? focused : favoriteStreams()[0]?.id || null; updateRootLabel(); render(); return; } state.rootPath = state.rootPath.filter((id) => state.streams.some((stream) => stream.id === id)); if (!state.selected || !state.streams.some((stream) => stream.id === state.selected)) state.selected = state.streams[0]?.id || null; if (!state.presentationLoaded) { applyUrlState(); applyPresentation(); } updateRootLabel(); render(); savePresentationAndUrl(); }
  async function setFavorite(id, favorite) { const stream = selectedStreamById(id); if (!stream) return; try { const body = await api(`/api/streams/${id}`, { method: "PATCH", body: JSON.stringify({ actor: actor(), revision: stream.revision, changes: { favorite } }) }); const updated = body.stream || body; Object.assign(stream, updated); render(); document.querySelector("#status-message").textContent = favorite ? "Added to favorites" : "Removed from favorites"; } catch (error) { document.querySelector("#status-message").textContent = error.status === 409 ? "This stream changed elsewhere. Refresh before changing its favorite status." : error.message; } }
  async function copyLink() { const link = new URL(window.location.href).toString(); try { await navigator.clipboard.writeText(link); } catch (_) { const input = document.createElement("input"); input.value = link; document.body.appendChild(input); input.select(); document.execCommand("copy"); input.remove(); } const button = document.querySelector('[data-action="copy-link"]'); const original = button.textContent; button.textContent = "Copied"; setTimeout(() => { button.textContent = original; }, 1400); }
  async function load() { try { const shortcutBody = await api("/api/shortcuts"); state.shortcuts = shortcutBody.shortcuts; renderShortcutHelp(); const body = await api("/api/bundles"); state.bundle = body.bundles[0] || null; document.querySelector("#view-select").value = state.view; updateChrome(); updateRootLabel(); await loadStreams(); } catch (error) { list.innerHTML = `<div class="empty-filter">${escapeHtml(error.message)}</div>`; } }

  list.addEventListener("click", (event) => { if (state.dashboard) { const unfavoriteButton = event.target.closest("[data-unfavorite]"); if (unfavoriteButton) { event.stopPropagation(); setFavorite(unfavoriteButton.dataset.unfavorite, false); return; } const breadcrumb = event.target.closest("[data-dashboard-root]"); if (breadcrumb) { openRootedView(breadcrumb.dataset.dashboardRoot); return; } const dashboardOpen = event.target.closest("[data-dashboard-open]"); const dashboardRow = event.target.closest("[data-favorite-row]"); if (dashboardOpen || dashboardRow) { openRootedView((dashboardOpen || dashboardRow).dataset.dashboardOpen || dashboardRow.dataset.favoriteRow); } return; } const row = event.target.closest(".stream-row"); const favoriteToggle = event.target.closest("[data-favorite-toggle]"); const toggle = event.target.closest("[data-toggle]"); const move = event.target.closest("[data-move]"); const edit = event.target.closest("[data-edit]"); const commentEdit = event.target.closest("[data-edit-comment]"); const deletion = event.target.closest("[data-delete]"); const comment = event.target.closest("[data-comment]"); if (favoriteToggle) { event.stopPropagation(); const stream = selectedStreamById(favoriteToggle.dataset.favoriteToggle); if (stream) setFavorite(stream.id, !stream.favorite); return; } if (toggle) { const stream = state.streams.find((item) => item.id === toggle.dataset.toggle); if (stream) { stream.expanded = stream.expanded === false; render(); savePresentationAndUrl(); } return; } if (move) { event.stopPropagation(); select(move.dataset.move); startMove(); return; } if (edit) { select(edit.dataset.edit); openEditor(selectedStream()); return; } if (commentEdit) { const card = event.target.closest(".comment-card"); const stream = event.target.closest(".stream-row"); const comment = stream && state.streams.find((item) => item.id === stream.dataset.id)?.comments?.find((item) => item.id === commentEdit.dataset.editComment); if (card && stream && comment) { state.selected = stream.dataset.id; state.focusColumn = "comments"; state.commentIndex = Number(card.dataset.commentIndex); state.commentId = comment.id; savePresentationAndUrl(); openCommentEditor(comment); } return; } if (deletion) { select(deletion.dataset.delete); openDelete(selectedStream(), "stream"); return; } if (comment) { select(comment.dataset.comment); openComment(); return; } const card = event.target.closest(".comment-card"); if (card && row) { state.selected = row.dataset.id; state.focusColumn = "comments"; state.commentIndex = Number(card.dataset.commentIndex); state.commentId = state.streams.find((item) => item.id === row.dataset.id)?.comments?.[state.commentIndex]?.id || null; render(); savePresentationAndUrl(); return; } if (row) select(row.dataset.id); });
  list.addEventListener("dblclick", (event) => { const row = event.target.closest(".stream-row"); if (row) { select(row.dataset.id); enterRoot(); } });
  document.querySelector("#view-select").addEventListener("change", (event) => { state.view = validViews.has(event.target.value) ? event.target.value : "priority"; applyPresentation(); render(); savePresentationAndUrl(); }); search.addEventListener("input", () => { state.query = search.value.trim(); render(); });
  window.addEventListener("popstate", restoreFromHistory);
  username.addEventListener("change", saveUsername); username.addEventListener("blur", saveUsername);
  document.querySelector("#editor-form").addEventListener("submit", submitStream); document.querySelector("#comment-form").addEventListener("submit", submitComment); document.querySelector("#delete-form").addEventListener("submit", submitDelete);
  document.querySelector('[data-action="add-stream"]').addEventListener("click", requestRootInsertion); document.querySelector('[data-action="dashboard"]').addEventListener("click", () => openDashboard()); document.querySelector('[data-action="index"]').addEventListener("click", () => openIndex()); document.querySelector('[data-action="copy-link"]').addEventListener("click", copyLink); document.querySelector('[data-action="refresh"]').addEventListener("click", loadStreams); document.querySelector('[data-action="shortcuts"]').addEventListener("click", () => shortcutsDialog.showModal()); document.querySelector('[data-action="close-shortcuts"]').addEventListener("click", () => shortcutsDialog.close());
  document.querySelectorAll('[data-action="close-editor"]').forEach((button) => button.addEventListener("click", () => editorDialog.close())); document.querySelectorAll('[data-action="close-comment"]').forEach((button) => button.addEventListener("click", () => commentDialog.close())); document.querySelectorAll('[data-action="close-delete"]').forEach((button) => button.addEventListener("click", () => deleteDialog.close()));
  commentDialog.addEventListener("close", () => { state.editing = null; state.commentEditing = null; requestAnimationFrame(restoreCommentFocus); });
  editorDialog.addEventListener("close", () => { if (!state.editing) { state.pendingInsert = null; render(); } state.editing = null; state.editingPlacement = null; });
  function dispatchShortcut(action) {
    if (action === "move_down") moveVertical(1);
    else if (action === "move_up") moveVertical(-1);
    else if (action === "move_left") moveHorizontal(-1);
    else if (action === "move_right") moveHorizontal(1);
    else if (action === "move_previous_sibling") moveSibling(-1);
    else if (action === "move_next_sibling") moveSibling(1);
    else if (action === "start_move") startMove();
    else if (action === "start_selection") startSelection();
    else if (action === "move_before") completeMove("before");
    else if (action === "move_after") completeMove("after");
    else if (action === "move_child") completeMove("child");
    else if (action === "move_promote") completeMove("promote");
    else if (action === "edit") { if (state.focusColumn === "comments") openCommentEditor(selectedComment()); else openEditor(selectedStream()); }
    else if (action === "add_comment") openComment();
    else if (action === "open_help") shortcutsDialog.showModal();
    else if (action === "zoom_enter") enterRoot();
    else if (action === "zoom_back") popRoot();
    else if (action === "delete_stream") openDelete(selectedStream(), "stream");
    else if (action === "delete_comment") openDelete(selectedComment(), "comment");
    else if (action.startsWith("fold_")) fold(action);
    else if (action.startsWith("insert_")) {
      const placement = insertionPlacement(action);
      if (placement === "child" && !selectedStream()) return;
      if (insertionBlocked(placement)) { showInsertionBlocked(); return; }
      openEditor(null, placement);
    }
  }
  document.addEventListener("keydown", (event) => {
    event.stopImmediatePropagation();
    const active = document.activeElement;
    const inTextField = ["INPUT", "TEXTAREA", "SELECT"].includes(active.tagName) || active.isContentEditable;
    const cancelBinding = state.shortcuts.cancel_command?.some((binding) => bindingTokens(binding).length === 1 && bindingTokens(binding)[0] === event.key);
    if (cancelBinding && (state.pendingCommand.length || state.moveMode || state.selecting || state.selectionReady)) { event.preventDefault(); state.pendingCommand = []; state.moveMode = null; state.selecting = false; state.selectionReady = false; state.selectedIds = []; showCommandHud(""); render(); return; }
    if (editorDialog.open || commentDialog.open || deleteDialog.open || shortcutsDialog.open || inTextField) return;
    if (isModifierOnlyKey(event.key)) return;
    const candidate = [...state.pendingCommand, event.key];
    const exact = matchingShortcuts(candidate).filter(({ tokens }) => tokens.length === candidate.length);
    const prefixes = matchingShortcuts(candidate).filter(({ tokens }) => tokens.length > candidate.length);
    if (exact.length) { event.preventDefault(); state.pendingCommand = []; showCommandHud(""); dispatchShortcut(exact[0].action); return; }
    if (prefixes.length) { event.preventDefault(); state.pendingCommand = candidate; showCommandHud(`[${candidate.join(" ")}] ${shortcutGroupLabel(prefixes)} · ${nextShortcutHints(prefixes, candidate.length)}`); return; }
    if (state.pendingCommand.length) { state.pendingCommand = []; showCommandHud(""); return; }
  }, true);
  loadUsername(); load();
})();
