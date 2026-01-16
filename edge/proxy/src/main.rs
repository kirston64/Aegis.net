use std::convert::Infallible;
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::{Duration, Instant};
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper::{body::Incoming, Request, Response, StatusCode};
use hyper_util::rt::TokioIo;
use http_body_util::{Full, BodyExt, Empty};
use hyper::body::Bytes;
use tokio::net::TcpListener;
use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use tracing::{info, warn, error};

// ============================================================================
// Configuration & State
// ============================================================================

#[derive(Clone, Debug, Serialize, Deserialize)]
struct Config {
    protection_level: u8,
    rate_limit: u32,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            protection_level: 1,
            rate_limit: 100,
        }
    }
}

struct RateLimitEntry {
    count: u32,
    window_start: Instant,
}

#[derive(Clone)]
struct AppState {
    config: Arc<parking_lot::RwLock<Config>>,
    rate_limits: Arc<DashMap<String, RateLimitEntry>>,
    stats: Arc<Stats>,
    origin_url: String,
}

struct Stats {
    total_requests: prometheus::IntCounter,
    blocked_requests: prometheus::IntCounter,
}

// ============================================================================
// Main Entry Point
// ============================================================================

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Setup tracing
    tracing_subscriber::fmt()
        .with_env_filter("aegis_proxy=debug,hyper=info")
        .init();

    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    let origin_url = std::env::var("ORIGIN_URL").unwrap_or_else(|_| "http://localhost:9000".to_string());

    info!("🛡️  Aegis Edge Proxy starting on {}", addr);
    info!("📡 Origin server: {}", origin_url);

    // Initialize metrics
    let stats = Arc::new(Stats {
        total_requests: prometheus::IntCounter::new("aegis_total_requests", "Total requests").unwrap(),
        blocked_requests: prometheus::IntCounter::new("aegis_blocked_requests", "Blocked requests").unwrap(),
    });

    let state = AppState {
        config: Arc::new(parking_lot::RwLock::new(Config::default())),
        rate_limits: Arc::new(DashMap::new()),
        stats,
        origin_url,
    };

    let listener = TcpListener::bind(addr).await?;

    info!("✅ Server ready - accepting connections");

    loop {
        let (stream, remote_addr) = listener.accept().await?;
        let io = TokioIo::new(stream);
        let state = state.clone();

        tokio::spawn(async move {
            let service = service_fn(move |req| {
                let state = state.clone();
                let client_ip = remote_addr.ip().to_string();
                handle_request(req, state, client_ip)
            });

            if let Err(err) = http1::Builder::new()
                .serve_connection(io, service)
                .await
            {
                error!("Connection error: {:?}", err);
            }
        });
    }
}

// ============================================================================
// Request Handler
// ============================================================================

async fn handle_request(
    req: Request<Incoming>,
    state: AppState,
    client_ip: String,
) -> Result<Response<Full<Bytes>>, Infallible> {
    state.stats.total_requests.inc();

    let path = req.uri().path().to_string();

    // API Endpoints
    if path == "/api/stats" {
        return Ok(handle_stats(state).await);
    }

    if path == "/api/config" {
        return Ok(handle_config(req, state).await);
    }

    // Protection Logic
    match decide_action(&state, &client_ip).await {
        Action::Block => {
            state.stats.blocked_requests.inc();
            Ok(serve_block_page(client_ip))
        }
        Action::Challenge => {
            // Check for aegis_passed cookie
            let has_cookie = req
                .headers()
                .get("cookie")
                .and_then(|v| v.to_str().ok())
                .map(|s| s.contains("aegis_passed=1"))
                .unwrap_or(false);

            if !has_cookie {
                Ok(serve_js_challenge())
            } else {
                proxy_to_origin(req, &state.origin_url).await
            }
        }
        Action::Allow => proxy_to_origin(req, &state.origin_url).await,
    }
}

// ============================================================================
// Protection Logic
// ============================================================================

enum Action {
    Allow,
    Challenge,
    Block,
}

async fn decide_action(state: &AppState, ip: &str) -> Action {
    let config = state.config.read();
    let level = config.protection_level;
    let limit = config.rate_limit;

    // Level 4: Lockdown
    if level == 4 {
        return Action::Block;
    }

    // Rate Limiting Check
    let is_limited = check_rate_limit(state, ip, limit).await;

    if is_limited {
        if level == 3 {
            return Action::Challenge;
        }
        return Action::Block;
    }

    // Level 3: Challenge Mode (Under Attack)
    if level == 3 {
        return Action::Challenge;
    }

    Action::Allow
}

async fn check_rate_limit(state: &AppState, ip: &str, limit: u32) -> bool {
    let now = Instant::now();
    let window = Duration::from_secs(1);

    let mut entry = state.rate_limits.entry(ip.to_string()).or_insert(RateLimitEntry {
        count: 0,
        window_start: now,
    });

    if now.duration_since(entry.window_start) > window {
        entry.count = 1;
        entry.window_start = now;
        false
    } else {
        entry.count += 1;
        entry.count > limit
    }
}

// ============================================================================
// Response Handlers
// ============================================================================

async fn handle_stats(state: AppState) -> Response<Full<Bytes>> {
    let config = state.config.read();
    let response = serde_json::json!({
        "total": state.stats.total_requests.get(),
        "blocked": state.stats.blocked_requests.get(),
        "rps": 0,
        "blocked_rps": 0,
        "active_ips": state.rate_limits.len(),
        "config": {
            "protection_level": config.protection_level,
            "rate_limit": config.rate_limit,
        },
        "recent_attacks": [],
        "status": "active"
    });

    Response::builder()
        .status(StatusCode::OK)
        .header("Content-Type", "application/json")
        .header("Access-Control-Allow-Origin", "*")
        .body(Full::new(Bytes::from(response.to_string())))
        .unwrap()
}

async fn handle_config(req: Request<Incoming>, state: AppState) -> Response<Full<Bytes>> {
    if req.method() == hyper::Method::POST {
        let whole_body = req.collect().await.unwrap().to_bytes();
        
        if let Ok(new_config) = serde_json::from_slice::<Config>(&whole_body) {
            *state.config.write() = new_config;
            
            let response = serde_json::json!({
                "status": "ok",
                "config": *state.config.read(),
            });

            return Response::builder()
                .status(StatusCode::OK)
                .header("Content-Type", "application/json")
                .header("Access-Control-Allow-Origin", "*")
                .body(Full::new(Bytes::from(response.to_string())))
                .unwrap();
        }
    }

    Response::builder()
        .status(StatusCode::BAD_REQUEST)
        .body(Full::new(Bytes::from("Invalid request")))
        .unwrap()
}

fn serve_js_challenge() -> Response<Full<Bytes>> {
    let html = r#"
    <!DOCTYPE html>
    <html>
    <head>
        <title>Aegis Security Check</title>
        <style>
            body { background: #111; color: #eee; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .box { text-align: center; padding: 40px; border: 1px solid #333; border-radius: 8px; background: #1a1a1a; }
            .spinner { border: 4px solid #333; border-top: 4px solid #00ff88; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px auto; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body>
        <div class="box">
            <h1>🛡️ Aegis DDoS Protection</h1>
            <div class="spinner"></div>
            <p>Checking your browser...</p>
            <p style="color: #666; font-size: 12px; margin-top: 20px;">Powered by Aegis.net - Rust Edition</p>
        </div>
        <script>
            setTimeout(function() {
                document.cookie = "aegis_passed=1; path=/; max-age=3600";
                window.location.reload();
            }, 2000);
        </script>
    </body>
    </html>
    "#;

    Response::builder()
        .status(StatusCode::SERVICE_UNAVAILABLE)
        .header("Content-Type", "text/html")
        .body(Full::new(Bytes::from(html)))
        .unwrap()
}

fn serve_block_page(ip: String) -> Response<Full<Bytes>> {
    let html = format!(
        r#"
        <!DOCTYPE html>
        <html>
        <head><title>Access Denied</title></head>
        <body style="background: #111; color: #eee; font-family: sans-serif; text-align: center; padding: 100px;">
            <h1>🚫 Access Denied</h1>
            <p>Your IP: {}</p>
            <p>Blocked by Aegis Protection</p>
        </body>
        </html>
        "#,
        ip
    );

    Response::builder()
        .status(StatusCode::FORBIDDEN)
        .header("Content-Type", "text/html")
        .body(Full::new(Bytes::from(html)))
        .unwrap()
}

async fn proxy_to_origin(req: Request<Incoming>, origin_url: &str) -> Result<Response<Full<Bytes>>, Infallible> {
    let client = reqwest::Client::new();
    let path = req.uri().path_and_query().map(|x| x.as_str()).unwrap_or("/");
    let url = format!("{}{}", origin_url, path);

    match client.get(&url).send().await {
        Ok(resp) => {
            let status = resp.status();
            let body_bytes = resp.bytes().await.unwrap_or_default();

            Ok(Response::builder()
                .status(status)
                .body(Full::new(body_bytes))
                .unwrap())
        }
        Err(_) => {
            Ok(Response::builder()
                .status(StatusCode::BAD_GATEWAY)
                .body(Full::new(Bytes::from("Origin server unavailable")))
                .unwrap())
        }
    }
}
