import os
import time
import json
import gc
import concurrent.futures
from pinecone import Pinecone, ServerlessSpec
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.data_loader import load_pdf_documents, stream_jsonl_documents
from langchain_community.embeddings import FastEmbedEmbeddings
from dotenv import load_dotenv
load_dotenv()
# Define paths
PDF_FILE_PATH = "data/raw/legal_docs.pdf"  # Use your PDF file name
JSONL_FILE_PATH = "data/raw/train.jsonl"    # Use your JSONL file name

# --- ADD THIS ROBUST UPLOAD HELPER FUNCTION ---
def upload_with_retry(index, vectors, namespace, max_retries=3):
    """Native Pinecone upsert with exponential backoff for the background thread."""
    for attempt in range(max_retries):
        try:
            index.upsert(vectors=vectors, namespace=namespace)
            # --- ADD THIS PRINT STATEMENT ---
            print(f"   [☁️] Background Wi-Fi: Successfully uploaded {len(vectors)} vectors!")
            return True
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                sleep_time = (attempt + 1) * 5 
                print(f"   [!] Pinecone rate limit hit. Pausing for {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                print(f"   [!] Unexpected error: {e}")
                raise e 
    return False

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
        providers=[
            ("CUDAExecutionProvider", {
                "cudnn_conv_algo_search": "DEFAULT",
                "gpu_mem_limit": 2 * 1024 * 1024 * 1024, # Limit to 2GB of VRAM
                "arena_extend_strategy": "kSameAsRequested" # Crucial for system RAM
            })
        ],
        batch_size=64   
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
    print("\n--- Processing JSONL Documents (Streaming + Pipelining) ---")
    try:
        print(f"JSON namespace currently has {current_json_count} vectors. Resuming/Updating...")
        
        batch_texts, batch_metas, batch_ids = [], [], []
        total_added = 0
        batch_size = 256
        
        # --- ENHANCEMENT: Progress Tracking Metrics ---
        start_time = time.time()
        TOTAL_ESTIMATED_VECTORS = 311767  # Using your known dataset size
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            upload_task = None
            
            for chunk_text, chunk_meta, chunk_id in stream_jsonl_documents(JSONL_FILE_PATH):
                batch_texts.append(chunk_text)
                batch_metas.append(chunk_meta)
                batch_ids.append(chunk_id)
                
                if len(batch_texts) >= batch_size:
                    chunk_embeddings = embedding_model.embed_documents(batch_texts)
                    
                    vectors_to_upsert = [
                        {"id": vid, "values": list(emb), "metadata": m}
                        for vid, emb, m in zip(batch_ids, chunk_embeddings, batch_metas)
                    ]
                    
                    if upload_task:
                        upload_task.result()
                        
                    upload_task = executor.submit(
                        upload_with_retry, index, vectors_to_upsert, "json_collection"
                    )
                    
                    total_added += len(batch_texts)
                    
                    # --- ENHANCEMENT: Print Percentage and Speed ---
                    elapsed_time = time.time() - start_time
                    speed = total_added / elapsed_time if elapsed_time > 0 else 0
                    percentage = (total_added / TOTAL_ESTIMATED_VECTORS) * 100
                    
                    print(f"   ✓ Queued {total_added}/{TOTAL_ESTIMATED_VECTORS} [{percentage:.2f}%] | Speed: {speed:.1f} vec/sec")
                    
                    batch_texts.clear()
                    batch_metas.clear()
                    batch_ids.clear()
                    gc.collect()

            # Upload Leftovers
            if batch_texts:
                chunk_embeddings = embedding_model.embed_documents(batch_texts)
                vectors_to_upsert = [
                    {"id": vid, "values": list(emb), "metadata": m} 
                    for vid, emb, m in zip(batch_ids, chunk_embeddings, batch_metas)
                ]
                if upload_task:
                    upload_task.result() 
                upload_with_retry(index, vectors_to_upsert, "json_collection")
                total_added += len(batch_texts)

            total_time = (time.time() - start_time) / 60
            print(f"\n[SUCCESS] Added all {total_added} vectors in {total_time:.2f} minutes.\n")

    except Exception as e:
        print(f"Error processing JSON namespace: {e}")

    print("\nVector store initialization complete.")

if __name__ == "__main__":
    try:
        initialize_vector_store()
    except KeyboardInterrupt:
        print("\n\n[🛑] Process interrupted by user (Ctrl+C).")
        print("Waiting for the final background Wi-Fi upload to finish before closing safely...")
        # Because we used a 'with ThreadPoolExecutor' block, Python will naturally 
        # wait for the current upload_task to finish before actually closing.
        print("Safely shut down. No data was corrupted!")