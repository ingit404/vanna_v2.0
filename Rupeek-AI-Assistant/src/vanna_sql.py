import vanna
from vanna.base import VannaBase
from src.qdrant_cloud  import MyQdrantVectorStore
from src.gemini import GeminiLLM



class MyVanna(MyQdrantVectorStore, GeminiLLM, VannaBase):
    def __init__(self, config=None):
        VannaBase.__init__(self, config=config)
        MyQdrantVectorStore.__init__(self, config=config)
        GeminiLLM.__init__(self)

if __name__ == "__main__":
    print("MyVanna module loaded successfully ✅")
