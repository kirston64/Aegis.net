
from cli.auth import auth_manager
from cli.config import ensure_config_dirs
import json

def run_setup():
    ensure_config_dirs()
    print("Generating SSH keys...")
    key_path = auth_manager.setup_ssh_keys()
    public_key = auth_manager.get_ssh_public_key()
    
    print("Generating TOTP secret...")
    totp_secret = auth_manager.setup_totp()
    
    result = {
        "ssh_public_key": public_key,
        "totp_secret": totp_secret
    }
    
    print("\n--- SETUP RESULTS ---")
    print(json.dumps(result, indent=2))
    print("---------------------")

if __name__ == "__main__":
    run_setup()
