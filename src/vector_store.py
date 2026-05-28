import os
import time
import json
from pinecone import Pinecone, ServerlessSpec
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.data_loader import load_pdf_documents, load_jsonl_documents
from langchain_community.embeddings import FastEmbedEmbeddings
from dotenv import load_dotenv
load_dotenv()
# Define paths
PDF_FILE_PATH = "data/raw/legal_docs.pdf"  # Use your PDF file name
JSONL_FILE_PATH = "data/raw/train.jsonl"    # Use your JSONL file name

# --- START OF FIX: Helper function for batching ---
def batch_iterable(iterable, batch_size=200):
    """Yields successive chunks from an iterable."""
    it = iter(iterable)
    while True:
        chunk = []
        try:
            for _ in range(batch_size):
                chunk.append(next(it))
        except StopIteration:
            if chunk:
                yield chunk
            break
        yield chunk
# --- END OF FIX ---


def initialize_vector_store():
    """
    Initializes and populates the cloud-hosted Pinecone vector store using namespaces.
    """
    # 0. Core Environment Checks
    api_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME", "legal-buddy")
    
    if not api_key:
        raise ValueError("Missing PINECONE_API_KEY in environment variables.")

    print("Loading FastEmbed model (BAAI/bge-small-en-v1.5)...")
    embedding_model = FastEmbedEmbeddings(
        model_name="BAAI/bge-small-en-v1.5",
        providers=["CUDAExecutionProvider"], # This routes it to your GPU
        batch_size=256                       # Controls VRAM usage (lower this if it crashes)
    )
    print("Initializing Pinecone client...")
    pc = Pinecone(api_key=api_key)
    
    # Ensure the single index exists on the serverless free tier
    existing_indexes = [index.name for index in pc.list_indexes()]
    if index_name not in existing_indexes:
        print(f"Creating fresh Pinecone index: '{index_name}'...")
        pc.create_index(
            name=index_name,
            dimension=384,  # Perfect match for BAAI/bge-small-en-v1.5 dimensions
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        print("Pinecone index initialized.")
        
    index = pc.Index(index_name)
    
    # Fetch current stats to see vector counts per namespace
    index_stats = index.describe_index_stats()
    namespaces = index_stats.get('namespaces', {})
    
    current_text_count = namespaces.get('text_collection', {}).get('vector_count', 0)
    current_json_count = namespaces.get('json_collection', {}).get('vector_count', 0)

    # === 1. Populate Text Namespace (from PDFs) ===
    print("\n--- Processing PDF Documents ---")
    try:
        if current_text_count == 0:
            print("Text namespace is empty. Populating...")
            docs = load_pdf_documents(PDF_FILE_PATH)
            
            if docs:
                documents = [doc.page_content for doc in docs]
                metadatas = [doc.metadata for doc in docs]
                ids = [f"text_chunk_{i}" for i in range(len(documents))]
                
                print(f"Embedding {len(documents)} text documents using 'BAAI/bge-small-en-v1.5'... (This may take a while)")
                embeddings = embedding_model.embed_documents(documents)
                
                batch_size = 200  # Optimized network chunk size for Pinecone
                total_added = 0
                data_batch = zip(embeddings, documents, metadatas, ids)
                
                for batch in batch_iterable(data_batch, batch_size):
                    batch_embeddings, batch_documents, batch_metadatas, batch_ids = zip(*batch)
                    
                    # Pinecone stores the document text explicitly inside the metadata object
                    vectors_to_upsert = []
                    for emb, doc, meta, vector_id in zip(batch_embeddings, batch_documents, batch_metadatas, batch_ids):
                        meta['text'] = doc  # standard LangChain/RAG metadata convention
                        vectors_to_upsert.append({
                            "id": vector_id,
                            "values": list(emb),
                            "metadata": meta
                        })
                    
                    print(f"Upserting batch of {len(batch_ids)} vectors to namespace 'text_collection'...")
                    index.upsert(vectors=vectors_to_upsert, namespace="text_collection")
                    total_added += len(batch_ids)
                
                print(f"Added {total_added} text chunks to namespace 'text_collection'.")
            else:
                print("No documents found to add.")
        else:
            print(f"'text_collection' namespace already has {current_text_count} vectors. Skipping.")
            
    except Exception as e:
        print(f"Error processing text namespace: {e}")

    # === 2. Populate JSON Namespace (from JSONL) ===
    print("\n--- Processing JSONL Documents ---")
    try:
        print(f"JSON namespace currently has {current_json_count} vectors. Resuming/Updating...")
        
        docs = load_jsonl_documents(JSONL_FILE_PATH)
        
        if docs:
            documents = [doc.page_content for doc in docs]
            metadatas = [doc.metadata for doc in docs]
            ids = [meta.pop('chunk_id') for meta in metadatas]

            # --- START OF STREAMING EMBEDDING & UPSERT ---
            total_docs = len(documents)
            print(f"\n[START] Processing {total_docs} JSONL chunks...")
            
            batch_size = 500
            total_added = 0
            
            for i in range(0, total_docs, batch_size):
                chunk_docs = documents[i : i + batch_size]
                chunk_metas = metadatas[i : i + batch_size]
                chunk_ids = ids[i : i + batch_size]
                
                chunk_embeddings = embedding_model.embed_documents(chunk_docs)
                
                vectors_to_upsert = []
                for emb, doc, meta, vector_id in zip(chunk_embeddings, chunk_docs, chunk_metas, chunk_ids):
                    meta['text'] = doc 
                    vectors_to_upsert.append({
                        "id": vector_id,
                        "values": list(emb),
                        "metadata": meta
                    })
                
                # --- THE BULLETPROOF RETRY LOOP ---
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        index.upsert(vectors=vectors_to_upsert, namespace="json_collection")
                        break 
                    except Exception as e:
                        if "429" in str(e) or "Too Many Requests" in str(e):
                            sleep_time = (attempt + 1) * 5 
                            print(f"   [!] Pinecone rate limit hit. Pausing for {sleep_time} seconds...")
                            time.sleep(sleep_time)
                        else:
                            print(f"   [!] Unexpected error: {e}")
                            raise e 
                # -----------------------------------
                
                total_added += len(vectors_to_upsert)
                percentage = (total_added / total_docs) * 100
                print(f"   ✓ Embedded & Upserted {total_added}/{total_docs} chunks [{percentage:.2f}%]")
            
            print(f"\n[SUCCESS] Added all {total_added} vectors to namespace 'json_collection'.\n")
        else:
            print("No JSONL documents found to add.")
            
    except Exception as e:
        print(f"Error processing JSON namespace: {e}")

    print("\nVector store initialization complete.")

if __name__ == "__main__":
    initialize_vector_store()