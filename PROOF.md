# What the PoCs Prove

One line per stack — the claim each one earned with measured evidence, and the
gap that claim does **not** cover. Full numbers, commands, and the complete
⚠️ Not verified sections live in each stack's README.

| Stack | What it proves | ⚠️ Not verified |
|---|---|---|
| [`shiny-docker`](stacks/shiny-docker) | Shiny for Python containerizes and serves a stateful WebSocket dashboard — but session state lives in-process, so a load balancer in front of it **must** use sticky sessions, and plotnine drags scipy + statsmodels in for an 863 MB image. | Live browser reactivity. The extension was disconnected, so nobody clicked a filter and watched all nine outputs move. The WebSocket transport was proven in this container setup — that is evidence about the container, not about this reactive graph. Close it: `just up`, open `localhost:8000`, toggle a species. |
| [`dash-docker`](stacks/dash-docker) | The same dashboard on Dash scales **statelessly**: inputs ride in the HTTP POST body, so 4 gunicorn workers return one identical answer with no stickiness, and dropping pandas/numpy entirely lands the image at 500 MB. | The UI driven in a real browser. Every callback returns correct data over HTTP, including the cross-filter path — but look, feel, Bootstrap at real viewport widths, brush gesture and console errors are unchecked. Close it: `just up`, drag a box over the Gentoo cluster, confirm everything follows. |
| [`pydantic-openapi-react`](stacks/pydantic-openapi-react) | Pydantic models can **be** the API contract: `openapi.json` is generated without booting a server, TypeScript is generated downstream, and schema drift surfaces as a compile error instead of a runtime 422. | The stack has **no ⚠️ Not verified section at all** — the contract's mandatory gap statement is missing, and its verified-on date is reconstructed from the working session rather than stamped by a run. Close it: `just gate`, re-stamp the date, and write the section. |
| [`genui-controlled-nextjs`](stacks/dynamic-dashboard/genui-controlled-nextjs) | An LLM can drive a **Controlled-tier** generative UI deterministically: with two tools whose Zod schemas carry every legal column as an enum, `gpt-5.6-terra` picked the right tool 20/20 and produced byte-identical props 20/20 — *after* the one free-text prop (`title`) was deleted; with it present, `title` was the only field that drifted (2/4 intents). 3/3 out-of-catalog prompts were refused in text with zero tool calls. | The UI under *automation*. Every tool call and computed row was verified over HTTP, and KS drove the UI by hand on 2026-09-03 (prompts typed, cards rendered) — but no browser driver has asserted the caption, the `spec` flip, or the layout at narrow widths. Close it: automate `localhost:3000`, click the first suggestion, assert the caption and the spec JSON, save the screenshot. |

The first two are the same app built twice — a controlled pair, so the
statefulness and image-size gaps between them are framework findings, not
application noise. See the root [`README.md`](README.md) for the side-by-side.

All three dashboards share the same standing gap: **browser automation has not been
run against any of them**. `genui-controlled-nextjs` was at least driven by hand; for the
other two, any claim about how the UI feels is unproven.
