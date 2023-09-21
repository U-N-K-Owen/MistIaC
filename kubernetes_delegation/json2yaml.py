import json
import yaml

with open("output_device_info.json", 'r') as in_json:
    file_content = json.load(in_json)

with open("nodes.yaml", 'w') as out_yaml:
    yaml.safe_dump(file_content, out_yaml)