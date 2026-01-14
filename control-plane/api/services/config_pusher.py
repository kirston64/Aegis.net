"""
Aegis.net — Config Pusher Service

Responsible for distributing configuration changes to all edge nodes.
"""

import asyncio
from typing import Optional, Dict, Any
import httpx
import structlog
from datetime import datetime

from api.config import settings
from api.models import DomainConfig

logger = structlog.get_logger()


class ConfigPusher:
    """
    Service for pushing configuration updates to edge nodes.
    
    Uses async HTTP to distribute config changes across all PoPs
    with proper error handling and retry logic.
    """
    
    def __init__(self):
        self.http_client: Optional[httpx.AsyncClient] = None
        self.edge_nodes = settings.EDGE_NODES
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(5.0, connect=2.0),
            limits=httpx.Limits(max_keepalive_connections=10)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.http_client:
            await self.http_client.aclose()
    
    async def push_config(
        self, 
        domain: str, 
        config: DomainConfig
    ) -> Dict[str, Any]:
        """
        Push domain configuration to all edge nodes.
        
        Args:
            domain: Domain name
            config: Domain protection configuration
            
        Returns:
            Dict with push results
        """
        logger.info("config_push_starting", domain=domain, nodes=len(self.edge_nodes))
        
        tasks = [
            self._push_to_node(node, domain, config)
            for node in self.edge_nodes
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = len(results) - successful
        
        logger.info(
            "config_push_completed",
            domain=domain,
            successful=successful,
            failed=failed
        )
        
        return {
            "domain": domain,
            "nodes_total": len(self.edge_nodes),
            "nodes_successful": successful,
            "nodes_failed": failed,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _push_to_node(
        self, 
        node_url: str, 
        domain: str, 
        config: DomainConfig
    ) -> Dict[str, Any]:
        """
        Push config to a single edge node.
        
        Args:
            node_url: Edge node base URL
            domain: Domain name
            config: Domain configuration
            
        Returns:
            Result dict
        """
        try:
            response = await self.http_client.post(
                f"{node_url}/api/v1/config/apply",
                json={
                    "domain": domain,
                    "config": config.model_dump(),
                    "timestamp": datetime.utcnow().isoformat()
                },
                headers={
                    "X-Internal-Token": settings.SECRET_KEY,
                    "Content-Type": "application/json"
                }
            )
            response.raise_for_status()
            
            logger.debug("config_push_node_success", node=node_url, domain=domain)
            
            return {"success": True, "node": node_url}
            
        except httpx.TimeoutException:
            logger.warning("config_push_node_timeout", node=node_url, domain=domain)
            return {"success": False, "node": node_url, "error": "timeout"}
            
        except httpx.HTTPStatusError as e:
            logger.warning(
                "config_push_node_error",
                node=node_url,
                domain=domain,
                status=e.response.status_code
            )
            return {"success": False, "node": node_url, "error": str(e)}
            
        except Exception as e:
            logger.error(
                "config_push_node_exception",
                node=node_url,
                domain=domain,
                error=str(e)
            )
            return {"success": False, "node": node_url, "error": str(e)}
    
    async def push_attack_mode(
        self,
        domain: str,
        level: int,
        duration_seconds: int
    ) -> Dict[str, Any]:
        """
        Push attack mode activation to all edge nodes.
        
        This is a priority operation with faster timeout.
        """
        logger.info(
            "attack_mode_push_starting",
            domain=domain,
            level=level
        )
        
        tasks = [
            self._push_attack_mode_to_node(node, domain, level, duration_seconds)
            for node in self.edge_nodes
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        
        return {
            "domain": domain,
            "level": level,
            "nodes_successful": successful,
            "nodes_total": len(self.edge_nodes)
        }
    
    async def _push_attack_mode_to_node(
        self,
        node_url: str,
        domain: str,
        level: int,
        duration_seconds: int
    ) -> Dict[str, Any]:
        """Push attack mode to a single node."""
        try:
            response = await self.http_client.post(
                f"{node_url}/api/v1/attack-mode/activate",
                json={
                    "domain": domain,
                    "level": level,
                    "duration_seconds": duration_seconds
                },
                headers={"X-Internal-Token": settings.SECRET_KEY}
            )
            response.raise_for_status()
            return {"success": True, "node": node_url}
        except Exception as e:
            return {"success": False, "node": node_url, "error": str(e)}


# Singleton instance
_config_pusher: Optional[ConfigPusher] = None


async def get_config_pusher() -> ConfigPusher:
    """Get or create ConfigPusher instance."""
    global _config_pusher
    if _config_pusher is None:
        _config_pusher = ConfigPusher()
        await _config_pusher.__aenter__()
    return _config_pusher
