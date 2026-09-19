# Streams UI prototype

This is a standalone, dependency-free prototype for reviewing the first-pass UI direction. It is intentionally separate from the application implementation and uses in-memory mock data.

## Run locally

From the repository root:

```sh
python3 -m http.server 8080 --directory prototype
```

Then open <http://127.0.0.1:8080/>.

The prototype is not a production UI and does not connect to SQLite or the Flask app.

The current pass shows mock comments in a horizontally scrollable rail beside each stream. Add/reorder controls remain intentionally omitted. Double-click a summary or description to preview the “plain when reading, editable when active” behavior.
