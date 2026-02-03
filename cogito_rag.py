"""
Cogito Requiem - RAG System with ChromaDB
==========================================
Implements proper Retrieval-Augmented Generation as specified in the proposal:
"Create a RAG knowledge base from software engineering best practices"
"Agents must use the RAG (via Tool Invocation) to find evidence"

Uses ChromaDB for vector storage (as specified in PDF Table - Technology Stack)
"""

import os
from crewai.tools import tool
from pypdf import PdfReader
import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime
import uuid

# --- CONFIGURATION ---
DOCS_DIR = "knowledge_docs"
CHROMA_PERSIST_DIR = "./cogito_chromadb"

# Global ChromaDB client and collection
chroma_client = None
knowledge_collection = None

# Evidence tracking for database logging
evidence_log = []


def init_rag_system():
    """
    Initialize the RAG system with ChromaDB vector database.
    This creates embeddings for semantic search (not just keyword matching).
    """
    global chroma_client, knowledge_collection
    
    print("\n" + "="*50)
    print("[RAG System]: Initializing ChromaDB Vector Store...")
    print("="*50)
    
    # Initialize ChromaDB client (in-memory for simplicity)
    chroma_client = chromadb.Client()
    
    # Use default embedding function (all-MiniLM-L6-v2)
    embedding_function = embedding_functions.DefaultEmbeddingFunction()
    
    # Create or get collection
    knowledge_collection = chroma_client.get_or_create_collection(
        name="cogito_knowledge_base",
        embedding_function=embedding_function,
        metadata={"description": "Software Engineering Best Practices"}
    )
    
    # Check if we need to load documents
    if knowledge_collection.count() == 0:
        load_documents_to_chromadb()
    else:
        print(f"[RAG System]: Collection already has {knowledge_collection.count()} documents")
    
    print(f"[RAG System]: Ready with {knowledge_collection.count()} searchable chunks")
    print("="*50 + "\n")


def load_documents_to_chromadb():
    """
    Load PDF documents into ChromaDB with vector embeddings.
    This enables semantic search (finding similar meaning, not just keywords).
    """
    global knowledge_collection
    
    if not os.path.exists(DOCS_DIR):
        print(f"[RAG System]: Warning - '{DOCS_DIR}' folder not found!")
        print(f"[RAG System]: Please create the folder and add PDF documents.")
        # Add some default SE knowledge so system works without PDFs
        add_default_knowledge()
        return
    
    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".pdf")]
    
    if not pdf_files:
        print(f"[RAG System]: No PDF files found in '{DOCS_DIR}'")
        add_default_knowledge()
        return
    
    all_chunks = []
    all_ids = []
    all_metadata = []
    
    for filename in pdf_files:
        filepath = os.path.join(DOCS_DIR, filename)
        print(f"[RAG System]: Processing: {filename}")
        
        try:
            reader = PdfReader(filepath)
            full_text = ""
            
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
            
            # Split into chunks of ~500 characters for better retrieval
            chunks = split_into_chunks(full_text, chunk_size=500, overlap=50)
            
            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) > 50:  # Skip very short chunks
                    chunk_id = f"{filename}_{i}_{uuid.uuid4().hex[:8]}"
                    all_chunks.append(chunk.strip())
                    all_ids.append(chunk_id)
                    all_metadata.append({
                        "source": filename,
                        "chunk_index": i,
                        "indexed_at": datetime.now().isoformat()
                    })
            
            print(f"  - Extracted {len(chunks)} chunks from {filename}")
            
        except Exception as e:
            print(f"  - Error reading {filename}: {e}")
    
    # Add all chunks to ChromaDB
    if all_chunks:
        # Add in batches to avoid memory issues
        batch_size = 100
        for i in range(0, len(all_chunks), batch_size):
            batch_end = min(i + batch_size, len(all_chunks))
            knowledge_collection.add(
                documents=all_chunks[i:batch_end],
                ids=all_ids[i:batch_end],
                metadatas=all_metadata[i:batch_end]
            )
        print(f"[RAG System]: Loaded {len(all_chunks)} chunks into vector store")
    else:
        print("[RAG System]: No content extracted, adding default knowledge")
        add_default_knowledge()


def split_into_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """Split text into overlapping chunks for better retrieval."""
    chunks = []
    
    # Split by paragraphs first
    paragraphs = text.split('\n\n')
    
    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        if len(current_chunk) + len(para) < chunk_size:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def add_default_knowledge():
    """
    Add default software engineering knowledge if no PDFs are available.
    This ensures the system works for demos even without external documents.
    """
    global knowledge_collection
    
    default_docs = [
        {
            "id": "microservices_benefits",
            "content": """Microservices Architecture Benefits:
            - Independent deployment: Each service can be deployed separately
            - Technology diversity: Different services can use different tech stacks
            - Scalability: Individual services can scale independently
            - Fault isolation: Failure in one service doesn't bring down the whole system
            - Team autonomy: Small teams can own and manage individual services
            Source: Software Architecture Best Practices""",
            "source": "default_knowledge"
        },
        {
            "id": "microservices_challenges",
            "content": """Microservices Architecture Challenges:
            - Distributed system complexity: Network latency, message serialization
            - Data consistency: Managing transactions across services is difficult
            - Operational overhead: More services mean more deployments, monitoring
            - Testing complexity: Integration testing becomes more challenging
            - Service discovery and load balancing required
            Source: Software Architecture Best Practices""",
            "source": "default_knowledge"
        },
        {
            "id": "monolith_benefits",
            "content": """Monolithic Architecture Benefits:
            - Simplicity: Single codebase, easier to understand and develop
            - Easy debugging: All code in one place, straightforward debugging
            - Performance: No network overhead between components
            - ACID transactions: Easy to maintain data consistency
            - Simple deployment: One artifact to deploy
            Source: Software Architecture Best Practices""",
            "source": "default_knowledge"
        },
        {
            "id": "monolith_challenges",
            "content": """Monolithic Architecture Challenges:
            - Scaling limitations: Must scale entire application, not just busy parts
            - Technology lock-in: Entire app uses same tech stack
            - Deployment risk: Any change requires full redeployment
            - Team coordination: Large teams working on same codebase cause conflicts
            - Long build times as application grows
            Source: Software Architecture Best Practices""",
            "source": "default_knowledge"
        },
        {
            "id": "sql_vs_nosql",
            "content": """SQL vs NoSQL Database Comparison:
            SQL Databases (PostgreSQL, MySQL):
            - ACID compliance for data integrity
            - Complex queries with JOINs
            - Fixed schema, good for structured data
            - Vertical scaling primarily
            
            NoSQL Databases (MongoDB, Cassandra):
            - Flexible schema for evolving data
            - Horizontal scaling built-in
            - Better for unstructured/semi-structured data
            - Eventually consistent (in most cases)
            Source: Designing Data-Intensive Applications""",
            "source": "default_knowledge"
        },
        {
            "id": "event_driven",
            "content": """Event-Driven Architecture:
            Benefits:
            - Loose coupling between services
            - Better scalability and resilience
            - Real-time data processing
            - Audit trail of all events
            
            Challenges:
            - Eventual consistency complexity
            - Event ordering and deduplication
            - Debugging distributed flows
            - Message broker dependency
            Source: Software Architecture Patterns""",
            "source": "default_knowledge"
        },
        {
            "id": "api_design",
            "content": """API Design Best Practices:
            REST API Guidelines:
            - Use nouns for resources, HTTP verbs for actions
            - Version your APIs (v1, v2)
            - Return appropriate HTTP status codes
            - Implement pagination for large datasets
            - Use HATEOAS for discoverability
            
            GraphQL Considerations:
            - Single endpoint, flexible queries
            - Client specifies needed data
            - Reduces over-fetching and under-fetching
            Source: API Design Guidelines""",
            "source": "default_knowledge"
        },
        {
            "id": "cloud_patterns",
            "content": """Cloud Architecture Patterns:
            - Circuit Breaker: Prevent cascade failures
            - Retry with backoff: Handle transient failures
            - Bulkhead: Isolate critical resources
            - Sidecar: Deploy components alongside services
            - Ambassador: Proxy for external services
            - CQRS: Separate read and write models
            Source: Cloud Design Patterns""",
            "source": "default_knowledge"
        }
    ]
    
    documents = [doc["content"] for doc in default_docs]
    ids = [doc["id"] for doc in default_docs]
    metadatas = [{"source": doc["source"]} for doc in default_docs]
    
    knowledge_collection.add(
        documents=documents,
        ids=ids,
        metadatas=metadatas
    )
    
    print(f"[RAG System]: Added {len(default_docs)} default knowledge chunks")


def search_knowledge(query: str, n_results: int = 5) -> list:
    """
    Perform semantic search on the knowledge base.
    Returns relevant chunks with their sources.
    """
    global knowledge_collection, evidence_log
    
    if knowledge_collection is None:
        init_rag_system()
    
    results = knowledge_collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    formatted_results = []
    
    if results["documents"] and results["documents"][0]:
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            source = metadata.get("source", "Unknown")
            distance = results["distances"][0][i] if results["distances"] else 0
            
            evidence_entry = {
                "evidence_id": str(uuid.uuid4()),
                "query": query,
                "source_document": source,
                "content_chunk": doc[:500],  # Truncate for logging
                "relevance_score": 1 - distance,  # Convert distance to similarity
                "retrieved_at": datetime.now().isoformat()
            }
            evidence_log.append(evidence_entry)
            
            formatted_results.append({
                "content": doc,
                "source": source,
                "relevance": 1 - distance
            })
    
    return formatted_results


def get_evidence_log() -> list:
    """Return the evidence log for database storage."""
    global evidence_log
    return evidence_log


def clear_evidence_log():
    """Clear the evidence log after storing to database."""
    global evidence_log
    evidence_log = []


# Initialize RAG system on module import
init_rag_system()


# === THE CREWAI TOOL ===
@tool("Architecture Search Tool")
def rag_tool(query: str) -> str:
    """
    Search the knowledge base for software architecture evidence.
    Uses semantic search (ChromaDB) to find relevant information.
    
    Input: A search query (e.g., "microservices scalability benefits")
    Output: Relevant evidence from the knowledge base with sources.
    """
    print(f"\n  📚 [RAG Tool]: Searching for '{query}'...")
    
    results = search_knowledge(query, n_results=3)
    
    if not results:
        return f"No relevant evidence found for: '{query}'"
    
    output = f"Found {len(results)} relevant sources for '{query}':\n"
    output += "=" * 50 + "\n"
    
    for i, result in enumerate(results, 1):
        source = result["source"]
        content = result["content"]
        relevance = result["relevance"]
        
        output += f"\n📄 EVIDENCE {i} (Source: {source}, Relevance: {relevance:.2f}):\n"
        output += "-" * 40 + "\n"
        output += content[:600]  # Limit content length
        if len(content) > 600:
            output += "...[truncated]"
        output += "\n"
    
    output += "=" * 50
    
    print(f"  📚 [RAG Tool]: Found {len(results)} results")
    
    return output