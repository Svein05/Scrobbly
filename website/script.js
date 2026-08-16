document.addEventListener('DOMContentLoaded', () => {
    // Smooth scrolling for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Sistema de mockup dinámico
    const mockupBody = document.querySelector('.mockup-body');
    const mockupContainer = document.querySelector('.mockup');
    
    if (mockupBody && mockupContainer) {
        const mockups = [
            {
                userCommand: '/np',
                botHtml: `
                    <div class="embed">
                        <div class="embed-author">
                            <img src="https://ui-avatars.com/api/?name=User&background=random" alt="User">
                            <span>User - Escuchando ahora</span>
                        </div>
                        <div class="embed-title">Bohemian Rhapsody</div>
                        <div class="embed-desc">
                            <strong>Queen</strong><br>
                            <em>A Night At The Opera</em>
                        </div>
                        <div class="embed-footer">Total Scrobbles: 15,420</div>
                    </div>
                `
            },
            {
                userCommand: '/link xSvein',
                botHtml: `
                    <div style="color: #dcddde; font-size: 14px;">✅ ¡Cuenta vinculada exitosamente a **xSvein**!</div>
                `
            },
            {
                userCommand: '/linkcanal #leaderboard',
                botHtml: `
                    <div style="color: #dcddde; font-size: 14px;">✅ El canal <span style="color: #c9cdfb; background: rgba(88, 101, 242, 0.3); padding: 2px 4px; border-radius: 3px;">#leaderboard</span> ha sido configurado. El Leaderboard se actualizará automáticamente allí.</div>
                `
            }
        ];

        let currentIndex = 0;
        let isHovered = false;

        mockupContainer.addEventListener('mouseenter', () => isHovered = true);
        mockupContainer.addEventListener('mouseleave', () => isHovered = false);

        function updateMockup() {
            if (isHovered) return;

            currentIndex = (currentIndex + 1) % mockups.length;
            const currentMockup = mockups[currentIndex];
            
            mockupBody.style.opacity = '0';
            
            setTimeout(() => {
                mockupBody.innerHTML = `
                    <div class="message">
                        <img src="https://ui-avatars.com/api/?name=User&background=random" alt="Avatar" class="avatar">
                        <div class="message-content">
                            <span class="username">Usuario</span> <span class="timestamp">Hoy a las 14:30</span>
                            <p>${currentMockup.userCommand}</p>
                        </div>
                    </div>
                    <div class="message bot">
                        <img src="https://ui-avatars.com/api/?name=Bot&background=d51007&color=fff" alt="Bot Avatar" class="avatar bot-avatar">
                        <div class="message-content">
                            <span class="username bot-name">Scrobbly <span class="bot-tag">BOT</span></span> <span class="timestamp">Hoy a las 14:30</span>
                            ${currentMockup.botHtml}
                        </div>
                    </div>
                `;
                mockupBody.style.opacity = '1';
            }, 300);
        }

        mockupBody.style.transition = 'opacity 0.3s ease';
        setInterval(updateMockup, 2500); // Cambia cada 2.5 segundos
    }
});
