from smolagents import Tool
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class RetrieverTool(Tool):
    """Tool for retrieving user-uploaded documents using semantic/lexical search.
    
    Uses BM25 algorithm to retrieve the parts of user documents that are most
    relevant to a query. Documents are fetched from the AI training files table.
    """
    
    name = "retriever"
    description = "Search through your uploaded documents to find relevant information for answering questions."
    inputs = {
        "query": {
            "type": "string",
            "description": "The query to search for in your documents. Be specific and use key terms from what you're looking for.",
        },
        "user_id": {
            "type": "string",
            "description": "The user ID whose documents to retrieve.",
        }
    }
    output_type = "string"

    def __init__(self, db_session: Session, **kwargs):
        """Initialize the retriever tool.
        
        Args:
            db_session: SQLAlchemy database session for database operations.
        """
        super().__init__(**kwargs)
        self.db_session = db_session
        self.user_id = None
        self.retriever = None
        self.docs = None
    
    def _load_user_documents_from_db(self, user_id: str):
        """Load document metadata from the AI training files table.
        
        Args:
            user_id: The user ID whose documents to load
        """
        try:
            from core.cloudstorage.model.aitrainingfilemodel import AITrainingFileModel
            
            # Query all documents for the user
            training_files = self.db_session.query(AITrainingFileModel).filter(
                AITrainingFileModel.user_id == user_id
            ).all()
            
            if not training_files:
                logger.warning(f"No training files found for user {user_id}")
                self.docs = None
                self.retriever = None
                return
            
            # Convert database records to Document objects for BM25
            self.docs = []
            for file_record in training_files:
                # Use extracted content if available, otherwise use metadata
                if file_record.content and file_record.content.strip():
                    page_content = file_record.content
                else:
                    # Fallback to metadata if content not extracted yet
                    page_content = f"File: {file_record.file_name}\nURL: {file_record.file_url}\nType: {file_record.file_type}"
                
                doc = Document(
                    page_content=page_content,
                    metadata={
                        "file_name": file_record.file_name,
                        "file_url": file_record.file_url,
                        "subfolder": file_record.subfolder,
                        "file_type": file_record.file_type,
                        "file_size": file_record.file_size,
                        "upload_timestamp": file_record.upload_timestamp.isoformat() if file_record.upload_timestamp else None,
                        "content_extracted": getattr(file_record, 'content_extracted', 'unknown'),
                    }
                )
                self.docs.append(doc)
            
            # Initialize BM25 retriever
            if self.docs:
                self.retriever = BM25Retriever.from_documents(self.docs, k=10)
                logger.info(f"Loaded {len(self.docs)} documents for user {user_id} from database")
            else:
                logger.warning(f"No documents created for user {user_id}")
                self.retriever = None
                
        except Exception as e:
            logger.error(f"Error loading documents from database for user {user_id}: {str(e)}")
            self.docs = None
            self.retriever = None
    
    def set_user_docs(self, user_id: str):
        """Change the active user's documents.
        
        Args:
            user_id: The new user ID to load documents for
        """
        self.user_id = user_id
        self._load_user_documents_from_db(user_id)

    def forward(self, query: str, user_id: str) -> str:
        """Execute the retrieval based on the provided query and user ID.
        
        Args:
            query: The search query
            user_id: The user ID whose documents to search
            
        Returns:
            str: Formatted retrieved documents, or error message if no documents available
        """
        # Load documents for the user if not already loaded or if user changed
        if self.user_id != user_id:
            self.set_user_docs(user_id)
        
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
            logger.error(f"Error during retrieval for user {user_id}: {str(e)}")
            return f"Error during retrieval: {str(e)}"