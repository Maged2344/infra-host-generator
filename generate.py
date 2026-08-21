from pathlib import Path
import argparse
from render import render

ROOT = Path(__file__).parent

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate infra host documentation for a specific site.")
    parser.add_argument("--site", required=True, help="Path to the site YAML file (e.g. sites/infra-dev.yaml)")
    args = parser.parse_args()
    (ROOT/"generated/infratest-components.yaml").write_text(render(args.site))
