document.addEventListener('DOMContentLoaded', () => {
    
    // --- 1. Commands Page: Search Functionality ---
    const searchInput = document.getElementById('searchInput');
    const commandsGrid = document.getElementById('commandsGrid');
    const noResults = document.getElementById('noResults');

    if (searchInput && commandsGrid) {
        const commandCards = Array.from(commandsGrid.getElementsByClassName('command-card'));

        searchInput.addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase().trim();
            let visibleCount = 0;

            commandCards.forEach(card => {
                const name = card.getAttribute('data-name') || "";
                const desc = card.getAttribute('data-desc') || "";
                
                if (name.includes(term) || desc.includes(term)) {
                    card.style.display = 'flex';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            });

            if (visibleCount === 0) {
                noResults.classList.remove('hidden');
                commandsGrid.classList.add('hidden');
            } else {
                noResults.classList.add('hidden');
                commandsGrid.classList.remove('hidden');
            }
        });
    }

    // --- 2. Home Page: Fetch Live Stats ---
    const statsContainer = document.getElementById('stats-container');
    
    if (statsContainer) {
        const elServers = document.getElementById('stat-servers');
        const elUsers = document.getElementById('stat-users');

        async function fetchBotStats() {
            try {
                // Obtenemos el archivo stats.json generado por el bot
                const response = await fetch('stats.json');
                
                if (!response.ok) {
                    throw new Error('No se encontró stats.json o hubo un error al cargar');
                }
                
                const data = await response.json();

                // Animamos los valores usando los datos reales
                animateValue(elServers, 0, data.servers || 0, 1000);
                animateValue(elUsers, 0, data.users || 0, 1000);

            } catch (error) {
                console.warn('Error con las stats (usando mock de respaldo):', error);
                // Fallback de demostración si stats.json aún no se ha generado
                animateValue(elServers, 0, 150, 1000);
                animateValue(elUsers, 0, 3200, 1000);
            }
        }

        fetchBotStats();
    }

    // --- Utility: Animate Number Counting ---
    function animateValue(obj, start, end, duration) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const easeProgress = progress * (2 - progress); 
            obj.innerHTML = Math.floor(easeProgress * (end - start) + start).toLocaleString();
            if (progress < 1) {
                window.requestAnimationFrame(step);
            } else {
                obj.innerHTML = end.toLocaleString() + "+";
            }
        };
        window.requestAnimationFrame(step);
    }
    
    // --- 3. Scroll Animations (Intersection Observer) ---
    const scrollElements = document.querySelectorAll('.fade-in-scroll');
    
    const elementInView = (el, dividend = 1) => {
        const elementTop = el.getBoundingClientRect().top;
        return (elementTop <= (window.innerHeight || document.documentElement.clientHeight) / dividend);
    };

    const displayScrollElement = (element) => {
        element.classList.add('fade-in');
        element.classList.remove('fade-in-scroll'); 
    };

    const handleScrollAnimation = () => {
        scrollElements.forEach((el) => {
            if (elementInView(el, 1.15)) {
                displayScrollElement(el);
            }
        })
    }

    handleScrollAnimation();
    window.addEventListener('scroll', () => {
        handleScrollAnimation();
    });

    // --- 4. Fetch GitHub Contributors ---
    const contributorsContainer = document.querySelector('.contributors');
    if (contributorsContainer) {
        async function fetchContributors() {
            try {
                // Llamada a la API de GitHub para obtener los contribuidores del repositorio
                const response = await fetch('https://api.github.com/repos/Svein05/Scrobbly/contributors');
                if (!response.ok) throw new Error('No se pudieron obtener los contribuidores');
                
                const contributors = await response.json();
                
                // Limpiar los placeholders
                contributorsContainer.innerHTML = '';
                
                // Crear un elemento por cada contribuidor
                contributors.forEach(user => {
                    const div = document.createElement('div');
                    div.className = 'contributor';
                    div.innerHTML = `
                        <a href="${user.html_url}" target="_blank" rel="noopener noreferrer" style="text-decoration: none;">
                            <img src="${user.avatar_url}" alt="${user.login}" title="${user.login}">
                        </a>
                        <span class="contributor-name">${user.login}</span>
                    `;
                    contributorsContainer.appendChild(div);
                });
            } catch (error) {
                console.warn('No se pudieron cargar los contribuidores:', error);
                // Si falla, dejamos el HTML por defecto o un mensaje
            }
        }
        
        fetchContributors();
    }
});
