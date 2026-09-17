from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader

BASE = Path(__file__).parent

REQUIRED_FIELDS = ("environment", "domain", "co", "product", "env_name", "networks")

REQUIRED_NETWORK_FIELDS = ("type", "label", "host_prefix", "azs")

REQUIRED_AZ_FIELDS = ("number", "network_hostname", "region")

def load_site(path):
    return yaml.safe_load(Path(path).read_text())

def _validate_networks(site, site_path):
    for i, net in enumerate(site["networks"]):
        missing = [f for f in REQUIRED_NETWORK_FIELDS if f not in net]
        if missing:
            raise ValueError(
                f"Missing required fields in networks[{i}] in {site_path}: {', '.join(missing)}"
            )
        for j, az in enumerate(net["azs"]):
            missing = [f for f in REQUIRED_AZ_FIELDS if f not in az]
            if missing:
                raise ValueError(
                    f"Missing required fields in networks[{i}].azs[{j}] in {site_path}: {', '.join(missing)}"
                )

def render(site_path):
    site = load_site(site_path)
    missing = [f for f in REQUIRED_FIELDS if f not in site]
    if missing:
        raise ValueError(f"Missing required fields in {site_path}: {', '.join(missing)}")
    _validate_networks(site, site_path)
    env = Environment(
        loader=FileSystemLoader(BASE / "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env.get_template("execution-environment.j2").render(**site)
