import datasets
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pickle  # To save processed docs

def prepare_knowledge_base():
    # Load and process documents
    knowledge_base = datasets.load_dataset("m-ric/huggingface_doc", split="train")
    knowledge_base = knowledge_base.filter(lambda row: row["source"].startswith("huggingface/transformers"))
    
    source_docs = [
        Document(page_content=doc["text"], metadata={"source": doc["source"].split("/")[1]})
        for doc in knowledge_base
    ]
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        add_start_index=True,
        strip_whitespace=True,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    docs_processed = text_splitter.split_documents(source_docs)
    
    # Save for later use
    with open("docs_processed.pkl", "wb") as f:
        pickle.dump(docs_processed, f)
    
    print(f"Knowledge base prepared with {len(docs_processed)} document chunks")
    return docs_processed

if __name__ == "__main__":
    prepare_knowledge_base()