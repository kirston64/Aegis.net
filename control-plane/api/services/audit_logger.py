"""
Audit Logger Service
Logs all CLI commands and configuration changes
"""
import structlog
import json
from datetime import datetime
from typing import Optional, List, Dict
import redis

logger = structlog.get_logger()


class AuditLogger:
    """Audit logging service"""
    
    def __init__(self, redis_client: redis.Redis, retention_days: int = 90):
        """
        Initialize audit logger
        
        Args:
            redis_client: Redis client for storing logs
            retention_days: Number of days to retain logs
        """
        self.redis = redis_client
        self.retention_seconds = retention_days * 86400
        self.log_key = "audit:logs"
    
    def log_action(self, 
                   user: str,
                   action: str,
                   details: Optional[Dict] = None,
                   client_ip: Optional[str] = None,
                   success: bool = True):
        """
        Log an audit event
        
        Args:
            user: User who performed the action
            action: Action performed (e.g., 'domain.add', 'ratelimit.update')
            details: Additional details about the action
            client_ip: Client IP address
            success: Whether the action succeeded
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user": user,
            "action": action,
            "details": details or {},
            "client_ip": client_ip,
            "success": success
        }
        
        # Store in Redis list
        self.redis.lpush(self.log_key, json.dumps(log_entry))
        
        # Trim to retention period (keep last N entries based on time)
        # Using LTRIM to keep last 10000 entries (approximate retention)
        self.redis.ltrim(self.log_key, 0, 10000)
        
        # Also log to structured logger
        logger.info("audit_log",
                   user=user,
                   action=action,
                   details=details,
                   client_ip=client_ip,
                   success=success)
    
    def get_logs(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Retrieve audit logs
        
        Args:
            limit: Maximum number of logs to return
            offset: Offset for pagination
        
        Returns:
            List of audit log entries
        """
        entries = self.redis.lrange(self.log_key, offset, offset + limit - 1)
        
        logs = []
        for entry in entries:
            try:
                log = json.loads(entry)
                logs.append(log)
            except Exception as e:
                logger.warning("failed_to_parse_audit_log", error=str(e))
        
        return logs
    
    def search_logs(self, 
                    user: Optional[str] = None,
                    action: Optional[str] = None,
                    limit: int = 100) -> List[Dict]:
        """
        Search audit logs by criteria
        
        Args:
            user: Filter by user
            action: Filter by action
            limit: Maximum number of results
        
        Returns:
            Filtered list of audit log entries
        """
        all_logs = self.get_logs(limit=limit * 2)  # Get more than needed for filtering
        
        filtered = []
        for log in all_logs:
            if user and log.get("user") != user:
                continue
            if action and log.get("action") != action:
                continue
            filtered.append(log)
            
            if len(filtered) >= limit:
                break
        
        return filtered


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        raise RuntimeError("Audit logger not initialized")
    return _audit_logger


def init_audit_logger(redis_client: redis.Redis, retention_days: int = 90):
    """Initialize global audit logger"""
    global _audit_logger
    _audit_logger = AuditLogger(redis_client, retention_days)
    logger.info("audit_logger_initialized", retention_days=retention_days)
