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

> **Status.** **Scenario A is implemented** and is what runs today. Scenario B
> (the national general database) is the planned next step; the code is laid out
> so it can be added without touching the existing layers.

---

## What is being modelled

| Real-world element              | In the simulation                                          |
| ------------------------------- | ---------------------------------------------------------- |
| Health post (*Posto de Saúde*)  | a `health-post` container that generates and sends records |
| Local data of each post         | A per-post `RegionalProfile` (formats + missing rate)      |
| Central SUS database            | the `sus-database` container that standardizes and stores  |
| National general database (B)   | An authoritative source that fills/corrects civil data     |
| Network between actors          | The Docker network (real HTTP requests)                    |
| Posts not talking to each other | Posts only ever message the database, never a peer         |

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
db_server.py                 entry point for the database container
post_runner.py               entry point for a health-post container
Dockerfile                   one image, shared by both roles
docker-compose.yml           database + N isolated post containers
.env                         tunable parameters (read by Compose)
└── src/
    ├── domain/              core data models — depends on nothing
    │   └── models.py        ConsultationRecord, StandardizedRecord
    ├── standardization/     format normalization (Strategy pattern)
    │   └── normalizers.py   CpfNormalizer, BirthDateNormalizer, SexNormalizer
    ├── generation/          synthetic data with regional variance
    │   ├── regional_profile.py
    │   └── record_generator.py
    ├── metrics/             metric aggregation (pure, no transport)
    │   └── report.py        SimulationReport
    ├── database.py          IngestionEngine — the central database core
    └── net/                 network transport (the Docker deployment)
        ├── protocol.py      wire format + endpoint paths
        ├── server.py        HTTP database server (wraps IngestionEngine)
        └── client.py        health-post HTTP client
```

The simulation logic lives in transport-free layers (domain, generation,
standardization, metrics) plus the `IngestionEngine` that standardizes and
stores each record. The `net` layer is just the wire: it carries records from
the post containers to the database container as real HTTP requests.

### Design principles applied

- **Single Responsibility** — generation, standardization, transport and
  metrics each live in their own module.
- **Open/Closed** — supporting a new field means adding a normalizer; no
  existing class changes.
- **Dependency Inversion** — `IngestionEngine` depends on the `FieldNormalizer`
  *protocol*, not on concrete normalizers (they are injected).
- **Testability** — domain, standardization and metrics layers are free of any
  transport concern and can be unit-tested in isolation.
- **Reproducibility** — every random choice is seed-driven. Pinning each post's
  index makes its seed `BASE_SEED + index*1000`, so a run becomes fully
  repeatable and a future Scenario B can reuse the exact same data (see the
  reproducibility note under *Running*).

### Why the actor model

Posts and the database run as separate containers that communicate **only**
through HTTP requests across the Docker network. This mirrors the proposal's
isolated containers for real: each post is its own container with no route to
its peers, and the only legal destination for a post's data is the central
database.

---

## Running

The simulation runs entirely on Docker — one container per actor. The only
requirement on the host is Docker with Compose v2 (no Python, no dependencies).

Run it the first time (the `--build` builds the image):

```bash
docker compose up --build
```

This starts one `sus-database` container and five `health-post` containers on a
shared Docker network. Each post submits its records to the database over HTTP;
once the posts go quiet, the database prints the final report to its logs and
every container exits on its own.

> Run with plain `docker compose up`, **not** `--abort-on-container-exit`: that
> flag kills the database the moment the first post exits, before it can print
> the report.

### You don't need `--build` every time

`--build` only rebuilds the image, which is needed **after you change the code
or the Dockerfile**. On every other run just use:

```bash
docker compose up
```

It reuses the already-built `sus-sim:latest` image (one image, shared by the
database and all the posts — nothing is duplicated per post).

### Cleaning up (optional)

The containers stop on their own when the run ends, but they stay on disk in an
"exited" state. To remove them and the network:

```bash
docker compose down
```

This is just housekeeping — you can re-run `docker compose up` without it. It is
worth doing when you *lower* the post count (e.g. went from `--scale
health-post=8` back to 3), so the leftover containers don't linger as orphans.

### Changing the number of posts

The post count is just how many replicas of the `health-post` service you ask
for — the database discovers them at runtime, nothing else needs to change:

```bash
docker compose up --scale health-post=8
```

Each replica derives a distinct seed from its container id, so every post gets
its own regional profile automatically.

### Tuning the parameters

The tunable parameters live in the [`.env`](.env) file, which Compose reads
automatically. Edit a value there and re-run `docker compose up`:

```bash
POSTS=5             # number of health posts (also settable with --scale)
CONSULTATIONS=200   # consultations each post generates
BASE_SEED=42        # base random seed (shifts the whole population)
IDLE_TIMEOUT=5      # seconds of silence before the report is finalized
```

You can also override any of them for a single run, without editing the file:

```powershell
# PowerShell
$env:BASE_SEED=7; $env:CONSULTATIONS=500; docker compose up
```

```bash
# bash
BASE_SEED=7 CONSULTATIONS=500 docker compose up
```

| Variable        | Default | Description                                            |
| --------------- | ------- | ------------------------------------------------------ |
| `POSTS`         | 5       | Number of health posts (also settable with `--scale`)  |
| `CONSULTATIONS` | 200     | Consultations generated per post                       |
| `BASE_SEED`     | 42      | Shifts the whole population of posts                    |
| `IDLE_TIMEOUT`  | 5       | Seconds of silence before the report is finalized      |
| `POST_INDEX`    | —       | Set per post for an exactly reproducible per-post seed  |

The database's `GET /report` endpoint is also published on `localhost:8000` if
you want to poll the metrics while a run is in progress.

> **Reproducibility.** With `--scale` (or the `POSTS` replicas), seeds come from
> the run-varying container ids, so the exact numbers shift between runs while
> the aggregate picture is stable. For a run that is reproducible down to the
> per-post seed, give each post a fixed `POST_INDEX` (its seed becomes
> `BASE_SEED + index*1000`).

### Example output

```
=== Simulation report: Scenario A - no national general database (Docker) ===

  Access rate ............... 100.00%   (1000/1000 records)
  Utilization rate ..........  61.40%   (614/1000 analysis-ready)
  Integrated data volume .... 1000 records
  Inconsistency correction ..  73.78%   (1401/1899 fixed)
  Average response time ..... 1.89 ms
```
