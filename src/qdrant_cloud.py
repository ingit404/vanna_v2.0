# qdrant cloud vector store integration
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer
from vanna.qdrant import Qdrant_VectorStore
import numpy as np
from typing import List


class MyQdrantVectorStore(Qdrant_VectorStore):
    def __init__(self, config=None):
        cfg = config or {}

       # Validate embedder model ---
        embedder_path = cfg.get("embedder_model")
        if not embedder_path:
            raise ValueError("Embedder model not found")

        self.embedder = SentenceTransformer(embedder_path)
        self.embeddings_dimension = 1024

        # Setup Qdrant Cloud connection ---
        qdrant_url = cfg.get("qdrant_url")
        api_key = cfg.get("qdrant_api_key")

        print(">Qrant URL in use:", qdrant_url)

        self._client = QdrantClient(
            url=qdrant_url,
            api_key=api_key,
            timeout=60,
            prefer_grpc=False ,verify=False)

        # Initialize internal collection names ---
        self.ddl_collection_name = "ddl"
        self.documentation_collection_name = "documentation"
        self.sql_collection_name = "sql"

        #  Add the missing internal mappings from Vanna base class ---
        self.id_suffixes = {
            self.ddl_collection_name: "ddl",
            self.documentation_collection_name: "documentation",
            self.sql_collection_name: "sql",
        }

        self.collection_params = {}
        self.top_k = cfg.get("top_k", 7)
        self.n_results = self.top_k 

        #  Manually ensure collections exist on Qdrant Cloud ---
        for cname in [
            self.ddl_collection_name,
            self.documentation_collection_name,
            self.sql_collection_name,
        ]:
            try:
                self._client.get_collection(cname)
                print(f"Collection '{cname}' already exists.")
            except Exception:
                print(f"Creating collection '{cname}' (size={self.embeddings_dimension})")
                self._client.recreate_collection(
                    collection_name=cname,
                    vectors_config=VectorParams(
                        size=self.embeddings_dimension,
                        distance=Distance.COSINE
                    ),
                )
    def generate_embedding(self, text: str, **kwargs) -> List[float]:
        emb = self.embedder.encode(text)
        return np.asarray(emb).tolist()


if __name__ == "__main__":
    print("✅ Qdrant Cloud vector store module loaded successfully!")
