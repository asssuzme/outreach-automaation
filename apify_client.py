"""Apify API client wrapper for LinkedIn profile scraping."""
import requests
import time
from typing import Dict, Any
from config import APIFY_API_KEY, APIFY_API_BASE_URL, LINKEDIN_PROFILE_ACTOR, LINKEDIN_POSTS_ACTOR


class ApifyClient:
    """Client for interacting with Apify API."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize Apify client.
        
        Args:
            api_key: Apify API key. If not provided, uses the one from config.
        """
        self.api_key = api_key or APIFY_API_KEY
        self.base_url = APIFY_API_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def scrape_linkedin_profile(self, profile_url: str, wait_timeout: int = 300) -> Dict[str, Any]:
        """
        Scrape LinkedIn profile using Apify actor.
        
        Args:
            profile_url: Full LinkedIn profile URL
            wait_timeout: Maximum time to wait for the actor to complete (seconds)
            
        Returns:
            Dictionary containing scraped profile data
            
        Raises:
            Exception: If API call fails or actor run fails
        """
        actor_id = LINKEDIN_PROFILE_ACTOR.replace('/', '~')
        
        # Prepare the input payload
        # The actor expects "username" parameter which can be a username, full URL, or URN
        payload = {
            "username": profile_url
        }
        
        try:
            # Start the actor run
            print("Starting Apify actor run...")
            run_response = requests.post(
                f"{self.base_url}/acts/{actor_id}/runs",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            run_response.raise_for_status()
            run_data = run_response.json()
            run_id = run_data['data']['id']
            
            print(f"Actor run started. Run ID: {run_id}")
            print("Waiting for actor to complete...")
            
            # Poll for completion
            start_time = time.time()
            while time.time() - start_time < wait_timeout:
                status_response = requests.get(
                    f"{self.base_url}/actor-runs/{run_id}",
                    headers=self.headers,
                    timeout=30
                )
                status_response.raise_for_status()
                status_data = status_response.json()
                status = status_data['data']['status']
                
                if status == 'SUCCEEDED':
                    print("Actor run completed successfully!")
                    # Get the dataset ID
                    dataset_id = status_data['data']['defaultDatasetId']
                    
                    # Fetch the results
                    items_response = requests.get(
                        f"{self.base_url}/datasets/{dataset_id}/items",
                        headers=self.headers,
                        timeout=30
                    )
                    items_response.raise_for_status()
                    items_data = items_response.json()
                    
                    # Handle different response structures
                    items = None
                    if isinstance(items_data, dict):
                        if 'data' in items_data:
                            data = items_data['data']
                            # Check if data has 'items' key or is the items itself
                            if isinstance(data, dict) and 'items' in data:
                                items = data['items']
                            elif isinstance(data, list):
                                items = data
                            else:
                                # If data is a dict without 'items', it might be the profile data itself
                                items = [data]
                        elif 'items' in items_data:
                            items = items_data['items']
                        else:
                            # If the dict itself is the profile data
                            items = [items_data]
                    elif isinstance(items_data, list):
                        items = items_data
                    
                    # Return the first item (or all items if multiple)
                    if items and len(items) > 0:
                        # If items is a list, return first item, otherwise return as-is
                        if isinstance(items, list):
                            return items[0] if len(items) == 1 else items
                        else:
                            return items
                    else:
                        raise Exception(f"Actor completed but no data was returned. Response structure: {type(items_data)}")
                        
                elif status == 'FAILED':
                    error_msg = f"Actor run failed. Status: {status}"
                    if 'stats' in status_data['data']:
                        error_msg += f"\nStats: {status_data['data']['stats']}"
                    raise Exception(error_msg)
                
                # Wait before next poll
                time.sleep(5)
            
            raise Exception(f"Actor run timed out after {wait_timeout} seconds")
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to scrape LinkedIn profile: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f"\nResponse details: {error_detail}"
                except:
                    error_msg += f"\nResponse text: {e.response.text}"
            raise Exception(error_msg) from e
    
    def scrape_linkedin_posts(self, profile_url: str, wait_timeout: int = 300) -> list:
        """
        Scrape LinkedIn profile posts using Apify actor.
        
        Args:
            profile_url: Full LinkedIn profile URL
            wait_timeout: Maximum time to wait for the actor to complete (seconds)
            
        Returns:
            List of posts data
            
        Raises:
            Exception: If API call fails or actor run fails
        """
        actor_id = LINKEDIN_POSTS_ACTOR.replace('/', '~')
        
        # Prepare the input payload
        payload = {
            "username": profile_url
        }
        
        try:
            # Start the actor run
            print("Starting Apify posts actor run...")
            run_response = requests.post(
                f"{self.base_url}/acts/{actor_id}/runs",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            run_response.raise_for_status()
            run_data = run_response.json()
            run_id = run_data['data']['id']
            
            print(f"Posts actor run started. Run ID: {run_id}")
            print("Waiting for posts actor to complete...")
            
            # Poll for completion
            start_time = time.time()
            while time.time() - start_time < wait_timeout:
                status_response = requests.get(
                    f"{self.base_url}/actor-runs/{run_id}",
                    headers=self.headers,
                    timeout=30
                )
                status_response.raise_for_status()
                status_data = status_response.json()
                status = status_data['data']['status']
                
                if status == 'SUCCEEDED':
                    print("Posts actor run completed successfully!")
                    # Get the dataset ID
                    dataset_id = status_data['data']['defaultDatasetId']
                    
                    # Fetch the results
                    items_response = requests.get(
                        f"{self.base_url}/datasets/{dataset_id}/items",
                        headers=self.headers,
                        timeout=30
                    )
                    items_response.raise_for_status()
                    items_data = items_response.json()
                    
                    # Handle different response structures
                    posts = None
                    if isinstance(items_data, dict):
                        if 'data' in items_data:
                            data = items_data['data']
                            if isinstance(data, list):
                                posts = data
                            elif isinstance(data, dict) and 'items' in data:
                                posts = data['items']
                            else:
                                posts = [data]
                        elif 'items' in items_data:
                            posts = items_data['items']
                        else:
                            posts = [items_data]
                    elif isinstance(items_data, list):
                        posts = items_data
                    
                    # Return list of posts
                    if posts:
                        return posts if isinstance(posts, list) else [posts]
                    else:
                        return []
                        
                elif status == 'FAILED':
                    error_msg = f"Posts actor run failed. Status: {status}"
                    if 'stats' in status_data['data']:
                        error_msg += f"\nStats: {status_data['data']['stats']}"
                    raise Exception(error_msg)
                
                # Wait before next poll
                time.sleep(5)
            
            raise Exception(f"Posts actor run timed out after {wait_timeout} seconds")
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to scrape LinkedIn posts: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f"\nResponse details: {error_detail}"
                except:
                    error_msg += f"\nResponse text: {e.response.text}"
            raise Exception(error_msg) from e
