from sentence_transformers import SentenceTransformer
import os

# Set a persistent cache directory for models
# This is good practice for MLOps
os.environ['SENTENCE_TRANSFORMERS_HOME'] = 'models'

def get_embedding_model(model_name="BAAI/bge-small-en-v1.5"):
    """
    Loads and returns the SentenceTransformer embedding model.
    Models will be cached in the 'models/' directory.
    """
    print(f"Loading embedding model: {model_name}...")
    # trust_remote_code=True is required for nomic-embed-text
    embedder = SentenceTransformer(model_name)
    print("Embedding model loaded.")
    return embedder

# You can have a single, pre-loaded model instance
# that other modules can import if you want to save loading time.
# This pattern is called a singleton.
embedding_model = get_embedding_model()

if __name__ == '__main__':
    # This block allows you to test this file directly
    # Run: python src/embedding.py
    print("Testing embedding model...")
    test_text = "This is a test sentence."
    embeddings = embedding_model.encode(test_text)
    print(f"Embedding dimension: {len(embeddings)}")
    print("embedding.py is working correctly.")