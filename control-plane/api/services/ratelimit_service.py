"""
Rate Limiting Service - Memory-optimized for 4GB RAM
"""
import redis
import json
import structlog
from typing import Optional, Dict, List
from datetime import datetime
from ..models.ratelimit_config import RateLimitConfig, RateLimitStats

logger = structlog.get_logger()


class RateLimitService:
    """Service for managing rate limiting configurations"""
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize rate limit service
        
        Args:
            redis_client: Redis client for storing configurations
        """
        self.redis = redis_client
        self.config_prefix = "ratelimit:config:"
        self.stats_prefix = "ratelimit:stats:"
        self.counter_prefix = "ratelimit:counter:"
        
        # Memory optimization settings
        self.max_tracked_ips = 100_000  # Maximum IPs to track per domain
        self.counter_ttl = 300  # 5 minutes TTL for counters
    
    def create_or_update_config(self, config: RateLimitConfig) -> RateLimitConfig:
        """Create or update rate limit configuration"""
        config.updated_at = datetime.utcnow()
        
        # Store config in Redis
        key = f"{self.config_prefix}{config.domain}"
        config_json = config.model_dump_json()
        
        self.redis.set(key, config_json)
        
        logger.info("ratelimit_config_updated", 
                   domain=config.domain,
                   rps=config.requests_per_second,
                   rpm=config.requests_per_minute)
        
        # Notify edge nodes about config change (pub/sub)
        self.redis.publish("ratelimit_config_update", json.dumps({
            "domain": config.domain,
            "action": "update"
        }))
        
        return config
    
    def get_config(self, domain: str) -> Optional[RateLimitConfig]:
        """Get rate limit configuration for a domain"""
        key = f"{self.config_prefix}{domain}"
        config_json = self.redis.get(key)
        
        if not config_json:
            return None
        
        return RateLimitConfig.model_validate_json(config_json)
    
    def delete_config(self, domain: str) -> bool:
        """Delete rate limit configuration"""
        key = f"{self.config_prefix}{domain}"
        result = self.redis.delete(key)
        
        if result > 0:
            logger.info("ratelimit_config_deleted", domain=domain)
            
            # Notify edge nodes
            self.redis.publish("ratelimit_config_update", json.dumps({
                "domain": domain,
                "action": "delete"
            }))
            
            return True
        
        return False
    
    def list_configs(self) -> List[RateLimitConfig]:
        """List all rate limit configurations"""
        pattern = f"{self.config_prefix}*"
        keys = self.redis.keys(pattern)
        
        configs = []
        for key in keys:
            config_json = self.redis.get(key)
            if config_json:
                try:
                    config = RateLimitConfig.model_validate_json(config_json)
                    configs.append(config)
                except Exception as e:
                    logger.warning("failed_to_parse_config", key=key, error=str(e))
        
        return configs
    
    def increment_counter(self, domain: str, ip: str, window: str = "second") -> int:
        """
        Increment rate limit counter for IP
        
        Args:
            domain: Domain name
            ip: Client IP address
            window: Time window ('second' or 'minute')
        
        Returns:
            Current counter value
        """
        # Use HyperLogLog for memory-efficient unique IP counting
        hll_key = f"{self.stats_prefix}{domain}:unique_ips"
        self.redis.pfadd(hll_key, ip)
        self.redis.expire(hll_key, 86400)  # 24 hour expiry
        
        # Counter key with time bucketing
        timestamp = int(datetime.utcnow().timestamp())
        
        if window == "second":
            bucket = timestamp
            ttl = 2  # Keep for 2 seconds
        else:  # minute
            bucket = timestamp // 60
            ttl = 120  # Keep for 2 minutes
        
        counter_key = f"{self.counter_prefix}{domain}:{ip}:{window}:{bucket}"
        
        # Increment counter
        counter = self.redis.incr(counter_key)
        
        # Set TTL to auto-expire old counters (memory optimization)
        if counter == 1:
            self.redis.expire(counter_key, ttl)
        
        return counter
    
    def check_rate_limit(self, domain: str, ip: str) -> Dict[str, any]:
        """
        Check if request should be rate limited
        
        Returns:
            Dict with 'allowed' boolean and 'reason' if blocked
        """
        config = self.get_config(domain)
        
        if not config or not config.active:
            return {"allowed": True}
        
        # Check blacklist
        if ip in config.blacklist_ips:
            logger.info("request_blocked_blacklist", domain=domain, ip=ip)
            return {"allowed": False, "reason": "IP blacklisted"}
        
        # Check whitelist
        if ip in config.whitelist_ips:
            return {"allowed": True, "reason": "IP whitelisted"}
        
        # Check per-IP RPS
        if config.per_ip_rps:
            current_rps = self.get_current_rate(domain, ip, "second")
            if current_rps >= config.per_ip_rps:
                logger.info("request_blocked_rps", domain=domain, ip=ip, current=current_rps, limit=config.per_ip_rps)
                return {"allowed": False, "reason": f"Per-IP RPS limit exceeded ({current_rps}/{config.per_ip_rps})"}
        
        # Check per-IP RPM
        if config.per_ip_rpm:
            current_rpm = self.get_current_rate(domain, ip, "minute")
            if current_rpm >= config.per_ip_rpm:
                logger.info("request_blocked_rpm", domain=domain, ip=ip, current=current_rpm, limit=config.per_ip_rpm)
                return {"allowed": False, "reason": f"Per-IP RPM limit exceeded ({current_rpm}/{config.per_ip_rpm})"}
        
        # Increment counters
        self.increment_counter(domain, ip, "second")
        self.increment_counter(domain, ip, "minute")
        
        return {"allowed": True}
    
    def get_current_rate(self, domain: str, ip: str, window: str) -> int:
        """Get current request rate for IP"""
        timestamp = int(datetime.utcnow().timestamp())
        
        if window == "second":
            bucket = timestamp
        else:  # minute
            bucket = timestamp // 60
        
        counter_key = f"{self.counter_prefix}{domain}:{ip}:{window}:{bucket}"
        counter = self.redis.get(counter_key)
        
        return int(counter) if counter else 0
    
    def get_stats(self, domain: str) -> RateLimitStats:
        """Get rate limiting statistics for a domain"""
        # Get unique IPs using HyperLogLog
        hll_key = f"{self.stats_prefix}{domain}:unique_ips"
        unique_ips = self.redis.pfcount(hll_key)
        
        # Get total/blocked from separate counters
        total_key = f"{self.stats_prefix}{domain}:total"
        blocked_key = f"{self.stats_prefix}{domain}:blocked"
        
        total_requests = int(self.redis.get(total_key) or 0)
        blocked_requests = int(self.redis.get(blocked_key) or 0)
        
        # Calculate current RPS (approximate)
        # This could be enhanced with more sophisticated sliding window
        current_rps = 0.0  # TODO: implement real-time RPS calculation
        
        return RateLimitStats(
            domain=domain,
            total_requests=total_requests,
            blocked_requests=blocked_requests,
            current_rps=current_rps,
            unique_ips=unique_ips,
            top_ips=[],  # TODO: implement top IPs tracking
            last_updated=datetime.utcnow()
        )
    
    def increment_stats(self, domain: str, blocked: bool = False):
        """Increment statistics counters"""
        total_key = f"{self.stats_prefix}{domain}:total"
        self.redis.incr(total_key)
        self.redis.expire(total_key, 86400)  # 24 hour expiry
        
        if blocked:
            blocked_key = f"{self.stats_prefix}{domain}:blocked"
            self.redis.incr(blocked_key)
            self.redis.expire(blocked_key, 86400)


# Global service instance
_ratelimit_service: Optional[RateLimitService] = None


def get_ratelimit_service() -> RateLimitService:
    """Get global rate limit service instance"""
    global _ratelimit_service
    if _ratelimit_service is None:
        raise RuntimeError("Rate limit service not initialized")
    return _ratelimit_service


def init_ratelimit_service(redis_client: redis.Redis):
    """Initialize global rate limit service"""
    global _ratelimit_service
    _ratelimit_service = RateLimitService(redis_client)
    logger.info("ratelimit_service_initialized")
