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

> **Status.** **Both scenarios are implemented.** Scenario A runs by default;
> Scenario B adds a `national-database` container that the central database
> consults to complete the civil data it could not resolve on its own. It was
> added without changing the existing domain, generation, standardization or
> metrics layers — only an optional reconciler was injected into the central
> database core (see *Running → Scenario B*).

---

## What is being modelled

| Real-world element              | In the simulation                                          |
| ------------------------------- | ---------------------------------------------------------- |
| Health post (*Posto de Saúde*)  | a `health-post` container that generates and sends records |
| Local data of each post         | A per-post `RegionalProfile` (formats + missing rate)      |
| Central SUS database            | the `sus-database` container that standardizes and stores  |
| National general database (B)   | a `national-database` container the central database queries |
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
db_server.py                 entry point for the central database container
post_runner.py               entry point for a health-post container
national_server.py           entry point for the national database container (B)
Dockerfile                   one image, shared by all three roles
docker-compose.yml           database + N isolated posts + national database (B)
.env                         tunable parameters (read by Compose)
└── src/
    ├── domain/              core data models — depends on nothing
    │   └── models.py        ConsultationRecord, StandardizedRecord
    ├── standardization/     format normalization (Strategy pattern)
    │   └── normalizers.py   CpfNormalizer, BirthDateNormalizer, SexNormalizer
    ├── generation/          synthetic data with regional variance
    │   ├── regional_profile.py
    │   └── record_generator.py
    ├── national/            authoritative civil registry (Scenario B core)
    │   └── national_database.py   NationalDatabase — fills/corrects civil data
    ├── metrics/             metric aggregation (pure, no transport)
    │   └── report.py        SimulationReport
    ├── database.py          IngestionEngine — the central database core
    └── net/                 network transport (the Docker deployment)
        ├── protocol.py          wire format + endpoint paths
        ├── server.py            HTTP central database server (wraps IngestionEngine)
        ├── client.py            health-post HTTP client
        ├── national_server.py   HTTP national database server (wraps NationalDatabase)
        └── national_client.py   client the central database uses to reach it
```

The simulation logic lives in transport-free layers (domain, generation,
standardization, metrics, national) plus the `IngestionEngine` that standardizes
and stores each record. The `net` layer is just the wire: it carries records
from the post containers to the central database, and — in Scenario B — the
central database's reconcile requests to the national database, as real HTTP
requests.

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

### Both scenarios at a glance

```bash
# Scenario A — isolated posts + central database (default, no national base)
docker compose up --build

# Scenario B — adds the national database that completes the civil data
SCENARIO=B docker compose --profile scenario-b up --build
```

```powershell
# PowerShell equivalents
docker compose up --build
$env:SCENARIO="B"; docker compose --profile scenario-b up --build
```

The only differences are the **`--profile scenario-b`** flag (which starts the
extra `national-database` container) and **`SCENARIO=B`** (which tells the central
database to consult it). Everything else — posts, scaling, tuning, the final
report — works the same in both. Each run prints its own report labelled with the
scenario it ran; compare the two reports to see what the national database adds.
Details of Scenario B are in [its own section](#scenario-b--adding-the-national-database) below.

### Scenario A (default)

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

### Scenario B — adding the national database

Scenario B starts a third actor: the `national-database` container. The central
database consults it for every record, asking it to supply the essential civil
fields it could not complete on its own. The national database talks only to the
central database — posts never see it.

It lives behind a Compose **profile**, so Scenario A stays a plain
`docker compose up`. To run Scenario B, activate the profile and set `SCENARIO=B`
so the central database knows to consult it:

```bash
# bash
SCENARIO=B docker compose --profile scenario-b up --build
```

```powershell
# PowerShell
$env:SCENARIO="B"; docker compose --profile scenario-b up --build
```

The national database is **not** an oracle. Two real-world limits keep
Scenario B short of a perfect score, as the proposal expects:

- **Identification** — a patient can only be looked up through a usable CPF. A
  record whose CPF arrived missing cannot be matched, so it stays incomplete.
- **Coverage** — the registry holds only a `COVERAGE` fraction of identifiable
  patients (default `0.9`); the rest cannot be completed even once identified.

Compared with Scenario A on the same data, the **access rate** stays the same
(records get through either way) while the **utilization** and **inconsistency
correction** rates rise, quantifying exactly what the national database adds.

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
| `SCENARIO`      | A       | `A` (isolated) or `B` (consult the national database)   |
| `COVERAGE`      | 0.9     | Scenario B: share of identifiable patients on file      |
| `REPORT_DIR`    | reports | Where the report is also saved as JSON + CSV            |
| `POST_INDEX`    | —       | Set per post for an exactly reproducible per-post seed  |

The database's `GET /report` endpoint is also published on `localhost:8000` if
you want to poll the metrics while a run is in progress.

### Saved report (JSON + CSV)

Besides printing to the log, the central database writes the final report to
`REPORT_DIR` (mounted to **`./reports`** on the host) when the run ends:

- `report-scenario-<a|b>.json` — the complete report (every metric plus the
  per-field breakdown).
- `report-scenario-<a|b>.csv` — just the per-field breakdown table, ready for a
  spreadsheet.

The filename carries the scenario, so a Scenario A run and a Scenario B run land
side by side instead of overwriting each other — which is how you compare them.

> **Reproducibility.** With `--scale` (or the `POSTS` replicas), seeds come from
> the run-varying container ids, so the exact numbers shift between runs while
> the aggregate picture is stable. For a run that is reproducible down to the
> per-post seed, give each post a fixed `POST_INDEX` (its seed becomes
> `BASE_SEED + index*1000`).

### Example output

```
=== Simulation report: Scenario A - no national general database (Docker) ===

  Access rate ............... 100.00%   (1000/1000 records)
  Utilization rate ..........  41.10%   (411/1000 analysis-ready)
  Integrated data volume .... 1000 records
  Inconsistency correction ..  59.08%   (1240/2099 fixed)
  Average response time ..... 1.89 ms

  Missing civil data by field (recovered by national base):
    cpf ..........  208 missing,    0 recovered
    birth_date ...  217 missing,    0 recovered
    sex ..........  219 missing,    0 recovered
    city .........  215 missing,    0 recovered
```

Re-running the same data under Scenario B, the access rate is unchanged while
utilization and correction climb — and the breakdown shows exactly where: the
national base recovers `birth_date`, `sex` and `city`, but **never `cpf`**,
because without a CPF the patient cannot be identified in the first place.

```
=== Simulation report: Scenario B - with national general database (Docker) ===

  Access rate ............... 100.00%   (1000/1000 records)
  Utilization rate ..........  75.80%   (758/1000 analysis-ready)
  Integrated data volume .... 1000 records
  Inconsistency correction ..  81.04%   (1701/2099 fixed)
  Average response time ..... 2.40 ms

  Missing civil data by field (recovered by national base):
    cpf ..........  208 missing,    0 recovered
    birth_date ...  217 missing,  154 recovered
    sex ..........  219 missing,  152 recovered
    city .........  215 missing,  155 recovered
```
