"""
Aegis.net — Nginx Manager
"""
import os
import subprocess
import structlog

logger = structlog.get_logger()

# Docker-compatible configuration
IS_DOCKER = os.getenv("DOCKER_ENV", "false").lower() == "true"
NGINX_CONFIG_DIR = os.getenv("NGINX_CONFIG_DIR", "/etc/nginx/conf.d/sites" if IS_DOCKER else "/etc/nginx/sites-available")
NGINX_CONTAINER_NAME = os.getenv("NGINX_CONTAINER_NAME", "aegis-nginx-edge")

class NginxManager:
    """Manages Nginx configuration and process."""

    TEMPLATE = """
server {{
    listen 80;
    server_name {domain};

    location / {{
        # Aegis Protection Rules
        limit_req zone=aegis_limit burst=20 nodelay;
        
        proxy_pass http://{origin_ip}:{origin_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""

    @staticmethod
    def create_config(domain: str, origin_ip: str, origin_port: int = 80):
        """Create Nginx config file for a domain."""
        logger.info("creating_nginx_config", domain=domain, origin=origin_ip)
        
        config_content = NginxManager.TEMPLATE.format(
            domain=domain,
            origin_ip=origin_ip,
            origin_port=origin_port
        )

        config_path = f"{NGINX_CONFIG_DIR}/{domain}.conf"

        try:
            # Ensure config directory exists
            os.makedirs(NGINX_CONFIG_DIR, exist_ok=True)
            
            # Write config file
            with open(config_path, "w") as f:
                f.write(config_content)
                
            logger.info("nginx_config_created", domain=domain, path=config_path)
            return True
        except Exception as e:
            logger.error("nginx_config_creation_failed", error=str(e))
            raise

    @staticmethod
    def reload_nginx():
        """Reload Nginx service."""
        try:
            if IS_DOCKER:
                # In Docker, send reload signal to nginx container
                subprocess.run(
                    ["docker", "exec", NGINX_CONTAINER_NAME, "nginx", "-s", "reload"],
                    check=True
                )
            else:
                # On bare metal, use systemctl
                subprocess.run(["/usr/bin/sudo", "/usr/bin/systemctl", "reload", "nginx"], check=True)
            
            logger.info("nginx_reloaded", docker=IS_DOCKER)
        except subprocess.CalledProcessError as e:
            logger.error("nginx_reload_failed", error=str(e), docker=IS_DOCKER)
            raise
