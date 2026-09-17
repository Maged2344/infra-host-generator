# Changes — Generic Data-Driven Template Refactor

## Summary

Replaced all hardcoded AZ1/AZ2 blocks in `execution-environment.j2` with
Jinja2 loops driven by a generic `networks` list in the site YAML.

Adding an AZ or network type now requires **only a YAML change** — no template
modification.

## Files Changed

| File | Change |
|------|--------|
| `sites/infra-dev.yaml` | Refactored flat `azN_<type>_<field>` variables into a `networks` list |
| `templates/execution-environment.j2` | Replaced static AZ1/AZ2 blocks with loops over `networks` and `net.azs` |
| `render.py` | Added `trim_blocks=True, lstrip_blocks=True` for clean loop output |
| `README.md` | Updated schema docs, added "Adding an AZ" section |
| `infra_host_generator_README.md` | Updated all references to the new YAML structure |
| `generated/infratest-components.yaml` | Regenerated (identical FQDNs, cleaner formatting) |

## Files NOT Changed

- `generate.py` — no changes needed
- `split.py` — no changes needed

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

## What Was Hardcoded Before

- Exactly 2 AZs per network type (static AZ1/AZ2 blocks)
- `z1`/`z2` suffix written literally in FQDNs
- `m`/`w` host prefix hardcoded per section
- Jumphost IDs `b3,b4,b11,b12,b13` written as literal list items
- Workloads compute hardcoded as `[]` instead of driven by quantity

## What Is Data-Driven Now

- AZ count — iterate over `net.azs` list
- `z{N}` suffix — derived from `az.number`
- `m`/`w` prefix — derived from `net.host_prefix`
- Jumphost IDs — driven by `net.jumphost_ids` list
- Workloads compute — driven by `az.compute_qty` (generates real hosts when > 0)
- Management-only sections (Panorama, jumphosts, gridmasters) — gated by `net.type == 'management'`

## Preserved Naming Conventions

- `network_hostname` values used exactly as supplied (e.g. `defraama`)
- Panorama uses `az.region` (not `network_hostname`) — special rule preserved
- `aa`/`im`/`ir` FQDN prefixes remain in template
- Compute numbering starts at 3 (`range(3, 3 + compute_qty)`)

## Validation

- All 33 FQDNs identical to pre-refactor output
- All generated YAML files valid
- All 4 AZ-specific split files identical to pre-refactor output
- `generate.py` and `split.py` work unchanged

## Edge Cases Tested

- Third AZ added — auto-generated via loop
- `compute_qty: 0` — produces `[]`
- Missing `jumphost_ids` — empty section, no invalid rows
- No workloads network — only management sections generated
- Different regions/compute quantities per AZ — each AZ uses its own values
