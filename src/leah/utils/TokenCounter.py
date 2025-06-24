import tiktoken
from typing import List

class TokenLimiter:
    def __init__(self, max_tokens: int, encoding_name: str = "cl100k_base"):
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.max_tokens = max_tokens
        self.total_counted = 0
        
    def count(self, message: str) -> bool:
        if self.total_counted + len(self.encoding.encode(message)) > self.max_tokens:
            return False
        self.total_counted += len(self.encoding.encode(message))
        return True
    
    def reset(self) -> None:
        self.total_counted = 0

class TokenCounter:
    def __init__(self, max_tokens: int, encoding_name: str = "cl100k_base"):
        """Initialize TokenCounter with specified encoding and maximum token limit.
        
        Args:
            max_tokens (int): Maximum number of tokens allowed in the buffer.
            encoding_name (str): The name of the tiktoken encoding to use.
                               Defaults to cl100k_base (used by GPT-4 and GPT-3.5).
        """
        self.encoding = tiktoken.get_encoding(encoding_name)
        self.chunks: List[str] = []
        self.max_tokens = max_tokens
        
    def feed(self, text: str) -> None:
        """Add text as a new chunk to the buffer. If adding the chunk would exceed max_tokens,
        older chunks are removed from the beginning until we're within the limit.
        
        Args:
            text (str): The text to add as a new chunk.
        """

        # Add the new chunk
        self.chunks.append(text)
        
       
    def count(self) -> int:
        """Count the number of tokens in all current chunks.
        
        Returns:
            int: The total number of tokens across all chunks.
        """
        return len(self.encoding.encode(''.join(self.chunks)))
    
    def clear(self) -> None:
        """Clear all chunks."""
        self.chunks = []
        
    def remaining_tokens(self) -> int:
        """Get the number of tokens remaining before hitting the limit.
        
        Returns:
            int: Number of tokens remaining before reaching max_tokens.
        """
        return self.max_tokens - self.count()
    
    def tail(self) -> str:
        """Return the end chunks that fit within max_tokens, never splitting chunks.
        Will return the maximum number of complete chunks from the end that fit
        within the token limit.
        
        Returns:
            str: The last complete chunks that fit within max_tokens.
        """
        if not self.chunks:
            return ""
            
        result_chunks = []
        token_count = 0
        
        # Work backwards through chunks
        for chunk in reversed(self.chunks):
            chunk_tokens = len(self.encoding.encode(chunk))
            if token_count + chunk_tokens <= self.max_tokens:
                result_chunks.insert(0, chunk)
                token_count += chunk_tokens
            else:
                break
                
        return result_chunks
    
    def head(self) -> str:
        """Return the beginning chunks that fit within max_tokens, never splitting chunks.
        Will return the maximum number of complete chunks from the start that fit
        within the token limit.
        
        Returns:
            str: The first complete chunks that fit within max_tokens.
        """
        if not self.chunks:
            return ""
            
        result_chunks = []
        token_count = 0
        
        # Work forward through chunks
        for chunk in self.chunks:
            chunk_tokens = len(self.encoding.encode(chunk))
            if token_count + chunk_tokens <= self.max_tokens:
                result_chunks.append(chunk)
                token_count += chunk_tokens
            else:
                break
                
        return result_chunks
        
   