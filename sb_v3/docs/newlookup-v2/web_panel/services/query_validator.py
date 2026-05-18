"""
Query validation service to prevent SQL injection
Fixes SEC-2: SQL Injection Risk via Dynamic Column Access
"""

from typing import Optional, List, Set, Callable, Any
from fastapi import HTTPException
from sqlalchemy import Column


class QueryValidator:
    """
    Validates user-provided query parameters against whitelists
    to prevent SQL injection and unauthorized data access.
    """
    
    def __init__(self, allowed_fields: Set[str], field_name: str = "field"):
        """
        Initialize validator with allowed field names
        
        Args:
            allowed_fields: Set of allowed field names
            field_name: Name of the field for error messages
        """
        self.allowed_fields = frozenset(f.lower() for f in allowed_fields)
        self.field_name = field_name
    
    def validate(self, value: Optional[str]) -> Optional[str]:
        """
        Validate a single field name
        
        Args:
            value: Field name to validate
            
        Returns:
            Validated field name (lowercase) or None
            
        Raises:
            HTTPException: If field name is not allowed
        """
        if value is None:
            return None
        
        normalized = value.lower().strip()
        
        if not normalized:
            return None
        
        if normalized not in self.allowed_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {self.field_name}: '{value}'. Allowed values: {', '.join(sorted(self.allowed_fields))}"
            )
        
        return normalized
    
    def validate_multiple(self, values: Optional[List[str]]) -> List[str]:
        """
        Validate multiple field names
        
        Args:
            values: List of field names to validate
            
        Returns:
            List of validated field names
            
        Raises:
            HTTPException: If any field name is not allowed
        """
        if not values:
            return []
        
        validated = []
        for value in values:
            validated_field = self.validate(value)
            if validated_field:
                validated.append(validated_field)
        
        return validated


# Common validators for reuse
USER_SORT_FIELDS = {
    "user_id", "username", "balance", "created_at", "updated_at",
    "language", "is_banned", "last_active"
}

ORDER_SORT_FIELDS = {
    "order_id", "created_at", "updated_at", "status", "price",
    "user_id", "worker_id", "category"
}

SELLER_SORT_FIELDS = {
    "seller_id", "username", "balance", "created_at", "status",
    "total_orders", "total_sales"
}

TRANSACTION_SORT_FIELDS = {
    "transaction_id", "created_at", "amount", "type", "status",
    "user_id", "entity_type"
}

SUPPORT_TICKET_SORT_FIELDS = {
    "ticket_id", "created_at", "updated_at", "status", "priority",
    "user_id", "category"
}

# Validators instances
user_sort_validator = QueryValidator(USER_SORT_FIELDS, "sort field")
order_sort_validator = QueryValidator(ORDER_SORT_FIELDS, "sort field")
seller_sort_validator = QueryValidator(SELLER_SORT_FIELDS, "sort field")
transaction_sort_validator = QueryValidator(TRANSACTION_SORT_FIELDS, "sort field")
ticket_sort_validator = QueryValidator(SUPPORT_TICKET_SORT_FIELDS, "sort field")


def validate_sort_field(
    value: Optional[str],
    allowed_fields: Set[str],
    field_name: str = "sort field"
) -> Optional[str]:
    """
    Validate a sort field against whitelist
    
    Args:
        value: Sort field to validate
        allowed_fields: Set of allowed field names
        field_name: Name for error messages
        
    Returns:
        Validated field name or None
        
    Raises:
        HTTPException: If field is not allowed
    """
    validator = QueryValidator(allowed_fields, field_name)
    return validator.validate(value)


def validate_filter_field(
    field: Optional[str],
    value: Any,
    allowed_filters: dict,
) -> tuple[Optional[str], Any]:
    """
    Validate filter field and sanitize value
    
    Args:
        field: Filter field name
        value: Filter value
        allowed_filters: Dict mapping field names to validator functions
        
    Returns:
        Tuple of (validated field, sanitized value)
        
    Raises:
        HTTPException: If field is not allowed or value is invalid
    """
    if field is None:
        return None, None
    
    field_lower = field.lower().strip()
    
    if field_lower not in allowed_filters:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid filter field: '{field}'. Allowed: {', '.join(allowed_filters.keys())}"
        )
    
    validator_func = allowed_filters[field_lower]
    if validator_func is None:
        # No validation, pass through
        return field_lower, value
    
    try:
        sanitized_value = validator_func(value)
        return field_lower, sanitized_value
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid filter value for '{field}': {str(e)}"
        )


# Example filter validators
def validate_int(value: Any) -> int:
    """Validate and convert to integer"""
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    raise ValueError(f"Expected integer, got {type(value).__name__}")


def validate_float(value: Any) -> float:
    """Validate and convert to float"""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Expected number, got {type(value).__name__}")


def validate_date_string(value: str) -> str:
    """Validate date string format YYYY-MM-DD"""
    from datetime import datetime
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        raise ValueError("Expected YYYY-MM-DD format")


def validate_status(value: str, allowed: Set[str]) -> str:
    """Validate status against allowed values"""
    if value not in allowed:
        raise ValueError(f"Must be one of: {', '.join(allowed)}")
    return value
