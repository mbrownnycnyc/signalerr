
import requests
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class OverseerrAPI:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-Api-Key': api_key,
            'Content-Type': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request to Overseerr API"""
        url = f"{self.base_url}/api/v1{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Overseerr API request failed: {method} {url} - {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test connection to Overseerr"""
        try:
            response = self._make_request('GET', '/status')
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Overseerr connection test failed: {e}")
            return False
    
    def search_media(self, query: str, media_type: str = None) -> List[Dict]:
        """Search for media in Overseerr"""
        try:
            params = {'query': query}
            if media_type:
                params['type'] = media_type
            
            response = self._make_request('GET', '/search', params=params)
            data = response.json()
            
            return data.get('results', [])
        except Exception as e:
            logger.error(f"Media search failed for '{query}': {e}")
            return []
    
    def get_media_details(self, media_type: str, media_id: int) -> Optional[Dict]:
        """Get detailed media information"""
        try:
            endpoint = f"/{media_type}/{media_id}"
            response = self._make_request('GET', endpoint)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get {media_type} details for ID {media_id}: {e}")
            return None
    
    def request_movie(self, movie_id: int, is_4k: bool = False) -> Tuple[bool, Optional[int], Optional[str]]:
        """Request a movie"""
        try:
            payload = {
                'mediaId': movie_id,
                'mediaType': 'movie',
                'is4k': is_4k
            }
            
            response = self._make_request('POST', '/request', json=payload)
            data = response.json()
            
            request_id = data.get('id')
            logger.info(f"Movie request created: ID {request_id} for movie {movie_id}")
            return True, request_id, None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                # Already requested
                return False, None, "This movie has already been requested"
            else:
                error_msg = f"Failed to request movie: {e}"
                logger.error(error_msg)
                return False, None, error_msg
        except Exception as e:
            error_msg = f"Failed to request movie {movie_id}: {e}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def request_tv_show(self, tv_id: int, seasons: List[int] = None, is_4k: bool = False) -> Tuple[bool, Optional[int], Optional[str]]:
        """Request a TV show"""
        try:
            payload = {
                'mediaId': tv_id,
                'mediaType': 'tv',
                'is4k': is_4k
            }
            
            if seasons:
                payload['seasons'] = seasons
            
            response = self._make_request('POST', '/request', json=payload)
            data = response.json()
            
            request_id = data.get('id')
            logger.info(f"TV show request created: ID {request_id} for show {tv_id}")
            return True, request_id, None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                # Already requested
                return False, None, "This TV show has already been requested"
            else:
                error_msg = f"Failed to request TV show: {e}"
                logger.error(error_msg)
                return False, None, error_msg
        except Exception as e:
            error_msg = f"Failed to request TV show {tv_id}: {e}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def get_request_status(self, request_id: int) -> Optional[Dict]:
        """Get status of a specific request"""
        try:
            response = self._make_request('GET', f'/request/{request_id}')
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get request status for ID {request_id}: {e}")
            return None
    
    def get_all_requests(self, take: int = 20, skip: int = 0, filter_status: str = None) -> List[Dict]:
        """Get all requests with pagination"""
        try:
            params = {'take': take, 'skip': skip}
            if filter_status:
                params['filter'] = filter_status
            
            response = self._make_request('GET', '/request', params=params)
            data = response.json()
            
            return data.get('results', [])
        except Exception as e:
            logger.error(f"Failed to get requests: {e}")
            return []
    
    def get_media_status(self, media_id: int) -> Optional[Dict]:
        """Get media availability status"""
        try:
            response = self._make_request('GET', f'/media/{media_id}/status')
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get media status for ID {media_id}: {e}")
            return None
    
    def approve_request(self, request_id: int) -> bool:
        """Approve a request (admin only)"""
        try:
            response = self._make_request('POST', f'/request/{request_id}/approve')
            logger.info(f"Request {request_id} approved")
            return True
        except Exception as e:
            logger.error(f"Failed to approve request {request_id}: {e}")
            return False
    
    def decline_request(self, request_id: int, reason: str = None) -> bool:
        """Decline a request (admin only)"""
        try:
            payload = {}
            if reason:
                payload['reason'] = reason
            
            response = self._make_request('POST', f'/request/{request_id}/decline', json=payload)
            logger.info(f"Request {request_id} declined")
            return True
        except Exception as e:
            logger.error(f"Failed to decline request {request_id}: {e}")
            return False
    
    def get_user_requests(self, user_id: int) -> List[Dict]:
        """Get requests for a specific user"""
        try:
            params = {'requestedBy': user_id}
            response = self._make_request('GET', '/request', params=params)
            data = response.json()
            
            return data.get('results', [])
        except Exception as e:
            logger.error(f"Failed to get user requests for user {user_id}: {e}")
            return []
    
    def parse_media_info(self, media_data: Dict) -> Dict:
        """Parse media information from search results"""
        media_type = media_data.get('mediaType', 'movie')
        
        parsed = {
            'id': media_data.get('id'),
            'title': media_data.get('title') or media_data.get('name'),
            'year': None,
            'overview': media_data.get('overview', ''),
            'poster_path': media_data.get('posterPath'),
            'media_type': media_type,
            'tmdb_id': media_data.get('id')
        }
        
        # Extract year from release date
        if media_type == 'movie':
            release_date = media_data.get('releaseDate')
            if release_date:
                parsed['year'] = int(release_date.split('-')[0])
        else:  # TV show
            first_air_date = media_data.get('firstAirDate')
            if first_air_date:
                parsed['year'] = int(first_air_date.split('-')[0])
        
        # TV show specific info
        if media_type == 'tv':
            parsed['seasons'] = media_data.get('numberOfSeasons', 0)
            parsed['episodes'] = media_data.get('numberOfEpisodes', 0)
        
        return parsed
    
    def get_request_status_text(self, status_code: int) -> str:
        """Convert Overseerr status code to readable text"""
        status_map = {
            1: "Pending Approval",
            2: "Approved",
            3: "Declined",
            4: "Processing",
            5: "Available"
        }
        return status_map.get(status_code, f"Unknown ({status_code})")
    
    def is_media_available(self, media_id: int) -> bool:
        """Check if media is already available"""
        try:
            status = self.get_media_status(media_id)
            if status:
                return status.get('status') == 5  # Available
            return False
        except Exception as e:
            logger.error(f"Failed to check media availability for {media_id}: {e}")
            return False
