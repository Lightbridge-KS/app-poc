# Repository Guidelines

## Purpose

Monorepo of runnable application-stack PoCs: each `stacks/<stack-name>/` is a
self-contained app that answers one deployment question with **measured**
evidence. **Evidence outranks completeness** — a stack here exists to prove
something about how a stack behaves when actually run, so prefer the honest
narrow result over the impressive broad claim, and name what is still unproven.

Every factual claim in a stack's README must be reproducible by a recipe in
that stack's `justfile`. If there is no recipe, there is no claim.

## Layout invariants

- One stack per `stacks/<stack-name>/` directory; stacks never import from each
  other and never share a virtualenv, image, or lockfile.
- Every stack carries: `README.md` (the section contract below), `justfile`
  (the front door), and its own environment manifest — `pyproject.toml` +
  `uv.lock` for Python, `package.json` + lockfile for Node.
- Single repo rooted here. Stacks do not get their own `.git`.
- Stack names describe the stack, not the status: `shiny-docker`, not
  `shiny-python-docker-poc`. The repo is already the PoC.

## The README section contract

Every stack README carries these, in this order. Sections may be empty only if
genuinely inapplicable; they may not be silently omitted.

1. **Verified-on line** — date, OS/arch, and the versions that matter
   (`Verified 2026-08-14 on macOS / Apple Silicon, Docker 29.1.3, Dash 4.4.1`).
2. **Quick start** — the `just` recipes, in the order a newcomer runs them.
3. **What the app is** + a plain-text **dataflow diagram** and a module-split
   table (file → responsibility).
4. **Deliberate choices** — the two or three decisions a reader would otherwise
   assume were accidents, each with the reason.
5. **Evidence** — the payload. Measured output, pasted, with the command that
   produced it.
6. **⚠️ Not verified** — mandatory, see below.
7. **Lessons worth stealing** — the transferable gotchas.
8. **Not covered** — the scope boundary, so nobody mistakes an omission for a
   finding.

## Evidence rules

- **Measured, not recalled.** A number goes into a README only after a command
  produced it in the environment being described — inside the container, not on
  the host that built it. Show the command.
- **⚠️ Not verified is mandatory.** Every stack states what was *not* checked
  and how to close the gap. A PoC with no stated gap is a PoC nobody audited,
  and the browser-automation gap in both dashboards is the standing example.
- **Distinguish the container from the app.** Evidence about the transport
  ("the WebSocket accepted a connection") is not evidence about the feature
  ("the reactive graph updates all nine outputs"). Say which one you have.
- **Re-verification is part of the change.** Touching a stack means re-running
  its recipes and updating the verified-on date in *both* its README and the
  root table. A stale date is a useful signal; a wrong date is a lie.

## Entry points

- `just` is the front door for every stack; bare `just` lists recipes.
- Shared lifecycle verbs where the lifecycle is shared: `build up smoke dev
  down`. Evidence verbs stay stack-specific — `prove`, `brush`, `workers`,
  `preview`, `gate`, `drift-demo`, `gotchas`.
- Do **not** force a stack into verbs it doesn't have.
  `pydantic-openapi-react` has no container to start; its lifecycle is
  genuinely `setup gen check gate`.

## Docs

- Stack-specific docs live inside the stack (`stacks/pydantic-openapi-react/docs/`).
- No root `docs/` yet. The candidate for promotion is the container-lessons
  list duplicated between `shiny-docker` and `dash-docker`; it stays duplicated
  until a third containerized stack makes deduplication worth the indirection.
  Each stack README must stand alone when reached by a direct link.

## Adding a new stack

1. Scaffold with the ecosystem's own tool inside `stacks/<stack-name>/`
   (`uv init`, `npm create vite@latest`, …) — no nested git.
2. Write the `justfile` as you go; each new claim gets its recipe at the moment
   you first make the claim.
3. Write the README's Evidence section from pasted real output, and the guided
   parts last, from the finished stack.
4. Add the stack to the root `README.md` table, verdict and date included.

## Git

- Conventional Commits, scoped by stack when useful:
  `feat(dash-docker): add cross-filter brush`, `docs(shiny-docker): re-verify on Docker 30`.
- GitHub Flow: branch → PR → `main`. Direct commits to `main` are fine while
  the repo is this young.
