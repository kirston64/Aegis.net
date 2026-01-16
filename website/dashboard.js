// Aegis.net Dashboard Logic

document.addEventListener('DOMContentLoaded', function () {
    // Initialize theme
    if (typeof initTheme === 'function') {
        initTheme();
    }

    // ========================
    // Sidebar Navigation
    // ========================
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    const sections = document.querySelectorAll('.dashboard-section');

    sidebarLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();

            const targetSection = link.getAttribute('data-section');

            // Update active link
            sidebarLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // Update active section
            sections.forEach(s => s.classList.remove('active'));
            const section = document.getElementById(`${targetSection}-section`);
            if (section) {
                section.classList.add('active');
            }

            // Update URL hash
            window.location.hash = targetSection;
        });
    });

    // Handle initial hash
    const hash = window.location.hash.substring(1);
    if (hash) {
        const link = document.querySelector(`[data-section="${hash}"]`);
        if (link) {
            link.click();
        }
    }

    // ========================
    // Simple Chart
    // ========================
    const chartCanvas = document.getElementById('trafficChart');
    if (chartCanvas) {
        drawSimpleChart(chartCanvas);
    }

    // ========================
    // Live Stats Animation
    // ========================
    animateStats();
});

// ========================
// API Key Copy Function
// ========================
window.copyApiKey = function () {
    const apiKey = document.getElementById('api-key');
    if (apiKey) {
        navigator.clipboard.writeText(apiKey.textContent).then(() => {
            // Show feedback
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = 'Скопировано!';
            btn.style.color = '#34a853';

            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.color = '';
            }, 2000);
        });
    }
};

// ========================
// Add Domain Modal (Placeholder)
// ========================
window.showAddDomainModal = function () {
    const domain = prompt('Введите домен для добавления:');
    if (domain) {
        alert(`Домен ${domain} будет добавлен после верификации DNS записей.`);
        // In real app, this would open a proper modal and make API call
    }
};

// ========================
// Simple Chart Drawing
// ========================
function drawSimpleChart(canvas) {
    const ctx = canvas.getContext('2d');
    const isDark = document.body.classList.contains('dark-theme');

    // Resize canvas
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;

    // Mock data for 7 days
    const labels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    const totalData = [145000, 178000, 192000, 168000, 215000, 201000, 245000];
    const blockedData = [1200, 1800, 2100, 1500, 2400, 1900, 3200];

    const maxValue = Math.max(...totalData);
    const padding = 40;
    const chartWidth = canvas.width - padding * 2;
    const chartHeight = canvas.height - padding * 2;

    // Colors
    const totalColor = '#1a73e8';
    const blockedColor = '#ea4335';
    const gridColor = isDark ? '#2a2a2a' : '#e8eaed';
    const textColor = isDark ? '#a0a0a0' : '#5f6368';

    // Draw grid
    ctx.strokeStyle = gridColor;
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
        const y = padding + (chartHeight / 5) * i;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(canvas.width - padding, y);
        ctx.stroke();
    }

    // Draw bars
    const barWidth = chartWidth / labels.length / 3;
    const groupWidth = chartWidth / labels.length;

    labels.forEach((label, index) => {
        const x = padding + groupWidth * index + groupWidth / 2;

        // Total bar
        const totalHeight = (totalData[index] / maxValue) * chartHeight;
        ctx.fillStyle = totalColor;
        ctx.fillRect(x - barWidth - 4, padding + chartHeight - totalHeight, barWidth, totalHeight);

        // Blocked bar
        const blockedHeight = (blockedData[index] / maxValue) * chartHeight;
        ctx.fillStyle = blockedColor;
        ctx.fillRect(x + 4, padding + chartHeight - blockedHeight, barWidth, blockedHeight);

        // Labels
        ctx.fillStyle = textColor;
        ctx.font = '12px Inter';
        ctx.textAlign = 'center';
        ctx.fillText(label, x, canvas.height - padding + 20);
    });

    // Draw values on Y axis
    ctx.fillStyle = textColor;
    ctx.font = '12px Inter';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 5; i++) {
        const value = Math.round((maxValue / 5) * (5 - i) / 1000) + 'K';
        const y = padding + (chartHeight / 5) * i;
        ctx.fillText(value, padding - 10, y + 4);
    }
}

// ========================
// Stats Animation
// ========================
function animateStats() {
    const statValues = document.querySelectorAll('.stat-value');

    statValues.forEach(stat => {
        const text = stat.textContent;
        // Only animate numbers
        if (/\d/.test(text) && !text.includes('%')) {
            const finalValue = text;
            stat.textContent = '0';

            setTimeout(() => {
                stat.textContent = finalValue;
            }, 300);
        }
    });
}

// ========================
// Real-time Updates (Mock)
// ========================
function updateStats() {
    const totalRequests = document.getElementById('total-requests');
    const blockedRequests = document.getElementById('blocked-requests');

    if (totalRequests && blockedRequests) {
        // Simulate real-time updates
        setInterval(() => {
            const currentTotal = parseInt(totalRequests.textContent.replace(/,/g, ''));
            const newTotal = currentTotal + Math.floor(Math.random() * 100);
            totalRequests.textContent = newTotal.toLocaleString();

            const currentBlocked = parseInt(blockedRequests.textContent.replace(/,/g, ''));
            const newBlocked = currentBlocked + Math.floor(Math.random() * 5);
            blockedRequests.textContent = newBlocked.toLocaleString();
        }, 5000);
    }
}

// Start real-time updates
setTimeout(updateStats, 2000);

// Redraw chart on theme change
const originalToggleTheme = window.toggleTheme;
if (originalToggleTheme) {
    window.toggleTheme = function () {
        originalToggleTheme();
        const chartCanvas = document.getElementById('trafficChart');
        if (chartCanvas) {
            setTimeout(() => drawSimpleChart(chartCanvas), 100);
        }
    };
}

console.log('📊 Dashboard loaded');
