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
from typing import Optional, Dict, Any, List, Callable
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
            content=TextContent(text=f"Payment is required. Cost: {service_charge} points."),
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
    
    async def process_server_payment_and_service(
        self,
        payment_submitted_msg: Message,
        original_message: str,
        service_handler: Callable[[str], str]
    ) -> Message:
        """
        Server-side: Process payment submission and execute the actual service.
        
        Args:
            payment_submitted_msg: The payment-submitted message from client
            original_message: The original service request
            service_handler: Function that processes the original request and returns response
            
        Returns:
            Message with payment-completed status and actual service response
        """
        try:
            # Step 1: Verify payment submission
            payment_completion_msg = await self.handle_payment_submission(
                payment_submitted_msg=payment_submitted_msg,
                original_message=original_message
            )
            
            # Step 2: If payment successful, execute the actual service
            if self.is_payment_completed_message(payment_completion_msg):
                logger.info(f"✅ Payment verified, executing service for: {original_message}")
                
                # Execute the actual service
                service_response = service_handler(original_message)
                
                # Create combined response: payment completion + service result
                combined_text = f"{service_response}"
                
                # Update the payment completion message with service response
                payment_completion_msg.content = TextContent(text=combined_text)
                
                logger.info(f"✅ Service executed successfully with payment completion")
                return payment_completion_msg
            else:
                logger.error(f"❌ Payment verification failed")
                return payment_completion_msg  # Return the payment failure message
                
        except Exception as e:
            logger.error(f"❌ Server payment processing failed: {e}")
            return self.create_payment_failed_message(str(e))

    async def process_client_payment(
        self,
        payment_required_msg: Message,
        original_message: str,
        from_agent: str,
        target_agent: str = "payment_processor"
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
                to_agent=target_agent,
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
        """Process payment through MCP server using existing payment middleware logic."""
        try:
            # Use the existing payment middleware logic
            from .payment_middleware import PaymentMiddleware, PaymentStatus
            from .mcp_client import MCPClient
            
            # Create payment middleware instance
            payment_middleware = PaymentMiddleware(self.registry)
            
            # Process payment using the proven logic from payment_middleware
            payment_result = await payment_middleware.process_payment(
                source_agent_id=from_agent,
                target_agent_id=to_agent,
                amount=amount,
                mcp_server_url=self.mcp_server_url,
                anthropic_client=None  # Will use default client from MCPClient
            )
            
            logger.info(f"Payment result: {payment_result}")
            
            if payment_result.status == PaymentStatus.PAID:
                return {
                    "success": True,
                    "transaction_id": payment_result.transaction_id or payment_result.receipt_id,
                    "amount": payment_result.amount,
                    "status": "completed",
                    "receipt_id": payment_result.receipt_id
                }
            elif payment_result.status == PaymentStatus.INSUFFICIENT_BALANCE:
                return {
                    "success": False,
                    "error": "Insufficient balance",
                    "message": payment_result.message
                }
            else:
                return {
                    "success": False,
                    "error": "Payment failed",
                    "message": payment_result.message
                }
                    
        except Exception as e:
            logger.error(f"MCP payment processing failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _settle_payment_via_mcp(
        self,
        transaction_id: str,
        network: str,
        original_message: str
    ) -> Dict[str, Any]:
        """Settle payment through MCP server for verification using existing payment middleware."""
        try:
            # Use the existing payment middleware to validate the receipt/transaction
            from .payment_middleware import PaymentMiddleware, PaymentStatus
            
            payment_middleware = PaymentMiddleware(self.registry)
            
            logger.info(f"Validating transaction/receipt: {transaction_id}")
            
            # Validate the receipt using existing logic
            validation_result = await payment_middleware.validate_receipt(
                receipt_id=transaction_id,
                mcp_server_url=self.mcp_server_url,
                anthropic_client=None
            )
            
            if validation_result.status == PaymentStatus.PAID:
                return {
                    "success": True,
                    "transaction_hash": transaction_id,
                    "network": network,
                    "verified": True,
                    "amount": validation_result.amount
                }
            else:
                return {
                    "success": False,
                    "error": f"Receipt validation failed: {validation_result.message}"
                }
            
        except Exception as e:
            logger.error(f"Payment settlement failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def process_complete_payment_flow(
        self,
        payment_required_msg: Message,
        client,  # HTTP client for sending requests
        customer_agent_id: str,
        original_message: str,
        target_agent_url: str
    ) -> Optional[Message]:
        """
        Complete client-side payment flow:
        1. Process payment-required message
        2. Submit payment to target agent
        3. Receive final response with original request fulfilled
        """
        try:
            # Step 1: Process the payment-required message and create payment-submitted message
            logger.info(f"🔄 Step 1: Processing payment-required message for {customer_agent_id}")
            # Extract target agent from URL (simple extraction)
            target_agent = target_agent_url.split('/')[-2] if '/' in target_agent_url else "unknown_agent"
            
            payment_submitted_msg = await self.process_client_payment(
                payment_required_msg=payment_required_msg,
                original_message=original_message,
                from_agent=customer_agent_id,
                target_agent=target_agent
            )
            
            # Step 2: Send payment-submitted message back to target agent
            logger.info(f"🔄 Step 2: Submitting payment to target agent")
            
            # Format the payment submission as A2A message
            from .protocol import format_a2a_message
            payment_submission_data = format_a2a_message(
                content=payment_submitted_msg.content.text if hasattr(payment_submitted_msg.content, 'text') else str(payment_submitted_msg.content),
                sender_id=customer_agent_id,
                receiver_id="target_agent",
                metadata=payment_submitted_msg.metadata
            )
            
            # Send payment submission to target agent
            payment_response = client.post(
                target_agent_url,
                json=payment_submission_data,
                timeout=30
            )
            
            if payment_response.status_code != 200:
                raise X402PaymentError(f"Payment submission failed: {payment_response.status_code}")
            
            # Step 3: Process the response (should be payment-completed + actual service response)
            logger.info(f"🔄 Step 3: Processing payment completion response")
            
            response_data = payment_response.json()
            
            # Extract the response content and metadata
            response_content = response_data.get('content', '')
            response_metadata = response_data.get('metadata', {})
            
            # Create response message
            if PYTHON_A2A_AVAILABLE:
                final_response = Message(
                    role=MessageRole.AGENT,
                    content=TextContent(text=response_content),
                    metadata=Metadata()
                )
                if response_metadata:
                    final_response.metadata.custom_fields = response_metadata
            else:
                final_response = Message(
                    role="agent",
                    content=TextContent(text=response_content),
                    metadata=None
                )
            
            # Verify it's a payment-completed message
            if self.is_payment_completed_message(final_response):
                logger.info(f"✅ Payment flow completed successfully!")
                return final_response
            else:
                logger.warning(f"⚠️ Received response is not a payment-completed message")
                return final_response
                
        except Exception as e:
            logger.error(f"❌ Complete payment flow failed: {e}")
            raise X402PaymentError(f"Payment flow failed: {str(e)}")

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