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

## Adding another site

1. Create a new YAML file under `sites/` (for example `sites/infra-prod.yaml`).
2. Copy the variable structure from `sites/infra-dev.yaml` and fill in the
   values for the new site.
3. Run the generator with the new site file:

```bash
python generate.py --site sites/infra-prod.yaml
```

The same Jinja2 template (`templates/execution-environment.j2`) is reused for
every site.  Only the site YAML file changes.

## Panorama naming convention

Panorama uses the corrected format:

`{co}-mgmt-{az1_m_region}-1-panorama.infra.{domain}`

`{co}-mgmt-{az2_m_region}-1-panorama.infra.{domain}`

## AZ naming convention

AZs follow the vCenter naming convention: `{co}_{mgmt|workloads}_{region}-{N}`

- `de_mgmt_fra11-1` — Infra Dev Mgmt AZ1
- `de_mgmt_fra11-2` — Infra Dev Mgmt AZ2
- `de_workloads_fra11-1` — Infra Dev Workloads AZ1
- `de_workloads_fra11-2` — Infra Dev Workloads AZ2

These names are used as keys in the template and as filenames in `generated/`.
