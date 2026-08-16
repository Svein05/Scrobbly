import aiohttp
from typing import Optional, Dict, Any
from config import config

class LastFMError(Exception):
    pass

class LastFMClient:
    BASE_URL = "http://ws.audioscrobbler.com/2.0/"
    
    def __init__(self):
        self.api_key = config.lastfm_api_key

    async def _request(self, method: str, **params) -> Dict[str, Any]:
        params['method'] = method
        params['api_key'] = self.api_key
        params['format'] = 'json'
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.BASE_URL, params=params) as response:
                if response.status != 200:
                    raise LastFMError(f"Error de la API HTTP: {response.status}")
                
                data = await response.json()
                if 'error' in data:
                    raise LastFMError(f"Error de Last.fm: {data.get('message', 'Desconocido')}")
                
                return data

    async def get_user_info(self, username: str) -> Dict[str, Any]:
        """Obtiene la información general del usuario (scrobbles totales, etc)."""
        data = await self._request('user.getinfo', user=username)
        return data.get('user', {})

    async def get_recent_tracks(self, username: str, limit: int = 1) -> list[Dict[str, Any]]:
        """Obtiene las canciones más recientes escuchadas por el usuario."""
        data = await self._request('user.getrecenttracks', user=username, limit=limit)
        tracks = data.get('recenttracks', {}).get('track', [])
        
        if isinstance(tracks, dict):
            return [tracks]
        return tracks
