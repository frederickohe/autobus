# Autobus Multi-Agent System Architecture

## Overview

The Autobus system has been refactored from a single monolithic agent into a sophisticated multi-agent architecture following the pattern recommended by HuggingFace. This architecture improves modularity, maintainability, and scalability.

## Architecture Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                   AUTOBUS MANAGER AGENT                      │
│              (CodeAgent - Planning & Routing)               │
│                                                              │
│  Direct Tools:                                               │
│  - FinalAnswerTool (answers user questions)                 │
│                                                              │
│  Managed Sub-Agents (via managed_agents parameter):         │
│  - ConfigAgent                                              │
│  - ConversationAgent                                        │
│  - EmailAgent                                               │
│  - ImageGenerationAgent                                     │
│  - VideoGenerationAgent                                     │
│  - ProductsAgent                                            │
│  - ChatbotAgent (RAG)                                       │
│  - AITrainingAgent                                          │
│  - WebSearchAgent                                           │
└─────────────────────────────────────────────────────────────┘
```

## Component Description

### Manager Agent (AutoBus)
- **Type**: `CodeAgent`
- **Role**: Central coordinator and planner
- **Direct Tools**: `FinalAnswerTool` only
- **Managed Agents**: All 9 sub-agents
- **Responsibility**: 
  - Understands user intent
  - Routes requests to appropriate sub-agents
  - Coordinates complex multi-step tasks
  - Provides final responses

## Sub-Agents

### 1. ConfigAgent (ToolCallingAgent)
**Purpose**: Agent configuration management

**Tools**:
- `CreateAgentTool` - Create new agent configurations
- `GetAgentTool` - Retrieve agent configurations
- `UpdateAgentTool` - Update existing configurations
- `DeleteAgentTool` - Remove agent configurations
- `ListAgentsTool` - List all agent configurations

**Use Cases**:
- Creating custom agent configurations
- Updating agent parameters
- Managing agent lifecycle

---

### 2. ConversationAgent (ToolCallingAgent)
**Purpose**: Handle multi-turn conversations

**Tools**:
- `ConversationTool` - Manage conversation flow

**Use Cases**:
- Multi-turn dialogue
- Context-aware responses
- Conversation history management

---

### 3. EmailAgent (ToolCallingAgent)
**Purpose**: Email composition and delivery

**Tools**:
- `EmailTool` - Send emails

**Use Cases**:
- Send notifications
- Compose professional emails
- Format email content

---

### 4. ImageGenerationAgent (ToolCallingAgent)
**Purpose**: Generate images from text descriptions

**Tools**:
- `text-to-image` (Hugging Face Hub)

**Use Cases**:
- Generate illustrations
- Create visual content
- Design asset generation

---

### 5. VideoGenerationAgent (ToolCallingAgent)
**Purpose**: Generate videos from text descriptions

**Tools**:
- `text-to-video` (Hugging Face Hub)

**Use Cases**:
- Create video content
- Generate animated sequences
- Multimedia asset generation

---

### 6. ProductsAgent (ToolCallingAgent)
**Purpose**: Product and inventory management

**Tools**:
- `CreateProductTool` - Add new products
- `GetProductTool` - Retrieve product details
- `UpdateProductTool` - Update product information
- `FetchProductByNameTool` - Search products by name
- `UserSelectProductTool` - Handle user product selection
- `GetProductInventoryTool` - Check inventory levels
- `IncrementInventoryTool` - Increase stock
- `DecrementInventoryTool` - Decrease stock

**Use Cases**:
- Product catalog management
- Inventory tracking
- Stock optimization
- User product selection

---

### 7. ChatbotAgent (ToolCallingAgent)
**Purpose**: RAG (Retrieval-Augmented Generation) based chatbot

**Tools**:
- `RetrieverTool` - Retrieve relevant documents
- `UploadDocumentTool` - Upload knowledge documents
- `GetDocumentsTool` - List available documents
- `DeleteDocumentTool` - Remove documents

**Use Cases**:
- Question answering with knowledge base
- Document-based assistance
- Knowledge management
- Context-aware responses

---

### 8. AITrainingAgent (ToolCallingAgent)
**Purpose**: AI model training and optimization

**Tools**: (Extensible for future training tools)

**Use Cases**:
- Model fine-tuning
- Training job management
- AI model optimization

---

### 9. WebSearchAgent (ToolCallingAgent)
**Purpose**: Web search and content retrieval

**Tools**:
- `WebSearchTool` - Search the web
- `visit_webpage` - Retrieve and convert webpage content to markdown

**Use Cases**:
- Real-time web search
- Information gathering
- Web content analysis
- External knowledge integration

---

## How Requests Flow

### Example Flow 1: Generate an Image
```
User: "Create an image of a sunset"
         ↓
Manager Agent (Understanding intent)
         ↓
Identifies: Image generation task
         ↓
Delegates to: ImageGenerationAgent
         ↓
ImageGenerationAgent processes with text-to-image tool
         ↓
Returns: Generated image URL/path
         ↓
Manager returns final answer
```

### Example Flow 2: Complex Query
```
User: "What products are available? Show me their inventories and search for similar items online"
         ↓
Manager Agent (Planning multi-step task)
         ↓
Step 1: ProductsAgent → Get products and inventory
Step 2: ProductsAgent → Verify stock levels
Step 3: WebSearchAgent → Search for similar items
         ↓
Consolidate results
         ↓
FinalAnswerTool provides response
```

## Key Design Benefits

1. **Modularity**: Each domain logic is isolated in its own agent
2. **Scalability**: Easy to add new sub-agents without modifying core manager
3. **Maintainability**: Easier to debug and update specific functionalities
4. **Specialization**: Each agent optimized for its specific domain
5. **Reusability**: Sub-agents can be used independently if needed
6. **Clear Separation of Concerns**: Each agent has specific responsibilities

## Implementation Details

### Manager Agent Configuration
```python
self.agent = CodeAgent(
    model=self.model,
    tools=[self.final_answer],  # Direct tools only
    managed_agents=[all sub-agents],  # Via managed_agents parameter
    max_steps=6,
    verbosity_level=1,
    planning_interval=None,
    name="autobus_manager",
    description="Autobus Manager Agent - Coordinates specialized sub-agents"
)
```

### Sub-Agent Template
```python
agent = ToolCallingAgent(
    tools=[specific_tools],
    model=model,
    max_steps=appropriate_for_domain,
    name="specific_agent_name",
    description="Clear description of purpose"
)
```

## Usage

### Initialize Autobus
```python
from src.core.agent.agent import AutoBus
from sqlalchemy.orm import Session

db_session = Session()  # Your database session
autobus = AutoBus(db_session=db_session)
```

### Process User Message
```python
response = autobus.process_user_message(
    userid="user123",
    message="What products are available?",
    agent_name="products"
)
```

## Future Extensions

### Adding New Sub-Agents
1. Create new file: `src/core/agent/agents/new_agent.py`
2. Create class extending `ToolCallingAgent`
3. Add import to `src/core/agent/agents/__init__.py`
4. Add instance initialization in AutoBus.__init__()
5. Add agent to managed_agents list

### Adding New Tools to Existing Agents
1. Add tool to the sub-agent's tools list
2. Update sub-agent's description if functionality changes

## Performance Considerations

- **Context Switching**: Manager agent plans and routes (overhead minimal)
- **Parallel Execution**: While sub-agents execute sequentially in current implementation, smolagents supports parallel tool execution where applicable
- **Token Usage**: Slightly higher due to manager agent's planning, but offset by specialized sub-agents
- **Max Steps**: Configured per agent based on domain complexity

## Error Handling

Each sub-agent includes comprehensive error handling:
- Try-catch blocks around processing
- Logging of all errors with context
- Graceful fallback responses
- User-friendly error messages

## Conversation Management

The system maintains:
- **Conversation History**: Per user for context
- **Media Storage**: For generated images/videos
- **State Tracking**: Via ConversationManager

## Testing Recommendations

1. Test each sub-agent independently
2. Test manager agent routing logic
3. Test multi-step request scenarios
4. Test error scenarios and edge cases
5. Test conversation history maintenance

## References

- HuggingFace smolagents documentation
- CodeAgent and ToolCallingAgent APIs
- Sub-agent specialized tool documentation
