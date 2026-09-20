(() => {
  "use strict";

  const list = document.querySelector("#transaction-list");
  const query = document.querySelector("#transaction-query");
  const kind = document.querySelector("#transaction-kind");
  const state = document.querySelector("#transaction-state");
  const count = document.querySelector("#transaction-count");
  const filters = document.querySelector("#transaction-filters");
  const detail = document.querySelector("#transaction-detail");
  let transactions = [];

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));
  }

  function dateLabel(value) {
    if (!value) return "Unknown time";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
  }

  function relationship(transaction) {
    if (!transaction.target_transaction_id) return "";
    const verb = transaction.kind === "redo" ? "redo of" : "undo of";
    return `${verb} ${transaction.target_transaction_id}`;
  }

  function render() {
    const needle = query.value.trim().toLowerCase();
    const visible = transactions.filter((transaction) => {
      const haystack = [transaction.id, transaction.actor, transaction.action_type, transaction.summary, transaction.target_transaction_id].join(" ").toLowerCase();
      return (!needle || haystack.includes(needle)) && (!kind.value || transaction.kind === kind.value) && (!state.value || transaction.state === state.value);
    });
    count.textContent = `${visible.length} of ${transactions.length} transaction${transactions.length === 1 ? "" : "s"}`;
    if (!visible.length) {
      list.innerHTML = '<div class="empty-filter">No transactions match these filters.</div>';
      return;
    }
    list.innerHTML = visible.map((transaction) => {
      const abandoned = transaction.state === "abandoned";
      const classes = `transaction-row${abandoned ? " is-abandoned" : ""}`;
      const relation = relationship(transaction);
      return `<article class="${classes}" data-transaction-id="${escapeHtml(transaction.id)}">
        <div class="transaction-main">
          <div class="transaction-title-line"><span class="transaction-kind kind-${escapeHtml(transaction.kind)}">${escapeHtml(transaction.kind)}</span><strong>${escapeHtml(transaction.summary || transaction.action_type)}</strong>${abandoned ? '<span class="transaction-branch-label">abandoned branch</span>' : ""}</div>
          <div class="transaction-meta"><span>${escapeHtml(transaction.actor)}</span><time datetime="${escapeHtml(transaction.created_at)}">${escapeHtml(dateLabel(transaction.created_at))}</time><span class="transaction-id">${escapeHtml(transaction.id)}</span></div>
        </div>
        <div class="transaction-state state-${escapeHtml(transaction.state)}">${escapeHtml(transaction.state)}</div>
        ${relation ? `<div class="transaction-relation">${escapeHtml(relation)}</div>` : ""}
        <button class="secondary-button transaction-detail-button" type="button" data-detail="${escapeHtml(transaction.id)}">Details</button>
      </article>`;
    }).join("");
  }

  async function showDetail(transactionId) {
    detail.hidden = false;
    detail.innerHTML = "Loading transaction details…";
    try {
      const response = await fetch(`/api/transactions/${encodeURIComponent(transactionId)}`, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`Unable to load details (${response.status})`);
      const transaction = (await response.json()).transaction;
      const objects = (transaction.related_objects || []).map((item) => `<li>${escapeHtml(item.object_type)} ${escapeHtml(item.object_id)}${item.summary ? ` · ${escapeHtml(item.summary)}` : ""}</li>`).join("");
      detail.innerHTML = `<strong>${escapeHtml(transaction.summary)}</strong><span>${escapeHtml(transaction.actor)} · ${escapeHtml(dateLabel(transaction.created_at))}</span><ul>${objects || "<li>No object details</li>"}</ul>`;
      detail.scrollIntoView({ block: "nearest" });
    } catch (error) {
      detail.textContent = error.message;
    }
  }

  async function load() {
    try {
      const response = await fetch("/api/transactions?limit=500", { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`Unable to load history (${response.status})`);
      const payload = await response.json();
      transactions = Array.isArray(payload.transactions) ? payload.transactions : [];
      render();
    } catch (error) {
      count.textContent = "History unavailable";
      list.innerHTML = `<div class="empty-filter">${escapeHtml(error.message)}<br><a href="/">Return to streams</a></div>`;
    }
  }

  [query, kind, state].forEach((control) => control.addEventListener("input", render));
  filters.addEventListener("reset", () => window.setTimeout(render));
  list.addEventListener("click", (event) => {
    const button = event.target.closest("[data-detail]");
    if (button) showDetail(button.dataset.detail);
  });
  load();
})();
