import json
from pathlib import Path
from jsonschema import validate, ValidationError

# Load the standard schema
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "config/schema.json"
if not SCHEMA_PATH.exists():
    # If the schema filename is different, find the first similar file
    for fname in (SCHEMA_PATH.parent).iterdir():
        if fname.name.strip().startswith("schema") and fname.name.strip().endswith(".json"):
            SCHEMA_PATH = fname
            break
    else:
        raise FileNotFoundError("No schema json found in config/")

with open(SCHEMA_PATH, encoding="utf-8") as f:
    SCHEMA = json.load(f)

def validate_config(config_dict):
    """
    Validate a config dictionary against the project's standard schema.
    Returns True if valid, otherwise returns False and the error message.
    """
    try:
        validate(instance=config_dict, schema=SCHEMA)
        return True, None
    except ValidationError as e:
        return False, str(e)
