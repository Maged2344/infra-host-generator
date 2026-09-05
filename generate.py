from pathlib import Path
import argparse
from render import render
from split import split_by_az

ROOT = Path(__file__).parent

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate infra host documentation for a specific site.")
    parser.add_argument("--site", required=True, help="Path to the site YAML file (e.g. sites/infra-dev.yaml)")
    args = parser.parse_args()
    generated_dir = ROOT / "generated"
    generated_dir.mkdir(exist_ok=True)
    (generated_dir / "infratest-components.yaml").write_text(render(args.site))
    split_by_az(source=str(generated_dir / "infratest-components.yaml"), output_dir=str(generated_dir))
