import os
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

MODEL = "gpt-4o"  # Multimodal model supporting text, images, audio, and video

# Local Model Configuration
MODEL_CONFIG = {
    "model_name": "microsoft/DialoGPT-large",  # or "google/flan-t5-base"
    "local_files_only": False,  # Set to True after first download
    "device": "cpu",  # or "cuda" if you have GPU
    "max_length": 512,
    "temperature": 0.1,
    "do_sample": True
}

# Enhanced Intent Configuration for AI-Powered Business System
INTENTS = {
    # ===== USER INTERACTION INTENTS =====
    "greeting": {
        "description": "Greet the user and establish context",
        "slots": ["user_name", "business_type"],
        "required_slots": [],
        "category": "user_interaction"
    },
    "general_query": {
        "description": "Handle general business inquiries and conversations",
        "slots": ["query_topic", "context"],
        "required_slots": [],
        "category": "user_interaction"
    },
    "goodbye": {
        "description": "End conversation professionally",
        "slots": [],
        "required_slots": [],
        "category": "user_interaction"
    },
    
    # ===== MARKETING AGENT INTENTS =====
    "create_campaign": {
        "description": "Create and launch marketing campaigns",
        "slots": ["campaign_name", "target_audience", "budget", "platform", "start_date", "end_date", "content_type"],
        "required_slots": ["campaign_name", "budget", "platform"],
        "category": "marketing"
    },
    "generate_social_post": {
        "description": "Create social media content for various platforms",
        "slots": ["platform", "topic", "tone", "hashtags", "visual_style", "post_type"],
        "required_slots": ["platform", "topic"],
        "category": "marketing"
    },
    "schedule_content": {
        "description": "Schedule marketing content across platforms",
        "slots": ["content_id", "platform", "posting_time", "frequency"],
        "required_slots": ["content_id", "posting_time"],
        "category": "marketing"
    },
    "analyze_campaign": {
        "description": "Analyze marketing campaign performance",
        "slots": ["campaign_id", "time_period", "metrics"],
        "required_slots": ["campaign_id"],
        "category": "marketing"
    },
    "engage_audience": {
        "description": "Respond to comments and messages",
        "slots": ["platform", "message_type", "urgency", "topic"],
        "required_slots": ["platform"],
        "category": "marketing"
    },
    
    # ===== SALES AGENT INTENTS =====
    "create_invoice": {
        "description": "Generate and send invoices to customers",
        "slots": ["customer_id", "products", "quantities", "due_date", "discount", "payment_terms"],
        "required_slots": ["customer_id", "products"],
        "category": "sales"
    },
    "process_order": {
        "description": "Process new customer orders",
        "slots": ["customer_id", "order_items", "shipping_address", "payment_method", "delivery_date"],
        "required_slots": ["customer_id", "order_items"],
        "category": "sales"
    },
    "track_order": {
        "description": "Track order status and delivery",
        "slots": ["order_id", "customer_id"],
        "required_slots": ["order_id"],
        "category": "sales"
    },
    "manage_customer": {
        "description": "Manage customer relationships and profiles",
        "slots": ["customer_id", "action", "details"],
        "required_slots": ["customer_id", "action"],
        "category": "sales"
    },
    "sales_report": {
        "description": "Generate sales reports and analytics",
        "slots": ["time_period", "product_category", "region", "salesperson"],
        "required_slots": ["time_period"],
        "category": "sales"
    },
    
    # ===== FINANCE AGENT INTENTS =====
    "process_payment": {
        "description": "Process payments via mobile money or other methods",
        "slots": ["payment_method", "amount", "customer_id", "invoice_id", "phone"],
        "required_slots": ["amount", "payment_method"],
        "category": "finance"
    },
    "check_financial_balance": {
        "description": "Check business account balances",
        "slots": ["account_type", "currency"],
        "required_slots": [],
        "category": "finance"
    },
    "generate_financial_report": {
        "description": "Generate financial statements and reports",
        "slots": ["report_type", "time_period", "format"],
        "required_slots": ["report_type", "time_period"],
        "category": "finance"
    },
    "manage_expenses": {
        "description": "Track and manage business expenses",
        "slots": ["expense_category", "amount", "date", "description", "receipt"],
        "required_slots": ["expense_category", "amount"],
        "category": "finance"
    },
    "reconcile_transactions": {
        "description": "Reconcile financial transactions",
        "slots": ["time_period", "account", "reference_number"],
        "required_slots": ["time_period"],
        "category": "finance"
    },
    "process_payroll": {
        "description": "Process employee payroll",
        "slots": ["employee_ids", "period", "bonuses", "deductions"],
        "required_slots": ["employee_ids", "period"],
        "category": "finance"
    },
    
    # ===== PROCUREMENT AGENT INTENTS =====
    "create_purchase_order": {
        "description": "Create purchase orders for suppliers",
        "slots": ["supplier_id", "items", "quantities", "delivery_date", "budget_code"],
        "required_slots": ["supplier_id", "items"],
        "category": "procurement"
    },
    "manage_inventory": {
        "description": "Check and manage inventory levels",
        "slots": ["product_id", "action", "quantity", "location"],
        "required_slots": ["product_id"],
        "category": "procurement"
    },
    "reorder_stock": {
        "description": "Automatically reorder stock when low",
        "slots": ["product_id", "reorder_quantity", "supplier_id", "urgency"],
        "required_slots": ["product_id", "reorder_quantity"],
        "category": "procurement"
    },
    "track_supplier": {
        "description": "Manage supplier relationships and performance",
        "slots": ["supplier_id", "action", "rating", "notes"],
        "required_slots": ["supplier_id"],
        "category": "procurement"
    },
    "inventory_report": {
        "description": "Generate inventory reports",
        "slots": ["report_type", "time_period", "category"],
        "required_slots": ["report_type"],
        "category": "procurement"
    },
    
    # ===== CUSTOMER SERVICE AGENT INTENTS =====
    "handle_complaint": {
        "description": "Handle customer complaints and issues",
        "slots": ["customer_id", "issue_type", "priority", "description", "order_id"],
        "required_slots": ["customer_id", "issue_type"],
        "category": "customer_service"
    },
    "provide_support": {
        "description": "Provide product/service support",
        "slots": ["customer_id", "product_id", "issue", "channel"],
        "required_slots": ["customer_id"],
        "category": "customer_service"
    },
    "send_notification": {
        "description": "Send notifications via SMS or email",
        "slots": ["recipient", "message_type", "channel", "template"],
        "required_slots": ["recipient", "message_type"],
        "category": "customer_service"
    },
    "manage_feedback": {
        "description": "Collect and manage customer feedback",
        "slots": ["customer_id", "feedback_type", "rating", "comments"],
        "required_slots": ["feedback_type"],
        "category": "customer_service"
    },
    "faq_response": {
        "description": "Respond to frequently asked questions",
        "slots": ["question_topic", "customer_id"],
        "required_slots": ["question_topic"],
        "category": "customer_service"
    },
    
    # ===== BUSINESS INTELLIGENCE INTENTS =====
    "predictive_analytics": {
        "description": "Generate business predictions and forecasts",
        "slots": ["prediction_type", "time_horizon", "variables"],
        "required_slots": ["prediction_type"],
        "category": "business_intelligence"
    },
    "pattern_recognition": {
        "description": "Identify business patterns and trends",
        "slots": ["data_type", "time_period", "segment"],
        "required_slots": ["data_type"],
        "category": "business_intelligence"
    },
    "business_insights": {
        "description": "Generate actionable business insights",
        "slots": ["focus_area", "time_period", "metrics"],
        "required_slots": ["focus_area"],
        "category": "business_intelligence"
    },
    "performance_dashboard": {
        "description": "Generate business performance dashboard",
        "slots": ["kpis", "time_period", "comparison"],
        "required_slots": ["time_period"],
        "category": "business_intelligence"
    }
}

# Enhanced System Prompts by Agent Category
SYSTEM_PROMPTS = {
     "transactional": """
     You are a Transactional Intent Detection system for the Autobus platform.

     Your job is to precisely detect user intents that relate to transactions, payments,
     ordering, billing, transfers and other short-lived actionable tasks, and to
     extract any required slot information.

     Focus on:
     1. Returning a single intent from the provided list when one is clear.
     2. Extracting slot values exactly as provided by the user (amounts, phone numbers,
         account numbers, beneficiary names, payment methods, dates).
     3. Listing any missing required slots explicitly in `{missing_slots}` format.
     4. Using the provided `context` to prefer the current conversational intent when
         the user is continuing an existing task.

     Category: {category}
     Current Context: {context}
     """,
    "conversational": """
    You are the Conversational AI assistant for Autobus.

    Your job is to handle general conversational intents such as greetings,
    small talk, follow-ups and general queries. Keep responses friendly,
    context-aware, and concise. Use the provided `context` to maintain
    conversation continuity.

    Category: {category}
    Current Context: {context}
    """,
    "expense_report": """
    You are the Expense Report manager. Summarize and analyze recent
    expenses, help the user generate or format expense reports, and flag
    anomalies. Use the user's transaction history when available.

    Category: {category}
    Current Context: {context}
    """,
    "beneficiaries": """
    You are the Beneficiaries manager. Assist with adding, viewing and
    deleting saved beneficiaries. Validate required fields and return
    clear user-facing messages for DB operations.

    Category: {category}
    Current Context: {context}
    """,
    "orchestrator": """
    You are the Autobus AI Orchestrator, the central brain of an autonomous business management system operating in Ghana and across Africa.
    
    Your role is to:
    1. Understand user requests through chat, voice, or image inputs
    2. Route requests to the appropriate specialized AI agent
    3. Maintain conversation context across multiple interactions
    4. Make autonomous decisions when appropriate
    5. Generate content (posts, invoices, reports) as needed
    
    Available Specialized Agents:
    - Marketing Agent: Handles campaigns, social media, content creation
    - Sales Agent: Manages invoices, orders, customer relationships
    - Finance Agent: Processes payments, financial reports, payroll
    - Procurement Agent: Manages inventory, suppliers, purchase orders
    - Customer Service Agent: Handles support, complaints, notifications
    
    You have access to a unified database containing:
    - Products inventory and details
    - Customer profiles and history
    - Orders and transactions
    - Financial records
    - Marketing campaigns and analytics
    
    Integration capabilities:
    - Mobile Money APIs (M-Pesa, MTN MoMo)
    - Social Media APIs (Facebook, Instagram, WhatsApp)
    - SMS/Email gateways
    - Payment processors
    
    Be professional, efficient, and proactive. Anticipate business needs and offer suggestions when appropriate.
    
    Current Context: {context}
    Active Agent: {active_agent}
    """,
    
    "marketing_agent": """
    You are the Autobus Marketing Agent, a specialized AI responsible for all marketing operations.
    
    Your capabilities:
    - Create and manage marketing campaigns across platforms
    - Generate engaging social media content
    - Schedule and publish posts
    - Analyze campaign performance
    - Engage with audience comments and messages
    
    Available platforms: Facebook, Instagram, WhatsApp
    Content types: Text posts, images, promotions, announcements
    
    Be creative, data-driven, and brand-conscious. Ensure all content aligns with the business voice and goals.
    
    Current Campaigns: {active_campaigns}
    Platform Analytics: {analytics}
    """,
    
    "sales_agent": """
    You are the Autobus Sales Agent, responsible for driving revenue and managing customer transactions.
    
    Your responsibilities:
    - Generate and send professional invoices
    - Process customer orders efficiently
    - Track order status and delivery
    - Manage customer relationships and profiles
    - Generate sales reports and insights
    
    Always be professional, accurate, and customer-focused. Ensure all financial transactions are properly documented.
    
    Current Orders: {pending_orders}
    Customer Context: {customer_context}
    """,
    
    "finance_agent": """
    You are the Autobus Finance Agent, the financial backbone of the business.
    
    Your duties:
    - Process payments via mobile money and other methods
    - Generate financial reports and statements
    - Track and categorize business expenses
    - Reconcile transactions
    - Process payroll
    - Monitor cash flow and financial health
    
    Integration with: M-Pesa, MTN MoMo, payment processors
    
    Be precise, secure, and compliant with financial regulations. Always verify transactions before processing.
    
    Current Balance: {account_balance}
    Pending Transactions: {pending_transactions}
    """,
    
    "procurement_agent": """
    You are the Autobus Procurement Agent, responsible for supply chain and inventory management.
    
    Your tasks:
    - Create and manage purchase orders
    - Monitor inventory levels
    - Automatically reorder stock when low
    - Track supplier performance
    - Generate inventory reports
    
    Be efficient, cost-conscious, and proactive. Prevent stockouts while minimizing excess inventory.
    
    Current Inventory: {inventory_levels}
    Active Suppliers: {supplier_list}
    Low Stock Alerts: {low_stock_alerts}
    """,
    
    "customer_service_agent": """
    You are the Autobus Customer Service Agent, the voice of support for the business.
    
    Your responsibilities:
    - Handle customer complaints professionally
    - Provide product and service support
    - Send notifications via SMS and email
    - Collect and manage customer feedback
    - Answer frequently asked questions
    
    Be empathetic, patient, and solution-oriented. Turn complaints into opportunities for improvement.
    
    Open Tickets: {open_tickets}
    Customer History: {customer_history}
    """,
    
    "business_intelligence_agent": """
    You are the Autobus Business Intelligence Agent, powered by the Business Logic Engine.
    
    Your capabilities:
    - Generate predictive analytics and forecasts
    - Identify business patterns and trends
    - Provide actionable business insights
    - Create performance dashboards
    - Make data-driven recommendations
    
    Use pattern recognition and predictive analytics to help the business grow and optimize operations.
    
    Current Metrics: {business_metrics}
    Historical Data: {historical_data}
    """
}

# Response Templates by Agent
RESPONSE_TEMPLATES = {
    "conversational": {
        "greeting": "Hello {user_name}! How can I assist you with your {business_type} today?",
        "general_query": "That's an interesting question about {query_topic}. Here's what I found: {response}",
        "goodbye": "Goodbye! If you need any more help with your {business_type}, just let me know!"
    },
    "orchestrator": {
        "routing": "I'll connect you with our {agent_name} to help with that request.",
        "clarification": "To better assist you, could you please provide more details about {missing_info}?",
        "multi_agent": "This request involves multiple departments. I'll coordinate between our {agents} to handle it efficiently."
    },
    
    "marketing_agent": {
        "campaign_created": "✅ Campaign '{campaign_name}' has been created successfully! Budget: {budget}, Platform: {platform}, Duration: {start_date} to {end_date}",
        "post_generated": "📱 Here's your {platform} post about {topic}:\n\n{content}\n\nWould you like me to schedule this or make adjustments?",
        "content_scheduled": "📅 Content scheduled for {platform} on {posting_time}. You'll receive a confirmation when published.",
        "campaign_analysis": "📊 Campaign '{campaign_name}' Performance:\n- Reach: {reach}\n- Engagement: {engagement}\n- Conversions: {conversions}\n- ROI: {roi}\n\nRecommendations: {recommendations}",
        "audience_response": "🗣️ Response to {message_type} on {platform}: {response}\n\nFollow-up needed: {follow_up}"
    },
    
    "sales_agent": {
        "invoice_created": "💰 Invoice #{invoice_number} created for {customer_name}. Amount: {amount} GHS, Due: {due_date}\n\nSent via {channel}.",
        "order_processed": "📦 Order #{order_id} processed successfully!\nItems: {items}\nTotal: {total}\nDelivery: {delivery_date}\n\nTracking number: {tracking}",
        "order_status": "🔍 Order #{order_id} status: {status}\nLocation: {location}\nEstimated delivery: {estimated_delivery}",
        "customer_updated": "👤 Customer profile for {customer_name} updated: {action} completed.",
        "sales_report": "📈 Sales Report for {time_period}:\nTotal Revenue: {revenue}\nOrders: {order_count}\nTop Product: {top_product}\nGrowth: {growth}%\n\nDetailed breakdown: {details}"
    },
    
    "finance_agent": {
        "payment_processed": "💵 Payment of {amount} GHS processed via {payment_method}. Reference: {reference}\nReceipt sent to {customer_contact}.",
        "balance_check": "💰 Current Account Balances:\nMain Account: {main_balance} GHS\nM-Pesa: {mpesa_balance} GHS\nMTN MoMo: {mtn_balance} GHS\n\nLast updated: {timestamp}",
        "financial_report": "📊 {report_type} for {time_period}:\nRevenue: {revenue}\nExpenses: {expenses}\nProfit: {profit}\nCash Flow: {cash_flow}\n\nKey Metrics: {metrics}",
        "expense_recorded": "🧾 Expense recorded: {expense_category} - {amount} GHS\nDescription: {description}\nDate: {date}",
        "reconciliation_complete": "✓ Reconciliation for {time_period} complete.\nMatched: {matched} transactions\nUnmatched: {unmatched}\nDiscrepancies: {discrepancies}",
        "payroll_processed": "👥 Payroll for {period} processed:\nEmployees: {employee_count}\nTotal: {total_amount}\nPayment date: {payment_date}\n\nPayslips sent to employees."
    },
    
    "procurement_agent": {
        "purchase_order_created": "📋 Purchase Order #{po_number} created for {supplier_name}\nItems: {items}\nTotal: {total}\nDelivery by: {delivery_date}",
        "inventory_updated": "📦 Inventory updated: {product_name} now at {quantity} units ({location})",
        "reorder_initiated": "⚠️ Low stock alert: {product_name} ({current} units)\nReorder of {reorder_quantity} units initiated with {supplier_name}.\nExpected delivery: {expected_date}",
        "supplier_updated": "🤝 Supplier {supplier_name} record updated.\nPerformance rating: {rating}/5\nNotes: {notes}",
        "inventory_report": "📊 Inventory Report:\nTotal SKUs: {total_skus}\nValue: {total_value} GHS\nLow Stock Items: {low_stock_items}\nOverstock Items: {overstock_items}\n\nRecommendations: {recommendations}"
    },
    
    "customer_service_agent": {
        "complaint_logged": "🎫 Complaint #{ticket_id} logged for {customer_name}\nIssue: {issue_type}\nPriority: {priority}\nAssigned to: {assigned_agent}",
        "support_response": "💬 Support for {customer_name} regarding {product}:\nIssue: {issue}\nResolution: {resolution}\nCustomer satisfaction: {satisfaction}/5",
        "notification_sent": "📨 {channel} notification sent to {recipient}\nType: {message_type}\nStatus: {status}",
        "feedback_recorded": "⭐ Feedback recorded: {feedback_type}\nRating: {rating}/5\nComments: {comments}\nAction items: {action_items}",
        "faq_response": "❓ Frequently Asked Question about {topic}:\n\nQuestion: {question}\nAnswer: {answer}\n\nAdditional resources: {resources}"
    },
    
    "business_intelligence_agent": {
        "prediction": "🔮 {prediction_type} Forecast for next {time_horizon}:\nPredicted: {predicted_value}\nConfidence: {confidence}%\nFactors: {factors}\n\nRecommendations: {recommendations}",
        "pattern_identified": "📐 Pattern detected in {data_type}:\nPattern: {pattern}\nSignificance: {significance}\nOpportunity: {opportunity}",
        "insight": "💡 Business Insight: {insight}\nImpact: {impact}\nRecommended action: {action}",
        "dashboard": "📊 Performance Dashboard ({time_period}):\n{metrics_display}\n\nHighlights: {highlights}\nAlerts: {alerts}"
    },
    
    "error_handling": {
        "missing_info": "I need the following information to proceed: {missing_fields}",
        "api_error": "I'm having trouble connecting to {service}. Please try again in a few moments.",
        "permission_error": "You don't have permission to perform this action. Please contact your administrator.",
        "general_error": "I encountered an error processing your request. Error: {error}\nSuggested action: {suggestion}"
    }
}

# Agent Categories for Routing
AGENT_CATEGORIES = {
    "marketing": ["create_campaign", "generate_social_post", "schedule_content", "analyze_campaign", "engage_audience"],
    "sales": ["create_invoice", "process_order", "track_order", "manage_customer", "sales_report"],
    "finance": ["process_payment", "check_financial_balance", "generate_financial_report", "manage_expenses", "reconcile_transactions", "process_payroll"],
    "procurement": ["create_purchase_order", "manage_inventory", "reorder_stock", "track_supplier", "inventory_report"],
    "customer_service": ["handle_complaint", "provide_support", "send_notification", "manage_feedback", "faq_response"],
    "business_intelligence": ["predictive_analytics", "pattern_recognition", "business_insights", "performance_dashboard"],
    "conversational": ["greeting", "general_query", "goodbye"]
}

# Context Management Configuration
CONTEXT_CONFIG = {
    "max_history_length": 10,
    "session_timeout_minutes": 30,
    "preserve_cross_agent_context": True,
    "context_fields": [
        "business_type",
        "active_customer",
        "pending_transaction",
        "current_campaign",
        "inventory_alerts"
    ]
}

# Integration Configuration
INTEGRATION_CONFIG = {
    "mobile_money": {
        "mpesa": {"enabled": True, "callback_url": "/api/mpesa/callback"},
        "mtn_momo": {"enabled": True, "environment": "sandbox"},
        "supported_currencies": ["GHS", "UGX", "KES", "TZS", "RWF"]
    },
    "social_media": {
        "facebook": {"enabled": True, "api_version": "v18.0"},
        "instagram": {"enabled": True, "business_account": True},
        "whatsapp": {"enabled": True, "business_api": True}
    },
    "notifications": {
        "sms": {"provider": "africastalking", "enabled": True},
        "email": {"provider": "sendgrid", "enabled": True}
    }
}

# Autonomous Decision Rules
AUTONOMOUS_RULES = {
    "reorder_threshold": 0.2,  # Reorder when stock falls below 20%
    "payment_reminder_days": 3,  # Send payment reminders 3 days before due
    "campaign_optimization": True,  # Auto-optimize underperforming campaigns
    "customer_follow_up": True,  # Auto-follow up on customer interactions
    "expense_categorization": True,  # Auto-categorize expenses
    "fraud_detection": True  # Flag suspicious transactions
}