// Aegis.net — Particles Animation (Google Antigravity Style)

document.addEventListener('DOMContentLoaded', function () {
    // ========================
    // Particles Animation
    // ========================
    const canvas = document.getElementById('particles');
    const ctx = canvas.getContext('2d');

    let particles = [];
    const particleCount = 80;

    // Particle colors (blue and red accents like in Antigravity)
    const colors = [
        '#4285f4', // Google Blue
        '#4285f4',
        '#4285f4',
        '#1a73e8', // Darker blue
        '#ea4335', // Google Red (less frequent)
        '#5f6368', // Gray
    ];

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Particle class
    class Particle {
        constructor() {
            this.reset();
        }

        reset() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 3 + 1;
            this.speedX = (Math.random() - 0.5) * 0.5;
            this.speedY = (Math.random() - 0.5) * 0.5;
            this.color = colors[Math.floor(Math.random() * colors.length)];
            this.opacity = Math.random() * 0.5 + 0.3;
            this.rotation = Math.random() * 360;
            this.rotationSpeed = (Math.random() - 0.5) * 2;

            // Shape: 0 = circle, 1 = line, 2 = dot cluster
            this.shape = Math.floor(Math.random() * 3);
        }

        update() {
            this.x += this.speedX;
            this.y += this.speedY;
            this.rotation += this.rotationSpeed;

            // Wrap around screen
            if (this.x < -20) this.x = canvas.width + 20;
            if (this.x > canvas.width + 20) this.x = -20;
            if (this.y < -20) this.y = canvas.height + 20;
            if (this.y > canvas.height + 20) this.y = -20;
        }

        draw() {
            ctx.save();
            ctx.translate(this.x, this.y);
            ctx.rotate((this.rotation * Math.PI) / 180);
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
                    ctx.lineWidth = 1.5;
                    ctx.beginPath();
                    ctx.moveTo(-this.size * 2, 0);
                    ctx.lineTo(this.size * 2, 0);
                    ctx.stroke();
                    break;

                case 2: // Dot cluster (like confetti)
                    ctx.beginPath();
                    ctx.arc(0, 0, this.size * 0.7, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.beginPath();
                    ctx.arc(this.size * 1.5, this.size, this.size * 0.5, 0, Math.PI * 2);
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

    // ========================
    // Navigation
    // ========================
    const navbar = document.querySelector('.navbar');

    window.addEventListener('scroll', function () {
        if (window.scrollY > 50) {
            navbar.style.borderBottom = '1px solid #e8eaed';
        } else {
            navbar.style.borderBottom = 'none';
        }
    });

    // ========================
    // Smooth scroll
    // ========================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // ========================
    // Scroll animations
    // ========================
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Observe elements
    document.querySelectorAll('.feature-card, .game-card, .pricing-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        observer.observe(el);
    });

    console.log('🛡️ Aegis.net loaded');
});
