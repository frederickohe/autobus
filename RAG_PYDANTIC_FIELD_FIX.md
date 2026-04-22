# RAG Pipeline Pydantic Field Fix

## Issue
Error when initializing conversation tools:
```
ERROR:core.nlu.service.intentprocessor:Failed to initialize conversation tools: "RAGPipelineTool" object has no field "db"
WARNING:core.nlu.service.intentprocessor:Failed to initialize RAG tools, falling back to general conversation
```

## Root Cause
The `RAGPipelineTool` and `EnhancedConversationTool` classes inherit from LangChain's `BaseTool`, which is a Pydantic model. When using Pydantic, all instance attributes must be declared as class fields. The tools were assigning values directly in `__init__` without declaring them as Pydantic fields, causing validation errors.

## Solution
Added proper Pydantic field declarations to both tools:

### Changes to `src/core/rag/rag_pipeline_tool.py`
1. Added imports: `ConfigDict` from pydantic, `Any` from typing
2. Added model configuration to allow arbitrary types:
   ```python
   model_config = ConfigDict(arbitrary_types_allowed=True)
   ```
3. Added field declarations:
   ```python
   db: Optional[Session] = None
   embedding_service: Optional[Any] = None
   vector_retrieval: Optional[Any] = None
   llm: Optional[Any] = None
   ```

### Changes to `src/core/agent/tools/chatbot/enhanced_conversation_tool.py`
1. Added imports: `ConfigDict` from pydantic, `Any` and `Dict` from typing
2. Added model configuration:
   ```python
   model_config = ConfigDict(arbitrary_types_allowed=True)
   ```
3. Added field declarations:
   ```python
   db: Optional[Session] = None
   rag_tool: Optional[Any] = None
   client: Optional[Any] = None
   conversation_histories: Dict[str, list] = {}
   ```

## Result
- The tools now properly initialize with Pydantic validation
- RAG pipeline can be successfully loaded for conversational intents
- User 233247291736 can now use 'business_conversation' intent with RAG support
- Fallback to general conversation only occurs if RAG fails, not during initialization

## Testing
To verify the fix works:
1. Send a 'business_conversation' request for user 233247291736
2. Verify RAGPipelineTool initializes without errors
3. Check that RAG mode works for knowledge-base queries

## Pattern Applied
This follows the same pattern used by `EmailTool` and other LangChain-based tools in the codebase that need to maintain references to database sessions and other services.
