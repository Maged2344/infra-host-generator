from pathlib import Path
import yaml

def split_by_az(source="generated/infratest-components.yaml", output_dir="generated"):
    data = yaml.safe_load(Path(source).read_text())
    # Reusable splitter: AZ-specific selection can be extended independently.
    return data
