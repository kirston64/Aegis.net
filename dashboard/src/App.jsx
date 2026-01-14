import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import {
    Shield,
    Globe,
    BarChart3,
    Settings,
    AlertTriangle,
    Plus,
    ArrowUp,
    ArrowDown,
    Activity
} from 'lucide-react'
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    AreaChart,
    Area
} from 'recharts'

// Mock data for demo
const mockTrafficData = Array.from({ length: 24 }, (_, i) => ({
    time: `${i}:00`,
    legitimate: Math.floor(10000 + Math.random() * 5000),
    blocked: Math.floor(500 + Math.random() * 2000),
    challenged: Math.floor(200 + Math.random() * 800),
}))

const mockDomains = [
    { id: '1', domain: 'game-server.ru', status: 'active', level: 1, rps: 1250 },
    { id: '2', domain: 'minecraft.example.com', status: 'active', level: 0, rps: 450 },
    { id: '3', domain: 'api.myapp.io', status: 'warning', level: 2, rps: 3200 },
]

// Sidebar Component
function Sidebar() {
    const location = useLocation()
    const isActive = (path) => location.pathname === path ? 'nav-link active' : 'nav-link'

    return (
        <aside className="sidebar">
            <div className="logo">
                <span className="logo-icon">🛡️</span>
                <span>Aegis<span className="logo-accent">.net</span></span>
            </div>

            <nav className="nav-section">
                <h3 className="nav-title">Main</h3>
                <ul className="nav-links">
                    <li>
                        <Link to="/" className={isActive('/')}>
                            <BarChart3 size={18} />
                            <span>Dashboard</span>
                        </Link>
                    </li>
                    <li>
                        <Link to="/domains" className={isActive('/domains')}>
                            <Globe size={18} />
                            <span>Domains</span>
                        </Link>
                    </li>
                    <li>
                        <Link to="/attack-mode" className={isActive('/attack-mode')}>
                            <Shield size={18} />
                            <span>Smart Shield</span>
                        </Link>
                    </li>
                </ul>
            </nav>

            <nav className="nav-section">
                <h3 className="nav-title">System</h3>
                <ul className="nav-links">
                    <li>
                        <Link to="/logs" className={isActive('/logs')}>
                            <Activity size={18} />
                            <span>Logs</span>
                        </Link>
                    </li>
                    <li>
                        <Link to="/settings" className={isActive('/settings')}>
                            <Settings size={18} />
                            <span>Settings</span>
                        </Link>
                    </li>
                </ul>
            </nav>
        </aside>
    )
}

// Dashboard Page
function DashboardPage() {
    const [stats, setStats] = useState({
        totalRequests: '1.2M',
        blockedRequests: '45.2K',
        activeAttacks: 0,
        protectedDomains: 3,
    })

    return (
        <div>
            <div className="page-header">
                <h1 className="page-title">Dashboard</h1>
                <button className="btn btn-primary">
                    <Plus size={16} />
                    Add Domain
                </button>
            </div>

            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-label">Total Requests (24h)</div>
                    <div className="stat-value">{stats.totalRequests}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Blocked Requests</div>
                    <div className="stat-value warning">{stats.blockedRequests}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Active Attacks</div>
                    <div className="stat-value success">{stats.activeAttacks}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">Protected Domains</div>
                    <div className="stat-value">{stats.protectedDomains}</div>
                </div>
            </div>

            <div className="card">
                <div className="card-header">
                    <h2 className="card-title">Traffic Overview</h2>
                </div>
                <div className="chart-container">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={mockTrafficData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
                            <XAxis dataKey="time" stroke="#71717a" />
                            <YAxis stroke="#71717a" />
                            <Tooltip
                                contentStyle={{
                                    background: '#16161f',
                                    border: '1px solid #2a2a3a',
                                    borderRadius: '8px'
                                }}
                            />
                            <Area
                                type="monotone"
                                dataKey="legitimate"
                                stackId="1"
                                stroke="#22c55e"
                                fill="#22c55e"
                                fillOpacity={0.3}
                                name="Legitimate"
                            />
                            <Area
                                type="monotone"
                                dataKey="challenged"
                                stackId="1"
                                stroke="#f59e0b"
                                fill="#f59e0b"
                                fillOpacity={0.3}
                                name="Challenged"
                            />
                            <Area
                                type="monotone"
                                dataKey="blocked"
                                stackId="1"
                                stroke="#ef4444"
                                fill="#ef4444"
                                fillOpacity={0.3}
                                name="Blocked"
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div className="card">
                <div className="card-header">
                    <h2 className="card-title">Protected Domains</h2>
                </div>
                <ul className="domain-list">
                    {mockDomains.map(d => (
                        <li key={d.id} className="domain-item">
                            <div>
                                <div className="domain-name">{d.domain}</div>
                                <div className="domain-status">
                                    <span className={`status-dot ${d.status}`}></span>
                                    <span>{d.rps.toLocaleString()} req/s</span>
                                </div>
                            </div>
                            <div>
                                <span style={{
                                    padding: '0.25rem 0.75rem',
                                    background: 'rgba(99, 102, 241, 0.1)',
                                    borderRadius: '9999px',
                                    fontSize: '0.75rem',
                                    fontWeight: 600,
                                    color: '#6366f1'
                                }}>
                                    Level {d.level}
                                </span>
                            </div>
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    )
}

// Attack Mode Page
function AttackModePage() {
    const [level, setLevel] = useState(1)
    const levels = ['Observe', 'Soft', 'Medium', 'Hard', 'Lockdown']
    const levelColors = ['#22c55e', '#0ea5e9', '#f59e0b', '#f97316', '#ef4444']

    return (
        <div>
            <div className="page-header">
                <h1 className="page-title">Smart Shield Control</h1>
            </div>

            <div className="card">
                <div className="card-header">
                    <h2 className="card-title">🛡️ Current Protection Level</h2>
                    <span style={{ color: levelColors[level], fontWeight: 600 }}>
                        {levels[level]}
                    </span>
                </div>

                <div className="shield-level">
                    <div className="level-bar">
                        <div
                            className="level-fill"
                            style={{ width: `${(level + 1) * 20}%` }}
                        ></div>
                    </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
                    {levels.map((name, i) => (
                        <button
                            key={i}
                            onClick={() => setLevel(i)}
                            style={{
                                padding: '0.5rem 1rem',
                                background: level === i ? levelColors[i] : 'transparent',
                                border: `1px solid ${level === i ? levelColors[i] : '#2a2a3a'}`,
                                borderRadius: '0.5rem',
                                color: level === i ? 'white' : '#a1a1aa',
                                cursor: 'pointer',
                                fontWeight: 500,
                                fontSize: '0.875rem',
                            }}
                        >
                            {name}
                        </button>
                    ))}
                </div>

                <div style={{ display: 'flex', gap: '1rem' }}>
                    <button
                        className="btn btn-outline"
                        onClick={() => setLevel(Math.max(0, level - 1))}
                    >
                        <ArrowDown size={16} />
                        Decrease
                    </button>
                    <button
                        className="btn btn-danger"
                        onClick={() => setLevel(Math.min(4, level + 1))}
                    >
                        <ArrowUp size={16} />
                        Increase
                    </button>
                </div>
            </div>

            <div className="card">
                <div className="card-header">
                    <h2 className="card-title">Level Descriptions</h2>
                </div>
                <table className="table">
                    <thead>
                        <tr>
                            <th>Level</th>
                            <th>Action</th>
                            <th>Use Case</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><span style={{ color: '#22c55e' }}>0 — Observe</span></td>
                            <td>Logging only, no blocking</td>
                            <td>Normal traffic, ML training</td>
                        </tr>
                        <tr>
                            <td><span style={{ color: '#0ea5e9' }}>1 — Soft</span></td>
                            <td>Invisible PoW challenge</td>
                            <td>Slight traffic increase</td>
                        </tr>
                        <tr>
                            <td><span style={{ color: '#f59e0b' }}>2 — Medium</span></td>
                            <td>CAPTCHA for suspicious IPs</td>
                            <td>Moderate attack</td>
                        </tr>
                        <tr>
                            <td><span style={{ color: '#f97316' }}>3 — Hard</span></td>
                            <td>JS Challenge for everyone</td>
                            <td>Active DDoS attack</td>
                        </tr>
                        <tr>
                            <td><span style={{ color: '#ef4444' }}>4 — Lockdown</span></td>
                            <td>Whitelist only</td>
                            <td>Emergency, severe attack</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    )
}

// Domains Page
function DomainsPage() {
    return (
        <div>
            <div className="page-header">
                <h1 className="page-title">Domains</h1>
                <button className="btn btn-primary">
                    <Plus size={16} />
                    Add Domain
                </button>
            </div>

            <div className="card">
                <table className="table">
                    <thead>
                        <tr>
                            <th>Domain</th>
                            <th>Status</th>
                            <th>Protection Level</th>
                            <th>Traffic (req/s)</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {mockDomains.map(d => (
                            <tr key={d.id}>
                                <td><strong>{d.domain}</strong></td>
                                <td>
                                    <span className="domain-status">
                                        <span className={`status-dot ${d.status}`}></span>
                                        {d.status}
                                    </span>
                                </td>
                                <td>Level {d.level}</td>
                                <td>{d.rps.toLocaleString()}</td>
                                <td>
                                    <button className="btn btn-outline" style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}>
                                        Configure
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

// Settings Page
function SettingsPage() {
    return (
        <div>
            <div className="page-header">
                <h1 className="page-title">Settings</h1>
            </div>
            <div className="card">
                <h2 className="card-title">API Configuration</h2>
                <p style={{ color: '#a1a1aa', marginTop: '1rem' }}>
                    Configure your API keys and webhook endpoints here.
                </p>
            </div>
        </div>
    )
}

// Logs Page
function LogsPage() {
    return (
        <div>
            <div className="page-header">
                <h1 className="page-title">Access Logs</h1>
            </div>
            <div className="card">
                <p style={{ color: '#a1a1aa' }}>
                    Real-time access logs will appear here. Connect to the Control Plane API to view live data.
                </p>
            </div>
        </div>
    )
}

// Main App
function App() {
    return (
        <>
            <Sidebar />
            <main className="main-content">
                <Routes>
                    <Route path="/" element={<DashboardPage />} />
                    <Route path="/domains" element={<DomainsPage />} />
                    <Route path="/attack-mode" element={<AttackModePage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="/logs" element={<LogsPage />} />
                </Routes>
            </main>
        </>
    )
}

export default App
