from smolagents import Tool
from langchain_community.retrievers import BM25Retriever
import pickle
import os
import logging

logger = logging.getLogger(__name__)


class RetrieverTool(Tool):
    """Tool for retrieving user-uploaded documents using semantic/lexical search.
    
    Uses BM25 algorithm to retrieve the parts of user documents that are most
    relevant to a query.
    """
    
    name = "retriever"
    description = "Search through your uploaded documents to find relevant information for answering questions."
    inputs = {
        "query": {
            "type": "string",
            "description": "The query to search for in your documents. Be specific and use key terms from what you're looking for.",
        }
    }
    output_type = "string"

    def __init__(self, user_id: str = None, docs_path: str = None, docs_dir: str = "agent_outputs/docs_processed", **kwargs):
        """Initialize the retriever tool.
        
        Args:
            user_id: The user ID whose documents to retrieve from
            docs_path: Optional explicit path to docs pickle file (overrides user_id-based lookup)
            docs_dir: Directory containing user docs pickle files
        """
        super().__init__(**kwargs)
        self.user_id = user_id
        self.docs_dir = docs_dir
        self.docs_path = docs_path
        self.retriever = None
        self.docs = None
        
        # Load documents if path is provided
        if docs_path and os.path.exists(docs_path):
            self._load_documents(docs_path)
        elif user_id:
            # Try to load from user-specific path
            user_docs_path = os.path.join(docs_dir, f"{user_id}_docs_processed.pkl")
            if os.path.exists(user_docs_path):
                self._load_documents(user_docs_path)
            else:
                logger.warning(f"No documents found for user {user_id} at {user_docs_path}")
    
    def _load_documents(self, docs_path: str):
        """Load documents from pickle file.
        
        Args:
            docs_path: Path to the docs_processed.pkl file
        """
        try:
            with open(docs_path, "rb") as f:
                self.docs = pickle.load(f)
            
            if self.docs:
                self.retriever = BM25Retriever.from_documents(self.docs, k=10)
                logger.info(f"Loaded {len(self.docs)} documents from {docs_path}")
            else:
                logger.warning(f"No documents found in {docs_path}")
        except Exception as e:
            logger.error(f"Error loading documents from {docs_path}: {str(e)}")
            self.docs = None
            self.retriever = None
    
    def set_user_docs(self, user_id: str):
        """Change the active user's documents.
        
        Args:
            user_id: The new user ID to load documents for
        """
        self.user_id = user_id
        user_docs_path = os.path.join(self.docs_dir, f"{user_id}_docs_processed.pkl")
        
        if os.path.exists(user_docs_path):
            self._load_documents(user_docs_path)
        else:
            logger.warning(f"No documents found for user {user_id}")
            self.docs = None
            self.retriever = None

    def forward(self, query: str) -> str:
        """Execute the retrieval based on the provided query.
        
        Args:
            query: The search query
            
        Returns:
            str: Formatted retrieved documents, or error message if no documents available
        """
        if not self.retriever:
            return "Error: No documents available for retrieval. Please upload documents first."
        
        assert isinstance(query, str), "Your search query must be a string"

        try:
            # Retrieve relevant documents
            docs = self.retriever.invoke(query)

            if not docs:
                return "No relevant documents found for your query."

            # Format the retrieved documents for readability
            result = "Retrieved documents matching your query:\n"
            for i, doc in enumerate(docs, 1):
                result += f"\n{'='*50}\nDocument {i}:\n{'='*50}\n"
                result += doc.page_content
                
                # Include metadata if available
                if doc.metadata:
                    result += "\n\nMetadata:\n"
                    for key, value in doc.metadata.items():
                        result += f"  {key}: {value}\n"
            
            return result
        except Exception as e:
            logger.error(f"Error during retrieval: {str(e)}")
            return f"Error during retrieval: {str(e)}"
