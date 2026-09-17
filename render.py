from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader

BASE = Path(__file__).parent

def load_site(path):
    return yaml.safe_load(Path(path).read_text())

def render(site_path):
    site = load_site(site_path)
    env = Environment(
        loader=FileSystemLoader(BASE / "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env.get_template("execution-environment.j2").render(**site)
