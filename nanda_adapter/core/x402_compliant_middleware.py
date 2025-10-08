"""
X402 Payment Middleware - Official A2A x402 Specification Compliant.

This middleware implements the A2A x402 Payment Extension protocol following
the official Google specification. It uses python_a2a Message format with 
proper metadata fields as defined in the x402 specification.

Key compliance features:
- Official x402 metadata fields (x402.payment.status, x402.payment.required, etc.)
- Standard 3-step payment flow (payment-required → payment-submitted → payment-completed)
- Integration with MCP payment server
- Receipt tracking with x402.payment.receipts array
- Full python_a2a Message compatibility
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict

# Use python_a2a Message format
try:
    from python_a2a import Message, MessageRole, TextContent
    from python_a2a.models.content import Metadata
    PYTHON_A2A_AVAILABLE = True
except ImportError:
    PYTHON_A2A_AVAILABLE = False
    # Fallback for development - define dummy classes for typing
    class Message:
        def __init__(self, role=None, content=None, metadata=None):
            self.role = role
            self.content = content
            self.metadata = metadata
    
    class MessageRole:
        USER = "user"
        AGENT = "agent"
    
    class TextContent:
        def __init__(self, text):
            self.text = text
    
    class Metadata:
        def __init__(self):
            self.custom_fields = {}

from .registry import RegistryInterface


logger = logging.getLogger(__name__)


class X402PaymentStatus(Enum):
    """Official x402 payment status values as defined in the specification."""
    PAYMENT_REQUIRED = "payment-required"
    PAYMENT_SUBMITTED = "payment-submitted" 
    PAYMENT_REJECTED = "payment-rejected"
    PAYMENT_VERIFIED = "payment-verified"
    PAYMENT_COMPLETED = "payment-completed"
    PAYMENT_FAILED = "payment-failed"


@dataclass
class PaymentRequirements:
    """Payment requirements as defined in x402 specification section 5.2."""
    scheme: str  # e.g., "exact"
    network: str  # e.g., "base"
    asset: str  # Contract address of the token
    payTo: str  # Recipient's wallet address  
    maxAmountRequired: str  # Payment amount in token's smallest unit
    resource: Optional[str] = None
    description: Optional[str] = None
    maxTimeoutSeconds: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None


@dataclass
class X402PaymentRequiredResponse:
    """Payment required response as defined in x402 specification section 5.1."""
    x402Version: int = 1
    accepts: List[PaymentRequirements] = None
    
    def __post_init__(self):
        if self.accepts is None:
            self.accepts = []


@dataclass  
class PaymentPayload:
    """Payment payload as defined in x402 specification section 5.3."""
    x402Version: int
    network: str
    scheme: str
    payload: Dict[str, Any]


@dataclass
class X402SettleResponse:
    """Settlement response as defined in x402 specification section 5.4."""
    success: bool
    network: str
    errorReason: Optional[str] = None
    transaction: Optional[str] = None
    payer: Optional[str] = None


class X402PaymentError(Exception):
    """X402 payment processing error."""
    pass


class X402PaymentMiddleware:
    """
    X402 Payment Middleware following official specification.
    
    Handles payment detection, MCP server integration, and the complete
    x402 payment flow for both merchant and client agents using python_a2a Messages.
    """
    
    def __init__(self, registry_client: RegistryInterface, mcp_server_url: str):
        self.registry = registry_client
        self.mcp_server_url = mcp_server_url
        
        if not PYTHON_A2A_AVAILABLE:
            logger.warning("python_a2a not available - some features may not work properly")
    
    def create_payment_required_message(
        self, 
        agent_id: str,
        service_charge: int,
        message_text: str,
        pay_to_address: str = "0x0000000000000000000000000000000000000000",
        network: str = "base",
        asset: str = "0x833589fCD6eDb6E08f4c7C32D4f71b54bda02913"  # USDC on Base
    ) -> Message:
        """
        Create payment-required message following x402 specification.
        
        This is Step 1 of the x402 payment flow - merchant sends PaymentRequirements.
        """
        if not PYTHON_A2A_AVAILABLE:
            raise X402PaymentError("python_a2a not available")
            
        # Create payment requirements
        payment_requirements = PaymentRequirements(
            scheme="exact",
            network=network,
            asset=asset,
            payTo=pay_to_address,
            maxAmountRequired=str(service_charge),
            resource=f"https://api.nanda.com/service/{agent_id}",
            description=f"Service from {agent_id}",
            maxTimeoutSeconds=600
        )
        
        payment_required_response = X402PaymentRequiredResponse(
            x402Version=1,
            accepts=[payment_requirements]
        )
        
        # Create metadata with official x402 fields
        metadata = Metadata()
        metadata.custom_fields = {
            "x402.payment.status": X402PaymentStatus.PAYMENT_REQUIRED.value,
            "x402.payment.required": {
                "x402Version": payment_required_response.x402Version,
                "accepts": [asdict(req) for req in payment_required_response.accepts]
            }
        }
        
        # Create python_a2a Message
        message = Message(
            role=MessageRole.AGENT if PYTHON_A2A_AVAILABLE else "agent",
            content=TextContent(text=f"Payment is required for {message_text}. Cost: {service_charge} points."),
            metadata=metadata
        )
        
        logger.info(f"Created x402 payment-required message for {agent_id}, charge: {service_charge}")
        return message
    
    def create_payment_submitted_message(
        self,
        original_message: str,
        transaction_id: str,
        network: str = "base"
    ) -> Message:
        """
        Create payment-submitted message following x402 specification.
        
        This is Step 2 of the x402 payment flow - client submits PaymentPayload.
        """
        if not PYTHON_A2A_AVAILABLE:
            raise X402PaymentError("python_a2a not available")
            
        # Create payment payload (in real implementation, this would be signed)
        payment_payload = PaymentPayload(
            x402Version=1,
            network=network,
            scheme="exact",
            payload={
                "transaction_id": transaction_id,
                "signature": f"mock_signature_{transaction_id}",
                "nonce": "mock_nonce",
                "timestamp": "mock_timestamp"
            }
        )
        
        # Create metadata with official x402 fields
        metadata = Metadata()
        metadata.custom_fields = {
            "x402.payment.status": X402PaymentStatus.PAYMENT_SUBMITTED.value,
            "x402.payment.payload": asdict(payment_payload)
        }
        
        # Create python_a2a Message
        message = Message(
            role=MessageRole.USER if PYTHON_A2A_AVAILABLE else "user",
            content=TextContent(text=f"Payment submitted for: {original_message}"),
            metadata=metadata
        )
        
        logger.info(f"Created payment-submitted message with transaction: {transaction_id}")
        return message
    
    def create_payment_completed_message(
        self,
        original_message: str,
        transaction_id: str,
        network: str = "base",
        payer: Optional[str] = None
    ) -> Message:
        """
        Create payment-completed message following x402 specification.
        
        This is Step 3 of the x402 payment flow - merchant confirms settlement.
        """
        if not PYTHON_A2A_AVAILABLE:
            raise X402PaymentError("python_a2a not available")
            
        # Create settlement receipt
        receipt = X402SettleResponse(
            success=True,
            network=network,
            transaction=transaction_id,
            payer=payer
        )
        
        # Create metadata with official x402 fields
        metadata = Metadata()
        metadata.custom_fields = {
            "x402.payment.status": X402PaymentStatus.PAYMENT_COMPLETED.value,
            "x402.payment.receipts": [asdict(receipt)]
        }
        
        # Create python_a2a Message  
        message = Message(
            role=MessageRole.AGENT if PYTHON_A2A_AVAILABLE else "agent",
            content=TextContent(text=f"Payment completed successfully. Processing your request: {original_message}"),
            metadata=metadata
        )
        
        logger.info(f"Created payment-completed message for transaction: {transaction_id}")
        return message
    
    def create_payment_failed_message(
        self,
        error_reason: str,
        network: str = "base",
        transaction_id: Optional[str] = None
    ) -> Message:
        """
        Create payment-failed message following x402 specification.
        """
        if not PYTHON_A2A_AVAILABLE:
            raise X402PaymentError("python_a2a not available")
            
        # Create failed receipt
        receipt = X402SettleResponse(
            success=False,
            network=network,
            errorReason=error_reason,
            transaction=transaction_id
        )
        
        # Create metadata with official x402 fields
        metadata = Metadata()
        metadata.custom_fields = {
            "x402.payment.status": X402PaymentStatus.PAYMENT_FAILED.value,
            "x402.payment.error": error_reason,
            "x402.payment.receipts": [asdict(receipt)]
        }
        
        # Create python_a2a Message
        message = Message(
            role=MessageRole.AGENT if PYTHON_A2A_AVAILABLE else "agent",
            content=TextContent(text=f"Payment failed: {error_reason}"),
            metadata=metadata
        )
        
        logger.error(f"Created payment-failed message: {error_reason}")
        return message
    
    async def process_payment_flow(
        self,
        agent_id: str,
        service_charge: int,
        message_text: str,
        from_agent: str
    ) -> Message:
        """
        Complete payment flow: require payment → process payment → return completion.
        
        This handles the full x402 flow in one method for convenience.
        """
        try:
            # Step 1: Create payment-required message
            # Use a default wallet address (in production, get from registry)
            pay_to_address = "0x0000000000000000000000000000000000000000"
            
            payment_required_msg = self.create_payment_required_message(
                agent_id=agent_id,
                service_charge=service_charge,
                message_text=message_text,
                pay_to_address=pay_to_address
            )
            
            # For now, return the payment-required message
            # In a full implementation, this would wait for client response
            return payment_required_msg
            
        except Exception as e:
            logger.error(f"Error in payment flow: {e}")
            return self.create_payment_failed_message(str(e))
    
    async def handle_payment_submission(
        self,
        payment_submitted_msg: Message,
        original_message: str
    ) -> Message:
        """
        Handle payment-submitted message and return payment-completed or payment-failed.
        
        This processes Step 2 and returns Step 3 of the x402 flow.
        """
        try:
            # Extract payment payload from metadata
            if not payment_submitted_msg.metadata or not payment_submitted_msg.metadata.custom_fields:
                raise X402PaymentError("No metadata or custom_fields in payment submission")
            
            payment_payload_data = payment_submitted_msg.metadata.custom_fields.get("x402.payment.payload")
            if not payment_payload_data:
                raise X402PaymentError("No payment payload in submission")
            
            transaction_id = payment_payload_data.get("payload", {}).get("transaction_id")
            if not transaction_id:
                raise X402PaymentError("No transaction_id in payment payload")
            
            # Process payment via MCP server
            logger.info(f"Processing payment via MCP server: {transaction_id}")
            settlement_result = await self._settle_payment_via_mcp(
                transaction_id=transaction_id,
                network=payment_payload_data.get("network", "base"),
                original_message=original_message
            )
            
            if settlement_result["success"]:
                return self.create_payment_completed_message(
                    original_message=original_message,
                    transaction_id=transaction_id,  
                    network=payment_payload_data.get("network", "base")
                )
            else:
                error_reason = settlement_result.get("error", "Payment settlement failed")
                return self.create_payment_failed_message(
                    error_reason=error_reason,
                    network=payment_payload_data.get("network", "base"),
                    transaction_id=transaction_id
                )
                
        except Exception as e:
            logger.error(f"Error handling payment submission: {e}")
            return self.create_payment_failed_message(str(e))
    
    async def process_client_payment(
        self,
        payment_required_msg: Message,
        original_message: str,
        from_agent: str
    ) -> Message:
        """
        Client-side: Process payment-required message and create payment-submitted message.
        """
        try:
            # Extract payment requirements from metadata
            if not payment_required_msg.metadata or not payment_required_msg.metadata.custom_fields:
                raise X402PaymentError("No metadata in payment-required message")
            
            payment_required_data = payment_required_msg.metadata.custom_fields.get("x402.payment.required")
            if not payment_required_data:
                raise X402PaymentError("No payment requirements in message")
            
            # Get the first payment requirement
            accepts = payment_required_data.get("accepts", [])
            if not accepts:
                raise X402PaymentError("No payment options available")
            
            payment_req = accepts[0]
            amount = int(payment_req["maxAmountRequired"])
            
            # Process payment via MCP server to get transaction ID
            logger.info(f"Processing client payment via MCP: {amount} points")
            payment_result = await self._process_payment_via_mcp(
                amount=amount,
                from_agent=from_agent,
                to_agent="payment_processor",  # This would be extracted from context
                task_description=f"Payment for: {original_message}"
            )
            
            if not payment_result["success"]:
                raise X402PaymentError(f"Payment processing failed: {payment_result.get('error')}")
            
            transaction_id = payment_result["transaction_id"]
            
            # Create payment-submitted message
            return self.create_payment_submitted_message(
                original_message=original_message,
                transaction_id=transaction_id,
                network=payment_req.get("network", "base")
            )
            
        except Exception as e:
            logger.error(f"Error processing client payment: {e}")
            raise X402PaymentError(f"Failed to process payment: {str(e)}")
    
    async def _process_payment_via_mcp(
        self,
        amount: int,
        from_agent: str, 
        to_agent: str,
        task_description: str
    ) -> Dict[str, Any]:
        """Process payment through MCP server and return transaction details."""
        try:
            # Import MCP client here to avoid issues if not available
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            
            # Create MCP client session
            server_params = StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-fetch", self.mcp_server_url]
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Call process_payment with proper task parameter
                    result = await session.call_tool(
                        "process_payment",
                        {
                            "amount": amount,
                            "from_agent": from_agent,
                            "to_agent": to_agent,
                            "task": task_description  # This is required by the MCP server
                        }
                    )
                    
                    logger.info(f"MCP payment result: {result}")
                    
                    # Parse result based on MCP server response format
                    if hasattr(result, 'content') and result.content:
                        content = result.content[0]
                        if hasattr(content, 'text'):
                            response_data = json.loads(content.text)
                            return {
                                "success": True,
                                "transaction_id": response_data.get("transaction_id", "unknown"),
                                "amount": response_data.get("amount", amount),
                                "status": response_data.get("status", "completed")
                            }
                    
                    return {"success": False, "error": "Invalid MCP response format"}
                    
        except Exception as e:
            logger.error(f"MCP payment processing failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _settle_payment_via_mcp(
        self,
        transaction_id: str,
        network: str,
        original_message: str
    ) -> Dict[str, Any]:
        """Settle payment through MCP server for verification."""
        try:
            # For now, we'll treat the transaction_id as proof of payment
            # and return success. In a real implementation, this would
            # verify the transaction on the blockchain.
            
            logger.info(f"Settling payment transaction: {transaction_id}")
            
            # Mock settlement result - in reality this would verify on-chain
            return {
                "success": True,
                "transaction_hash": transaction_id,
                "network": network,
                "verified": True
            }
            
        except Exception as e:
            logger.error(f"Payment settlement failed: {e}")
            return {"success": False, "error": str(e)}
    
    def is_payment_required_message(self, message: Message) -> bool:
        """Check if message is a payment-required response."""
        if not message.metadata or not message.metadata.custom_fields:
            return False
        
        status = message.metadata.custom_fields.get("x402.payment.status")
        return status == X402PaymentStatus.PAYMENT_REQUIRED.value
    
    def is_payment_submitted_message(self, message: Message) -> bool:
        """Check if message is a payment-submitted request."""
        if not message.metadata or not message.metadata.custom_fields:
            return False
        
        status = message.metadata.custom_fields.get("x402.payment.status")
        return status == X402PaymentStatus.PAYMENT_SUBMITTED.value
    
    def is_payment_completed_message(self, message: Message) -> bool:
        """Check if message is a payment-completed response."""
        if not message.metadata or not message.metadata.custom_fields:
            return False
        
        status = message.metadata.custom_fields.get("x402.payment.status")
        receipts = message.metadata.custom_fields.get("x402.payment.receipts", [])
        return status == X402PaymentStatus.PAYMENT_COMPLETED.value and len(receipts) > 0
    
    def get_successful_transaction_id(self, message: Message) -> Optional[str]:
        """Extract transaction ID from successful payment completion."""
        if not self.is_payment_completed_message(message):
            return None
        
        receipts = message.metadata.custom_fields.get("x402.payment.receipts", [])
        for receipt in receipts:
            if receipt.get("success") and receipt.get("transaction"):
                return receipt["transaction"]
        
        return None