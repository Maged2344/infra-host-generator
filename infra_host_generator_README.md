# Infra Host Generator — Summary

## Overview

Generates infrastructure host FQDN documentation from a reusable Jinja2
template + a site-specific YAML file.

```text
sites/<site>.yaml  -->  render.py  -->  templates/execution-environment.j2
                                              |
                                              v
                              generated/infratest-components.yaml   (big file)
                                              |
                                              v
                                        split.py
                                              |
                    +-------------------------+-------------------------+
                    v                                                   v
          generated/<AZ name>.yaml  (one small file per AZ)
```

---

## 1. How to make the big file from the template

The "big file" is `generated/infratest-components.yaml`. It is produced by
rendering the Jinja2 template with a site YAML.

### Steps

1. The template `templates/execution-environment.j2` defines FQDN naming
   rules using Jinja2 loops over a `networks` list.
2. A site YAML (e.g. `sites/infra-dev.yaml`) supplies the values.
3. `generate.py` is the entry point:

```bash
python generate.py --site sites/infra-dev.yaml
```

4. `generate.py` calls `render.render(args.site)` which:
   - loads the YAML (`load_site`)
   - validates required fields (`_validate_networks`)
   - creates a Jinja2 `Environment` with `FileSystemLoader` pointing at
     `templates/`
   - renders `execution-environment.j2` with the site values
5. The rendered text is written to `generated/infratest-components.yaml`.

### What the big file contains

The big file has a top-level `components:` key with these sections:

| Section | Contents | Scope |
|---------|----------|-------|
| `network` | Network controller FQDNs (`aa...`) | All networks / AZs |
| `security` | Panorama FQDNs | Management networks only |
| `dns_ntp` | Gridmasters (`im...`) + resolvers (`ir...`) | All AZs; gridmasters mgmt-only |
| `jumphosts` | Jumphost FQDNs (`...-b<N>`) | Management networks with `jumphost_ids` |
| `compute` | Compute host FQDNs (`...-a<N>`) | All networks / AZs |

Each AZ is a key like `Infra Dev Mgmt AZ1`.

---

## 2. How to split the big file into small files

After the big file is generated, `generate.py` calls
`split.split_by_az(...)` to produce one YAML file per AZ.

### Steps

1. `split_by_az` reads `generated/infratest-components.yaml`.
2. It extracts AZ names from the `components.network` section keys (e.g.
   `Infra Dev Mgmt AZ1`, `Infra Dev Workloads AZ2`).
3. For each AZ name it builds a new dict containing only that AZ's data
   from every section where it appears.
4. It writes each to `generated/<AZ name>.yaml`.

```text
generated/infratest-components.yaml
    |
    +--> generated/Infra Dev Mgmt AZ1.yaml
    +--> generated/Infra Dev Mgmt AZ2.yaml
    +--> generated/Infra Dev Workloads AZ1.yaml
    +--> generated/Infra Dev Workloads AZ2.yaml
```

Each small file has the same `components:` structure but only the entries
for that single AZ. Sections where the AZ does not appear (e.g.
`security` for a workloads AZ) are simply omitted.

### Example small file (`Infra Dev Mgmt AZ1.yaml`)

```yaml
components:
  network:
  - aadefraama0002.infra.nzero.dev
  security:
  - de-mgmt-fra11-1-panorama.infra.nzero.dev
  dns_ntp:
    gridmasters:
    - imdefraama0001.infra.nzero.dev
    - imdefraama0002.infra.nzero.dev
    resolvers:
    - irdefraama0001.infra.nzero.dev
    - irdefraama0002.infra.nzero.dev
  jumphosts:
  - demfra11-z1-b3.infra.nzero.dev
  - demfra11-z1-b4.infra.nzero.dev
  - demfra11-z1-b11.infra.nzero.dev
  - demfra11-z1-b12.infra.nzero.dev
  - demfra11-z1-b13.infra.nzero.dev
  compute:
  - demfra11-z1-a3.infra.nzero.dev
  - demfra11-z1-a4.infra.nzero.dev
  - demfra11-z1-a5.infra.nzero.dev
```

The split logic is fully dynamic — it reads AZ names from the generated
data, so adding AZs in the site YAML automatically produces more split
files with no code change.

---

## 3. How to use the YAML file in `sites/`

Each file under `sites/` is a self-contained site/environment
configuration. You pick which one to use via the `--site` flag:

```bash
python generate.py --site sites/infra-dev.yaml
```

### Structure

```yaml
# Root-level (required)
environment: idev          # environment identifier
domain: nzero.dev          # DNS domain for FQDNs
co: de                     # company / country prefix
product: Infra             # product name (used in AZ keys)
env_name: Dev              # environment name (used in AZ keys)

# networks list (required) — one entry per network type
networks:
  - type: management        # management | workloads
    label: Mgmt             # appears in AZ keys: "Infra Dev Mgmt AZ1"
    host_prefix: m          # m / w letter in compute & jumphost FQDNs
    jumphost_ids: [3, 4, 11, 12, 13]   # optional, mgmt-only
    azs:
      - number: 1                       # AZ number -> z1 suffix, AZ1 label
        network_hostname: defraama      # full hostname component (do NOT shorten)
        region: fra11                   # region string
        compute_qty: 3                  # optional, default 0 -> []
        network_seq: 2                  # optional, sequence for network FQDN
        gridmaster_qty: 2               # optional, mgmt-only, gridmaster count
        resolver_qty: 2                 # optional, resolver count
      - number: 2
        network_hostname: defraamb
        region: fra11
        compute_qty: 3
        ...

  - type: workloads
    label: Workloads
    host_prefix: w
    azs:
      - number: 1
        network_hostname: defraawa
        region: fra11
        compute_qty: 0
        network_seq: 2
        resolver_qty: 2
      - number: 2
        ...
```

### Field reference

**Root-level (required):** `environment`, `domain`, `co`, `product`,
`env_name`, `networks`

**Network-level (required):** `type`, `label`, `host_prefix`, `azs`

**Network-level (optional):** `jumphost_ids` (mgmt-only; if missing or
empty, `jumphosts` section is omitted entirely)

**AZ-level (required):** `number`, `network_hostname`, `region`

**AZ-level (optional):**

| Field | Default | Purpose |
|-------|---------|---------|
| `compute_qty` | `0` | Number of compute FQDNs; `0` produces `[]` |
| `network_seq` | — | Sequence number for network controller FQDN (`aa...000N`) |
| `gridmaster_qty` | — | Number of gridmaster FQDNs (management only) |
| `resolver_qty` | — | Number of resolver FQDNs |

### Adding a new site

1. Create `sites/<new-site>.yaml` (copy from `infra-dev.yaml`).
2. Fill in the values for the new site/environment.
3. Run:

```bash
python generate.py --site sites/<new-site>.yaml
```

The same template is reused — no template change needed unless the
hostname convention itself changes.

### Adding an AZ

Add a new entry to the `azs` list under the relevant network. No code or
template change is needed — the Jinja2 loops iterate over all AZs.

---

## 4. Functions used

### `generate.py` — entry point

```python
parser.add_argument("--site", required=True, ...)
```

- Parses `--site` CLI argument.
- Creates `generated/` directory.
- Calls `render(args.site)` and writes result to
  `generated/infratest-components.yaml`.
- Calls `split_by_az(source=..., output_dir=...)` to produce per-AZ
  files.

### `render.py` — template rendering module

| Function | Purpose |
|----------|---------|
| `load_site(path)` | Reads a site YAML file with `yaml.safe_load` and returns it as a dict. Raises `ValueError` if the YAML root is not a mapping. |
| `_validate_networks(site, site_path)` | Validates that `networks` is a list of dicts, each with required fields (`type`, `label`, `host_prefix`, `azs`), and each AZ has required fields (`number`, `network_hostname`, `region`). Raises `ValueError` on missing fields. |
| `render(site_path)` | Loads the site YAML, validates required root-level fields (`environment`, `domain`, `co`, `product`, `env_name`, `networks`) and networks, creates a Jinja2 `Environment` (`trim_blocks=True`, `lstrip_blocks=True`) with `FileSystemLoader` on `templates/`, renders `execution-environment.j2`, and returns the rendered text. |

Can be imported and reused directly:

```python
from render import render

yaml_content = render("sites/infra-dev.yaml")
```

### `split.py` — AZ splitting module

| Function | Purpose |
|----------|---------|
| `split_by_az(source="generated/infratest-components.yaml", output_dir="generated")` | Reads the big YAML file, extracts AZ names from `components.network` keys, and for each AZ writes a `<AZ name>.yaml` file containing only that AZ's entries from every section where it appears. Returns the full parsed data. |

Can be imported and reused directly:

```python
from split import split_by_az

split_by_az(source="generated/infratest-components.yaml", output_dir="generated")
```

---

## 5. FQDN naming conventions

All FQDNs end with `.infra.<domain>`.

| Component | Pattern | Example |
|-----------|---------|---------|
| Network controller | `aa<network_hostname><NNNN>` | `aadefraama0002.infra.nzero.dev` |
| Panorama (security) | `<co>-mgmt-<region>-1-panorama` | `de-mgmt-fra11-1-panorama.infra.nzero.dev` |
| Gridmaster (dns_ntp) | `im<network_hostname><NNNN>` | `imdefraama0001.infra.nzero.dev` |
| Resolver (dns_ntp) | `ir<network_hostname><NNNN>` | `irdefraama0001.infra.nzero.dev` |
| Jumphost | `<co><host_prefix><region>-z<N>-b<id>` | `demfra11-z1-b3.infra.nzero.dev` |
| Compute | `<co><host_prefix><region>-z<N>-a<id>` | `demfra11-z1-a3.infra.nzero.dev` |

Key rules:
- `network_hostname` is used exactly as supplied (never shortened).
- Panorama uses `region` (not `network_hostname`).
- Compute IDs start at 3: `range(3, 3 + compute_qty)`.
- `z<N>` suffix and `AZ<N>` label are derived from `az.number`.
- `m`/`w` host prefix is derived from `net.host_prefix`.

---

## 6. Installation & run

```bash
pip install Jinja2 PyYAML
python generate.py --site sites/infra-dev.yaml
```

Output:
- `generated/infratest-components.yaml` — big validation file (all AZs).
- `generated/<AZ name>.yaml` — one small file per AZ.

---

## 7. Tests

```bash
python -m pytest tests/test_generator.py -v
```

or:

```bash
python tests/test_generator.py
```

The test suite covers baseline generation, adding AZs, different regions,
compute quantities, missing optional fields, validation errors, split
output, and template genericness (no hardcoded AZ1/AZ2).
