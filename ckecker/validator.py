import json
from pathlib import Path
from jsonschema import validate, ValidationError
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Module logger
logger = logging.getLogger("ckecker.validator")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s"))
logger.addHandler(handler)

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
        logger.debug("Config valid")
        return True, None
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return False, str(e)

def validate_configs(configs, max_workers: int = 10):
    """
    Validate a list of config dictionaries in parallel.
    Returns a list of dicts with 'index', 'valid', and 'error'.
    """
    results = [None] * len(configs)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(validate_config, cfg): i for i, cfg in enumerate(configs)}
        for future in as_completed(future_map):
            idx = future_map[future]
            try:
                valid, error = future.result()
            except Exception as e:
                logger.error(f"Unexpected error validating config at index {idx}: {e}")
                valid, error = False, str(e)
            results[idx] = {"index": idx, "valid": valid, "error": error}
    return results
