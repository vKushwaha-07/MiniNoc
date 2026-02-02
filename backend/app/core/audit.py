import functools
import json
from datetime import datetime
from fastapi import Request
from ..db.session import get_db_context
from ..db.models.audit import AuditLog
from ..core.logging import main_logger

def log_audit(action: str, resource: str, details: str = None, meta: dict = None, user: str = "admin"):
    """
    Directly write an audit log entry to the database.
    This should be used when the decorator isn't sufficient.
    """
    try:
        with get_db_context() as db:
            log = AuditLog(
                user=user,
                action=action,
                resource=resource,
                details=details,
                metadata_json=meta
            )
            db.add(log)
            db.commit()
            main_logger.info(f"AUDIT: {user} performed {action} on {resource}")
    except Exception as e:
        main_logger.error(f"Failed to write audit log: {e}")

def audit_action(action_name: str, resource_field: str = None):
    """
    Decorator to automatically log API actions.
    
    args:
        action_name: The name of the action (e.g. "SSH_TEST")
        resource_field: The name of the parameter content to use as the resource identifier.
                        If None, tries to find 'ip' or 'mac'.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract basic info
            resource = "unknown"
            
            # Try to grab resource from kwargs
            if resource_field and resource_field in kwargs:
                resource = str(kwargs[resource_field])
            else:
                # Fallback heuristics
                for k in ['ip', 'ip_address', 'host', 'mac', 'mac_address', 'device_id']:
                    if k in kwargs:
                        resource = str(kwargs[k])
                        break
            
            result = None
            error = None
            
            try:
                # Execute the actual function
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error = str(e)
                raise e
            finally:
                # Log success or failure
                status = "FAILED" if error else "SUCCESS"
                details = f"Action {status}"
                if error:
                    details += f": {error}"
                elif isinstance(result, dict) and "message" in result:
                    details = result["message"]
                
                log_audit(
                    action=action_name,
                    resource=resource,
                    details=details,
                    meta={"kwargs": kwargs, "error": error}
                )
        return wrapper
    return decorator
