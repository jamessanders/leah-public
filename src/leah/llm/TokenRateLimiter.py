import threading
import time
from leah.config.GlobalConfig import GlobalConfig

class TokenRateLimiter:
    """
    Singleton class for tracking and limiting token usage across different connectors.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TokenRateLimiter, cls).__new__(cls)
                cls._instance._token_usage = {}  # Dictionary to track token usage per connector
                cls._instance._limiter_lock = threading.Lock()
            return cls._instance
    
    def add_tokens(self, connector_type: str, token_count: int) -> None:
        """
        Add consumed tokens to the rate limiter for tracking.
        
        Args:
            connector_type: The type of connector (e.g., 'gemini', 'openai')
            token_count: Number of tokens consumed in this request
        """
        with self._limiter_lock:
            current_time = time.time()
            
            # Initialize if needed
            if connector_type not in self._token_usage:
                self._token_usage[connector_type] = []
                
            # Add current token usage with timestamp
            self._token_usage[connector_type].append((current_time, token_count))
    
    def check_rate_limit(self, connector_type: str, estimated_tokens: int = 0) -> bool:
        """
        Check if we can make a request for this connector type based on token rate limits.
        Returns True if request is allowed, False if we need to wait.
        
        Args:
            connector_type: The type of connector (e.g., 'gemini', 'openai')
            estimated_tokens: Estimated number of tokens for the upcoming request
        """
        config = GlobalConfig()
        tokens_per_minute = int(config.get_connector_rate_limit(connector_type)) # TOKENS per minute
        print(f" - Checking rate limit for {connector_type} with limit {tokens_per_minute} tokens/minute")
        
        with self._limiter_lock:
            current_time = time.time()
            
            # Initialize if needed
            if connector_type not in self._token_usage:
                self._token_usage[connector_type] = []
            
            # Remove token usage entries older than 1 minute
            one_minute_ago = current_time - 60
            self._token_usage[connector_type] = [(t, tokens) for (t, tokens) in self._token_usage[connector_type] if t > one_minute_ago]
            
            # Calculate total tokens used in the last minute
            total_tokens_used = sum(tokens for _, tokens in self._token_usage[connector_type])
            estimated_total = total_tokens_used + estimated_tokens
            
            print(f" - Used {total_tokens_used} tokens in the last minute for {connector_type}")
           
            # Check if we've exceeded the token rate limit
            if estimated_total > tokens_per_minute:
                print(f" - Estimated total tokens: {estimated_total} is greater than tpm limit of {tokens_per_minute}")
                return False
                
            # The actual token usage will be added after the request completes via add_tokens
            return True 