from pathlib import Path
import yaml

def split_by_az(source="generated/infratest-components.yaml", output_dir="generated"):
    data = yaml.safe_load(Path(source).read_text())
    components = data.get("components", {})

    az_names = list(components.get("network", {}).keys())

    for az_name in az_names:
        az_data = {"components": {}}
        for section, section_data in components.items():
            if isinstance(section_data, dict) and az_name in section_data:
                az_data["components"][section] = section_data[az_name]

        output_path = Path(output_dir) / f"{az_name}.yaml"
        output_path.write_text(yaml.dump(az_data, default_flow_style=False, sort_keys=False))

    return data
