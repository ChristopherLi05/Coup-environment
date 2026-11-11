# The Court

The React interface uses a local Python API so matches run through the
repository's `src.Game` engine and the existing Python agents in `agents/`.
Agents are discovered from `agents/` when the API starts; new `Player`
subclasses with `choose_action(game)` and `decide(kind, context)` are available
in the setup menu without adding a TypeScript policy.

## Run locally

Use two terminals from this directory:

```bash
npm install
npm run dev
```

```bash
npm run dev:api
```

The Vite development server proxies `/api` requests to the Python API on
`127.0.0.1:8000`. The API uses only the Python standard library and imports
`src/` and `agents/` from the repository root.

Build and lint the client with:

```bash
npm run build
npm run lint
```

## Deploy to GitHub Pages

The repository includes a GitHub Actions workflow that builds `app/` and
deploys it to GitHub Pages when changes are pushed to `main`. In the repository
settings, set **Pages → Build and deployment → Source** to **GitHub Actions**.
After the workflow completes, the site is available at
https://punnpunnpunn.github.io/Coup-environment/.

GitHub Pages only hosts the static React app; it does not run the Python API.
The game interface needs the API endpoints served by `server.py`, so gameplay
will remain unavailable on the Pages site until the API is deployed to a
separate host and the frontend is configured to use that host.
