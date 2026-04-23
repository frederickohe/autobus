# core/nlu/service/intent_processor.py
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Any, Optional
from core.customers.service.customer_service import CustomerService
from core.product.service.product_service import ProductService
from core.product.dto.product_create_dto import ProductCreateDTO
from core.product.dto.product_update_dto import ProductUpdateDTO
from core.orders.service.order_service import OrderService
from core.orders.dto.order_create_dto import OrderCreateDTO
from core.orders.dto.order_update_dto import OrderUpdateDTO
from core.nlu.service.llmclient import LLMClient
from core.nlu.config import SYSTEM_PROMPTS, RESPONSE_TEMPLATES
from core.nlu.service.datapipe.dataconfig import FINANCIAL_INSIGHTS_SYSTEM_PROMPT, INSIGHTS_SYSTEM_PROMPT
from core.nlu.service.datapipe.user_rag import UserRAGManager
from core.user.controller.usercontroller import get_db
from core.customers.service.customer_service import CustomerService
import logging
from core.nlu.service.datapipe.dataengine import EnhancedUserRAGManager

# Import agent framework tools
from core.agent.tools.email.email import EmailTool

# Import RAG tools for conversation support
from core.rag import RAGPipelineTool
from core.agent.tools.chatbot.enhanced_conversation_tool import EnhancedConversationTool

logger = logging.getLogger(__name__)

class IntentProcessor:
    """Processes intents using LLM and agent framework tools"""
    
    def __init__(self, db_session=None):
        self.llm_client = LLMClient()
        self.rag_manager = UserRAGManager()  # Initialize RAG manager
        self.db_session = db_session
        
        # Initialize agent framework tools
        self.email_tool = EmailTool()
        
        # Initialize RAG and conversation tools (lazy initialized if needed)
        self.rag_tool = None
        self.conversation_tool = None
    
    def process_conversational_intent(
        self, 
        intent: str, 
        user_message: str, 
        conversation_history: List[Dict],
        slots: Dict[str, Any],
        user_id: str = None,
        user_data: Optional[Dict] = None,
        use_rag: bool = False
    ) -> str:
        """
        Process conversational intents with optional RAG support.
        Uses EnhancedConversationTool for intelligent responses.
        Can detect when RAG should be used based on message content.
        
        Args:
            intent: Intent type
            user_message: User's message
            conversation_history: Conversation history
            slots: Extracted slots
            user_id: User ID (for RAG filtering)
            user_data: Additional user data
            use_rag: Whether to use RAG for this query (default: False)
            
        Returns:
            Generated response
        """
        # If RAG is requested or should be auto-detected, use EnhancedConversationTool
        if user_id and (use_rag or self._should_use_rag(user_message, slots)):
            return self._handle_conversational_with_rag(
                user_message=user_message,
                user_id=user_id,
                conversation_history=conversation_history
            )
        
        # Fallback to LLM-only conversation
        # Prepare enhanced system prompt with user context
        system_prompt = self._build_enhanced_system_prompt(
            base_prompt=SYSTEM_PROMPTS["conversational"],
            user_data=user_data,
            intent=intent,
            slots=slots
        )
        
        response = self.llm_client.chat_completion(
            system_prompt=system_prompt,
            user_message=user_message,
            conversation_history=conversation_history,
            temperature=0.7
        )
        
        return self._format_conversational_response(intent, response, slots)
    
    def process_financial_tips_intent(
        self,
        intent: str,
        user_message: str,
        conversation_history: List[Dict],
        slots: Dict[str, Any],
        user_data: Optional[Dict] = None  # Add user_data parameter
    ) -> str:
        """
        Process financial tips with personalized user context
        """
        # Prepare enhanced system prompt with user context
        system_prompt = self._build_enhanced_system_prompt(
            base_prompt=SYSTEM_PROMPTS["financial_tips"],
            user_data=user_data,
            intent=intent,
            slots=slots
        )
        
        response = self.llm_client.chat_completion(
            system_prompt=system_prompt,
            user_message=user_message,
            conversation_history=conversation_history,
            temperature=0.4
        )
        
        return self._format_financial_tips_response(intent, response, slots)

    def process_expense_report_intent(
        self,
        intent: str,
        user_message: str,
        conversation_history: List[Dict],
        slots: Dict[str, Any],
        user_data: Optional[Dict] = None
    ) -> str:
        """
        Process expense report with enhanced financial insights
        """
        
        # Build enhanced system prompt
        system_prompt = self._build_enhanced_system_prompt(
            base_prompt=SYSTEM_PROMPTS["expense_report"],
            user_data=user_data,
            intent=intent,
            slots=slots
        )
        
        response = self.llm_client.chat_completion(
            system_prompt=system_prompt,
            user_message=user_message,
            conversation_history=conversation_history,
            temperature=0.4
        )
        
        return self._clean_markdown_formatting(response)
    
    def process_customers_intent(
    self,
    intent: str,
    user_message: str,
    conversation_history: List[Dict],
    slots: Dict[str, Any],
    user_data: Optional[Dict] = None
    ) -> str:
        """
        Process customers management using CustomerService
        """

        db = next(get_db())

        customer_service = CustomerService(db)
        
        # For customer DB operations we need the internal `users.id` (FK target).
        user_id = (user_data or {}).get("db_user_id") or (user_data or {}).get("user_id") or "unknown"
        
        if intent == "add_customer":
            return self._handle_add_customer(customer_service, user_id, slots)
        elif intent == "view_customers":
            return self._handle_view_customers(customer_service, user_id)
        elif intent == "delete_customer":
            return self._handle_delete_customer(customer_service, user_id, slots)
        elif intent == "update_customer":
            return self._handle_update_customer(customer_service, user_id, slots)
        else:
            return "Customer intent not supported"

    def _handle_add_customer(self, customer_service: CustomerService, user_id: str, slots: Dict) -> str:
        """Handle adding a new customer"""
        name = slots.get("customer_name")
        customer_number = slots.get("customer_number")
        network = slots.get("network")
        bank_code = slots.get("bank_code")

        # print user data
        print(f"[METHOD_HANDLE_ADD_BENEFICIARY] User Data for {user_id}")
        
        if not name or not customer_number:
            return "Please provide both customer name and customer number to save a new customer."
        
        success, customer, message = customer_service.add_customer(
            user_id=user_id,
            name=name,
            customer_number=customer_number,
            network=network,
            bank_code=bank_code
        )
        
        return message

    def _handle_view_customers(self, customer_service: CustomerService, user_id: str) -> str:
        """Handle viewing all customers"""
        customers = customer_service.get_customers(user_id)
        return customer_service.format_customer_list(customers)

    def _handle_delete_customer(self, customer_service: CustomerService, user_id: str, slots: Dict) -> str:
        """Handle deleting a customer"""
        customer_name = slots.get("customer_name")
        
        if not customer_name:
            return "Please specify which customer you want to remove."
        
        customers = customer_service.get_customers(user_id)
        
        # Find customer by name
        target_customer = None
        for customer in customers:
            if customer.name.lower() == customer_name.lower():
                target_customer = customer
                break
        
        if not target_customer:
            return f"Customer '{customer_name}' not found in your saved customers."
        
        success, message = customer_service.delete_customer(target_customer.id, user_id)
        return message

    def _handle_update_customer(self, customer_service: CustomerService, user_id: str, slots: Dict) -> str:
        """Handle updating a customer"""
        customer_name = slots.get("customer_name")
        new_name = slots.get("new_customer_name")
        customer_number = slots.get("customer_number")
        bank_code = slots.get("bank_code")

        if not customer_name:
            return "Please specify which customer you want to edit."

        if not any([new_name, customer_number, bank_code]):
            return "What would you like to update? You can send a new name, phone number, or bank code."

        customers = customer_service.get_customers(user_id)
        target_customer = None
        for customer in customers:
            if customer.name.lower() == customer_name.lower():
                target_customer = customer
                break

        if not target_customer:
            return f"Customer '{customer_name}' not found in your saved customers."

        success, customer, message = customer_service.update_customer(
            customer_id=target_customer.id,
            user_id=user_id,
            name=new_name,
            customer_number=customer_number,
            bank_code=bank_code
        )
        return message

    def _build_enhanced_system_prompt(
        self,
        base_prompt: str,
        user_data: Optional[Dict],
        intent: str,
        slots: Dict
    ) -> str:
        """
        Build enhanced system prompt with user context RAG
        """
        # Add user context if available
        user_context_section = ""
        if user_data and intent == "expense_report":
            # user_data produced by NLU uses the key 'user_id' (not 'id')
            # Ensure we pass a string user_id to the RAG manager so it matches
            # the History.user_id column (which is stored as string).
            # Get user name
            user_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
            if not user_name:
                user_name = user_data.get('username', 'User')
            
            # Get time frame from slots or default
            time_frame = slots.get('time_period', 'the selected period')
            
            # Fetch transactions using your existing method
            transactions = self.rag_manager.get_transaction_history(
                user_id=user_data.get('user_id'),
                intent=intent,
                slots=slots
            )
            
            rag_manager = EnhancedUserRAGManager()
            
            user_financial_context = rag_manager.get_financial_insights_context(
                user_name=user_name,
                user_id=user_data.get('user_id'),
                transactions=transactions,
                time_frame=time_frame,
                user_phone=user_data.get('phone_number')
            )
            user_context_section = f"User Transaction Data:\n{json.dumps(user_financial_context, indent=2)}"
            print(f"[ENHANCED_SYSTEM_PROMPT] User Transaction Data for {user_name}:\n{json.dumps(user_financial_context, indent=2)}")
        # Build the enhanced prompt
        enhanced_prompt = base_prompt.format(
            context=user_context_section,
            missing_slots="",
            category=slots.get('category', 'general')
        )
             
        return enhanced_prompt

    def _format_conversational_response(self, intent: str, response: str, slots: Dict) -> str:
        """Format conversational responses using templates"""
        template_data = RESPONSE_TEMPLATES["conversational"]
        
        if intent in template_data:
            template = template_data[intent]
            return template.format(response=response, **slots)
        
        return response

    def _format_financial_tips_response(self, intent: str, response: str, slots: Dict) -> str:
        """Format financial tips responses using templates"""
        template_data = RESPONSE_TEMPLATES["financial_tips"]
        
        if intent in template_data:
            template = template_data[intent]
            return template.format(response=response, **slots)
        
        return response

    def _clean_markdown_formatting(self, response: str) -> str:
        """
        Remove markdown formatting from response.
        Removes bold (**text**), italic (*text*), and other common markdown symbols
        """
        import re
        
        # Remove bold (**text** or __text__)
        response = re.sub(r'\*\*(.+?)\*\*', r'\1', response)
        response = re.sub(r'__(.+?)__', r'\1', response)
        
        # Remove italic (*text* or _text_) - be careful not to remove single asterisks
        response = re.sub(r'\*([^*\n]+)\*', r'\1', response)
        response = re.sub(r'_([^_\n]+)_', r'\1', response)
        
        # Remove markdown headings (# ## ### etc)
        response = re.sub(r'^#+\s+', '', response, flags=re.MULTILINE)
        
        # Remove markdown code blocks (```code```)
        response = re.sub(r'```.*?```', '', response, flags=re.DOTALL)
        
        # Remove inline code (`code`)
        response = re.sub(r'`([^`]+)`', r'\1', response)
        
        return response.strip()

    # ===== CONVERSATION INTENT HANDLER (WITH RAG SUPPORT) =====
    def _should_use_rag(self, user_message: str, slots: Dict) -> bool:
        """
        Detect if RAG should be used based on message content.
        
        Uses heuristics to determine if the query is about the user's knowledge base.
        Keywords like 'document', 'file', 'article', 'policy', 'info', etc. trigger RAG.
        """
        rag_keywords = [
            'document', 'file', 'article', 'policy', 'procedure',
            'guide', 'information', 'details', 'about', 'explain',
            'what', 'tell me', 'know', 'learn', 'find out',
            'look up', 'search', 'retrieve', 'get', 'show'
        ]
        
        message_lower = (user_message or "").lower()
        return any(keyword in message_lower for keyword in rag_keywords)
    
    def _initialize_conversation_tools(self, db_session=None) -> bool:
        """
        Initialize RAG and conversation tools.
        
        Args:
            db_session: Database session (if None, will use self.db_session or create new one)
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if self.conversation_tool is not None:
                return True  # Already initialized
            
            # Get or create db_session
            session = db_session or self.db_session
            if session is None:
                session = next(get_db())
            
            # Initialize RAG tool
            self.rag_tool = RAGPipelineTool(db_session=session)
            logger.debug("RAGPipelineTool initialized")
            
            # Initialize conversation tool with RAG support
            self.conversation_tool = EnhancedConversationTool(
                db_session=session,
                rag_tool=self.rag_tool
            )
            logger.debug("EnhancedConversationTool initialized with RAG support")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize conversation tools: {str(e)}")
            return False
    
    def _handle_conversational_with_rag(
        self,
        user_message: str,
        user_id: str,
        conversation_history: List[Dict] = None
    ) -> str:
        """
        Handle conversation using RAG-aware tool.
        
        Uses EnhancedConversationTool to provide knowledge-base aware responses.
        Falls back to general conversation if RAG fails.
        
        Args:
            user_message: User's message
            user_id: User ID for RAG filtering
            conversation_history: Conversation history (optional)
            
        Returns:
            Generated response
        """
        try:
            # Initialize tools if needed
            if not self._initialize_conversation_tools():
                logger.warning("Failed to initialize RAG tools, falling back to general conversation")
                return self._handle_fallback_conversation(user_message)
            
            logger.info(f"Processing conversation with RAG for user {user_id}")
            
            # Use the enhanced conversation tool in RAG-aware mode
            response = self.conversation_tool._run(
                message=user_message,
                user_id=user_id,
                conversation_mode="rag_aware",
                use_rag=True
            )
            
            logger.info(f"RAG conversation completed for user {user_id}")
            return response
            
        except Exception as e:
            logger.error(f"RAG conversation error: {str(e)}", exc_info=True)
            # Fallback to general LLM-only conversation
            return self._handle_fallback_conversation(user_message)
    
    def _handle_fallback_conversation(self, user_message: str) -> str:
        """
        Fallback conversation handler when RAG is unavailable.
        
        Uses basic LLM conversation without knowledge base context.
        
        Args:
            user_message: User's message
            
        Returns:
            Generated response
        """
        try:
            system_prompt = (
                "You are a helpful and friendly AI assistant. "
                "Provide concise and accurate responses to user questions."
            )
            
            response = self.llm_client.chat_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                conversation_history=[],
                temperature=0.7
            )
            
            logger.info("Fallback conversation generated successfully")
            return response
            
        except Exception as e:
            logger.error(f"Fallback conversation failed: {str(e)}")
            return (
                "I'm experiencing technical difficulties. "
                "Please try again in a moment."
            )

    def _prepare_conversation_context(self, conversation_history: List[Dict]) -> str:
        """Prepare conversation context from history"""
        if not conversation_history:
            return "New conversation"
        
        context = "Recent conversation history:\n"
        for msg in conversation_history:
            role = "User" if msg["role"] == "user" else "Assistant"
            context += f"{role}: {msg['content']}\n"
        
        return context

    # ===== EMAIL INTENT HANDLER =====
    def process_email_intent(
        self,
        intent: str,
        user_message: str,
        conversation_history: List[Dict],
        slots: Dict[str, Any],
        user_id: str,
        agent_name: str = "email_agent",
        user_data: Optional[Dict] = None
    ) -> str:
        """
        Process email intents using EmailTool
        
        Supported intents:
        - send_email: Send an email to a recipient
        - read_emails: Read recent emails from inbox
        """
        try:
            if intent == "send_email":
                return self._handle_send_email(user_id, slots, agent_name)
            elif intent == "read_emails":
                return self._handle_read_emails(user_id, slots)
            else:
                return f"❌ Email intent '{intent}' not supported"
        except Exception as e:
            logger.error(f"Error processing email intent: {e}", exc_info=True)
            return f"❌ Error processing email: {str(e)[:100]}"

    def _handle_send_email(self, user_id: str, slots: Dict[str, Any], agent_name: str) -> str:
        """Handle send_email intent using EmailTool"""
        recipient_email = slots.get("recipient_email")
        subject = slots.get("subject")
        body = slots.get("body")
        
        if not recipient_email or not subject or not body:
            missing = []
            if not recipient_email:
                missing.append("recipient email")
            if not subject:
                missing.append("subject")
            if not body:
                missing.append("body")
            return f"❌ Missing required fields: {', '.join(missing)}"
        
        # Use EmailTool to send email
        result = self.email_tool._run(
            to_email=recipient_email,
            subject=subject,
            body=body,
            user_id=user_id,
            agent_name=agent_name
        )
        
        return result

    def _handle_read_emails(self, user_id: str, slots: Dict[str, Any]) -> str:
        """Handle read_emails intent"""
        num_emails = slots.get("num_emails", 10)
        
        # TODO: Implement email reading functionality when email API is available
        return f"📧 Email reading feature coming soon. Retrieving up to {num_emails} emails..."

    # ===== PRODUCT MANAGEMENT INTENT HANDLER =====
    def process_product_management_intent(
        self,
        intent: str,
        user_message: str,
        conversation_history: List[Dict],
        slots: Dict[str, Any],
        user_id: str,
        user_data: Optional[Dict] = None
    ) -> str:
        """
        Process product management intents
        
        Supported intents:
        - add_product: Add a new product to inventory
        - update_product: Update product details
        - delete_product: Delete a product
        - view_products: View all products
        - view_product: View specific product details
        """
        try:
            if intent == "add_product":
                return self._handle_add_product(user_id, slots)
            elif intent == "update_product":
                return self._handle_update_product(user_id, slots)
            elif intent == "delete_product":
                return self._handle_delete_product(user_id, slots)
            elif intent == "view_products":
                return self._handle_view_products(user_id, slots)
            elif intent == "view_product":
                return self._handle_view_product(user_id, slots)
            else:
                return f"❌ Product management intent '{intent}' not supported"
        except Exception as e:
            logger.error(f"Error processing product management intent: {e}", exc_info=True)
            return f"❌ Error processing product: {str(e)[:100]}"

    def _handle_add_product(self, user_id: str, slots: Dict[str, Any]) -> str:
        """Handle add_product intent"""
        product_name = slots.get("product_name")
        price = slots.get("price")
        quantity = slots.get("quantity")
        
        if not product_name or not price or not quantity:
            missing = []
            if not product_name:
                missing.append("product name")
            if not price:
                missing.append("price")
            if not quantity:
                missing.append("quantity")
            return f"❌ Missing required fields: {', '.join(missing)}"

        db = next(get_db())
        product_service = ProductService(db)

        try:
            product_data = ProductCreateDTO(
                photo=slots.get("photo") or "https://placeholder.local/product.png",
                name=product_name,
                description=slots.get("description"),
                price=self._to_float(price, default=0.0),
                category=slots.get("category"),
                condition=slots.get("condition") or "New",
                number_in_stock=self._to_int(quantity, default=0),
                link=slots.get("link")
            )
        except Exception as e:
            return f"❌ Invalid product details: {str(e)}"

        success, product, message = product_service.create_product(product_data)
        if not success:
            return f"❌ {message}"
        if not product:
            return "❌ Product was created but could not be retrieved."

        return (
            f"✅ {message}\n"
            f"Product: {product.name}\n"
            f"Inventory ID: {product.inventory_id}\n"
            f"Price: {product.price}\n"
            f"Stock: {product.number_in_stock if product.number_in_stock is not None else 'N/A'}"
        )

    def _handle_update_product(self, user_id: str, slots: Dict[str, Any]) -> str:
        """Handle update_product intent"""
        product_id = slots.get("product_id")

        db = next(get_db())
        product_service = ProductService(db)

        product = self._find_product(product_service, slots)
        if not product:
            if product_id:
                return f"❌ Product '{product_id}' not found"
            return "❌ Product ID, inventory ID, or product name is required for updating"

        update_payload = {}
        if slots.get("product_name") is not None:
            update_payload["name"] = slots.get("product_name")
        if slots.get("price") is not None:
            update_payload["price"] = self._to_float(slots.get("price"))
        if slots.get("quantity") is not None:
            update_payload["number_in_stock"] = self._to_int(slots.get("quantity"))
        if slots.get("condition") is not None:
            update_payload["condition"] = slots.get("condition")
        if slots.get("category") is not None:
            update_payload["category"] = slots.get("category")
        if slots.get("description") is not None:
            update_payload["description"] = slots.get("description")
        if slots.get("photo") is not None:
            update_payload["photo"] = slots.get("photo")
        if slots.get("link") is not None:
            update_payload["link"] = slots.get("link")

        if not update_payload:
            return "❌ No updates specified"

        try:
            update_data = ProductUpdateDTO(**update_payload)
        except Exception as e:
            return f"❌ Invalid update fields: {str(e)}"

        success, updated_product, message = product_service.update_product(str(product.product_id), update_data)
        if not success:
            return f"❌ {message}"
        if not updated_product:
            return "❌ Product was updated but could not be retrieved."

        return (
            f"✅ {message}\n"
            f"Product: {updated_product.name}\n"
            f"Inventory ID: {updated_product.inventory_id}"
        )

    def _handle_delete_product(self, user_id: str, slots: Dict[str, Any]) -> str:
        """Handle delete_product intent"""
        product_id = slots.get("product_id")

        db = next(get_db())
        product_service = ProductService(db)

        product = self._find_product(product_service, slots)
        if not product:
            if product_id:
                return f"❌ Product '{product_id}' not found"
            return "❌ Product ID, inventory ID, or product name is required for deletion"

        success, message = product_service.delete_product(str(product.product_id))
        if not success:
            return f"❌ {message}"

        return f"✅ {message} (Removed: {product.name} - {product.inventory_id})"

    def _handle_view_products(self, user_id: str, slots: Dict[str, Any]) -> str:
        """Handle view_products intent"""
        db = next(get_db())
        product_service = ProductService(db)

        category = slots.get("category")
        products = product_service.get_all_products(category=category)
        if not products:
            return "📦 No products found in your inventory yet."

        lines = ["📦 Your Products:"]
        for index, product in enumerate(products[:20], 1):
            lines.append(
                f"{index}. {product.name} | ID: {product.product_id} | "
                f"Inventory: {product.inventory_id} | Price: {product.price} | "
                f"Stock: {product.number_in_stock if product.number_in_stock is not None else 'N/A'}"
            )

        if len(products) > 20:
            lines.append(f"...and {len(products) - 20} more products.")
        return "\n".join(lines)

    def _handle_view_product(self, user_id: str, slots: Dict[str, Any]) -> str:
        """Handle view_product intent"""
        product_id = slots.get("product_id")

        db = next(get_db())
        product_service = ProductService(db)

        product = self._find_product(product_service, slots)
        if not product:
            if product_id:
                return f"❌ Product '{product_id}' not found"
            return "❌ Product ID, inventory ID, or product name is required"

        return (
            "📦 Product Details:\n"
            f"ID: {product.product_id}\n"
            f"Inventory ID: {product.inventory_id}\n"
            f"Name: {product.name}\n"
            f"Price: {product.price}\n"
            f"Quantity: {product.number_in_stock if product.number_in_stock is not None else 'N/A'}\n"
            f"Category: {product.category or 'N/A'}\n"
            f"Condition: {product.condition}\n"
            f"Description: {product.description or 'N/A'}\n"
            f"Link: {product.link or 'N/A'}"
        )

    # ===== ORDER MANAGEMENT INTENT HANDLER =====
    def process_order_management_intent(
        self,
        intent: str,
        user_message: str,
        conversation_history: List[Dict],
        slots: Dict[str, Any],
        user_id: str,
        user_data: Optional[Dict] = None
    ) -> str:
        """
        Process order management intents
        
        Supported intents:
        - create_order: Create a new order
        - update_order: Update order details
        """
        try:
            if intent == "create_order":
                return self._handle_create_order(user_id, slots)
            elif intent == "update_order":
                return self._handle_update_order(user_id, slots)
            else:
                return f"❌ Order management intent '{intent}' not supported"
        except Exception as e:
            logger.error(f"Error processing order management intent: {e}", exc_info=True)
            return f"❌ Error processing order: {str(e)[:100]}"

    def _handle_create_order(self, user_id: str, slots: Dict[str, Any]) -> str:
        """Handle create_order intent"""
        customer_name = slots.get("customer_name")
        item_name = slots.get("item_name")
        quantity = slots.get("quantity")
        
        if not customer_name or not item_name or not quantity:
            missing = []
            if not customer_name:
                missing.append("customer name")
            if not item_name:
                missing.append("item name")
            if not quantity:
                missing.append("quantity")
            return f"❌ Missing required fields: {', '.join(missing)}"

        db = next(get_db())
        order_service = OrderService(db)

        line_quantity = self._to_int(quantity, default=0)
        if line_quantity <= 0:
            return "❌ Quantity must be greater than 0."

        unit_price = self._to_decimal(slots.get("unit_price"), default=Decimal("0"))
        subtotal = self._to_decimal(slots.get("subtotal_amount"), default=(unit_price * line_quantity))

        try:
            order_data = OrderCreateDTO(
                customer_name=customer_name,
                customer_phone=slots.get("customer_phone") or "N/A",
                customer_email=slots.get("customer_email"),
                customer_location=slots.get("customer_location"),
                order_type=(slots.get("order_type") or "sale").lower(),
                item_name=item_name,
                quantity=line_quantity,
                order_source=slots.get("order_source") or "chat",
                subtotal_amount=subtotal,
                discount_amount=self._to_decimal(slots.get("discount_amount"), default=Decimal("0")),
                tax_amount=self._to_decimal(slots.get("tax_amount"), default=Decimal("0")),
                shipping_amount=self._to_decimal(slots.get("shipping_amount"), default=Decimal("0")),
                currency_code=(slots.get("currency_code") or "GHS").upper(),
                payment_method=slots.get("payment_method"),
                payment_reference=slots.get("payment_reference"),
                payment_details=slots.get("payment_details"),
                notes=slots.get("notes"),
                tags=slots.get("tags"),
                custom_metadata=slots.get("custom_metadata")
            )
        except Exception as e:
            return f"❌ Invalid order details: {str(e)}"

        success, order, message = order_service.create_order(order_data)
        if not success:
            return f"❌ {message}"
        if not order:
            return "❌ Order was created but could not be retrieved."

        return (
            f"✅ {message}\n"
            f"Order Number: {order.order_number}\n"
            f"Customer: {order.customer_name}\n"
            f"Total Amount: {order.total_amount} {order.currency_code}"
        )

    def _handle_update_order(self, user_id: str, slots: Dict[str, Any]) -> str:
        """Handle update_order intent"""
        order_id = slots.get("order_id")

        if not order_id:
            return "❌ Order ID is required for updating"

        db = next(get_db())
        order_service = OrderService(db)

        update_payload = {}
        for field in [
            "order_status", "payment_status", "fulfillment_status", "payment_method",
            "payment_reference", "payment_details", "customer_name", "customer_phone",
            "customer_email", "customer_location", "notes", "tags", "custom_metadata"
        ]:
            if slots.get(field) is not None:
                update_payload[field] = slots.get(field)

        if slots.get("subtotal_amount") is not None:
            update_payload["subtotal_amount"] = self._to_decimal(slots.get("subtotal_amount"))
        if slots.get("discount_amount") is not None:
            update_payload["discount_amount"] = self._to_decimal(slots.get("discount_amount"))
        if slots.get("tax_amount") is not None:
            update_payload["tax_amount"] = self._to_decimal(slots.get("tax_amount"))
        if slots.get("shipping_amount") is not None:
            update_payload["shipping_amount"] = self._to_decimal(slots.get("shipping_amount"))

        if slots.get("quantity") is not None or slots.get("item_name") is not None:
            item_qty = self._to_int(slots.get("quantity"), default=None)
            if item_qty is not None and item_qty <= 0:
                return "❌ Quantity must be greater than 0."

            if slots.get("item_name") is not None:
                update_payload["item_name"] = slots.get("item_name")

            if item_qty is not None:
                update_payload["quantity"] = item_qty

        if not update_payload:
            return "❌ No updates specified"

        try:
            update_data = OrderUpdateDTO(**update_payload)
        except Exception as e:
            return f"❌ Invalid order update details: {str(e)}"

        success, order, message = order_service.update_order(order_id, update_data)
        if not success:
            return f"❌ {message}"
        if not order:
            return "❌ Order was updated but could not be retrieved."

        return (
            f"✅ {message}\n"
            f"Order Number: {order.order_number}\n"
            f"Status: {order.order_status} | Payment: {order.payment_status} | Fulfillment: {order.fulfillment_status}"
        )

    def _find_product(self, product_service: ProductService, slots: Dict[str, Any]):
        """Resolve a product from supported slot keys."""
        product_id = slots.get("product_id")
        if product_id:
            product = product_service.get_product_by_id(str(product_id))
            if product:
                return product
            return product_service.get_product_by_inventory_id(str(product_id))

        inventory_id = slots.get("inventory_id")
        if inventory_id:
            return product_service.get_product_by_inventory_id(str(inventory_id))

        product_name = slots.get("product_name")
        if product_name:
            products = product_service.get_product_by_name(str(product_name), limit=1)
            return products[0] if products else None
        return None

    def _to_int(self, value: Any, default: Optional[int] = None) -> Optional[int]:
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _to_float(self, value: Any, default: Optional[float] = None) -> Optional[float]:
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _to_decimal(self, value: Any, default: Optional[Decimal] = None) -> Optional[Decimal]:
        if value is None:
            return default
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return default



