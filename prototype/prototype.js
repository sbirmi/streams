(() => {
  "use strict";

  const initialStreams = [
    { id: "ship", number: 1, parent: null, summary: "Ship the first usable version", description: "Finish the **first vertical slice** before sharing it.\nKeep the default view fast to scan.\nMake conflicts visible without interrupting work.\nLeave room for comments beside the stream.\nDocument the final interaction decisions.", priority: 0, deadline: "Today", updated: "2h ago", owners: ["alex"], tags: ["release"], open: true, expanded: true, children: ["test", "docs"], comments: [{ author: "sam", updated: "18m ago", text: "The conflict response is now visible in both browser sessions.\nI also checked the stale revision warning against the current copy.\nThe remaining question is whether the refresh should preserve the selected row.\nIf it does, keyboard navigation should continue without a jump.\nI would also keep the conflict details available in the eventual modal.\nThis final line should be truncated in the compact view." }, { author: "alex", updated: "1h ago", text: "I left the deployment checklist open for one more pass.\nThe backup notes still need a final example. See @Stream:1 for the related work." }] },
    { id: "test", number: 2, parent: "ship", summary: "Add conflict handling tests", description: "Test the stale revision path with two browser sessions.\nCover both the rejected write and the refreshed copy.\nKeep the failure message easy to understand.", priority: 0, deadline: "Tomorrow", updated: "Yesterday", owners: ["alex", "sam"], tags: ["engineering"], open: true, expanded: false, children: [], comments: [{ author: "alex", updated: "Yesterday", text: "The stale revision path still needs a browser-level regression test.\nIt should leave the user’s draft intact." }] },
    { id: "docs", number: 3, parent: "ship", summary: "Review the deployment notes", description: "Left off at the backup and restore section.", priority: 1, deadline: "Fri", updated: "3d ago", owners: ["alex"], tags: ["docs"], open: true, expanded: false, children: [], comments: [{ author: "sam", updated: "3d ago", text: "Backup and restore are the only sections still needing review." }] },
    { id: "garden", number: 4, parent: null, summary: "Decide what to do about the garden", description: "Compare the low-maintenance options.", priority: 1, deadline: "Next week", updated: "5d ago", owners: ["alex"], tags: ["home"], open: true, expanded: false, children: [], comments: [{ author: "alex", updated: "5d ago", text: "The native-plant option looks like the simplest long-term choice." }] },
    { id: "taxes", number: 5, parent: null, summary: "Send the tax documents", description: "Waiting for the last statement.", priority: 2, deadline: "Mar 30", updated: "1w ago", owners: ["alex"], tags: ["admin"], open: true, expanded: false, children: [], comments: [{ author: "alex", updated: "1w ago", text: "Still waiting for the final statement before sending everything." }] },
    { id: "old", number: 6, parent: null, summary: "Look into the old side project", description: "Not urgent. Revisit when the current project is quieter.", priority: 2, deadline: null, updated: "3w ago", owners: ["alex"], tags: ["side-project"], open: false, expanded: false, children: [], comments: [{ author: "sam", updated: "3w ago", text: "Parking this until the current project is quieter." }] },
    { id: "resolved", number: 7, parent: null, summary: "Publish the prototype review", description: "The first layout review is complete and the decisions are recorded.", priority: 1, deadline: null, updated: "2w ago", owners: ["alex"], tags: ["done", "prototype"], open: false, expanded: false, children: [], comments: [{ author: "alex", updated: "2w ago", text: "Resolved after the header, viewbar, and comment rail review." }] },
  ];

  const state = { streams: structuredClone(initialStreams), selected: "ship", view: "priority", query: "", focusColumn: "stream", commentIndex: 0 };
  const list = document.querySelector("#stream-list");
  const viewSelect = document.querySelector("#view-select");
  const search = document.querySelector("#search");

  function visibleStreams() {
    return state.streams.filter((stream) => {
      const query = state.query.toLowerCase();
      const matchesQuery = !query || stream.summary.toLowerCase().includes(query) || stream.tags.some((tag) => tag.includes(query)) || stream.owners.some((owner) => owner.includes(query));
      return matchesQuery;
    });
  }
  function roots(items) { return items.filter((stream) => !stream.parent); }
  function descendants(id, items) { return items.filter((stream) => stream.parent === id); }
  function ordered(items) {
    if (state.view === "recent") return [...items].sort((a, b) => b.id.localeCompare(a.id));
    if (state.view === "stale") return [...items].sort((a, b) => Number(a.open) - Number(b.open) || b.priority - a.priority);
    return [...items].sort((a, b) => a.priority - b.priority || Number(b.open) - Number(a.open));
  }
  function visibleNavigationItems() {
    const items = visibleStreams();
    const result = [];
    function visit(stream) {
      result.push(stream);
      if (stream.expanded) descendants(stream.id, items).forEach(visit);
    }
    ordered(roots(items)).forEach(visit);
    return result;
  }
  function render() {
    const items = visibleStreams();
    list.innerHTML = items.length ? ordered(roots(items)).map((stream) => renderStream(stream, 0, items)).join("") : '<div class="empty-filter">No streams match this filter.</div>';
    const selectedRow = list.querySelector(`[data-id="${state.selected}"]`);
    selectedRow?.classList.add("is-selected");
    if (selectedRow && state.focusColumn === "comments") selectedRow.querySelector(`[data-comment-index="${state.commentIndex}"]`)?.classList.add("is-focused");
  }
  function renderStream(stream, depth, items) {
    const children = descendants(stream.id, items);
    const hasChildren = children.length > 0;
    const childMarkup = stream.expanded ? children.map((child) => renderStream(child, depth + 1, items)).join("") : "";
    const tags = [`<span class="tag priority-tag ${stream.priority === 0 ? "p0" : ""}">#P${stream.priority}</span>`, ...stream.tags.map((tag) => `<span class="tag">#${escapeHtml(tag)}</span>`), stream.deadline ? `<span class="due-tag">due ${escapeHtml(stream.deadline)}</span>` : ""].join("");
    return `<article class="stream-row ${stream.open ? "" : "is-closed"}" style="--depth: ${depth}" data-id="${stream.id}" tabindex="-1">
      <div class="stream-gutter"><button class="disclosure ${hasChildren ? "" : "is-empty"}" type="button" data-toggle="${stream.id}" aria-label="${stream.expanded ? "Collapse" : "Expand"}">${stream.expanded ? "⌄" : "›"}</button><span class="status-box" aria-label="${stream.open ? "Open" : "Closed"}">${stream.open ? "" : "✓"}</span></div>
      <div class="stream-main"><div class="stream-content"><div class="stream-title-line"><span class="stream-id" title="Stream ${stream.number}">${stream.number}</span><span class="stream-title editable-text" data-edit="summary" data-id="${stream.id}">${renderMarkdown(stream.summary)}</span><button class="stream-edit" type="button" data-edit-stream="${stream.id}" aria-label="Edit stream" title="Edit stream">✎</button></div><div class="stream-meta"><span class="updated">${escapeHtml(stream.updated)}</span><span class="owners">${escapeHtml(stream.owners.join(", "))}</span><span class="tag-list">${tags}</span></div>${stream.description ? `<div class="stream-description editable-text" data-edit="description" data-id="${stream.id}">${renderMarkdown(stream.description)}</div>` : ""}</div>${renderComments(stream)}</div>
    </article>${childMarkup}`;
  }
  function select(id, preserveCommentFocus = false) { state.selected = id; if (!preserveCommentFocus) { state.focusColumn = "stream"; state.commentIndex = 0; } render(); document.querySelector(`[data-id="${id}"]`)?.scrollIntoView({ block: "nearest" }); }
  function focusedStream() { return state.streams.find((stream) => stream.id === state.selected); }
  function moveHorizontal(direction) {
    const stream = focusedStream();
    if (!stream) return;
    if (direction > 0) {
      if (state.focusColumn === "stream" && stream.comments?.length) state.focusColumn = "comments";
      else if (state.focusColumn === "comments" && state.commentIndex < stream.comments.length - 1) state.commentIndex += 1;
    } else if (state.focusColumn === "comments" && state.commentIndex > 0) state.commentIndex -= 1;
    else state.focusColumn = "stream";
    render();
    document.querySelector(`[data-id="${state.selected}"] [data-comment-index="${state.commentIndex}"]`)?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }
  function moveVertical(direction) {
    const visibleItems = visibleNavigationItems();
    const currentIndex = visibleItems.findIndex((stream) => stream.id === state.selected);
    if (currentIndex < 0) return;
    const target = visibleItems[Math.max(0, Math.min(visibleItems.length - 1, currentIndex + direction))];
    if (!target) return;
    const targetCommentCount = target.comments?.length || 0;
    const preserveCommentFocus = state.focusColumn === "comments" && targetCommentCount > 0;
    if (preserveCommentFocus) state.commentIndex = Math.min(state.commentIndex, targetCommentCount - 1);
    select(target.id, preserveCommentFocus);
  }
  function renderMarkdown(value) { return escapeHtml(value).replace(/@Stream:(\d+)/g, (_, number) => renderStreamReference(Number(number))).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/`(.+?)`/g, "<code>$1</code>").replace(/\n/g, "<br>"); }
  function renderStreamReference(number) { const stream = state.streams.find((item) => item.number === number); const status = stream?.open ? "open" : "resolved"; return `<span class="stream-reference ${stream?.open ? "" : "is-closed"}" title="Stream ${number} · ${status}" data-stream-reference="${number}">${stream?.open ? "" : "✓ "}${number}</span>`; }
  function renderComments(stream) {
    if (!stream.comments?.length) return "";
    return `<div class="comment-rail" aria-label="Comments">${stream.comments.map((comment, index) => `<article class="comment-card" data-comment-index="${index}" tabindex="-1"><div class="comment-meta"><strong>${escapeHtml(comment.author)}</strong><span>${escapeHtml(comment.updated)}</span></div><div class="comment-body">${renderMarkdown(comment.text)}</div></article>`).join("")}</div>`;
  }
  function escapeHtml(value) { return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char])); }

  list.addEventListener("click", (event) => {
    const row = event.target.closest(".stream-row");
    const toggle = event.target.closest("[data-toggle]");
    const edit = event.target.closest("[data-edit-stream]");
    if (toggle) { const stream = state.streams.find((item) => item.id === toggle.dataset.toggle); stream.expanded = !stream.expanded; render(); return; }
    if (edit) { select(edit.dataset.editStream); return; }
    const comment = event.target.closest(".comment-card");
    if (comment) { state.selected = row.dataset.id; state.focusColumn = "comments"; state.commentIndex = Number(comment.dataset.commentIndex); render(); return; }
    if (row) select(row.dataset.id);
  });
  list.addEventListener("dblclick", (event) => {
    const editable = event.target.closest("[data-edit]");
    if (!editable) return;
    editable.contentEditable = "true";
    editable.focus();
    const range = document.createRange();
    range.selectNodeContents(editable);
    range.collapse(false);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  });
  list.addEventListener("blur", (event) => {
    const editable = event.target.closest('[contenteditable="true"]');
    if (editable) editable.contentEditable = "false";
  }, true);
  viewSelect.addEventListener("change", () => { state.view = viewSelect.value; render(); });
  search.addEventListener("input", () => { state.query = search.value.trim(); render(); });
  document.querySelector('[data-action="reset"]').addEventListener("click", () => { state.streams = structuredClone(initialStreams); state.selected = "ship"; state.view = "priority"; state.query = ""; state.focusColumn = "stream"; state.commentIndex = 0; viewSelect.value = "priority"; search.value = ""; render(); });
  const dialog = document.querySelector("#shortcuts-dialog");
  document.querySelector('[data-action="shortcuts"]').addEventListener("click", () => dialog.showModal());
  document.querySelector('[data-action="close-shortcuts"]').addEventListener("click", () => dialog.close());
  document.addEventListener("keydown", (event) => {
    if (event.key === "?" && document.activeElement.tagName !== "INPUT") dialog.showModal();
    if (event.key === "Escape" && dialog.open) dialog.close();
    if (["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName)) return;
    const visibleItems = visibleNavigationItems();
    const currentIndex = visibleItems.findIndex((stream) => stream.id === state.selected);
    if ((event.key === "j" || event.key === "ArrowDown") && currentIndex >= 0) { event.preventDefault(); moveVertical(1); }
    if ((event.key === "k" || event.key === "ArrowUp") && currentIndex >= 0) { event.preventDefault(); moveVertical(-1); }
    if (event.key === "h" || event.key === "ArrowLeft") { event.preventDefault(); moveHorizontal(-1); }
    if (event.key === "l" || event.key === "ArrowRight") { event.preventDefault(); moveHorizontal(1); }
    if (event.key === "o") { const stream = state.streams.find((item) => item.id === state.selected); if (stream) { stream.expanded = !stream.expanded; render(); } }
  });

  render();
})();
