"""Central registry of agent required parameters.

Each agent maps to a list of required parameter keys that must be present
in the user's agent config stored in `User.agents`.
"""

AGENT_REQUIRED_PARAMS = {
    "Business Knowledge Agent": ["web_url", "database_url", "db_username", "db_password", "documentation_url"],
    "Email Agent": ["from_email"],
    "Financial Assistant Agent": ["payment_source", "account_id"],
    "Orders Management Agent": ["database_url", "db_username", "db_password", "orders_endpoint"],
    "Sales Management Agent": ["database_url", "db_username", "db_password", "crm_api_key", "crm_base_url"],
    "Digital Marketing Agent": ["meta_api","facebook_token", "whatsapp_token", "instagram_token"],
    "Data Handling Agent": ["storage_api_key", "storage_bucket"],
    "Inventory Agent": ["database_url", "db_username", "db_password",]
}
