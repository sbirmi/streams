(() => {
  "use strict";

  const state = { bundle: null, streams: [], selected: null, rootPath: [], focusColumn: "stream", commentIndex: 0, view: "priority", query: "", pendingCommand: [], editing: null, editingPlacement: null, deleteTarget: null, shortcuts: {} };
  const list = document.querySelector("#stream-list");
  const search = document.querySelector("#search");
  const username = document.querySelector("#username");
  const editorDialog = document.querySelector("#editor-dialog");
  const commentDialog = document.querySelector("#comment-dialog");
  const deleteDialog = document.querySelector("#delete-dialog");
  const shortcutsDialog = document.querySelector("#shortcuts-dialog");
  const shortcutList = document.querySelector("#shortcut-list");
  const commandHud = document.querySelector("#command-hud");

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
  function childrenOf(id, items = state.streams) { return items.filter((stream) => stream.parent_stream_id === id); }
  function selectedStreamById(id) { return state.streams.find((stream) => stream.id === id); }
  function currentRootId() { return state.rootPath[state.rootPath.length - 1] || null; }
  function descendantsOf(id) { const result = []; function visit(parentId) { childrenOf(parentId).forEach((child) => { result.push(child); visit(child.id); }); } visit(id); return result; }
  function currentRootItems() { const rootId = currentRootId(); return rootId ? [selectedStreamById(rootId), ...descendantsOf(rootId)].filter(Boolean) : state.streams; }
  function ordered(items) {
    return [...items].sort((a, b) => {
      if (state.view === "recent") return b.updated_at.localeCompare(a.updated_at) || a.id.localeCompare(b.id);
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
  function renderComment(comment, index) { return `<article class="comment-card ${state.focusColumn === "comments" && index === state.commentIndex && state.selected === comment.stream_id ? "is-focused" : ""}" data-comment-index="${index}" tabindex="-1"><div class="comment-meta"><strong>${escapeHtml(comment.creator)}</strong><span>${escapeHtml(comment.updated_at)}</span></div><div class="comment-body">${markdown(comment.body)}</div></article>`; }
  function renderPlaceholder(depth) { return `<article class="stream-row is-placeholder" style="--depth:${depth}" aria-label="New stream insertion point"><div class="stream-gutter"></div><div class="stream-main"><div class="stream-content"><div class="placeholder-pulse" aria-hidden="true"></div></div></div></article>`; }
  function renderChildren(parentId, depth, items) { let markup = ""; const children = ordered(childrenOf(parentId, items)); for (const child of children) { if (state.pendingInsert?.placement === "before" && state.pendingInsert.anchorId === child.id) markup += renderPlaceholder(depth); markup += renderStream(child, depth, items); if (state.pendingInsert?.placement === "after" && state.pendingInsert.anchorId === child.id) markup += renderPlaceholder(depth); } if (state.pendingInsert?.placement === "child" && state.pendingInsert.anchorId === parentId) markup += renderPlaceholder(depth); if (state.pendingInsert?.placement === "root" && parentId === null) markup += renderPlaceholder(depth); return markup; }
  function renderStream(stream, depth, items) {
    const children = ordered(childrenOf(stream.id, items));
    const insertingChild = state.pendingInsert?.placement === "child" && state.pendingInsert.anchorId === stream.id;
    const childMarkup = stream.expanded !== false || insertingChild ? renderChildren(stream.id, depth + 1, items) : "";
    const tags = [...(stream.priority == null ? [] : [`<span class="tag priority-tag">#P${stream.priority}</span>`]), ...(stream.tags || []).map((tag) => `<span class="tag">#${escapeHtml(tag)}</span>`)].join("");
    const comments = (stream.comments || []).map((comment, index) => renderComment(comment, index)).join("");
    return `<article class="stream-row ${stream.closed_at ? "is-closed" : ""} ${state.selected === stream.id ? "is-selected" : ""}" style="--depth:${depth}" data-id="${stream.id}" tabindex="-1"><div class="stream-gutter"><button class="disclosure ${children.length ? "" : "is-empty"}" type="button" data-toggle="${stream.id}" aria-label="${stream.expanded !== false ? "Collapse" : "Expand"}">${stream.expanded !== false ? "⌄" : "›"}</button><span class="status-box" aria-label="${stream.closed_at ? "Closed" : "Open"}">${stream.closed_at ? "✓" : ""}</span></div><div class="stream-main"><div class="stream-content"><div class="stream-title-line"><span class="stream-id" title="Stream ${escapeHtml(stream.id)}">${escapeHtml(stream.id.slice(0, 6))}</span><span class="stream-title">${markdown(stream.summary)}</span><button class="stream-edit" type="button" data-edit="${stream.id}" aria-label="Edit stream" title="Edit stream">✎</button><button class="stream-delete" type="button" data-delete="${stream.id}" aria-label="Delete stream" title="Delete stream">⌫</button></div><div class="stream-meta"><span class="updated">${escapeHtml(stream.updated_at)}</span><span class="owners">${escapeHtml((stream.owners || []).join(", "))}</span><span class="tag-list">${tags}</span><button class="comment-add" type="button" data-comment="${stream.id}" aria-label="Add comment">＋</button></div>${stream.description ? `<div class="stream-description">${markdown(stream.description)}</div>` : ""}</div>${comments ? `<div class="comment-rail" aria-label="Comments">${comments}</div>` : ""}</div></article>${childMarkup}`;
  }
  function render() {
    const items = visibleItems();
    const rootId = currentRootId();
    list.innerHTML = items.length ? (rootId ? renderStream(selectedStreamById(rootId), 0, items) : renderChildren(null, 0, items)) : (state.pendingInsert ? renderPlaceholder(0) : '<div class="empty-filter">No streams match this filter.</div>');
    const viewItems = currentRootItems();
    const open = viewItems.filter((stream) => !stream.closed_at).length;
    document.querySelector("#toolbar-stats").textContent = `${open} open stream${open === 1 ? "" : "s"} · ${viewItems.length} total`;
  }
  function selectedStream() { return state.streams.find((stream) => stream.id === state.selected); }
  function selectedComment() { const stream = selectedStream(); return state.focusColumn === "comments" ? stream?.comments?.[state.commentIndex] : null; }
  function updateRootLabel() {
    const path = state.rootPath.map((id) => selectedStreamById(id)?.summary).filter(Boolean);
    document.querySelector("#bundle-name").textContent = path.length ? ["Index", ...path].join(" / ") : state.bundle?.name || "Index";
  }
  function select(id, preserveComment = false) { state.selected = id; if (!preserveComment) { state.focusColumn = "stream"; state.commentIndex = 0; } render(); document.querySelector(`[data-id="${CSS.escape(id)}"]`)?.scrollIntoView({ block: "nearest" }); }
  function moveVertical(direction) { const items = navigationItems(); const index = items.findIndex((stream) => stream.id === state.selected); const target = items[Math.max(0, Math.min(items.length - 1, index + direction))]; if (target) { const preserve = state.focusColumn === "comments" && (target.comments || []).length; state.commentIndex = preserve ? Math.min(state.commentIndex, target.comments.length - 1) : 0; select(target.id, Boolean(preserve)); } }
  function moveHorizontal(direction) { const stream = selectedStream(); if (!stream) return; const count = (stream.comments || []).length; if (direction > 0 && state.focusColumn === "stream" && count) state.focusColumn = "comments"; else if (direction > 0 && state.focusColumn === "comments") state.commentIndex = Math.min(state.commentIndex + 1, count - 1); else if (direction < 0 && state.focusColumn === "comments" && state.commentIndex > 0) state.commentIndex -= 1; else if (direction < 0) state.focusColumn = "stream"; render(); document.querySelector(`[data-id="${CSS.escape(state.selected || "")}"]`)?.scrollIntoView({ block: "nearest" }); }
  function setExpanded(stream, expanded, recursive) { stream.expanded = expanded; if (recursive) childrenOf(stream.id).forEach((child) => setExpanded(child, expanded, true)); }
  function fold(action) { const stream = selectedStream(); if (!stream) return; if (action === "fold_open") setExpanded(stream, true, false); if (action === "fold_close") setExpanded(stream, false, false); if (action === "fold_open_all") setExpanded(stream, true, true); if (action === "fold_close_all") setExpanded(stream, false, true); if (action === "fold_toggle") stream.expanded = stream.expanded === false; render(); }
  function showCommandHud(text) { commandHud.textContent = text; commandHud.hidden = !text; }
  const shortcutLabels = { move_left: "Move across stream/comments", move_right: "Move across stream/comments", move_up: "Move selection", move_down: "Move selection", edit: "Edit the focused stream", add_comment: "Add a comment", open_help: "Show this help", cancel_command: "Cancel a pending command", zoom_enter: "Enter the focused rooted view", zoom_back: "Return to the parent view", delete_stream: "Delete the focused stream", delete_comment: "Delete the focused comment", insert_before: "Insert before the focused stream", insert_after: "Insert after the focused stream", insert_child: "Insert a child stream", fold_open: "Open one level", fold_open_all: "Open descendants", fold_close: "Close one level", fold_close_all: "Close descendants", fold_toggle: "Toggle the focused hierarchy" };
  function renderShortcutHelp() { shortcutList.innerHTML = Object.entries(state.shortcuts).map(([action, bindings]) => `<div><dt>${bindings.map((binding) => `<kbd>${escapeHtml(binding)}</kbd>`).join(" / ")}</dt><dd>${escapeHtml(shortcutLabels[action] || action)}</dd></div>`).join(""); }
  const namedKeys = new Set(["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Enter", "Backspace", "Escape", "PageUp", "PageDown", "Home", "End", "Tab"]);
  function bindingTokens(binding) { return binding.includes(" ") ? binding.trim().split(/\s+/) : (namedKeys.has(binding) ? [binding] : [...binding]); }
  function shortcutEntries() { return Object.entries(state.shortcuts).flatMap(([action, bindings]) => bindings.map((binding) => ({ action, tokens: bindingTokens(binding) }))); }
  function matchingShortcuts(tokens) { return shortcutEntries().filter(({ tokens: binding }) => tokens.every((token, index) => binding[index] === token)); }
  function insertionPlacement(action) { return action.startsWith("insert_") ? action.replace("insert_", "") : null; }
  function nextShortcutHints(matches, length) { return [...new Set(matches.map(({ tokens }) => tokens[length]).filter(Boolean))].join("/"); }
  function insertionBlocked(placement) { return (placement === "before" || placement === "after") && currentRootId() && selectedStream()?.id === currentRootId(); }
  function showInsertionBlocked() { showCommandHud("Cannot insert beside the rooted stream; use ic to add a child"); }
  function requestRootInsertion() { if (currentRootId()) { showCommandHud("Cannot add a root stream while viewing a rooted stream"); return; } openEditor(null, "root"); }
  function enterRoot() { const stream = selectedStream(); if (!stream || currentRootId() === stream.id) return; state.rootPath.push(stream.id); state.selected = stream.id; state.focusColumn = "stream"; state.commentIndex = 0; updateRootLabel(); render(); }
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
    updateRootLabel();
    render();
  }
  function openEditor(stream = null, placement = null) { state.editing = stream; state.editingPlacement = placement; state.pendingInsert = stream ? null : { placement: placement || "root", anchorId: state.selected }; render(); document.querySelector("#editor-title").textContent = stream ? "Edit stream" : "Add stream"; document.querySelector("#editor-placement").textContent = stream ? "" : ({ before: "Inserting before the focused stream", after: "Inserting after the focused stream", child: "Inserting as a child of the focused stream", root: "Adding a root stream" }[placement || "root"]); document.querySelector("#editor-summary").value = stream?.summary || ""; document.querySelector("#editor-description").value = stream?.description || ""; document.querySelector("#editor-priority").value = stream ? (stream.priority ?? "") : ""; document.querySelector("#editor-error").textContent = ""; const placeholder = document.querySelector(".is-placeholder"); placeholder?.scrollIntoView({ block: "center" }); if (!editorDialog.open) editorDialog.showModal(); requestAnimationFrame(() => document.querySelector("#editor-summary").focus()); }
  async function submitStream(event) { event.preventDefault(); const stream = state.editing; const priorityValue = document.querySelector("#editor-priority").value; const changes = { summary: document.querySelector("#editor-summary").value.trim(), description: document.querySelector("#editor-description").value, priority: priorityValue === "" ? null : Number(priorityValue) }; try { if (stream) await api(`/api/streams/${stream.id}`, { method: "PATCH", body: JSON.stringify({ actor: actor(), revision: stream.revision, changes }) }); else { if (!state.bundle) state.bundle = (await api("/api/bundles", { method: "POST", body: JSON.stringify({ name: "Index", actor: actor() }) })).bundle; const siblingInsertion = state.editingPlacement === "before" || state.editingPlacement === "after"; await api(`/api/bundles/${state.bundle.id}/streams`, { method: "POST", body: JSON.stringify({ actor: actor(), ...changes, parent_stream_id: state.editingPlacement === "child" ? state.selected : siblingInsertion ? selectedStream()?.parent_stream_id : null, anchor_stream_id: siblingInsertion ? state.selected : null, placement: state.editingPlacement === "root" ? null : state.editingPlacement, root_stream_id: currentRootId() }) }); } state.pendingInsert = null; editorDialog.close(); await loadStreams(); document.querySelector("#status-message").textContent = stream ? "Stream saved" : "Stream added"; } catch (error) { document.querySelector("#editor-error").textContent = error.message; } }
  function openComment(stream = selectedStream()) { if (!stream) return; state.editing = stream; document.querySelector("#comment-body").value = ""; document.querySelector("#comment-error").textContent = ""; commentDialog.showModal(); document.querySelector("#comment-body").focus(); }
  async function submitComment(event) { event.preventDefault(); const stream = state.editing; try { await api(`/api/streams/${stream.id}/comments`, { method: "POST", body: JSON.stringify({ actor: actor(), body: document.querySelector("#comment-body").value.trim() }) }); commentDialog.close(); await loadStreams(); document.querySelector("#status-message").textContent = "Comment added"; } catch (error) { document.querySelector("#comment-error").textContent = error.message; } }
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
  async function loadStreams() { if (!state.bundle) { state.streams = []; state.selected = null; render(); return; } const body = await api(`/api/bundles/${state.bundle.id}/streams`); state.streams = body.streams.map((stream) => ({ ...stream, expanded: stream.expanded !== false })); state.rootPath = state.rootPath.filter((id) => state.streams.some((stream) => stream.id === id)); if (!state.selected || !state.streams.some((stream) => stream.id === state.selected)) state.selected = state.streams[0]?.id || null; updateRootLabel(); render(); }
  async function load() { try { const shortcutBody = await api("/api/shortcuts"); state.shortcuts = shortcutBody.shortcuts; renderShortcutHelp(); const body = await api("/api/bundles"); state.bundle = body.bundles[0] || null; updateRootLabel(); await loadStreams(); } catch (error) { list.innerHTML = `<div class="empty-filter">${escapeHtml(error.message)}</div>`; } }

  list.addEventListener("click", (event) => { const row = event.target.closest(".stream-row"); const toggle = event.target.closest("[data-toggle]"); const edit = event.target.closest("[data-edit]"); const deletion = event.target.closest("[data-delete]"); const comment = event.target.closest("[data-comment]"); if (toggle) { const stream = state.streams.find((item) => item.id === toggle.dataset.toggle); if (stream) { stream.expanded = stream.expanded === false; render(); } return; } if (edit) { select(edit.dataset.edit); openEditor(selectedStream()); return; } if (deletion) { select(deletion.dataset.delete); openDelete(selectedStream(), "stream"); return; } if (comment) { select(comment.dataset.comment); openComment(); return; } const card = event.target.closest(".comment-card"); if (card && row) { state.selected = row.dataset.id; state.focusColumn = "comments"; state.commentIndex = Number(card.dataset.commentIndex); render(); return; } if (row) select(row.dataset.id); });
  list.addEventListener("dblclick", (event) => { const row = event.target.closest(".stream-row"); if (row) { select(row.dataset.id); enterRoot(); } });
  document.querySelector("#view-select").addEventListener("change", (event) => { state.view = event.target.value; render(); }); search.addEventListener("input", () => { state.query = search.value.trim(); render(); });
  username.addEventListener("change", saveUsername); username.addEventListener("blur", saveUsername);
  document.querySelector("#editor-form").addEventListener("submit", submitStream); document.querySelector("#comment-form").addEventListener("submit", submitComment); document.querySelector("#delete-form").addEventListener("submit", submitDelete);
  document.querySelector('[data-action="add-stream"]').addEventListener("click", requestRootInsertion); document.querySelector('[data-action="refresh"]').addEventListener("click", loadStreams); document.querySelector('[data-action="shortcuts"]').addEventListener("click", () => shortcutsDialog.showModal()); document.querySelector('[data-action="close-shortcuts"]').addEventListener("click", () => shortcutsDialog.close());
  document.querySelectorAll('[data-action="close-editor"]').forEach((button) => button.addEventListener("click", () => editorDialog.close())); document.querySelectorAll('[data-action="close-comment"]').forEach((button) => button.addEventListener("click", () => commentDialog.close())); document.querySelectorAll('[data-action="close-delete"]').forEach((button) => button.addEventListener("click", () => deleteDialog.close()));
  editorDialog.addEventListener("close", () => { if (!state.editing) { state.pendingInsert = null; render(); } state.editing = null; state.editingPlacement = null; });
  function dispatchShortcut(action) {
    if (action === "move_down") moveVertical(1);
    else if (action === "move_up") moveVertical(-1);
    else if (action === "move_left") moveHorizontal(-1);
    else if (action === "move_right") moveHorizontal(1);
    else if (action === "edit") openEditor(selectedStream());
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
    if (cancelBinding && state.pendingCommand.length) { event.preventDefault(); state.pendingCommand = []; showCommandHud(""); return; }
    if (editorDialog.open || commentDialog.open || deleteDialog.open || shortcutsDialog.open || inTextField) return;
    const candidate = [...state.pendingCommand, event.key];
    const exact = matchingShortcuts(candidate).filter(({ tokens }) => tokens.length === candidate.length);
    const prefixes = matchingShortcuts(candidate).filter(({ tokens }) => tokens.length > candidate.length);
    if (exact.length) { event.preventDefault(); state.pendingCommand = []; showCommandHud(""); dispatchShortcut(exact[0].action); return; }
    if (prefixes.length) { event.preventDefault(); state.pendingCommand = candidate; showCommandHud(`[${candidate.join(" ")}] … ${nextShortcutHints(prefixes, candidate.length)}`); return; }
    if (state.pendingCommand.length) { state.pendingCommand = []; showCommandHud(""); return; }
  }, true);
  loadUsername(); load();
})();
