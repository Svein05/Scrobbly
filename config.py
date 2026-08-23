from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    discord_token: str = "TU_DISCORD_TOKEN_AQUI"
    lastfm_api_key: str = "TU_LASTFM_API_KEY_AQUI"
    lastfm_api_secret: str = "" # Requerido para Auth Web y Scrobbling firmado
    
    # Configuración de Lavalink (Audio Node)
    lavalink_uri: str = "http://127.0.0.1:2333"
    lavalink_password: str = "youshallnotpass"
    lavalink_secure: bool = False
    
    # Configuramos Pydantic para leer desde .env ignorando mayúsculas/minúsculas
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

# Instancia global de configuración
config = Settings()
