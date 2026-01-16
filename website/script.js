// Aegis.net — Particles Animation & Logic

// ========================
// Theme Toggle
// ========================
function initTheme() {
    const savedTheme = localStorage.getItem('aegis-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.body.classList.add('dark-theme');
    }
}

window.toggleTheme = function () {
    document.body.classList.toggle('dark-theme');
    const isDark = document.body.classList.contains('dark-theme');
    localStorage.setItem('aegis-theme', isDark ? 'dark' : 'light');

    // Update particles color scheme
    updateParticleColors();
};

// ========================
// Mobile Menu Toggle
// ========================
window.toggleMobileMenu = function () {
    const navLinks = document.querySelector('.nav-links');
    const mobileToggle = document.querySelector('.mobile-menu-toggle');

    if (navLinks) {
        navLinks.classList.toggle('active');
    }
    if (mobileToggle) {
        mobileToggle.classList.toggle('active');
    }

    // Prevent body scroll when menu is open
    if (navLinks && navLinks.classList.contains('active')) {
        document.body.style.overflow = 'hidden';
    } else {
        document.body.style.overflow = '';
    }
};

// ========================
// Global Auth Functions
// ========================
window.openModal = function (mode) {
    const modal = document.getElementById('authModal');
    const title = document.getElementById('modalTitle');
    const subtitle = document.getElementById('modalSubtitle');
    const footerText = document.getElementById('modalFooterText');
    const formBtn = document.querySelector('.modal-content .btn-primary');

    if (!modal) return;

    modal.classList.add('active');
    document.body.style.overflow = 'hidden'; // Prevent scrolling

    // Reset button state
    if (formBtn) {
        formBtn.disabled = false;
        formBtn.style.opacity = '1';
        formBtn.style.cursor = 'pointer';
    }

    if (mode === 'register') {
        title.textContent = 'Создание аккаунта';
        subtitle.textContent = 'Начните использовать защиту бесплатно';
        if (formBtn) formBtn.textContent = 'Создать аккаунт';
        footerText.innerHTML = 'Уже есть аккаунт? <a href="#" onclick="switchModalMode(event)">Войти</a>';
    } else {
        title.textContent = 'Вход в систему';
        subtitle.textContent = 'Управляйте защитой своих проектов';
        if (formBtn) formBtn.textContent = 'Войти';
        footerText.innerHTML = 'Нет аккаунта? <a href="#" onclick="switchModalMode(event)">Регистрация</a>';
    }
};

window.closeModal = function () {
    const modal = document.getElementById('authModal');
    if (modal) modal.classList.remove('active');
    document.body.style.overflow = '';
};

window.switchModalMode = function (e) {
    if (e) e.preventDefault();
    const title = document.getElementById('modalTitle');
    title.textContent.includes('Вход') ? openModal('register') : openModal('login');
};

// Enhanced form validation
function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function showFieldError(input, message) {
    input.style.borderColor = '#ea4335';
    let error = input.parentElement.querySelector('.error-message');
    if (!error) {
        error = document.createElement('span');
        error.className = 'error-message';
        error.style.color = '#ea4335';
        error.style.fontSize = '0.75rem';
        error.style.marginTop = '0.25rem';
        error.style.display = 'block';
        input.parentElement.appendChild(error);
    }
    error.textContent = message;
}

function clearFieldError(input) {
    input.style.borderColor = '';
    const error = input.parentElement.querySelector('.error-message');
    if (error) error.remove();
}

window.handleLogin = function (e) {
    e.preventDefault();
    const form = e.target;
    const emailInput = form.querySelector('input[type="email"]');
    const passwordInput = form.querySelector('input[type="password"]');
    const btn = form.querySelector('button[type="submit"]') || form.querySelector('.btn-primary');

    // Clear previous errors
    clearFieldError(emailInput);
    clearFieldError(passwordInput);

    // Validate
    let hasError = false;
    if (!validateEmail(emailInput.value)) {
        showFieldError(emailInput, 'Введите корректный email');
        hasError = true;
    }
    if (passwordInput.value.length < 6) {
        showFieldError(passwordInput, 'Пароль должен содержать минимум 6 символов');
        hasError = true;
    }

    if (hasError) return;

    if (btn) {
        const originalText = btn.textContent;
        btn.textContent = 'Загрузка...';
        btn.disabled = true;
        btn.style.opacity = '0.7';
        btn.style.cursor = 'not-allowed';
    }

    // Simulate API call
    setTimeout(() => {
        // In a real app, verify credentials here
        // For demo, redirect to dashboard
        window.location.href = 'dashboard.html';

        if (btn) {
            btn.textContent = 'Успешно!';
        }
    }, 1500);
};

document.addEventListener('DOMContentLoaded', function () {
    // Initialize theme
    initTheme();

    // ========================
    // Particles Configuration
    // ========================
    const canvas = document.getElementById('particles');
    if (!canvas) return; // Guard clause

    const ctx = canvas.getContext('2d');
    let particles = [];
    const particleCount = 80;

    let colors = [
        '#4285f4', // Google Blue
        '#4285f4',
        '#1a73e8',
        '#ea4335', // Red
        '#5f6368'  // Gray
    ];

    // Update colors based on theme
    window.updateParticleColors = function () {
        const isDark = document.body.classList.contains('dark-theme');
        colors = isDark ? [
            '#4c9aff',
            '#6bb0ff',
            '#4c9aff',
            '#ff6b6b',
            '#a0a0a0'
        ] : [
            '#4285f4',
            '#4285f4',
            '#1a73e8',
            '#ea4335',
            '#5f6368'
        ];

        // Update existing particles
        particles.forEach(p => {
            p.color = colors[Math.floor(Math.random() * colors.length)];
        });
    };

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // ========================
    // Event Listeners
    // ========================
    // Close on backdrop click
    const modal = document.getElementById('authModal');
    if (modal) {
        modal.addEventListener('click', e => {
            if (e.target.id === 'authModal') closeModal();
        });
    }

    // Attach form handler (fallback if inline fails)
    const form = document.querySelector('.modal-content form');
    if (form) {
        form.onsubmit = window.handleLogin;
    }

    // ========================
    // Scroll Animations
    // ========================
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, observerOptions);

    // Observe elements
    document.querySelectorAll('.feature-card, .game-card, .pricing-card, .hero-content').forEach(el => {
        el.classList.add('animate-on-scroll');
        observer.observe(el);
    });

    // ========================
    // Interactive Particles
    // ========================
    let mouse = { x: null, y: null, radius: 120 };

    window.addEventListener('mousemove', function (e) {
        mouse.x = e.x;
        mouse.y = e.y;
    });

    // Particle class
    class Particle {
        constructor() {
            this.reset();
        }

        reset() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 3 + 1;
            this.baseX = this.x;
            this.baseY = this.y;
            this.density = (Math.random() * 30) + 1;
            this.speedX = (Math.random() - 0.5) * 0.5;
            this.speedY = (Math.random() - 0.5) * 0.5;
            this.color = colors[Math.floor(Math.random() * colors.length)];
            this.opacity = Math.random() * 0.5 + 0.3;
            // Removed rotation for simplicity in interaction
            this.shape = Math.floor(Math.random() * 3);
        }

        update() {
            // Mouse interaction
            let dx = mouse.x - this.x;
            let dy = mouse.y - this.y;
            let distance = Math.sqrt(dx * dx + dy * dy);
            let forceDirectionX = dx / distance;
            let forceDirectionY = dy / distance;
            let maxDistance = mouse.radius;
            let force = (maxDistance - distance) / maxDistance;
            let directionX = forceDirectionX * force * this.density;
            let directionY = forceDirectionY * force * this.density;

            if (distance < mouse.radius) {
                this.x -= directionX;
                this.y -= directionY;
            } else {
                // Return to normal movement
                if (this.x !== this.baseX) {
                    let dx = this.x - this.baseX;
                    this.x -= dx / 50;
                }
                if (this.y !== this.baseY) {
                    let dy = this.y - this.baseY;
                    this.y -= dy / 50;
                }

                // Drift
                this.x += this.speedX;
                this.y += this.speedY;

                // Update base position for drift
                this.baseX += this.speedX;
                this.baseY += this.speedY;
            }

            // Wrap around screen
            if (this.baseX < -20) { this.x = canvas.width + 20; this.baseX = this.x; }
            if (this.baseX > canvas.width + 20) { this.x = -20; this.baseX = this.x; }
            if (this.baseY < -20) { this.y = canvas.height + 20; this.baseY = this.y; }
            if (this.baseY > canvas.height + 20) { this.y = -20; this.baseY = this.y; }
        }

        draw() {
            ctx.save();
            ctx.translate(this.x, this.y);
            ctx.globalAlpha = this.opacity;
            ctx.fillStyle = this.color;
            ctx.strokeStyle = this.color;

            switch (this.shape) {
                case 0: // Small dot
                    ctx.beginPath();
                    ctx.arc(0, 0, this.size, 0, Math.PI * 2);
                    ctx.fill();
                    break;
                case 1: // Line/dash
                case 2: // Simplified to dot for performance
                    ctx.beginPath();
                    ctx.arc(0, 0, this.size, 0, Math.PI * 2);
                    ctx.fill();
                    break;
            }
            ctx.restore();
        }
    }

    // Initialize particles
    function initParticles() {
        particles = [];
        for (let i = 0; i < particleCount; i++) {
            particles.push(new Particle());
        }
    }

    // Animation loop
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        particles.forEach(particle => {
            particle.update();
            particle.draw();
        });

        requestAnimationFrame(animate);
    }

    initParticles();
    animate();

    console.log('🛡️ Aegis.net loaded');
});
