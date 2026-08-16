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

    // Simple interaction for the mockup bot message
    const botMessage = document.querySelector('.message.bot');
    if (botMessage) {
        botMessage.style.opacity = '0';
        botMessage.style.transform = 'translateY(10px)';
        botMessage.style.transition = 'all 0.5s ease-out';
        
        setTimeout(() => {
            botMessage.style.opacity = '1';
            botMessage.style.transform = 'translateY(0)';
        }, 1000);
    }
});
