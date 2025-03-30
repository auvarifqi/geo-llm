"""
API Client Utilities for GeoViz3D

This module contains general API client functions.
"""
import requests
import logging
import time
import functools
from typing import Dict, Any, Optional, Callable, TypeVar, Tuple, List

# Import configuration
from config.settings import (
    API_TIMEOUT,
    MAX_RETRIES
)

# Set up logging
logger = logging.getLogger(__name__)

# Type variables for generics
T = TypeVar('T')
R = TypeVar('R')

def rate_limited(max_calls: int, time_frame: int) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """
    Decorator to rate limit API calls.
    
    Args:
        max_calls (int): Maximum number of calls allowed in the time frame
        time_frame (int): Time frame in seconds
        
    Returns:
        Callable: Decorated function
    """
    calls = []
    
    def decorator(func: Callable[..., R]) -> Callable[..., R]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> R:
            now = time.time()
            
            # Remove calls older than the time frame
            nonlocal calls
            calls = [t for t in calls if now - t < time_frame]
            
            # Check if we're over the limit
            if len(calls) >= max_calls:
                # Calculate wait time
                oldest_call = min(calls)
                wait_time = time_frame - (now - oldest_call)
                logger.warning(f"Rate limit hit, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                
                # Refresh now time after waiting
                now = time.time()
            
            # Add current call to list
            calls.append(now)
            
            # Call the original function
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator

def retry_on_failure(
    max_retries: int = MAX_RETRIES, 
    backoff_factor: float = 2.0
) -> Callable[[Callable[..., R]], Callable[..., R]]:
    """
    Decorator to retry a function on failure with exponential backoff.
    
    Args:
        max_retries (int, optional): Maximum number of retries. Defaults to MAX_RETRIES.
        backoff_factor (float, optional): Factor for exponential backoff. Defaults to 2.0.
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable[..., R]) -> Callable[..., R]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> R:
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {str(e)}")
                        raise
                    
                    wait_time = backoff_factor ** retries
                    logger.warning(f"Retry {retries}/{max_retries} for {func.__name__} in {wait_time:.2f}s: {str(e)}")
                    time.sleep(wait_time)
            
            # This should never be reached due to the raise above
            raise RuntimeError(f"Unexpected error in retry logic for {func.__name__}")
        
        return wrapper
    
    return decorator

class APIClient:
    """Base class for API clients with common functionality."""
    
    def __init__(self, base_url: str, timeout: int = API_TIMEOUT):
        """
        Initialize the API client.
        
        Args:
            base_url (str): Base URL for the API
            timeout (int, optional): Request timeout in seconds. Defaults to API_TIMEOUT.
        """
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        
        # Set a user agent to be considerate to APIs
        self.session.headers.update({
            "User-Agent": "GeoViz3D/1.0 (https://github.com/your-username/geoviz3d)"
        })
    
    def get(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        """
        Make a GET request to the API.
        
        Args:
            endpoint (str): API endpoint
            params (Optional[Dict[str, Any]], optional): Query parameters. Defaults to None.
            headers (Optional[Dict[str, str]], optional): Additional headers. Defaults to None.
            
        Returns:
            requests.Response: Response object
            
        Raises:
            requests.exceptions.HTTPError: If the request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.get(
            url, 
            params=params, 
            headers=headers, 
            timeout=self.timeout
        )
        response.raise_for_status()
        return response
    
    def post(
        self, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None, 
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        """
        Make a POST request to the API.
        
        Args:
            endpoint (str): API endpoint
            data (Optional[Dict[str, Any]], optional): Form data. Defaults to None.
            json_data (Optional[Dict[str, Any]], optional): JSON data. Defaults to None.
            headers (Optional[Dict[str, str]], optional): Additional headers. Defaults to None.
            
        Returns:
            requests.Response: Response object
            
        Raises:
            requests.exceptions.HTTPError: If the request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        response = self.session.post(
            url, 
            data=data, 
            json=json_data, 
            headers=headers, 
            timeout=self.timeout
        )
        response.raise_for_status()
        return response
    
    def close(self) -> None:
        """Close the session."""
        self.session.close()
    
    def __enter__(self) -> 'APIClient':
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self.close()

@retry_on_failure()
def safe_request(
    url: str, 
    method: str = "GET", 
    **kwargs
) -> requests.Response:
    """
    Make a request with retry logic and error handling.
    
    Args:
        url (str): URL to request
        method (str, optional): HTTP method. Defaults to "GET".
        **kwargs: Additional arguments to pass to requests
        
    Returns:
        requests.Response: Response object
        
    Raises:
        requests.exceptions.HTTPError: If the request fails after all retries
    """
    # Set a default timeout if not provided
    if "timeout" not in kwargs:
        kwargs["timeout"] = API_TIMEOUT
    
    # Make the request
    if method.upper() == "GET":
        response = requests.get(url, **kwargs)
    elif method.upper() == "POST":
        response = requests.post(url, **kwargs)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
    
    # Check for errors
    response.raise_for_status()
    
    return response

def batch_requests(
    urls: List[str], 
    max_concurrent: int = 5, 
    **kwargs
) -> List[Tuple[str, Optional[requests.Response]]]:
    """
    Make multiple requests in batches to avoid overwhelming servers.
    
    Args:
        urls (List[str]): List of URLs to request
        max_concurrent (int, optional): Maximum concurrent requests. Defaults to 5.
        **kwargs: Additional arguments to pass to requests
        
    Returns:
        List[Tuple[str, Optional[requests.Response]]]: List of (url, response) tuples
            Response may be None if the request failed
    """
    results = []
    
    # Process URLs in batches
    for i in range(0, len(urls), max_concurrent):
        batch = urls[i:i+max_concurrent]
        batch_results = []
        
        # Make requests for this batch
        for url in batch:
            try:
                response = safe_request(url, **kwargs)
                batch_results.append((url, response))
            except Exception as e:
                logger.error(f"Failed to request {url}: {str(e)}")
                batch_results.append((url, None))
        
        results.extend(batch_results)
    
    return results