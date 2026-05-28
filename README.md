# SUS Data Integration & Standardization — Simulation

A simulation of the data flow inside Brazil's public health system (SUS),
built to study what happens to data quality when many health posts — each
following its own questionnaire standard — send patient records to a central
database, and how much an authoritative national database can improve that.

---

## Purpose

The SUS is large and regionally heterogeneous. During a consultation, the data
a patient reports is stored locally, but the questionnaire used at each post
may not match the standard expected by the central database. The same field
ends up recorded differently across municipalities, which harms any
cross-municipality analysis.

The simulation **measures data quality across two scenarios** and compares them
using the same metrics, to quantify the value of standardizing and integrating
the data:

- **Scenario A — no national general database.** Isolated health posts send
  records to the central SUS database. The central database can standardize the
  formats it recognizes, but there is no external authoritative source, so civil
  data that arrived missing or in an unrecognizable form cannot be repaired.

- **Scenario B — with national general database.** A national database talks
  only to the central SUS database, filling in missing civil data and correcting
  inconsistencies the central database could not resolve on its own.

Comparing the two answers the central question of the proposal: *how much do
access and usability of the data improve once a national database completes and
reconciles it?*

---

## What is being modelled

| Real-world element              | In the simulation                                      |
| ------------------------------- | ------------------------------------------------------ |
| Health post (*Posto de Saúde*)  | `HealthPost` — a thread that generates and sends records |
| Local data of each post         | A per-post `RegionalProfile` (formats + missing rate)  |
| Central SUS database            | `SusDatabase` — a thread that standardizes and stores  |
| National general database (B)   | An authoritative source that fills/corrects civil data |
| Network between actors          | Message queues + simulated latency                     |
| Posts not talking to each other | Posts only ever message the database, never a peer     |

Each post follows its own **regional profile**: a CPF style, a date style, a
sex-encoding style, and a probability of leaving essential fields blank. That
is what makes records from different posts incompatible.

The central database can **normalize the formats it recognizes** (e.g. turn
`01/02/1990` or `01-02-1990` into `1990-02-01`, `1`/`Male` into `M`, an
unpunctuated CPF into `000.000.000-00`). What it cannot do on its own — invent
missing or unrecognizable civil data — is exactly what the national database
contributes in Scenario B.

---

## Metrics

The five metrics from the proposal diagram, computed in `SimulationReport`:

| Metric                       | Meaning                                                     |
| ---------------------------- | ----------------------------------------------------------- |
| **Access rate**              | Share of sent records that reached the central database     |
| **Utilization rate**         | Share of integrated records that are usable for analysis    |
| **Integrated data volume**   | Number of records effectively stored centrally              |
| **Inconsistency correction** | Share of detected inconsistencies that were corrected       |
| **Average response time**    | Mean round-trip time per record (ms)                        |

The comparison is expected to show a similar **access rate** in both scenarios
(records get through either way), while the **utilization** and **correction**
rates rise in Scenario B, where the national database repairs the civil data the
central database could not fix alone.

---

## Architecture

The project follows a layered, modular design. Dependencies point **inward**:
outer layers know about inner ones, never the reverse.

```
main.py                      composition root / CLI
└── src/
    ├── config.py            SimulationConfig (tunable, seed-driven params)
    ├── domain/              core data models — depends on nothing
    │   └── models.py        ConsultationRecord, StandardizedRecord
    ├── standardization/     format normalization (Strategy pattern)
    │   └── normalizers.py   CpfNormalizer, BirthDateNormalizer, SexNormalizer
    ├── generation/          synthetic data with regional variance
    │   ├── regional_profile.py
    │   └── record_generator.py
    ├── metrics/             metric aggregation (pure, no threading)
    │   └── report.py        SimulationReport
    ├── actors/              concurrency + messaging
    │   ├── messages.py      IngestRequest
    │   ├── health_post.py   HealthPost  (producer actor)
    │   └── sus_database.py  SusDatabase (central actor)
    └── simulation/          scenario orchestration
        └── scenario_a.py    scenario orchestrator
```

### Design principles applied

- **Single Responsibility** — generation, standardization, transport, metrics
  and orchestration each live in their own module.
- **Open/Closed** — supporting a new field means adding a normalizer; no
  existing class changes.
- **Dependency Inversion** — `SusDatabase` depends on the `FieldNormalizer`
  *protocol*, not on concrete normalizers (they are injected).
- **Testability** — domain, standardization and metrics layers are free of any
  threading concern and can be unit-tested in isolation.
- **Reproducibility** — every random choice is seed-driven via
  `SimulationConfig`, so a run is fully repeatable and the two scenarios use the
  exact same data, making the comparison fair.

### Why the actor model

Posts and the database run as separate threads that communicate **only**
through message queues, with a small simulated network latency. This mirrors
the proposal's isolated containers: posts cannot reach one another, and the
only legal destination for a post's data is the central database.

---

## Running

Requires Python 3.10+ (standard library only — no dependencies).

```bash
python main.py
```

With custom parameters:

```bash
python main.py --posts 8 --consultations 500 --seed 7
```

| Flag              | Default | Description                        |
| ----------------- | ------- | ---------------------------------- |
| `--posts`         | 5       | Number of health posts (actors)    |
| `--consultations` | 200     | Consultations generated per post   |
| `--seed`          | 42      | Base random seed (reproducibility) |

### Example output

```
=== Simulation report: Scenario A - no national general database ===

  Access rate ............... 100.00%   (1000/1000 records)
  Utilization rate ..........  41.10%   (411/1000 analysis-ready)
  Integrated data volume .... 1000 records
  Inconsistency correction ..  59.08%   (1240/2099 fixed)
  Average response time ..... 5.25 ms
```
