# Embedded Reliability Data — Methodology & Schema

> A transferable engineering methodology for building **production-grade, drift-free data discipline** into embedded devices — so a fleet of devices can report its own health and yield.

**This repo is the free, open-source layer: the methodology + the event schema.** MIT licensed. Use it, adapt it, build it into your own product.

> ### ⚡ Try it now — no signup, no firmware changes
> Already have messy device logs? Open **[`tool/reliability-quickscan.html`](tool/reliability-quickscan.html)** in your browser, paste a CSV, and instantly see which units fail most and which error dominates. Runs fully client-side — your data never leaves the page.

> ### 🛰️ See the decision layer — interactive fleet twin
> Open **[`tool/fleet-twin-demo.html`](tool/fleet-twin-demo.html)** to play with a 200-unit fleet: switch scenarios, watch the yield histogram, and see how a *bimodal* distribution reveals a systemic batch defect — the ship-or-recall decision the methodology is built to answer. (Demo scenarios; the real twin runs on your devices' actual logs.)

---

## The problem this solves

You built a hardware prototype. It moves. It works. Then what?

Most solo developers and small teams get stuck in the same place: **the device runs, but you know nothing about its behavior, errors, or failures.** Build the tenth unit and you have no idea which one is healthy, which is about to die, or what your fleet yield is.

This isn't about how to spin a motor — there are a thousand free tutorials for that. It's the thing almost nobody covers but every production run hits: **how to build per-event, traceable, drift-free data discipline from your first line of code.**

---

## What's in this repo

| Path | Contents |
|------|----------|
| `methodology/` | The core methodology — the *why* and *how* of event-level data discipline. Device-agnostic. |
| `schema/` | The layered event schema spec (device-agnostic core + device-specific fields), with CSV/JSON consistency rules and Registry definitions. |

> Methodology is currently in Traditional Chinese (`*.zh-Hant.md`). English translation welcome via PR — see CONTRIBUTING.

---

## The six principles (TL;DR)

1. **One row per event** — never a counter as primary data. You can compute counters from events; never the reverse.
2. **Event/error names live in a Registry** — no hardcoded bare strings anywhere.
3. **Result and error code are separate columns** from event type — three orthogonal dimensions.
4. **Every row carries `machine_id` and `firmware_version`** — traceability from unit #1.
5. **CSV and JSON field names are identical** — no cross-format drift.
6. **Write what you *haven't* verified into the source code** — an honest risk register is engineering credibility.

---

## The event schema at a glance

```
timestamp_ms, machine_id, firmware_version, command_id, slot_id, event_type, duration_ms, result, error_code
```

```csv
0,EDEN001,v0.1.0,0,0,BOOT,0,OK,NONE
6680,EDEN001,v0.1.0,0,1,WATER,2500,OK,NONE
12100,EDEN001,v0.1.0,0,2,WATER,2480,FAIL,LOW_WATER
```

Full spec, field types, and Registry definitions in [`schema/`](schema/).

---

## How to use it

1. Read `methodology/` — understand the *why*. It's device-agnostic.
2. Steal the format design in `schema/`.
3. Map it onto your own device: build your own EventType and ErrorCode registries, give every unit an id and firmware version from day one.

---

## Beyond the methodology

This repo gives you the methodology, the schema, and two in-browser demo tools. The full source — a modular ESP32 firmware template, the complete physics-based digital-twin simulators, and a full real-world case study — is kept separate. If you'd find those useful, open an issue or reach out; I'm especially interested in hearing from people actually shipping hardware.

---

## License

MIT — see [LICENSE](LICENSE).

---

*A complete vertical stack — mechanics, firmware, data schema, simulation, frontend. This documents a real engineering thought process, not theory.*
