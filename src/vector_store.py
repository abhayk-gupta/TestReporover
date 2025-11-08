import chromadb
import os
import json
from src.data_loader import load_pdf_documents, load_jsonl_data
from langchain_community.embeddings import FastEmbedEmbeddings

# Define paths
DB_PATH = "db_storage/chroma_db"
PDF_FILE_PATH = "data/raw/legal_docs.pdf"  # Use your PDF file name
JSONL_FILE_PATH = "data/raw/train.jsonl"    # Use your JSONL file name

# Ensure the storage directory exists
os.makedirs(DB_PATH, exist_ok=True)

# --- START OF FIX: Add a helper function for batching ---
def batch_iterable(iterable, batch_size=5000):
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
    Initializes and populates the Chroma vector store.
    """
    print("Loading FastEmbed model (BAAI/bge-small-en-v1.5)...")
    embedding_model = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    
    print("Initializing ChromaDB client...")
    client = chromadb.PersistentClient(path=DB_PATH)
    
    # === 1. Populate Text Collection (from PDFs) ===
    print("\n--- Processing PDF Documents ---")
    try:
        text_collection = client.get_or_create_collection(name="text_collection")
        
        if text_collection.count() == 0:
            print("Text collection is empty. Populating...")
            # Load and chunk documents
            docs = load_pdf_documents(PDF_FILE_PATH)
            
            if docs:
                documents = [doc.page_content for doc in docs]
                metadatas = [doc.metadata for doc in docs]
                ids = [f"text_chunk_{i}" for i in range(len(documents))]
                
                print(f"Embedding {len(documents)} text documents using 'BAAI/bge-small-en-v1.5' model... (This may take a while)")
                embeddings = embedding_model.embed_documents(documents)
                
                # --- START OF FIX: Add documents in batches ---
                # Use a batch size smaller than the limit (e.g., 5000)
                batch_size = 5000
                total_added = 0
                
                # Zip all data together for batching
                data_batch = zip(embeddings, documents, metadatas, ids)
                
                for batch in batch_iterable(data_batch, batch_size):
                    batch_embeddings, batch_documents, batch_metadatas, batch_ids = zip(*batch)
                    
                    print(f"Adding batch of {len(batch_ids)} documents to 'text_collection'...")
                    text_collection.add(
                        embeddings=list(batch_embeddings),
                        documents=list(batch_documents),
                        metadatas=list(batch_metadatas),
                        ids=list(batch_ids)
                    )
                    total_added += len(batch_ids)
                
                print(f"Added {total_added} text chunks to 'text_collection'.")
                # --- END OF FIX ---
            else:
                print("No documents found to add.")
        else:
            print(f"'text_collection' already has {text_collection.count()} documents. Skipping.")
            
    except Exception as e:
        print(f"Error processing text collection: {e}")

    # === 2. Populate JSON Collection (from JSONL) ===
    print("\n--- Processing JSONL Documents ---")
    try:
        json_collection = client.get_or_create_collection(name="json_collection")
        
        if json_collection.count() == 0:
            print("JSON collection is empty. Populating...")
            qa_pairs_raw = load_jsonl_data(JSONL_FILE_PATH)
            
            if qa_pairs_raw:
                print("Validating JSONL documents...")
                docs_filtered = []
                for item in qa_pairs_raw:
                    if 'text' in item and 'labels' in item and 'id' in item and isinstance(item['text'], list):
                        docs_filtered.append(item)
                
                print(f"Found {len(docs_filtered)} valid documents out of {len(qa_pairs_raw)} total.")
                
                if not docs_filtered:
                    print("No valid documents found to add.")
                    return

                documents = ["\n".join(item['text']) for item in docs_filtered] 
                metadatas = [
                    {'source': f"jsonl_id_{item['id']}", 'labels': ", ".join(item['labels'])} 
                    for item in docs_filtered
                ] 
                ids = [f"json_id_{item['id']}" for item in docs_filtered]

                print(f"Embedding {len(documents)} JSONL documents using 'BAAI/bge-small-en-v1.5' model... (This may take a while)")
                embeddings = embedding_model.embed_documents(documents)
                
                # --- START OF FIX: Add documents in batches ---
                batch_size = 5000
                total_added = 0
                
                # Zip all data together for batching
                data_batch = zip(embeddings, documents, metadatas, ids)
                
                for batch in batch_iterable(data_batch, batch_size):
                    batch_embeddings, batch_documents, batch_metadatas, batch_ids = zip(*batch)
                    
                    print(f"Adding batch of {len(batch_ids)} documents to 'json_collection'...")
                    json_collection.add(
                        embeddings=list(batch_embeddings),
                        documents=list(batch_documents),
                        metadatas=list(batch_metadatas),
                        ids=list(batch_ids)
                    )
                    total_added += len(batch_ids)
                
                print(f"Added {total_added} documents to 'json_collection'.")
                # --- END OF FIX ---
            else:
                print("No JSONL documents found to add.")
        else:
            print(f"'json_collection' already has {json_collection.count()} documents. Skipping.")
            
    except Exception as e:
        print(f"Error processing JSON collection: {e}")

    print("\nVector store initialization complete.")

if __name__ == "__main__":
    initialize_vector_store()