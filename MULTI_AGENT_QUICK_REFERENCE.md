# Autobus Multi-Agent System - Quick Reference

## System Overview

Autobus is now a **multi-agent system** with a manager agent coordinating 9 specialized sub-agents.

## Quick Start

```python
from src.core.agent.agent import AutoBus
from sqlalchemy.orm import Session

# Initialize
db_session = Session()
autobus = AutoBus(db_session=db_session)

# Use it
response = autobus.process_user_message(
    userid="user123",
    message="Create a product called 'Widget' with price $9.99",
    agent_name="products"
)
```

## Sub-Agent Reference

| Agent | Purpose | Key Tools | Use When |
|-------|---------|-----------|----------|
| ConfigAgent | Manage agent configurations | Create, Get, Update, Delete, List | Managing AI agent setups |
| ConversationAgent | Handle conversations | Conversation flow | Multi-turn dialogue |
| EmailAgent | Send emails | Email sending | Sending notifications/messages |
| ImageGenerationAgent | Generate images | Text-to-image | Creating visual content |
| VideoGenerationAgent | Generate videos | Text-to-video | Creating video content |
| ProductsAgent | Manage products/inventory | 8 product tools | Product CRUD + inventory |
| ChatbotAgent | Answer questions w/ RAG | Retriever + Document mgmt | Knowledge-based Q&A |
| AITrainingAgent | Train/fine-tune models | (Extensible) | Model optimization |
| WebSearchAgent | Search & browse web | WebSearch + VisitWebpage | Finding info online |

## Architecture

```
User Message
    ↓
AutoBus Manager (CodeAgent)
    ↓
Understands intent & routes to appropriate sub-agent(s)
    ↓
Sub-Agent processes with specialized tools
    ↓
FinalAnswerTool formulates response
    ↓
Return to user
```

## File Structure

```
src/core/agent/
├── agent.py              # Main AutoBus manager
├── agents/               # Sub-agents package
│   ├── __init__.py
│   ├── config_agent.py
│   ├── conversation_agent.py
│   ├── email_agent.py
│   ├── image_generation_agent.py
│   ├── video_generation_agent.py
│   ├── products_agent.py
│   ├── chatbot_agent.py
│   ├── ai_training_agent.py
│   └── web_search_agent.py
├── tools/                # All tool implementations
│   ├── agent_config/
│   ├── conversation/
│   ├── email/
│   ├── product/
│   ├── rag/
│   ├── answer/
│   └── ...
└── ...
```

## Key Changes from Old System

### Before (Monolithic)
```python
CodeAgent(
    tools=[
        FinalAnswerTool,
        EmailTool,
        ProductTool,
        ImageGenerationTool,
        # ... 20+ tools in one agent
    ]
)
```

### After (Multi-Agent)
```python
CodeAgent(
    tools=[FinalAnswerTool],  # Only answer tool
    managed_agents=[
        ConfigAgent,
        ConversationAgent,
        EmailAgent,
        ImageGenerationAgent,
        # ... 9 specialized agents
    ]
)
```

## Common Operations

### Product Management
```python
response = autobus.process_user_message(
    userid="user123",
    message="What products are in stock?",
    agent_name="products"
)
```

### Knowledge Base Q&A
```python
response = autobus.process_user_message(
    userid="user123",
    message="What is mentioned in the company handbook?",
    agent_name="chatbot"
)
```

### Image Generation
```python
response = autobus.process_user_message(
    userid="user123",
    message="Generate an image of a futuristic city",
    agent_name="image_generation"
)
```

### Web Search
```python
response = autobus.process_user_message(
    userid="user123",
    message="Find recent information about AI trends",
    agent_name="web_search"
)
```

## Configuration

### In AutoBus.__init__()
- Model: `Qwen/Qwen2.5-Coder-32B-Instruct`
- Max steps: 6 (manager)
- Verbosity: 1
- Conversation history: Last 20 messages

### Per Sub-Agent
- Max steps: 5-10 (domain dependent)
- Agent type: ToolCallingAgent
- Conversation tracking: Automatic

## Adding a New Sub-Agent

1. **Create file**: `src/core/agent/agents/new_agent.py`
   ```python
   from smolagents import ToolCallingAgent, InferenceClientModel
   
   class NewAgent:
       def __init__(self, model, db_session):
           self.agent = ToolCallingAgent(
               tools=[...],
               model=model,
               max_steps=5,
               name="new_agent",
               description="Your agent description"
           )
       
       def process(self, message, user_id=None):
           # Processing logic
           pass
   ```

2. **Add to `__init__.py`**: Import and export the new agent

3. **Update `agent.py`**:
   - Import the new agent
   - Initialize in AutoBus.__init__()
   - Add to managed_agents list

## Troubleshooting

### Agent doesn't respond
- Check database session is valid
- Verify specific sub-agent is available
- Check tool dependencies are installed

### Tool not found
- Ensure tool is in sub-agent's tools list
- Verify tool is imported correctly
- Check tool initialization parameters

### Slow responses
- Reduce max_steps in sub-agent
- Check if multiple agents are being queried
- Monitor token usage

## Performance Notes

- **Routing overhead**: Minimal (manager plans once)
- **Parallel execution**: Currently sequential, can be enhanced
- **Token efficiency**: Optimized per domain
- **Conversation context**: Last 20 messages (configurable)

## Documentation

Full detailed documentation: See `MULTI_AGENT_ARCHITECTURE.md`

## Support

For issues or questions:
1. Check agent logs (verbosity_level=1)
2. Verify tool configurations
3. Test sub-agent independently
4. Review MULTI_AGENT_ARCHITECTURE.md
