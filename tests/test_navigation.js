const assert = require("node:assert/strict");
const { walkNavigationItems } = require("../app/static/js/app.js");

function makeTree() {
  const streams = [
    { id: "root", parent: null, expanded: true },
    { id: "child", parent: "root", expanded: true },
    { id: "grandchild", parent: "child", expanded: true },
    { id: "collapsed", parent: "root", expanded: false },
    { id: "hidden", parent: "collapsed", expanded: true },
    { id: "sibling", parent: null, expanded: true },
  ];
  const childrenOf = (id) => streams.filter((stream) => stream.parent === id);
  const ordered = (items) => [...items].sort((a, b) => a.id.localeCompare(b.id));
  return { streams, childrenOf, ordered };
}

function visitsVisibleRows() {
  const { streams, childrenOf, ordered } = makeTree();
  const roots = ordered(childrenOf(null));
  const result = walkNavigationItems(roots, childrenOf, ordered, (stream) => stream.expanded);

  assert.deepEqual(result.map((stream) => stream.id), [
    "root", "child", "grandchild", "collapsed", "sibling",
  ]);
}

function toleratesCycles() {
  const streams = [
    { id: "a", parent: null, expanded: true },
    { id: "b", parent: "a", expanded: true },
    { id: "a", parent: "b", expanded: true },
  ];
  const childrenOf = (id) => streams.filter((stream) => stream.parent === id);
  const ordered = (items) => items;

  assert.deepEqual(
    walkNavigationItems([streams[0]], childrenOf, ordered, () => true).map((stream) => stream.id),
    ["a", "b"],
  );
}

visitsVisibleRows();
toleratesCycles();
console.log("navigation tests: 2 passed");
