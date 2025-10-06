#!/usr/bin/env python3
"""
Payment middleware for NANDA agents.

This module handles payment flows between agents:
1. Checks if target agent requires payment (serviceCharge > 0)
2. Returns 402 Payment Required with amount if needed
3. Processes payments via nanda-payments MCP server
4. Validates receipts before processing requests
"""

import asyncio
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# MCP support imports
try:
    from .mcp_client import MCPClient
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


class PaymentStatus(Enum):
    """Payment status enum"""
    NOT_REQUIRED = "not_required"
    REQUIRED = "required" 
    PAID = "paid"
    INVALID_RECEIPT = "invalid_receipt"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    PAYMENT_FAILED = "payment_failed"


@dataclass
class PaymentResult:
    """Result of payment check/processing"""
    status: PaymentStatus
    amount: int = 0
    receipt_id: Optional[str] = None
    message: str = ""
    transaction_id: Optional[str] = None


class PaymentMiddleware:
    """
    Middleware for handling agent-to-agent payment flows.
    
    Handles the complete payment lifecycle:
    1. Check if payment required
    2. Process payment via MCP
    3. Validate receipts
    4. Return appropriate responses
    """
    
    def __init__(self, registry, mcp_registry=None):
        """
        Initialize payment middleware.
        
        Args:
            registry: Agent registry (LocalRegistry or MongoRegistry)
            mcp_registry: MCP registry for payment server access
        """
        self.registry = registry
        self.mcp_registry = mcp_registry
        
    def check_payment_requirement(self, target_agent_id: str) -> PaymentResult:
        """
        Check if target agent requires payment.
        
        Args:
            target_agent_id: ID of the agent being contacted
            
        Returns:
            PaymentResult indicating if payment is required
        """
        # Get target agent info
        agent_info = self.registry.get_agent_info(target_agent_id)
        
        if not agent_info:
            return PaymentResult(
                status=PaymentStatus.NOT_REQUIRED,
                message=f"Agent {target_agent_id} not found"
            )
        
        service_charge = agent_info.get("service_charge", 0)
        
        if service_charge <= 0:
            return PaymentResult(
                status=PaymentStatus.NOT_REQUIRED,
                message=f"Agent {target_agent_id} is free"
            )
        
        return PaymentResult(
            status=PaymentStatus.REQUIRED,
            amount=service_charge,
            message=f"Agent {target_agent_id} requires {service_charge} NP per request"
        )
    
    async def process_payment(
        self, 
        source_agent_id: str, 
        target_agent_id: str, 
        amount: int,
        mcp_server_url: str = "https://p01--nanda-points-mcp--qvf8hqwjtv29.code.run/mcp",
        anthropic_client=None
    ) -> PaymentResult:
        """
        Process payment from source to target agent.
        
        Args:
            source_agent_id: Agent making the payment
            target_agent_id: Agent receiving the payment  
            amount: Amount in Neural Points
            mcp_server_url: nanda-payments MCP server URL
            
        Returns:
            PaymentResult with transaction details
        """
        if not MCP_AVAILABLE:
            return PaymentResult(
                status=PaymentStatus.PAYMENT_FAILED,
                message="MCP support not available"
            )
        
        try:
            async with MCPClient(anthropic_client) as client:
                # Initiate transaction via MCP
                query = f"initiate a transaction of {amount} NP from {source_agent_id} to {target_agent_id}"
                result = await client.process_query(query, mcp_server_url)
                
                # Parse result to extract receipt/transaction ID
                # This is a simple parser - you might want to make it more robust
                if "receipt" in result.lower() and "id" in result.lower():
                    # Extract receipt ID from result
                    import re
                    receipt_match = re.search(r'receipt[_\s]?id[:\s]+([a-zA-Z0-9\-]+)', result, re.IGNORECASE)
                    transaction_match = re.search(r'transaction[_\s]?id[:\s]+([a-zA-Z0-9\-]+)', result, re.IGNORECASE)
                    
                    receipt_id = receipt_match.group(1) if receipt_match else None
                    transaction_id = transaction_match.group(1) if transaction_match else None
                    
                    return PaymentResult(
                        status=PaymentStatus.PAID,
                        amount=amount,
                        receipt_id=receipt_id,
                        transaction_id=transaction_id,
                        message=f"Payment of {amount} NP processed successfully"
                    )
                elif "insufficient" in result.lower():
                    return PaymentResult(
                        status=PaymentStatus.INSUFFICIENT_BALANCE,
                        message=f"Insufficient balance for {amount} NP payment"
                    )
                else:
                    return PaymentResult(
                        status=PaymentStatus.PAYMENT_FAILED,
                        message=f"Payment failed: {result}"
                    )
                    
        except Exception as e:
            return PaymentResult(
                status=PaymentStatus.PAYMENT_FAILED,
                message=f"Payment processing error: {str(e)}"
            )
    
    async def validate_receipt(
        self, 
        receipt_id: str,
        mcp_server_url: str = "https://p01--nanda-points-mcp--qvf8hqwjtv29.code.run/mcp",
        anthropic_client=None
    ) -> PaymentResult:
        """
        Validate a payment receipt.
        
        Args:
            receipt_id: Receipt ID to validate
            mcp_server_url: nanda-payments MCP server URL
            
        Returns:
            PaymentResult with validation status
        """
        if not MCP_AVAILABLE:
            return PaymentResult(
                status=PaymentStatus.INVALID_RECEIPT,
                message="MCP support not available"
            )
        
        try:
            async with MCPClient(anthropic_client) as client:
                # Get receipt via MCP
                query = f"get receipt for {receipt_id}"
                result = await client.process_query(query, mcp_server_url)
                
                # Check if receipt is valid
                if "not found" in result.lower() or "invalid" in result.lower():
                    return PaymentResult(
                        status=PaymentStatus.INVALID_RECEIPT,
                        message=f"Receipt {receipt_id} not found or invalid"
                    )
                
                # Extract amount from receipt
                import re
                amount_match = re.search(r'(\d+)\s*NP', result)
                amount = int(amount_match.group(1)) if amount_match else 0
                
                return PaymentResult(
                    status=PaymentStatus.PAID,
                    amount=amount,
                    receipt_id=receipt_id,
                    message=f"Receipt {receipt_id} validated for {amount} NP"
                )
                
        except Exception as e:
            return PaymentResult(
                status=PaymentStatus.INVALID_RECEIPT,
                message=f"Receipt validation error: {str(e)}"
            )
    
    def format_payment_required_response(self, payment_result: PaymentResult, target_agent_id: str) -> str:
        """
        Format 402 Payment Required response.
        
        Args:
            payment_result: Payment result with amount required
            target_agent_id: Target agent ID
            
        Returns:
            Formatted payment required message
        """
        return f"402-PAYMENT-REQUIRED: Agent '{target_agent_id}' requires {payment_result.amount} NP per request. Please include payment receipt in your message."
    
    def format_payment_success_response(self, payment_result: PaymentResult) -> str:
        """
        Format successful payment response.
        
        Args:
            payment_result: Payment result with transaction details
            
        Returns:
            Formatted success message
        """
        return f"✅ Payment processed: {payment_result.message}. Receipt ID: {payment_result.receipt_id}"
    
    def extract_receipt_from_message(self, message: str) -> Optional[str]:
        """
        Extract receipt ID from message.
        
        Args:
            message: Message that might contain receipt ID
            
        Returns:
            Receipt ID if found, None otherwise
        """
        import re
        
        # Look for receipt patterns
        patterns = [
            r'receipt[_\s]?id[:\s]+([a-zA-Z0-9\-]+)',
            r'receipt[:\s]+([a-zA-Z0-9\-]+)',
            r'payment[_\s]?receipt[:\s]+([a-zA-Z0-9\-]+)',
            r'#receipt[:\s]*([a-zA-Z0-9\-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None


# Helper function to create payment middleware
def create_payment_middleware(registry, mcp_registry=None):
    """
    Create payment middleware instance.
    
    Args:
        registry: Agent registry
        mcp_registry: MCP registry (optional)
        
    Returns:
        PaymentMiddleware instance
    """
    return PaymentMiddleware(registry, mcp_registry)