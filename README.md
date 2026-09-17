# Infra Host Documentation Generator

- `templates/execution-environment.j2`: reusable Jinja2 FQDN template.
- `sites/`: site-specific YAML files (one per site/environment).
  - `sites/infra-dev.yaml`: Infra Dev site values.
- `render.py`: reusable Jinja2 rendering module.
- `split.py`: reusable AZ module.
- `generate.py`: entry point.
- `generated/infratest-components.yaml`: FQDN-only validation file.
- `generated/de_mgmt_fra11-1.yaml`
- `generated/de_mgmt_fra11-2.yaml`
- `generated/de_workloads_fra11-1.yaml`
- `generated/de_workloads_fra11-2.yaml`

## Project structure

```text
infra_host_generator/
├── templates/
│   └── execution-environment.j2
│
├── sites/
│   ├── infra-dev.yaml
│   └── ...
│
├── render.py
├── split.py
├── generate.py
└── generated/
```

## Install

```bash
pip install Jinja2 PyYAML
```

## Run

Generate documentation for a specific site:

```bash
python generate.py --site sites/infra-dev.yaml
```

The main output is `generated/infratest-components.yaml`.

## Site YAML structure

The site YAML uses a generic, data-driven `networks` list. Each network entry
defines a network type (management, workloads) and its availability zones.

Adding an AZ to an existing supported network type requires **only** a YAML
change — the Jinja2 template iterates over whatever is defined.

A new network **type** (e.g. `dmz`) would require adding its naming rules to
the template, because the template must know the hostname convention for each
type.

```yaml
environment: idev
domain: nzero.dev
co: de
product: Infra
env_name: Dev

networks:
  - type: management
    label: Mgmt
    host_prefix: m
    jumphost_ids: [3, 4, 11, 12, 13]
    azs:
      - number: 1
        network_hostname: defraama
        region: fra11
        compute_qty: 3
      - number: 2
        network_hostname: defraamb
        region: fra11
        compute_qty: 3

  - type: workloads
    label: Workloads
    host_prefix: w
    azs:
      - number: 1
        network_hostname: defraawa
        region: fra11
        compute_qty: 0
      - number: 2
        network_hostname: defraawb
        region: fra11
        compute_qty: 0
```

### Network-level fields

| Field | Purpose |
|-------|---------|
| `type` | `management` or `workloads`; drives which sections are generated (Panorama, jumphosts, gridmasters are management-only) |
| `label` | Used in generated YAML keys (e.g. `Infra Dev Mgmt AZ1`) |
| `host_prefix` | The `m`/`w` letter in compute/jumphost FQDNs |
| `jumphost_ids` | List of jumphost ID numbers (management only); if missing or empty, `jumphosts` section is omitted |

### AZ-level fields

| Field | Purpose |
|-------|---------|
| `number` | AZ number; drives `z{N}` suffix and `AZ{N}` label |
| `network_hostname` | Complete hostname component (e.g. `defraama`) — must not be shortened |
| `region` | Region string (e.g. `fra11`) |
| `compute_qty` | Number of compute hosts to generate; `0` or missing produces `[]` |

### Optional data handling

If an optional field is missing, the template does not generate invalid FQDNs:

- Missing `jumphost_ids` → `jumphosts` section omitted entirely
- Missing `compute_qty` → treated as `0`, produces `[]`
- No management networks → `security` and `jumphosts` sections omitted

## Storage

Storage/NetApp FQDNs are mentioned in `infra_host_generator_README.md` as a
planned future section but were never implemented in the template. Storage is
**out of current scope**.

## Adding another site

1. Create a new YAML file under `sites/` (for example `sites/infra-prod.yaml`).
2. Copy the `networks` structure from `sites/infra-dev.yaml` and fill in the
   values for the new site.
3. Run the generator with the new site file:

```bash
python generate.py --site sites/infra-prod.yaml
```

The same Jinja2 template (`templates/execution-environment.j2`) is reused for
every site.  Only the site YAML file changes.

## Adding an AZ

Add a new entry to the `azs` list under the relevant network in the site YAML.
No template change is needed — the Jinja2 loops iterate over all AZs.

```yaml
    azs:
      - number: 1
        ...
      - number: 2
        ...
      - number: 3                # new AZ — automatically picked up
        network_hostname: defraamc
        region: fra11
        compute_qty: 2
```

## Panorama naming convention

Panorama uses the corrected format:

`{co}-mgmt-{region}-1-panorama.infra.{domain}`

Generated for each management AZ via a Jinja2 loop. Panorama is **not** derived
from the network hostname — it uses the `region` field directly.

## Validation

`render.py` validates required fields at three levels before rendering.
A `ValueError` is raised if any are missing.

- **Root-level**: `environment`, `domain`, `co`, `product`, `env_name`, `networks`
- **Network-level** (each `networks` entry): `type`, `label`, `host_prefix`, `azs`
- **AZ-level** (each `azs` entry): `number`, `network_hostname`, `region`

Optional fields (`compute_qty`, `jumphost_ids`) are not validated — the
template handles their absence safely.

## AZ naming convention

AZs follow the vCenter naming convention: `{co}_{mgmt|workloads}_{region}-{N}`

- `de_mgmt_fra11-1` — Infra Dev Mgmt AZ1
- `de_mgmt_fra11-2` — Infra Dev Mgmt AZ2
- `de_workloads_fra11-1` — Infra Dev Workloads AZ1
- `de_workloads_fra11-2` — Infra Dev Workloads AZ2

These names are used as keys in the template and as filenames in `generated/`.
