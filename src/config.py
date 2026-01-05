import os,yaml

def load_config():
    """This fucntions just loads the config.yaml"""

    #path of the file
    root_dir = os.path.dirname(os.path.dirname(__file__))
    config_path = os.path.join(root_dir, "config.yaml")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"config.yaml  file not found at {config_path}")

    # Load YAML config
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    print(f"Loaded config from: {config_path} ✅")
    return config


if __name__ == "__main__":
    print("✅ The configuration file is loaded successfully!")