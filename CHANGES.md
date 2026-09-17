# Changes — Generic Data-Driven Template Refactor

## Summary

Replaced all hardcoded AZ1/AZ2 blocks in `execution-environment.j2` with
Jinja2 loops driven by a generic `networks` list in the site YAML.

Adding an AZ to an existing supported network type now requires **only a YAML
change** — no template modification.

## Files Changed

| File | Change |
|------|--------|
| `sites/infra-dev.yaml` | Refactored flat `azN_<type>_<field>` variables into a `networks` list |
| `templates/execution-environment.j2` | Replaced static AZ1/AZ2 blocks with loops over `networks` and `net.azs`; added conditional section omission for missing optional data |
| `render.py` | Added `trim_blocks=True, lstrip_blocks=True` for clean loop output; added lightweight validation for required root-level YAML fields |
| `README.md` | Updated schema docs, added "Adding an AZ" section |
| `infra_host_generator_README.md` | Updated all references to the new YAML structure |
| `generated/infratest-components.yaml` | Regenerated (identical FQDNs, cleaner formatting) |
| `CHANGES.md` | This file |

## Files NOT Changed

- `generate.py` — no changes needed
- `split.py` — no changes needed (already dynamic, reads AZ names from generated data)

## Old YAML Structure (flat)

```yaml
az1_mgmt_network_hostname: defraama
az2_mgmt_network_hostname: defraamb
az1_workloads_network_hostname: defraawa
az2_workloads_network_hostname: defraawb
az1_m_region: fra11
az2_m_region: fra11
az1_w_region: fra11
az2_w_region: fra11
az1_m_compute_qty: 3
az2_m_compute_qty: 3
az1_w_compute_qty: 0
az2_w_compute_qty: 0
```

## New YAML Structure (generic)

```yaml
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

### Field Reference

**Network-level (required):**

| Field | Purpose |
|-------|---------|
| `type` | `management` or `workloads`; drives which sections are generated |
| `label` | Used in generated YAML keys (e.g. `Infra Dev Mgmt AZ1`) |
| `host_prefix` | The `m`/`w` letter in compute/jumphost FQDNs |
| `azs` | List of availability zones |

**Network-level (optional):**

| Field | Purpose |
|-------|---------|
| `jumphost_ids` | List of jumphost ID numbers (management only); if missing or empty, `jumphosts` section is omitted entirely |

**AZ-level (required):**

| Field | Purpose |
|-------|---------|
| `number` | AZ number; drives `z{N}` suffix and `AZ{N}` label |
| `network_hostname` | Complete hostname component (e.g. `defraama`) — must not be shortened |
| `region` | Region string (e.g. `fra11`) |

**AZ-level (optional):**

| Field | Default | Purpose |
|-------|---------|---------|
| `compute_qty` | `0` | Number of compute hosts to generate; `0` or missing produces `[]` |

## What Was Hardcoded Before

- Exactly 2 AZs per network type (static AZ1/AZ2 blocks)
- `z1`/`z2` suffix written literally in FQDNs
- `m`/`w` host prefix hardcoded per section
- Jumphost IDs `b3,b4,b11,b12,b13` written as literal list items
- Workloads compute hardcoded as `[]` instead of driven by quantity
- `security:` and `jumphosts:` section headers always rendered even when empty

## What Is Data-Driven Now

- AZ count — iterate over `net.azs` list
- `z{N}` suffix — derived from `az.number`
- `m`/`w` prefix — derived from `net.host_prefix`
- Jumphost IDs — driven by `net.jumphost_ids` list
- Workloads compute — driven by `az.compute_qty` (generates real hosts when > 0)
- Management-only sections (Panorama, jumphosts, gridmasters) — gated by `net.type == 'management'`
- `security` section — omitted entirely when no management networks exist
- `jumphosts` section — omitted entirely when `jumphost_ids` is missing or empty

## Optional/Missing Data Handling

The template distinguishes between required and optional configuration:

- **Required**: `network_hostname`, `region` — always present for each AZ
- **Optional**: `compute_qty`, `jumphost_ids` — safely handled when absent

| Scenario | Behavior |
|----------|----------|
| `jumphost_ids` missing | `jumphosts` section omitted entirely |
| `jumphost_ids` empty (`[]`) | `jumphosts` section omitted entirely |
| `compute_qty` missing | Treated as `0`, produces `[]` |
| `compute_qty: 0` | Produces `[]`, no FQDNs generated |
| No management networks | `security` and `jumphosts` sections omitted |
| No workloads networks | Only management sections generated |

No invalid FQDNs are generated when optional configuration is missing.

## Preserved Naming Conventions

- `network_hostname` values used exactly as supplied (e.g. `defraama`)
- Panorama uses `az.region` (not `network_hostname`) — special rule preserved
- `aa`/`im`/`ir` FQDN prefixes remain in template
- Compute numbering starts at 3 (`range(3, 3 + compute_qty)`)

## Storage

Storage/NetApp FQDNs (`-oob1`, `-oob2`, `-n1`, `-n2`, `-ic1`, `-ic2`) were
mentioned in the documentation as a planned future section but **never existed**
in the original template or generated output (verified via git history).

Storage is **out of current scope**. No storage schema has been invented.

## render.py Validation

`render.py` now validates that required root-level fields are present in the
site YAML before rendering:

- `environment`
- `domain`
- `co`
- `product`
- `env_name`
- `networks`

A `ValueError` is raised if any are missing. No hostname-generation logic has
been moved into Python.

## Validation Results

- **FQDN count**: 33 (identical to pre-refactor output)
- **FQDN match**: All 33 FQDNs identical
- **YAML validity**: All generated files valid
- **Split files**: All AZ-specific files correct
- `generate.py` and `split.py` work unchanged

## Edge Cases Tested

| Test Case | Result |
|-----------|--------|
| Third AZ added (management) | Auto-generated via loop, correct `z3` suffix |
| `compute_qty: 0` | Produces `[]` |
| `compute_qty > 0` | Generates correct number of hosts |
| `compute_qty` missing | Treated as `0`, produces `[]` |
| `jumphost_ids` exists | Generates jumphost FQDNs |
| `jumphost_ids` empty (`[]`) | `jumphosts` section omitted |
| `jumphost_ids` missing | `jumphosts` section omitted |
| Workloads network exists | Generates network/dns_ntp/compute sections |
| Workloads network absent | Only management sections generated |
| Management network exists | Generates security/jumphosts/gridmasters |
| Multiple management AZs | All AZs generated via loop |
| Different regions per AZ | Each AZ uses its own `region` value |
| No management networks | `security` and `jumphosts` sections omitted |
| AZ3 added via YAML only | No template change needed |

## What "Generic" Means

The template supports an arbitrary **number of AZs** for network types that
have defined hostname-generation rules (management and workloads).

Adding an AZ to an existing supported network type requires **only a YAML
change**.

A new network **type** (e.g. `dmz`) would require adding its naming rules to
the template, because the template must know the hostname convention for each
type. This is by design — hostname conventions are template logic, not data.
