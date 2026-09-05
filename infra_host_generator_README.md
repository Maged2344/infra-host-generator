# Infra Host Documentation Generator

## 1. Overview

This project provides a modular way to generate Infrastructure Host Documentation from a reusable Jinja2 template and site-specific YAML values.

The main goal is to replace a manually maintained Confluence host documentation page with a reusable, automated structure.

The project separates the work into four main areas:

1. **Site configuration** — contains values specific to a site/environment.
2. **Jinja2 template** — defines the hostname/FQDN generation rules.
3. **Python modules** — render and process the generated data.
4. **Generated YAML files** — provide a full validation file and separate files per Availability Zone.

The intended workflow is:

```text
sites/<site>.yaml
    |
    v
execution-environment.j2
    |
    v
infratest-components.yaml
    |
    v
AZ splitting
    |
    +--> de_mgmt_fra11-1.yaml
    +--> de_mgmt_fra11-2.yaml
    +--> de_workloads_fra11-1.yaml
    +--> de_workloads_fra11-2.yaml
```

The current stage is intentionally focused on **FQDN validation**. The generated validation file contains FQDNs only so that hostname conventions can be checked against the infrastructure documentation before expanding the template to all other host metadata.

---

# 2. Project Structure

```text
infra_host_generator/
│
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
│
├── README.md
│
└── generated/
    ├── infratest-components.yaml
    ├── de_mgmt_fra11-1.yaml
    ├── de_mgmt_fra11-2.yaml
    ├── de_workloads_fra11-1.yaml
    └── de_workloads_fra11-2.yaml
```

---

# 3. `sites/` directory

## Purpose

The `sites/` directory contains **site-specific configuration files**, one per
site/environment.

Each file is a self-contained YAML file with the values for that site.  There is
no single root-level `site.yaml`; the site is selected when running the generator.

The template should not contain values that change from one site to another when
those values can be supplied through a site YAML file.

The current example file is `sites/infra-dev.yaml`, which represents the Infra Dev
environment.

## Current configuration

```yaml
environment: idev
domain: nzero.dev
co: de

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

## Meaning of the main variables

### Environment

```yaml
environment: idev
```

Defines the environment being generated.

### Domain

```yaml
domain: nzero.dev
```

Defines the DNS domain used when constructing FQDNs.

### Company/Country prefix

```yaml
co: de
```

Used by hostname conventions that require the `co` value.

### Management network hostname prefixes

```yaml
az1_mgmt_network_hostname: defraama
az2_mgmt_network_hostname: defraamb
```

These are the complete network hostname values.

They must not be shortened.

For example:

```text
defraama
```

is correct.

```text
defraa
```

is incorrect.

The missing `ma` changes the resulting hostnames.

### Workloads network hostname prefixes

```yaml
az1_workloads_network_hostname: defraawa
az2_workloads_network_hostname: defraawb
```

These are also complete values and should be used exactly as provided.

### Regions

```yaml
az1_m_region: fra11
az2_m_region: fra11

az1_w_region: fra11
az2_w_region: fra11
```

These are used by hostname conventions that include the region.

### Compute quantities

```yaml
az1_m_compute_qty: 3
az2_m_compute_qty: 3
az1_w_compute_qty: 0
az2_w_compute_qty: 0
```

These control how many compute FQDNs are generated for each section.

For example:

```yaml
az1_m_compute_qty: 3
```

generates:

```text
demfra11-z1-a3.infra.nzero.dev
demfra11-z1-a4.infra.nzero.dev
demfra11-z1-a5.infra.nzero.dev
```

If the quantity is zero, no hosts are generated for that section.

---

# 4. `templates/execution-environment.j2`

## Purpose

This is the main reusable **Jinja2 template**.

It contains the hostname/FQDN construction rules.

The template receives values from a site YAML file (e.g. `sites/infra-dev.yaml`).

For example:

```jinja2
aa{{ az1_mgmt_network_hostname }}0002.infra.{{ domain }}
```

with:

```yaml
az1_mgmt_network_hostname: defraama
domain: nzero.dev
```

generates:

```text
aadefraama0002.infra.nzero.dev
```

The important point is that the template uses:

```text
defraama
```

exactly as supplied.

---

# 5. Network FQDNs

The template generates network FQDNs for:

```text
AZ1 Management
AZ2 Management
AZ1 Workloads
AZ2 Workloads
```

Example:

```jinja2
aa{{ az1_mgmt_network_hostname }}0002.infra.{{ domain }}
```

produces:

```text
aadefraama0002.infra.nzero.dev
```

The same pattern is used for the other Availability Zones with their corresponding site variables.

---

# 6. Panorama FQDNs

The Panorama appliances use a specific naming convention.

The corrected format is:

```text
{co}-mgmt-{az1_m_region}-1-panorama.infra.{domain}
```

and:

```text
{co}-mgmt-{az2_m_region}-1-panorama.infra.{domain}
```

The Jinja2 template therefore uses:

```jinja2
{{ co }}-mgmt-{{ az1_m_region }}-1-panorama.infra.{{ domain }}
```

and:

```jinja2
{{ co }}-mgmt-{{ az2_m_region }}-1-panorama.infra.{{ domain }}
```

For the current Infra Dev values this results in:

```text
de-mgmt-fra11-1-panorama.infra.nzero.dev
```

The Panorama naming convention is intentionally separate from the network hostname variables.

---

# 7. DNS and NTP FQDNs

The template generates FQDNs for:

- Gridmaster servers
- Management DNS/NTP resolvers
- Workloads DNS/NTP resolvers

Examples:

```jinja2
im{{ az1_mgmt_network_hostname }}0001.infra.{{ domain }}
```

generates:

```text
imdefraama0001.infra.nzero.dev
```

and:

```jinja2
ir{{ az1_mgmt_network_hostname }}0001.infra.{{ domain }}
```

generates:

```text
irdefraama0001.infra.nzero.dev
```

The same approach is used for AZ2 management and both workloads networks.

---

# 8. Jumphost FQDNs

The template generates the management jumphost FQDNs for AZ1 and AZ2.

Examples for AZ1:

```text
demfra11-z1-b3.infra.nzero.dev
demfra11-z1-b4.infra.nzero.dev
demfra11-z1-b11.infra.nzero.dev
demfra11-z1-b12.infra.nzero.dev
demfra11-z1-b13.infra.nzero.dev
```

Examples for AZ2:

```text
demfra11-z2-b3.infra.nzero.dev
demfra11-z2-b4.infra.nzero.dev
demfra11-z2-b11.infra.nzero.dev
demfra11-z2-b12.infra.nzero.dev
demfra11-z2-b13.infra.nzero.dev
```

These values are generated from the corresponding region variables.

---

# 9. Compute FQDNs

The template supports generating compute host FQDNs using Jinja2 loops.

Example:

```jinja2
{% for i in range(3, 3 + az1_m_compute_qty) %}
  - {{ co }}m{{ az1_m_region }}-z1-a{{ i }}.infra.{{ domain }}
{% endfor %}
```

With:

```yaml
az1_m_compute_qty: 3
```

the result is:

```text
demfra11-z1-a3.infra.nzero.dev
demfra11-z1-a4.infra.nzero.dev
demfra11-z1-a5.infra.nzero.dev
```

This makes the number of generated hosts configurable without changing the template.

---

# 10. Storage FQDNs

The template also contains FQDN patterns for storage/NetApp components.

The storage sections are separated into:

```text
AZ1 Management
AZ2 Management
AZ1 Workloads
AZ2 Workloads
```

The generated storage names include the relevant cluster, node, OOB, and intercluster naming patterns.

Examples include:

```text
-oob1
-oob2
-n1
-n2
-ic1
-ic2
```

The storage naming logic is kept in the template so that it can be reused for another site.

---

# 11. `render.py`

## Purpose

`render.py` is the reusable Python module responsible for rendering the Jinja2 template.

It separates the rendering logic from the command-line entry point.

The module contains:

```python
load_site()
```

and:

```python
render()
```

---

## `load_site()`

This function reads a site YAML configuration file.

Conceptually:

```text
sites/<site>.yaml
    |
    v
Python dictionary
```

The resulting dictionary is then passed to the Jinja2 template.

---

## `render()`

The `render()` function:

1. Loads the site YAML file
2. Creates a Jinja2 environment
3. Loads `execution-environment.j2`
4. Passes the site values into the template
5. Returns the rendered YAML content

Conceptually:

```text
sites/<site>.yaml
    |
    v
render.py
    |
    v
execution-environment.j2
    |
    v
Rendered YAML
```

Because this is implemented as a Python module, another Python application can import and reuse it.

Example:

```python
from render import render

yaml_content = render("sites/infra-dev.yaml")

print(yaml_content)
```

---

# 12. `split.py`

## Purpose

`split.py` is the reusable Python module for processing the generated documentation by Availability Zone.

The intended responsibility of this module is to take:

```text
generated/infratest-components.yaml
```

and split the relevant FQDNs into:

```text
de_mgmt_fra11-1.yaml
de_mgmt_fra11-2.yaml
de_workloads_fra11-1.yaml
de_workloads_fra11-2.yaml
```

The important architectural decision is that the splitting logic is separate from the Jinja2 rendering logic.

This means:

```text
Rendering
```

and:

```text
AZ processing
```

can evolve independently.

The module can also be reused by other Python programs later.

---

# 13. `generate.py`

## Purpose

`generate.py` is the main entry point.

Instead of manually importing the rendering module, the user can run:

```bash
python generate.py --site sites/infra-dev.yaml
```

The script:

1. Loads the site configuration from the file given via `--site`.
2. Renders the Jinja2 template.
3. Writes the generated validation YAML.

The output is:

```text
generated/infratest-components.yaml
```

The intended overall workflow is:

```text
python generate.py --site sites/infra-dev.yaml
        |
        v
sites/infra-dev.yaml
        |
        v
execution-environment.j2
        |
        v
infratest-components.yaml
```

---

# 14. `generated/infratest-components.yaml`

## Purpose

This is the main generated validation file.

It contains the FQDNs generated for the Infra Dev example.

The file is intentionally **FQDN-only**.

It is intended to be used to validate the Jinja2 naming logic against the infrastructure documentation before expanding the project to generate all host metadata.

The file contains sections such as:

```text
network
security
dns_ntp
jumphosts
compute
```

Example:

```yaml
components:
  network:
    de_mgmt_fra11-1:
      - aadefraama0002.infra.nzero.dev
```

---

# 15. `generated/de_mgmt_fra11-1.yaml`

This file contains the generated FQDNs belonging to:

```text
Management AZ1
```

The expected categories include:

```text
Network
Security / Panorama
DNS / NTP
Jumphosts
Compute
Storage
```

The file is useful when someone only needs the AZ1 management infrastructure.

---

# 16. `generated/de_mgmt_fra11-2.yaml`

This file contains the generated FQDNs belonging to:

```text
Management AZ2
```

It follows the same concept as `de_mgmt_fra11-1.yaml`.

Expected categories include:

```text
Network
Security / Panorama
DNS / NTP
Jumphosts
Compute
Storage
```

---

# 17. `generated/de_workloads_fra11-1.yaml`

This file contains the FQDNs belonging to:

```text
Workloads AZ1
```

Expected categories include:

```text
Network
DNS / NTP
Compute
Storage
```

For the current Infra Dev configuration:

```yaml
az1_w_compute_qty: 0
```

there are currently no workload compute FQDNs generated for this section.

---

# 18. `generated/de_workloads_fra11-2.yaml`

This file contains the FQDNs belonging to:

```text
Workloads AZ2
```

Expected categories include:

```text
Network
DNS / NTP
Compute
Storage
```

For the current Infra Dev configuration:

```yaml
az2_w_compute_qty: 0
```

there are currently no workload compute FQDNs generated for this section.

---

# 19. Complete Data Flow

The complete architecture is:

```text
                    sites/<site>.yaml
                        |
                        |
                        v
              +----------------+
              |    render.py   |
              +----------------+
                       |
                       v
        execution-environment.j2
                       |
                       |
                       v
          infratest-components.yaml
                       |
                       |
                       v
                +------------+
                |  split.py  |
                +------------+
                       |
       +---------------+---------------+
       |               |               |
       v               v               v
 de_mgmt_fra11-1.yaml   de_mgmt_fra11-2.yaml   workload files
                                       |
                              +--------+--------+
                              |                 |
                              v                 v
                       de_workloads_fra11-1.yaml   de_workloads_fra11-2.yaml
```

---

# 20. Why the Project Is Modular

The project intentionally separates data, templates, and processing logic.

## Site data

```text
sites/<site>.yaml
```

Contains site-specific values.

## Hostname/FQDN rules

```text
templates/execution-environment.j2
```

Contains reusable naming rules.

## Rendering logic

```text
render.py
```

Contains reusable Jinja2 rendering functions.

## AZ processing

```text
split.py
```

Contains reusable AZ splitting/processing functionality.

## Entry point

```text
generate.py
```

Provides the simple command used to generate the documentation.

This allows the Python modules to be imported and reused by other tools in the future.

---

# 21. Changing the Site

For another site/environment, create a new YAML file under `sites/`:

```text
sites/infra-prod.yaml
```

For example:

```yaml
environment: production
domain: infra.example.com
co: xx

az1_mgmt_network_hostname: ...
az2_mgmt_network_hostname: ...

az1_workloads_network_hostname: ...
az2_workloads_network_hostname: ...

az1_m_region: ...
az2_m_region: ...

az1_w_region: ...
az2_w_region: ...

az1_m_compute_qty: ...
az2_m_compute_qty: ...

az1_w_compute_qty: ...
az2_w_compute_qty: ...
```

Then run the generator with the new site file:

```bash
python generate.py --site sites/infra-prod.yaml
```

The same Jinja2 template can then be reused.

The template should only need to be modified if the actual infrastructure hostname convention changes.

---

# 22. Installation

The project requires Python and the following packages:

```bash
pip install Jinja2 PyYAML
```

Or:

```bash
python -m pip install Jinja2 PyYAML
```

---

# 23. Running the Generator

From the project root:

```bash
python generate.py --site sites/infra-dev.yaml
```

The main output is:

```text
generated/infratest-components.yaml
```

The AZ-specific files are stored under:

```text
generated/
```

---

# 24. Using the Renderer Directly

The Python renderer can be used independently.

Example:

```python
from render import render

result = render("sites/infra-dev.yaml")

print(result)
```

This makes the rendering functionality reusable from:

- Other Python scripts
- Automation tools
- CI/CD pipelines
- Future infrastructure documentation tools

---

# 25. Validation Workflow

The current implementation should be considered the **FQDN validation phase**.

The recommended workflow is:

```text
1. Define sites/<site>.yaml
       |
       v
2. Render execution-environment.j2
       |
       v
3. Generate infratest-components.yaml
       |
       v
4. Compare generated FQDNs against the source documentation
       |
       v
5. Fix hostname rules if required
       |
       v
6. Split the validated data into AZ files
       |
       v
7. Expand the template to include additional host metadata
```

This approach avoids generating a large amount of infrastructure data before the hostname conventions have been confirmed.

---

# 26. FQDN-Only Scope

The current generated validation file intentionally focuses on FQDNs.

It does not attempt to generate all infrastructure attributes.

The current validation scope does not include:

```text
IP addresses
Gateway addresses
Certificate expiry dates
Credentials
Operational state
Hardware specifications
Other non-FQDN metadata
```

These can be added later after the hostname conventions are validated.

---

# 27. Important Naming Rules

The following values are especially important:

```yaml
az1_mgmt_network_hostname: defraama
az2_mgmt_network_hostname: defraamb
az1_workloads_network_hostname: defraawa
az2_workloads_network_hostname: defraawb
```

They must be treated as complete hostname components.

For example:

```text
defraama
```

must remain:

```text
defraama
```

and must not be changed to:

```text
defraa
```

The missing characters would cause the generated hostnames to be incorrect.

---

# 28. Panorama Naming Rule

Panorama is a special case because its naming convention is different from the network controller naming convention.

The required format is:

```text
{co}-mgmt-{az1_m_region}-1-panorama.infra.{domain}
```

and:

```text
{co}-mgmt-{az2_m_region}-1-panorama.infra.{domain}
```

For the current values:

```yaml
co: de
az1_m_region: fra11
az2_m_region: fra11
domain: nzero.dev
```

the generated FQDN is:

```text
de-mgmt-fra11-1-panorama.infra.nzero.dev
```

The template should not attempt to build Panorama names from:

```text
az1_mgmt_network_hostname
```

because Panorama has its own naming convention.

---

# 29. Design Principles

The project follows these principles.

## Reusability

The same Jinja2 template can be reused for different sites.

## Separation of data and logic

Site-specific values belong in:

```text
sites/<site>.yaml
```

Naming logic belongs in:

```text
execution-environment.j2
```

Processing logic belongs in:

```text
*.py
```

## Modularity

Rendering and AZ processing are separate modules.

## Validation before expansion

FQDNs are validated first before generating the full infrastructure documentation.

## Easy maintenance

If a site-specific value changes:

```text
Update sites/<site>.yaml
```

If a hostname convention changes:

```text
Update execution-environment.j2
```

If the processing workflow changes:

```text
Update the relevant Python module
```

---

# 30. Future Expansion

Once the FQDN generation is validated, the project can be extended to generate additional infrastructure information.

For example:

```text
Hostname
FQDN
IP address
Gateway
Interface
VLAN
VRF
Description
Certificate expiry
Management network
Storage network
VMware/vMotion network
OOB information
Service information
```

The same architecture can be retained:

```text
sites/<site>.yaml
      +
execution-environment.j2
      |
      v
Python rendering
      |
      v
Full host documentation
      |
      v
AZ-specific files
```

This means the current FQDN validation work becomes the foundation for the complete documentation generator.

---

# 31. Summary

This project replaces a manually maintained infrastructure documentation workflow with a reusable and modular generator.

The important separation is:

```text
SITE VALUES
    |
    v
sites/<site>.yaml
    |
    v
HOSTNAME RULES
    |
    v
execution-environment.j2
    |
    v
PYTHON RENDERING
    |
    v
infratest-components.yaml
    |
    v
AZ PROCESSING
    |
    +-------------------+
    |                   |
    v                   v
Management            Workloads
    |                   |
    +-------+-----------+
            |
            v
    AZ-specific YAML files
```

The current Infra Dev example uses:

```yaml
environment: idev
domain: nzero.dev
co: de

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

The first objective is to validate the generated FQDNs against the infrastructure documentation.

After validation, the same modular framework can be expanded to generate the complete Infrastructure Host Documentation.
