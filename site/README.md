# ZAPFISH — the whole site

One folder, one server, three pages, one navigation bar:

- `index.html` — **Observatory** (home): Wire → Fire (live 71,721-neuron brain) →
  Predict → Cognition → Decide → Everyday tasks cards.
- `tasks.html?task=tabletennis|bike|dog` — **Tasks**: the 545-cell brain model runs
  live in the browser and holds a paddle, handlebars or a leash. Worlds are modules
  (`dog.js` is the template).
- `trading.html` — **Trading desk**: the STONKFLY-style pixel scene, the story, the
  honesty box, and the engine's latest paper observation.

Serve: `python -m http.server 8140 --bind 127.0.0.1` from this folder → http://localhost:8140

Shared: `vendor/` (three.js r170 + addons), `assets/`, `data/` (brain positions,
activity, web model, prediction traces, HUD raster). Source projects that fed this
build: `../zapfish-observatory`, `../zapfish-tasks`, `../zapfish` (page) and
`../zapfish/engine` (Python trading engine). `tools/unify.py` re-applies the nav and
cross-links after copying fresh page files in.

Deploy: the folder is static; zip it with Python (not Compress-Archive) for Netlify or
drop it on Cloudflare Pages. CA and X are TBA on purpose.
