import hashlib
import aiohttp
from typing import Optional, Dict, Any, List
from config import config

class LastFMError(Exception):
    pass

class LastFMClient:
    BASE_URL = "http://ws.audioscrobbler.com/2.0/"
    
    def __init__(self):
        self.api_key = config.lastfm_api_key
        self.api_secret = config.lastfm_api_secret

    def _create_signature(self, params: Dict[str, Any]) -> str:
        """
        Genera la firma api_sig requerida por Last.fm para peticiones autenticadas:
        MD5(param1value1param2value2...api_secret) ordenado alfabéticamente por clave.
        Los parámetros 'format' y 'callback' NO se incluyen en la firma.
        """
        if not self.api_secret:
            raise LastFMError("Falta configurar 'lastfm_api_secret' en el archivo .env.")
            
        filtered_params = {k: v for k, v in params.items() if k not in ('format', 'callback') and v is not None}
        sorted_keys = sorted(filtered_params.keys())
        
        signature_base = "".join(f"{k}{filtered_params[k]}" for k in sorted_keys)
        signature_base += self.api_secret
        
        return hashlib.md5(signature_base.encode('utf-8')).hexdigest()

    async def _request(self, method: str, is_post: bool = False, signed: bool = False, **params) -> Dict[str, Any]:
        params['method'] = method
        params['api_key'] = self.api_key
        
        if signed:
            params['api_sig'] = self._create_signature(params)
            
        params['format'] = 'json'
        
        # Eliminar valores None
        clean_params = {k: str(v) for k, v in params.items() if v is not None}
        
        async with aiohttp.ClientSession() as session:
            if is_post:
                async with session.post(self.BASE_URL, data=clean_params) as response:
                    return await self._handle_response(response)
            else:
                async with session.get(self.BASE_URL, params=clean_params) as response:
                    return await self._handle_response(response)

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        if response.status != 200:
            try:
                data = await response.json()
                msg = data.get('message', f'HTTP {response.status}')
                raise LastFMError(f"Error de Last.fm ({response.status}): {msg}")
            except aiohttp.ContentTypeError:
                text = await response.text()
                raise LastFMError(f"Error HTTP {response.status}: {text[:150]}")
                
        data = await response.json()
        if 'error' in data:
            raise LastFMError(f"Error de Last.fm ({data.get('error')}): {data.get('message', 'Desconocido')}")
            
        return data

    # --- Consultas Públicas ---
    async def get_user_info(self, username: str) -> Dict[str, Any]:
        """Obtiene la información general del usuario (scrobbles totales, etc)."""
        data = await self._request('user.getinfo', user=username)
        return data.get('user', {})

    async def get_recent_tracks(self, username: str, limit: int = 1) -> List[Dict[str, Any]]:
        """Obtiene las canciones más recientes escuchadas por el usuario."""
        data = await self._request('user.getrecenttracks', user=username, limit=limit)
        tracks = data.get('recenttracks', {}).get('track', [])
        
        if isinstance(tracks, dict):
            return [tracks]
        return tracks

    # --- Flujo de Autenticación Web (OAuth / Session Key) ---
    async def get_auth_token(self) -> str:
        """Solicita un token temporal para el flujo de autorización web de Last.fm."""
        data = await self._request('auth.getToken', signed=True)
        return data.get('token', '')

    def get_auth_url(self, token: str) -> str:
        """Genera la URL oficial de Last.fm donde el usuario autoriza la aplicación con 1 clic."""
        return f"https://www.last.fm/api/auth/?api_key={self.api_key}&token={token}"

    async def get_session(self, token: str) -> Dict[str, str]:
        """
        Intercambia el token aprobado por el usuario por un Session Key (sk) permanente.
        Retorna: {'name': 'username', 'key': 'session_key'}
        """
        data = await self._request('auth.getSession', is_post=False, signed=True, token=token)
        session = data.get('session', {})
        return {
            'name': session.get('name', ''),
            'key': session.get('key', '')
        }

    # --- Scrobbling y Now Playing (Requiere Session Key) ---
    async def update_now_playing(self, artist: str, track: str, session_key: str, album: Optional[str] = None, duration: Optional[int] = None) -> Dict[str, Any]:
        """Actualiza el estado 'Now Playing' en Last.fm para el usuario dueño del session_key."""
        params = {
            'artist': artist,
            'track': track,
            'sk': session_key
        }
        if album:
            params['album'] = album
        if duration:
            params['duration'] = duration
            
        return await self._request('track.updateNowPlaying', is_post=True, signed=True, **params)

    async def scrobble(self, artist: str, track: str, timestamp: int, session_key: str, album: Optional[str] = None) -> Dict[str, Any]:
        """Envía un scrobble oficial a Last.fm registrado con la fecha y hora proporcionada."""
        params = {
            'artist': artist,
            'track': track,
            'timestamp': timestamp,
            'sk': session_key
        }
        if album:
            params['album'] = album
            
        return await self._request('track.scrobble', is_post=True, signed=True, **params)

