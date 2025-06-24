from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from typing import List
from leah.config.GlobalConfig import GlobalConfig as GCM
from langchain_text_splitters import RecursiveCharacterTextSplitter

class NotesRag:
    def __init__(self, files: List[str], model: str = "models/gemini-embedding-exp-03-07", task_type: str = "RETRIEVAL_DOCUMENT", chunk_size: int = 1000, chunk_overlap: int = 200):
        self.config = GCM()
        api_key = self.config.get_gemini_api_key()
        self.embeddings = GoogleGenerativeAIEmbeddings(model=model, task_type=task_type, google_api_key=api_key)
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        texts = self._load_and_split_files(files)
        self.vector_store = InMemoryVectorStore.from_texts(texts, embedding=self.embeddings)

    def _load_and_split_files(self, files: List[str]) -> List[str]:
        all_chunks = []
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Split content into chunks
                chunks = self.text_splitter.split_text(content)
                all_chunks.extend(chunks)
            except Exception as e:
                print(f"Error reading or splitting {file_path}: {e}")
        return all_chunks

    def add_documents(self, texts: List[str]):
        # Add new documents to the vector store
        new_store = InMemoryVectorStore.from_texts(texts, embedding=self.embeddings)
        self.vector_store._vectors.extend(new_store._vectors)
        self.vector_store._documents.extend(new_store._documents)

    def similarity_search(self, query: str, k: int = 3):
        # Return the top-k most similar documents to the query
        retriever = self.vector_store.as_retriever(search_kwargs={"k": k})
        return retriever.invoke(query)
