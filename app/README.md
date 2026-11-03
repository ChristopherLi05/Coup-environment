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
