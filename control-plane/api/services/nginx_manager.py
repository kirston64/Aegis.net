"""
Aegis.net — Nginx Manager
"""
import os
import subprocess
import structlog

logger = structlog.get_logger()

class NginxManager:
    """Manages Nginx configuration and process."""

    TEMPLATE = """
server {{
    listen 80;
    server_name {domain};

    location / {{
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

        config_path = f"/etc/nginx/sites-available/{domain}"
        symlink_path = f"/etc/nginx/sites-enabled/{domain}"

        try:
            # Write config file
            with open(config_path, "w") as f:
                f.write(config_content)
            
            # Create symlink if not exists
            if not os.path.exists(symlink_path):
                os.symlink(config_path, symlink_path)
                
            logger.info("nginx_config_created", domain=domain)
            return True
        except Exception as e:
            logger.error("nginx_config_creation_failed", error=str(e))
            raise

    @staticmethod
    def reload_nginx():
        """Reload Nginx service."""
        try:
            subprocess.run(["systemctl", "reload", "nginx"], check=True)
            logger.info("nginx_reloaded")
        except subprocess.CalledProcessError as e:
            logger.error("nginx_reload_failed", error=str(e))
            raise
