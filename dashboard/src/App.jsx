import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { useState, useEffect, createContext, useContext } from 'react'
import {
    Shield,
    Globe,
    BarChart3,
    Settings,
    Activity,
    ArrowUp,
    ArrowDown,
    Menu,
    X,
    Check
} from 'lucide-react'
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer
} from 'recharts'
import AttackMap from './components/AttackMap'

// --- i18n System ---
const translations = {
    en: {
        dashboard: "Dashboard",
        domains: "Domains",
        smartShield: "Smart Shield",
        logs: "Logs",
        settings: "Settings",
        main: "Main",
        system: "System",
        totalRequests: "Total Requests",
        blockedRequests: "Blocked Requests",
        currentRps: "Current RPS",
        protectedDomains: "Protected Domains",
        realTimeTraffic: "Real-time Traffic",
        underAttack: "UNDER ATTACK",
        systemHealthy: "SYSTEM HEALTHY",
        addDomain: "Add Domain",
        protectionLevel: "Protection Level",
        levelDescriptions: "Level Descriptions",
        increase: "Increase",
        decrease: "Decrease",
        reqPerSec: "req/s",
        legitimate: "Legitimate",
        blocked: "Blocked",
        status: "Status",
        actions: "Actions",
        configure: "Configure",
        welcome: "Welcome to Aegis",
        selectLanguage: "Select your language",
        continue: "Continue"
    },
    ru: {
        dashboard: "Дашборд",
        domains: "Домены",
        smartShield: "Умная Защита",
        logs: "Логи",
        settings: "Настройки",
        main: "Главная",
        system: "Система",
        totalRequests: "Всего запросов",
        blockedRequests: "Заблокировано",
        currentRps: "Текущий RPS",
        protectedDomains: "Доменов под защитой",
        realTimeTraffic: "Трафик в реальном времени",
        underAttack: "АТАКА ОБНАРУЖЕНА",
        systemHealthy: "СИСТЕМА В НОРМЕ",
        addDomain: "Добавить домен",
        protectionLevel: "Уровень защиты",
        levelDescriptions: "Описание уровней",
        increase: "Повысить",
        decrease: "Понизить",
        reqPerSec: "зап/сек",
        legitimate: "Легитимный",
        blocked: "Заблокирован",
        status: "Статус",
        actions: "Действия",
        configure: "Настроить",
        welcome: "Добро пожаловать в Aegis",
        selectLanguage: "Выберите язык",
        continue: "Продолжить"
    }
}

const LanguageContext = createContext()

function LanguageProvider({ children }) {
    const [language, setLanguage] = useState(null) // null initiates selection screen

    const t = (key) => translations[language]?.[key] || key

    return (
        <LanguageContext.Provider value={{ language, setLanguage, t }}>
            {children}
        </LanguageContext.Provider>
    )
}

const useTranslation = () => useContext(LanguageContext)

// --- Components ---

function LanguageSelector() {
    const { setLanguage } = useTranslation()

    return (
        <div style={{
            position: 'fixed',
            inset: 0,
            background: '#ffffff',
            zIndex: 9999,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '2rem'
        }}>
            <div style={{ maxWidth: '400px', width: '100%', textAlign: 'center' }}>
                <div style={{ fontSize: '4rem', marginBottom: '2rem' }}>🛡️</div>
                <h1 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '0.5rem', color: '#18181b' }}>
                    Aegis.net
                </h1>
                <p style={{ color: '#71717a', marginBottom: '3rem' }}>
                    Advanced DDoS Protection
                </p>

                <div style={{ display: 'grid', gap: '1rem' }}>
                    <button
                        onClick={() => setLanguage('en')}
                        className="btn btn-outline"
                        style={{ justifyContent: 'space-between', padding: '1.5rem', fontSize: '1.1rem' }}
                    >
                        <span>English</span>
                        <span style={{ opacity: 0.5 }}>EN</span>
                    </button>
                    <button
                        onClick={() => setLanguage('ru')}
                        className="btn btn-outline"
                        style={{ justifyContent: 'space-between', padding: '1.5rem', fontSize: '1.1rem' }}
                    >
                        <span>Русский</span>
                        <span style={{ opacity: 0.5 }}>RU</span>
                    </button>
                </div>
            </div>
        </div>
    )
}

function Sidebar() {
    const location = useLocation()
    const { t } = useTranslation()
    const isActive = (path) => location.pathname === path ? 'nav-link active' : 'nav-link'

    return (
        <aside className="sidebar">
            <div className="logo">
                <span className="logo-icon">🛡️</span>
                <span>Aegis</span>
            </div>

            <nav className="nav-section">
                <h3 className="nav-title">{t('main')}</h3>
                <ul className="nav-links">
                    <li>
                        <Link to="/" className={isActive('/')}>
                            <BarChart3 size={20} strokeWidth={1.5} />
                            <span>{t('dashboard')}</span>
                        </Link>
                    </li>
                    <li>
                        <Link to="/domains" className={isActive('/domains')}>
                            <Globe size={20} strokeWidth={1.5} />
                            <span>{t('domains')}</span>
                        </Link>
                    </li>
                    <li>
                        <Link to="/attack-mode" className={isActive('/attack-mode')}>
                            <Shield size={20} strokeWidth={1.5} />
                            <span>{t('smartShield')}</span>
                        </Link>
                    </li>
                </ul>
            </nav>

            <nav className="nav-section">
                <h3 className="nav-title">{t('system')}</h3>
                <ul className="nav-links">
                    <li>
                        <Link to="/logs" className={isActive('/logs')}>
                            <Activity size={20} strokeWidth={1.5} />
                            <span>{t('logs')}</span>
                        </Link>
                    </li>
                    <li>
                        <Link to="/settings" className={isActive('/settings')}>
                            <Settings size={20} strokeWidth={1.5} />
                            <span>{t('settings')}</span>
                        </Link>
                    </li>
                </ul>
            </nav>
        </aside>
    )
}

function DashboardPage() {
    const { t } = useTranslation()
    const [stats, setStats] = useState({
        totalRequests: 0,
        blockedRequests: 0,
        rps: 0,
        activeAttacks: 0,
        protectedDomains: 1,
        recent_attacks: []
    })

    const [trafficData, setTrafficData] = useState(
        Array.from({ length: 60 }, (_, i) => ({ time: i, rps: 0, blocked: 0 }))
    )

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch('http://localhost:8080/api/stats')
                const data = await response.json()

                setStats({
                    totalRequests: data.total.toLocaleString(),
                    blockedRequests: data.blocked.toLocaleString(),
                    rps: data.rps,
                    activeAttacks: data.blocked > 0 ? 1 : 0,
                    protectedDomains: 1,
                    recent_attacks: data.recent_attacks || []
                })

                setTrafficData(prev => {
                    const newData = [...prev.slice(1), {
                        time: new Date().toLocaleTimeString(),
                        rps: data.rps,
                        blocked: data.blocked_rps
                    }]
                    return newData
                })

            } catch (error) {
                // Silent fail for demo
            }
        }

        const interval = setInterval(fetchData, 1000)
        return () => clearInterval(interval)
    }, [])

    return (
        <div>
            <div className="page-header">
                <h1 className="page-title">{t('dashboard')}</h1>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className={`status-dot ${stats.activeAttacks > 0 ? 'warning' : 'active'}`}></span>
                    <span style={{
                        color: stats.activeAttacks > 0 ? 'var(--color-warning)' : 'var(--color-success)',
                        fontWeight: 500,
                        fontSize: '0.875rem'
                    }}>
                        {stats.activeAttacks > 0 ? t('underAttack') : t('systemHealthy')}
                    </span>
                </div>
            </div>

            {/* Live Map Section */}
            <div className="card mb-8 relative overflow-hidden" style={{ padding: '1.5rem' }}>
                <div className="flex items-center justify-between mb-4" style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
                    <h3 className="text-lg font-semibold flex items-center gap-2" style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "1.125rem", fontWeight: 600 }}>
                        <Globe size={20} className="text-blue-400" style={{ color: "#60a5fa" }} />
                        Live Threat Intelligence
                    </h3>
                    <div className="flex gap-2 text-xs text-gray-400" style={{ display: "flex", gap: "0.5rem", fontSize: "0.75rem", color: "#9ca3af" }}>
                        {stats.activeAttacks > 0 && (
                            <span className="flex items-center gap-1" style={{ display: "flex", alignItems: "center", gap: "0.25rem", color: "#ef4444" }}>
                                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: "#ef4444", display: "inline-block" }}></span>
                                Active Attack
                            </span>
                        )}
                    </div>
                </div>

                <div className="relative z-10">
                    <AttackMap attacks={stats.recent_attacks || []} />
                </div>
            </div>

            {/* Charts Section */}
            <div className="stats-grid" style={{ marginBottom: "2rem" }}>
                <div className="stat-card">
                    <div className="stat-label">{t('totalRequests')}</div>
                    <div className="stat-value">{stats.totalRequests}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">{t('blockedRequests')}</div>
                    <div className="stat-value warning">{stats.blockedRequests}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">{t('currentRps')}</div>
                    <div className="stat-value">{stats.rps}</div>
                </div>
                <div className="stat-card">
                    <div className="stat-label">{t('protectedDomains')}</div>
                    <div className="stat-value">{stats.protectedDomains}</div>
                </div>
            </div>

            <div className="card">
                <div className="card-header">
                    <h2 className="card-title">{t('realTimeTraffic')}</h2>
                </div>
                <div className="chart-container">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={trafficData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
                            <XAxis dataKey="time" hide />
                            <YAxis
                                stroke="var(--color-text-muted)"
                                fontSize={12}
                                tickLine={false}
                                axisLine={false}
                            />
                            <Tooltip
                                contentStyle={{
                                    background: 'var(--color-bg)',
                                    border: '1px solid var(--color-border)',
                                    borderRadius: '8px',
                                    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'
                                }}
                            />
                            <Area
                                type="monotone"
                                dataKey="rps"
                                stackId="1"
                                stroke="var(--color-primary)"
                                fill="var(--color-primary)"
                                fillOpacity={0.1}
                                strokeWidth={2}
                                name={t('legitimate')}
                                isAnimationActive={false}
                            />
                            <Area
                                type="monotone"
                                dataKey="blocked"
                                stackId="2"
                                stroke="var(--color-danger)"
                                fill="var(--color-danger)"
                                fillOpacity={0.1}
                                strokeWidth={2}
                                name={t('blocked')}
                                isAnimationActive={false}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    )
}

function AttackModePage() {
    const { t } = useTranslation()
    const [level, setLevel] = useState(1)
    const levels = ['Observe', 'Soft', 'Medium', 'Hard', 'Lockdown']
    const levelColors = ['var(--color-success)', '#0ea5e9', 'var(--color-warning)', '#f97316', 'var(--color-danger)']

    useEffect(() => {
        // Build resilient fetch with retries or just simple for now
        fetch('http://localhost:8080/api/config')
            .then(res => res.json())
            .then(data => {
                if (data.protection_level !== undefined) {
                    setLevel(data.protection_level)
                }
            })
            .catch(err => console.log("Config fetch failed", err))
    }, [])

    const handleLevelChange = async (newLevel) => {
        try {
            const res = await fetch('http://localhost:8080/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ protection_level: newLevel })
            })
            if (res.ok) {
                setLevel(newLevel)
            }
        } catch (error) {
            console.error("Failed to update level", error)
        }
    }

    return (
        <div>
            <div className="page-header">
                <h1 className="page-title">{t('smartShield')}</h1>
            </div>

            <div className="card">
                <div className="card-header">
                    <h2 className="card-title">{t('protectionLevel')}</h2>
                    <span style={{ color: levelColors[level], fontWeight: 600 }}>
                        {levels[level]}
                    </span>
                </div>

                <div className="shield-level">
                    <div className="level-bar">
                        <div
                            className="level-fill"
                            style={{
                                width: `${(level + 1) * 20}%`,
                                background: levelColors[level]
                            }}
                        ></div>
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
                    <button
                        className="btn btn-outline"
                        onClick={() => handleLevelChange(Math.max(0, level - 1))}
                        disabled={level === 0}
                    >
                        <ArrowDown size={16} />
                        {t('decrease')}
                    </button>
                    <button
                        className="btn btn-primary"
                        onClick={() => handleLevelChange(Math.min(4, level + 1))}
                        style={{ background: level === 4 ? 'var(--color-danger)' : 'var(--color-primary)' }}
                        disabled={level === 4}
                    >
                        <ArrowUp size={16} />
                        {t('increase')}
                    </button>
                </div>
            </div>
        </div>
    )
}

function DomainsPage() {
    const { t } = useTranslation()
    return (
        <div>
            <div className="page-header">
                <h1 className="page-title">{t('domains')}</h1>
                <button className="btn btn-primary">
                    <Plus size={16} />
                    {t('addDomain')}
                </button>
            </div>
            <div className="card">
                <p style={{ color: 'var(--color-text-muted)' }}>Demo Only</p>
            </div>
        </div>
    )
}

function MainLayout() {
    const { language } = useTranslation()

    if (!language) {
        return <LanguageSelector />
    }

    return (
        <>
            <Sidebar />
            <main className="main-content">
                <Routes>
                    <Route path="/" element={<DashboardPage />} />
                    <Route path="/domains" element={<DomainsPage />} />
                    <Route path="/attack-mode" element={<AttackModePage />} />
                    <Route path="*" element={<DashboardPage />} />
                </Routes>
            </main>
        </>
    )
}

function App() {
    return (
        <LanguageProvider>
            <MainLayout />
        </LanguageProvider>
    )
}

function Plus({ size }) {
    return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
}

export default App
