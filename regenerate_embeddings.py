"""
Regenerate Embeddings for Existing Documents

This script finds all documents in the database without embeddings 
and generates embeddings for them.

Usage:
    python regenerate_embeddings.py
"""

import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import RAG services
from core.rag.embedding_service import EmbeddingService
from core.cloudstorage.model.aitrainingfilemodel import AITrainingFileModel

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

if not DATABASE_URL:
    logger.error("❌ SQLALCHEMY_DATABASE_URL is not set")
    exit(1)

logger.info(f"🔗 Connecting to database...")

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # Test connection
    db.execute(text("SELECT 1"))
    logger.info("✅ Database connection successful!\n")
    
except Exception as e:
    logger.error(f"❌ Database connection failed: {str(e)}")
    exit(1)


def regenerate_embeddings():
    """Find documents without embeddings and generate them."""
    
    try:
        # Find all documents without embeddings
        docs_without_embeddings = db.query(AITrainingFileModel).filter(
            AITrainingFileModel.embedding == None
        ).all()
        
        if not docs_without_embeddings:
            logger.info("✅ All documents already have embeddings!")
            return
        
        logger.info(f"📄 Found {len(docs_without_embeddings)} documents without embeddings\n")
        
        # Initialize embedding service
        try:
            embedding_service = EmbeddingService()
            logger.info("✅ EmbeddingService initialized\n")
        except Exception as e:
            logger.error(f"❌ Failed to initialize EmbeddingService: {str(e)}")
            logger.error("   Make sure OPENAI_API_KEY is set")
            return
        
        # Regenerate embeddings
        success_count = 0
        failed_count = 0
        
        for i, doc in enumerate(docs_without_embeddings, 1):
            try:
                logger.info(f"[{i}/{len(docs_without_embeddings)}] Processing: {doc.file_name}")
                logger.info(f"         ID: {doc.id}, User: {doc.user_id}")
                
                # Generate embedding
                content_to_embed = doc.content if doc.content else doc.file_name
                embedding = embedding_service.generate_embedding(content_to_embed)
                
                # Store embedding
                doc.embedding = embedding
                db.commit()
                
                logger.info(f"         ✅ Embedding generated (dimensions: {len(embedding)})\n")
                success_count += 1
                
            except Exception as e:
                logger.error(f"         ❌ Failed: {str(e)}\n")
                db.rollback()
                failed_count += 1
        
        # Summary
        logger.info("=" * 70)
        logger.info("📊 REGENERATION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"✅ Successfully regenerated: {success_count}")
        logger.info(f"❌ Failed:                  {failed_count}")
        logger.info(f"📊 Total processed:        {success_count + failed_count}")
        logger.info("=" * 70)
        
        if success_count > 0:
            logger.info("\n🎉 Documents are now ready for RAG search!")
        
    except Exception as e:
        logger.error(f"❌ Error during regeneration: {str(e)}", exc_info=True)
    
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("EMBEDDING REGENERATION TOOL")
    logger.info("=" * 70 + "\n")
    
    regenerate_embeddings()
