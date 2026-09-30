# Infra Host Generator — Quick Summary

## 1. Making the big file from the template

The big file (`generated/infratest-components.yaml`) is produced by
rendering the Jinja2 template with a site YAML:

```bash
python generate.py --site sites/infra-dev.yaml
```

`generate.py` calls `render.render(args.site)` which loads the YAML,
validates required fields, creates a Jinja2 environment pointing at
`templates/`, and renders `execution-environment.j2`. The output is
written to `generated/infratest-components.yaml`. This file contains
all FQDNs for every AZ grouped under `components:` with sections:
`network`, `security`, `dns_ntp`, `jumphosts`, `compute`.

## 2. Splitting the big file into small files

`generate.py` then calls `split.split_by_az(...)` which reads the big
file, extracts AZ names from the `components.network` keys (e.g.
`Infra Dev Mgmt AZ1`), and writes one file per AZ:

```text
generated/Infra Dev Mgmt AZ1.yaml
generated/Infra Dev Mgmt AZ2.yaml
generated/Infra Dev Workloads AZ1.yaml
generated/Infra Dev Workloads AZ2.yaml
```

Each small file has the same `components:` structure but only the
entries for that single AZ. Sections where the AZ does not appear are
omitted. The split is fully dynamic — no code change needed when AZs
are added.

## 3. Using the YAML file in `sites/`

Each file under `sites/` is a self-contained site configuration. You
select it with `--site`:

```bash
python generate.py --site sites/infra-dev.yaml
```

Key fields:

| Level | Required fields | Optional fields |
|-------|----------------|-----------------|
| Root | `environment`, `domain`, `co`, `product`, `env_name`, `networks` | — |
| Network | `type` (management/workloads), `label`, `host_prefix`, `azs` | `jumphost_ids` |
| AZ | `number`, `network_hostname`, `region` | `compute_qty`, `network_seq`, `gridmaster_qty`, `resolver_qty` |

- `network_hostname` must be used exactly as supplied (never shortened).
- `compute_qty: 0` or missing produces `[]`.
- Missing `jumphost_ids` omits the `jumphosts` section entirely.
- Adding an AZ = just add an entry to the `azs` list, no code change.

## 4. Functions used

| File | Function | Purpose |
|------|----------|---------|
| `generate.py` | `main` (CLI) | Parses `--site`, calls `render()` then `split_by_az()` |
| `render.py` | `load_site(path)` | Reads site YAML, returns dict, rejects non-mapping roots |
| `render.py` | `_validate_networks(site, path)` | Validates required network & AZ fields, raises `ValueError` on missing |
| `render.py` | `render(site_path)` | Loads YAML, validates, renders `execution-environment.j2`, returns text |
| `split.py` | `split_by_az(source, output_dir)` | Reads big file, writes one YAML per AZ |

## FQDN patterns (all end `.infra.<domain>`)

| Component | Pattern | Example |
|-----------|---------|---------|
| Network | `aa<hostname><NNNN>` | `aadefraama0002.infra.nzero.dev` |
| Panorama | `<co>-mgmt-<region>-1-panorama` | `de-mgmt-fra11-1-panorama.infra.nzero.dev` |
| Gridmaster | `im<hostname><NNNN>` | `imdefraama0001.infra.nzero.dev` |
| Resolver | `ir<hostname><NNNN>` | `irdefraama0001.infra.nzero.dev` |
| Jumphost | `<co><prefix><region>-z<N>-b<id>` | `demfra11-z1-b3.infra.nzero.dev` |
| Compute | `<co><prefix><region>-z<N>-a<id>` | `demfra11-z1-a3.infra.nzero.dev` |

## Install & run

```bash
pip install Jinja2 PyYAML
python generate.py --site sites/infra-dev.yaml
```
