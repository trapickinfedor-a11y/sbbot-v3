"""
Bulk operation validation service
Fixes VAL-2: No Validation on Bulk Operations
"""

from typing import List, TypeVar, Callable, Optional
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BulkOperationValidator:
    """
    Validates bulk operations to prevent memory exhaustion and DoS attacks
    """
    
    # Default limits
    DEFAULT_MAX_BULK_SIZE = 1000
    DEFAULT_MAX_BATCH_SIZE = 100
    
    def __init__(
        self,
        max_bulk_size: int = DEFAULT_MAX_BULK_SIZE,
        max_batch_size: int = DEFAULT_MAX_BATCH_SIZE
    ):
        """
        Initialize validator with size limits
        
        Args:
            max_bulk_size: Maximum number of items in a single bulk operation
            max_batch_size: Recommended batch size for processing
        """
        self.max_bulk_size = max_bulk_size
        self.max_batch_size = max_batch_size
    
    def validate_size(self, items: List[T], operation_name: str = "Bulk operation") -> List[T]:
        """
        Validate the size of a bulk operation
        
        Args:
            items: List of items to validate
            operation_name: Name of the operation for error messages
            
        Returns:
            Validated list of items
            
        Raises:
            HTTPException: If operation exceeds size limits
        """
        if not items:
            raise HTTPException(
                status_code=400,
                detail=f"{operation_name} requires at least 1 item"
            )
        
        item_count = len(items)
        
        if item_count > self.max_bulk_size:
            logger.warning(
                "Bulk operation rejected: %s with %d items (max: %d)",
                operation_name, item_count, self.max_bulk_size
            )
            raise HTTPException(
                status_code=400,
                detail=f"{operation_name} exceeds maximum size of {self.max_bulk_size} items (got {item_count})"
            )
        
        # Log warning if approaching limit
        if item_count > self.max_bulk_size * 0.8:
            logger.warning(
                "Bulk operation approaching limit: %s with %d/%d items",
                operation_name, item_count, self.max_bulk_size
            )
        
        logger.info(
            "Bulk operation validated: %s with %d items",
            operation_name, item_count
        )
        
        return items
    
    def get_batches(self, items: List[T]) -> List[List[T]]:
        """
        Split items into batches for processing
        
        Args:
            items: List of items to batch
            
        Returns:
            List of batches (each batch is a list)
        """
        return [
            items[i:i + self.max_batch_size]
            for i in range(0, len(items), self.max_batch_size)
        ]


# Global validator instance
bulk_validator = BulkOperationValidator()


def validate_bulk_operation(
    items: List[T],
    max_size: int = 1000,
    operation_name: str = "Bulk operation"
) -> List[T]:
    """
    Convenience function to validate bulk operations
    
    Args:
        items: List of items to validate
        max_size: Maximum allowed size
        operation_name: Name for error messages
        
    Returns:
        Validated list
        
    Raises:
        HTTPException: If validation fails
    """
    validator = BulkOperationValidator(max_bulk_size=max_size)
    return validator.validate_size(items, operation_name)


def validate_user_bulk(items: List[dict]) -> List[dict]:
    """Validate bulk user operations"""
    return validate_bulk_operation(items, max_size=500, operation_name="User bulk operation")


def validate_order_bulk(items: List[dict]) -> List[dict]:
    """Validate bulk order operations"""
    return validate_bulk_operation(items, max_size=200, operation_name="Order bulk operation")


def validate_message_bulk(items: List[dict]) -> List[dict]:
    """Validate bulk message operations"""
    return validate_bulk_operation(items, max_size=1000, operation_name="Message bulk operation")


def validate_withdrawal_bulk(items: List[dict]) -> List[dict]:
    """Validate bulk withdrawal operations (stricter limit)"""
    return validate_bulk_operation(items, max_size=100, operation_name="Withdrawal bulk operation")
