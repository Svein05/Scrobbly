<h1 align="center">
  <br>
  <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Lastfm_logo.svg/2560px-Lastfm_logo.svg.png" alt="Last.fm Discord Bot" width="300">
  <br>
  Last.fm Discord Bot
  <br>
</h1>

<h4 align="center">Un bot de Discord avanzado y modular para integrar tu actividad musical de Last.fm directamente en tu servidor.</h4>

<p align="center">
  <a href="https://discordpy.readthedocs.io/en/stable/">
    <img src="https://img.shields.io/badge/discord.py-2.3+-blue.svg" alt="discord.py">
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python">
  </a>
  <a href="https://github.com/tu-usuario/lastfm-discord-bot/stargazers">
    <img src="https://img.shields.io/github/stars/tu-usuario/lastfm-discord-bot.svg?style=flat&color=red" alt="Stars">
  </a>
  <a href="https://github.com/tu-usuario/lastfm-discord-bot/network/members">
    <img src="https://img.shields.io/github/forks/tu-usuario/lastfm-discord-bot.svg?style=flat&color=red" alt="Forks">
  </a>
</p>

<p align="center">
  <a href="#características">Características</a> •
  <a href="#instalación">Instalación</a> •
  <a href="#uso">Uso</a> •
  <a href="#sitio-web">Sitio Web</a> •
  <a href="#contacto">Contacto</a>
</p>

---

## Características

- 🎵 **Integración Completa con Last.fm**: Conecta tu cuenta y visualiza tu actividad.
- ⚡ **Asíncrono y Rápido**: Desarrollado usando `discord.py`, `aiohttp` y `aiosqlite` para no bloquear el hilo principal.
- 📊 **Leaderboards Locales**: Compara tus *scrobbles* con otros miembros de tu servidor de Discord.
- 🛠️ **Arquitectura Modular**: Utiliza el sistema de Cogs de Discord.py, haciendo el código limpio y fácil de mantener.
- 🎨 **Respuestas Diferidas**: Manejo optimizado para evitar problemas con Rate Limits de la API.

## Instalación

Para ejecutar este bot localmente o en tu propio servidor, sigue estos pasos:

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/lastfm-discord-bot.git
cd lastfm-discord-bot
```

### 2. Entorno Virtual (Recomendado)

Crea y activa un entorno virtual en Python:

```bash
python -m venv .venv
# En Windows:
.venv\Scripts\activate
# En Linux/Mac:
source .venv/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto y añade tus credenciales (no incluyas comillas):

```env
DISCORD_TOKEN=tu_token_de_discord_aqui
LASTFM_API_KEY=tu_api_key_de_lastfm_aqui
```

> **Nota:** Puedes obtener tu API Key en el [portal para desarrolladores de Last.fm](https://www.last.fm/api/account/create).

### 5. Iniciar el Bot

```bash
python main.py
```

## Uso

Una vez que el bot esté en tu servidor, puedes usar los siguientes comandos de barra (Slash Commands):

- `/help` - Muestra la lista de comandos disponibles e información general.
- `/link <username>` - Vincula tu cuenta de Discord con tu usuario de Last.fm.
- `/np [user]` - Muestra la canción que estás escuchando actualmente (o la última que escuchaste). Puedes mencionar a otro usuario para ver su estado.
- `/linkcanal <channel>` - *(Solo administradores)* Configura el canal donde se publicarán los Leaderboards semanales/mensuales.

## Sitio Web

Este proyecto incluye una página web moderna para promocionar el bot, generada automáticamente vía **GitHub Pages**. 
Puedes visitar la [página de demostración aquí](https://tu-usuario.github.io/lastfm-discord-bot/).

## Contacto

- Únete a nuestro [Servidor de Soporte en Discord](#)
- Repórtanos cualquier problema abriendo un [Issue](https://github.com/tu-usuario/lastfm-discord-bot/issues).

---
<p align="center">Hecho con ❤️ para la comunidad de Discord y Last.fm</p>
