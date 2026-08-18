# Guía para agregar comandos a la página web

Como me pediste, he dejado las secciones de comandos totalmente vacías en el código para que tú mismo añadas únicamente los comandos reales y precisos de tu bot.

Aquí te explico cómo rellenar cada sección:

---

## 1. Página Principal (Showcase de imágenes)
Abre el archivo `website/index.html` y busca el texto `PLANTILLA PARA AÑADIR DEMOSTRACIONES`.

Por cada imagen grande de un comando que quieras mostrar en la página principal, copia este bloque de código y pégalo justo debajo del comentario:

```html
<div class="showcase-item fade-in-scroll">
    <div class="showcase-content">
        <span class="showcase-tag">ETIQUETA (ej: Now Playing)</span>
        <h3>TÍTULO DEL COMANDO</h3>
        <p>Descripción detallada de lo que hace el comando y por qué es genial.</p>
    </div>
    <div class="showcase-image-wrapper">
        <img src="assets/NOMBRE_DE_TU_IMAGEN.png" alt="Descripción para lectores de pantalla">
    </div>
</div>
```

**Notas:**
- Asegúrate de poner tus imágenes dentro de la carpeta `website/assets/`.
- El diseño ya está programado en CSS para centrar la imagen automáticamente sin importar si es horizontal o vertical.

---

## 2. Página del Directorio de Comandos
Abre el archivo `website/commands.html` y busca el texto `PLANTILLA PARA AÑADIR COMANDOS A LA LISTA`.

Por cada comando que quieras listar (para que la gente pueda buscarlo), copia este bloque de código y pégalo dentro de `<div class="commands-grid" id="commandsGrid">`:

```html
<div class="command-card" data-name="NOMBRE_COMANDO" data-desc="PALABRAS CLAVE PARA EL BUSCADOR">
    <div class="command-header">
        <span class="command-name">/NOMBRE_COMANDO</span>
        <div class="command-tags">
            <span class="tag tag-user">Usuario</span>
            <!-- Otras etiquetas disponibles: 
                 <span class="tag tag-admin">Admin</span>
                 <span class="tag tag-music">Música</span>
            -->
        </div>
    </div>
    <p class="command-desc">Descripción corta y directa del comando.</p>
    <div class="command-usage">
        Uso: <span>/NOMBRE_COMANDO [argumento1] [argumento2]</span>
    </div>
</div>
```

**Explicación de variables:**
- `data-name`: Pon aquí el nombre del comando (ej: `nowplaying np`). El buscador usa esto.
- `data-desc`: Pon aquí palabras clave para que el buscador las encuentre (ej: `reproduce musica cancion actual`).
- `command-tags`: Borra o añade las etiquetas que correspondan según el tipo de comando.

---

Una vez que guardes los cambios en tus archivos HTML, las secciones se poblarán automáticamente y el buscador de JavaScript seguirá funcionando a la perfección con tus nuevos datos.
