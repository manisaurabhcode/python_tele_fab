# Indian Mythology Content Pipeline - Setup Guide

## Installation

### 1. Install Redis Stack

**Option A: Docker (Recommended)**
```bash
docker run -d --name redis-stack -p 6379:6379 -p 8001:8001 redis/redis-stack:latest
```

**Option B: Direct Installation**
```bash
# macOS
brew tap redis-stack/redis-stack
brew install redis-stack

# Ubuntu/Debian
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt-get update
sudo apt-get install redis-stack-server
```

### 2. Install Python Dependencies

**requirements.txt:**
```
langchain==0.1.0
langchain-openai==0.0.2
openai==1.7.0
redis==5.0.1
numpy==1.24.3
requests==2.31.0
python-dotenv==1.0.0

# Optional but recommended
tiktoken==0.5.2
tenacity==8.2.3
```

Install:
```bash
pip install -r requirements.txt
```

### 3. Environment Setup

Create `.env` file:
```bash
OPENAI_API_KEY=your_openai_api_key_here
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

### 4. Verify Redis Connection

```python
from redis import Redis

client = Redis(host='localhost', port=6379, decode_responses=True)
client.ping()  # Should return True
```

## Usage

### Basic Pipeline Execution

```python
from mythology_pipeline import MythologyPipeline, Config
import os

# Initialize
config = Config(openai_api_key=os.getenv("OPENAI_API_KEY"))
pipeline = MythologyPipeline(config)

# Run pipeline
pipeline.run_pipeline()

# Search for stories
results = pipeline.search_similar_stories(
    "stories about Lord Hanuman",
    top_k=5
)

for result in results:
    print(f"Title: {result['title']}")
    print(f"Score: {result['score']}")
    print(f"Text: {result['text'][:200]}...\n")
```

### Advanced Usage

**Filter by category:**
```python
# Only search fables
results = pipeline.search_similar_stories(
    "moral lessons for children",
    top_k=10,
    category="fables"
)
```

**Process specific books:**
```python
custom_books = [
    {
        "title": "My Custom Book",
        "url": "https://example.com/book.txt",
        "category": "custom",
        "age_appropriate": True,
        "priority": 1
    }
]

pipeline.run_pipeline(custom_books)
```

**Get database statistics:**
```python
stats = pipeline.get_stats()
print(f"Total documents: {stats['total_documents']}")
```

## Cost Estimation

### For Initial Setup (6 priority books):
- **Text Volume**: ~2-3 million characters
- **Chunks**: ~2,000-3,000 chunks
- **Embedding Cost**: 
  - Model: text-embedding-3-small
  - Cost: $0.02 per 1M tokens
  - **Total: ~$0.10-0.15** for initial indexing

### For Queries:
- Each search query embedding: ~$0.00002
- 1,000 searches: ~$0.02

## Performance

- **Indexing Speed**: ~100-200 chunks/minute
- **Search Speed**: <100ms for top-k=10
- **Storage**: ~2MB per 1,000 chunks (with embeddings)

## Redis Vector Search Commands

### Via Redis CLI

```bash
# Connect to Redis
redis-cli

# Get index info
FT.INFO mythology_stories

# Count documents
FT.SEARCH mythology_stories "*" LIMIT 0 0

# Search by category
FT.SEARCH mythology_stories "@category:{fables}" LIMIT 0 10
```

### Via RedisInsight (GUI)

Access at: http://localhost:8001

- Browse keys with `story:` prefix
- Visualize vector index
- Run queries with visual interface

## Troubleshooting

### "Index already exists" error
```python
pipeline.redis_client.ft(config.index_name).dropindex()
pipeline.create_vector_index()
```

### Connection refused
```bash
# Check if Redis is running
redis-cli ping

# Start Redis
docker start redis-stack
# or
redis-stack-server
```

### Out of memory
```bash
# Increase Redis memory
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Rate limiting from OpenAI
- Reduce batch_size in generate_embeddings()
- Add delays between API calls
- Use exponential backoff

## Next Steps

1. **Expand Book Catalog**: Add all 20 books from the list
2. **Character Extraction**: Build knowledge graph of characters
3. **Story Generation**: Use LLMs to create child-friendly adaptations
4. **Quality Filters**: Add age-appropriateness scoring
5. **Caching**: Cache frequently accessed stories

## Project Structure

```
mythology_project/
├── mythology_pipeline.py      # Main pipeline script
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables
├── mythology_data/            # Downloaded books
│   ├── pg14322.txt           # Mahabharata
│   ├── pg24869.txt           # Ramayana
│   └── ...
└── notebooks/                 # Jupyter notebooks for testing
    └── test_pipeline.ipynb
```

## Monitoring

### Check indexing progress
```python
import time

def monitor_indexing(pipeline, interval=10):
    while True:
        stats = pipeline.get_stats()
        print(f"Documents indexed: {stats['total_documents']}")
        time.sleep(interval)
```

### Log search queries
```python
import logging

logging.basicConfig(
    filename='search_queries.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# In search function
logging.info(f"Query: {query}, Results: {len(results)}")
```
