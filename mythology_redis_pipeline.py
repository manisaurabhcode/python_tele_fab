"""
Indian Mythology Content Pipeline with Redis Vector Database
Downloads, processes, and stores mythological texts for story generation
"""

import os
import re
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
import hashlib
from urllib.parse import urlparse

# Core dependencies
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.document_loaders import TextLoader
from redis import Redis
from redis.commands.search.field import VectorField, TextField, NumericField, TagField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
import numpy as np

# Configuration
@dataclass
class Config:
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    embedding_model: str = "text-embedding-3-small"
    vector_dim: int = 1536
    chunk_size: int = 1000
    chunk_overlap: int = 200
    index_name: str = "mythology_stories"
    data_dir: str = "./mythology_data"

# Book catalog
BOOK_CATALOG = [
    {
        "title": "Mahabharata by C. Rajagopalachari",
        "url": "https://www.gutenberg.org/cache/epub/14322/pg14322.txt",
        "category": "epic",
        "age_appropriate": True,
        "priority": 1
    },
    {
        "title": "Ramayana by C. Rajagopalachari",
        "url": "https://www.gutenberg.org/files/24869/24869-0.txt",
        "category": "epic",
        "age_appropriate": True,
        "priority": 1
    },
    {
        "title": "The Panchatantra by Arthur W. Ryder",
        "url": "https://www.gutenberg.org/files/25545/25545-0.txt",
        "category": "fables",
        "age_appropriate": True,
        "priority": 1
    },
    {
        "title": "Jataka Tales",
        "url": "https://www.gutenberg.org/files/51537/51537-0.txt",
        "category": "fables",
        "age_appropriate": True,
        "priority": 1
    },
    {
        "title": "Indian Fairy Tales by Joseph Jacobs",
        "url": "https://www.gutenberg.org/files/7128/7128-0.txt",
        "category": "folk_tales",
        "age_appropriate": True,
        "priority": 2
    },
    {
        "title": "Hitopadesha",
        "url": "https://www.gutenberg.org/files/46276/46276-0.txt",
        "category": "fables",
        "age_appropriate": True,
        "priority": 2
    }
]


class MythologyPipeline:
    """Main pipeline for processing mythology texts"""
    
    def __init__(self, config: Config):
        self.config = config
        self.redis_client = self._init_redis()
        self.embeddings = OpenAIEmbeddings(
            model=config.embedding_model,
            openai_api_key=config.openai_api_key
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Create data directory
        os.makedirs(config.data_dir, exist_ok=True)
        
    def _init_redis(self) -> Redis:
        """Initialize Redis connection"""
        return Redis(
            host=self.config.redis_host,
            port=self.config.redis_port,
            password=self.config.redis_password,
            decode_responses=False  # We'll handle encoding
        )
    
    def create_vector_index(self):
        """Create Redis vector search index"""
        try:
            # Drop existing index if it exists
            self.redis_client.ft(self.config.index_name).dropindex()
            print(f"Dropped existing index: {self.config.index_name}")
        except:
            pass
        
        # Define schema
        schema = (
            TextField("$.title", as_name="title"),
            TextField("$.text", as_name="text"),
            TextField("$.book", as_name="book"),
            TagField("$.category", as_name="category"),
            TagField("$.age_appropriate", as_name="age_appropriate"),
            NumericField("$.priority", as_name="priority"),
            NumericField("$.chunk_index", as_name="chunk_index"),
            VectorField(
                "$.embedding",
                "FLAT",
                {
                    "TYPE": "FLOAT32",
                    "DIM": self.config.vector_dim,
                    "DISTANCE_METRIC": "COSINE",
                },
                as_name="embedding"
            ),
        )
        
        # Create index
        definition = IndexDefinition(
            prefix=["story:"],
            index_type=IndexType.JSON
        )
        
        self.redis_client.ft(self.config.index_name).create_index(
            fields=schema,
            definition=definition
        )
        print(f"Created vector index: {self.config.index_name}")
    
    def download_book(self, book: Dict) -> Optional[str]:
        """Download book text from URL"""
        filename = self._get_filename(book["url"])
        filepath = os.path.join(self.config.data_dir, filename)
        
        # Check if already downloaded
        if os.path.exists(filepath):
            print(f"✓ Already downloaded: {book['title']}")
            return filepath
        
        try:
            print(f"Downloading: {book['title']}...")
            response = requests.get(book["url"], timeout=30)
            response.raise_for_status()
            
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            print(f"✓ Downloaded: {book['title']}")
            return filepath
            
        except Exception as e:
            print(f"✗ Error downloading {book['title']}: {e}")
            return None
    
    def _get_filename(self, url: str) -> str:
        """Generate filename from URL"""
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = hashlib.md5(url.encode()).hexdigest() + ".txt"
        return filename
    
    def clean_gutenberg_text(self, text: str) -> str:
        """Remove Project Gutenberg headers/footers"""
        # Remove header (before "START OF THE PROJECT")
        start_markers = [
            "*** START OF THE PROJECT GUTENBERG",
            "*** START OF THIS PROJECT GUTENBERG",
            "*END THE SMALL PRINT"
        ]
        
        for marker in start_markers:
            if marker in text:
                text = text.split(marker, 1)[1]
                break
        
        # Remove footer (after "END OF THE PROJECT")
        end_markers = [
            "*** END OF THE PROJECT GUTENBERG",
            "*** END OF THIS PROJECT GUTENBERG",
            "End of the Project Gutenberg"
        ]
        
        for marker in end_markers:
            if marker in text:
                text = text.split(marker, 1)[0]
                break
        
        # Clean up extra whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    
    def process_book(self, book: Dict, filepath: str) -> List[Dict]:
        """Process book into chunks with metadata"""
        print(f"Processing: {book['title']}...")
        
        # Load and clean text
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        
        text = self.clean_gutenberg_text(text)
        
        # Split into chunks
        chunks = self.text_splitter.split_text(text)
        print(f"  → Split into {len(chunks)} chunks")
        
        # Create documents with metadata
        documents = []
        for i, chunk in enumerate(chunks):
            doc = {
                "text": chunk,
                "book": book["title"],
                "category": book["category"],
                "age_appropriate": str(book["age_appropriate"]),
                "priority": book["priority"],
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
            documents.append(doc)
        
        return documents
    
    def generate_embeddings(self, documents: List[Dict], batch_size: int = 100):
        """Generate embeddings for documents"""
        print(f"Generating embeddings for {len(documents)} chunks...")
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            texts = [doc["text"] for doc in batch]
            
            # Generate embeddings
            embeddings = self.embeddings.embed_documents(texts)
            
            # Add to documents
            for doc, embedding in zip(batch, embeddings):
                doc["embedding"] = embedding
            
            print(f"  → Processed {min(i + batch_size, len(documents))}/{len(documents)}")
        
        return documents
    
    def store_in_redis(self, documents: List[Dict]):
        """Store documents with embeddings in Redis"""
        print(f"Storing {len(documents)} documents in Redis...")
        
        for i, doc in enumerate(documents):
            # Create unique key
            doc_id = hashlib.md5(
                f"{doc['book']}_{doc['chunk_index']}".encode()
            ).hexdigest()
            
            key = f"story:{doc_id}"
            
            # Convert embedding to bytes
            embedding_bytes = np.array(doc["embedding"], dtype=np.float32).tobytes()
            
            # Prepare document for Redis (without embedding in text form)
            redis_doc = {
                "title": f"{doc['book']} - Part {doc['chunk_index'] + 1}",
                "text": doc["text"],
                "book": doc["book"],
                "category": doc["category"],
                "age_appropriate": doc["age_appropriate"],
                "priority": doc["priority"],
                "chunk_index": doc["chunk_index"],
                "embedding": embedding_bytes
            }
            
            # Store as JSON
            self.redis_client.json().set(key, "$", redis_doc)
            
            if (i + 1) % 100 == 0:
                print(f"  → Stored {i + 1}/{len(documents)}")
        
        print(f"✓ Stored all documents in Redis")
    
    def search_similar_stories(
        self, 
        query: str, 
        top_k: int = 5,
        category: Optional[str] = None
    ) -> List[Dict]:
        """Search for similar stories using vector similarity"""
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        query_bytes = np.array(query_embedding, dtype=np.float32).tobytes()
        
        # Build query
        base_query = f"*=>[KNN {top_k} @embedding $vector AS score]"
        
        if category:
            base_query = f"@category:{{{category}}} " + base_query
        
        query_obj = (
            Query(base_query)
            .return_fields("title", "text", "book", "category", "score")
            .sort_by("score")
            .dialect(2)
        )
        
        # Execute search
        results = self.redis_client.ft(self.config.index_name).search(
            query_obj,
            query_params={"vector": query_bytes}
        )
        
        # Format results
        stories = []
        for doc in results.docs:
            stories.append({
                "title": doc.title,
                "text": doc.text,
                "book": doc.book,
                "category": doc.category,
                "score": float(doc.score)
            })
        
        return stories
    
    def run_pipeline(self, books: Optional[List[Dict]] = None):
        """Run complete pipeline"""
        if books is None:
            books = BOOK_CATALOG
        
        print("=" * 60)
        print("INDIAN MYTHOLOGY CONTENT PIPELINE")
        print("=" * 60)
        
        # Step 1: Create vector index
        print("\n[1/5] Creating Redis vector index...")
        self.create_vector_index()
        
        # Step 2: Download books
        print("\n[2/5] Downloading books...")
        downloaded_books = []
        for book in books:
            filepath = self.download_book(book)
            if filepath:
                downloaded_books.append((book, filepath))
        
        print(f"\n✓ Downloaded {len(downloaded_books)}/{len(books)} books")
        
        # Step 3: Process books
        print("\n[3/5] Processing books into chunks...")
        all_documents = []
        for book, filepath in downloaded_books:
            documents = self.process_book(book, filepath)
            all_documents.extend(documents)
        
        print(f"\n✓ Total chunks created: {len(all_documents)}")
        
        # Step 4: Generate embeddings
        print("\n[4/5] Generating embeddings...")
        all_documents = self.generate_embeddings(all_documents)
        
        # Step 5: Store in Redis
        print("\n[5/5] Storing in Redis...")
        self.store_in_redis(all_documents)
        
        print("\n" + "=" * 60)
        print("✓ PIPELINE COMPLETE!")
        print("=" * 60)
        print(f"Total documents stored: {len(all_documents)}")
        print(f"Redis index: {self.config.index_name}")
        print(f"Data directory: {self.config.data_dir}")
    
    def get_stats(self) -> Dict:
        """Get statistics about stored data"""
        info = self.redis_client.ft(self.config.index_name).info()
        
        return {
            "total_documents": info.get("num_docs", 0),
            "index_name": self.config.index_name,
            "vector_dimension": self.config.vector_dim
        }


# Example usage and testing
if __name__ == "__main__":
    # Initialize configuration
    config = Config(
        redis_host="localhost",
        redis_port=6379,
        openai_api_key=os.getenv("OPENAI_API_KEY"),  # Set this in environment
    )
    
    # Create pipeline
    pipeline = MythologyPipeline(config)
    
    # Run pipeline with priority books first
    priority_books = [b for b in BOOK_CATALOG if b["priority"] == 1]
    pipeline.run_pipeline(priority_books)
    
    # Show stats
    print("\n" + "=" * 60)
    print("DATABASE STATISTICS")
    print("=" * 60)
    stats = pipeline.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Test search
    print("\n" + "=" * 60)
    print("TESTING SEARCH")
    print("=" * 60)
    
    test_queries = [
        "stories about Krishna as a child",
        "animal fables with moral lessons",
        "tales of bravery and courage"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = pipeline.search_similar_stories(query, top_k=3)
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n  {i}. {result['title']}")
            print(f"     Book: {result['book']}")
            print(f"     Score: {result['score']:.4f}")
            print(f"     Preview: {result['text'][:150]}...")
