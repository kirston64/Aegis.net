--[[
    Aegis.net — OpenResty WAF Module
    
    L7 protection with bot detection, rate limiting, and challenge system.
    
    Installation:
    1. Copy to /usr/local/openresty/lualib/aegis/
    2. Include in nginx.conf: lua_package_path "/usr/local/openresty/lualib/?.lua;;";
    3. Use in location: access_by_lua_file /path/to/aegis_access.lua;
]]

local _M = { _VERSION = '1.0.0' }

local cjson = require "cjson.safe"
local redis = require "resty.redis"

-- Configuration
local config = {
    redis_host = os.getenv("REDIS_HOST") or "127.0.0.1",
    redis_port = tonumber(os.getenv("REDIS_PORT")) or 6379,
    
    -- Rate limits (requests per second)
    rate_limit_default = 100,
    rate_limit_strict = 20,
    
    -- Challenge settings
    challenge_cookie_name = "_aegis_verified",
    challenge_ttl = 3600,
    
    -- Bot detection thresholds
    bot_score_threshold = 0.7,
}

-- Protection levels
local LEVELS = {
    OBSERVE = 0,
    SOFT = 1,
    MEDIUM = 2,
    HARD = 3,
    LOCKDOWN = 4,
}

-- Redis connection pool
local function get_redis()
    local red = redis:new()
    red:set_timeout(1000)
    
    local ok, err = red:connect(config.redis_host, config.redis_port)
    if not ok then
        ngx.log(ngx.ERR, "Failed to connect to Redis: ", err)
        return nil
    end
    
    return red
end

-- Get client IP (with proxy support)
local function get_client_ip()
    local headers = ngx.req.get_headers()
    return headers["CF-Connecting-IP"] 
        or headers["X-Real-IP"]
        or headers["X-Forwarded-For"]
        or ngx.var.remote_addr
end

-- Get domain configuration
function _M.get_domain_config(domain)
    local red = get_redis()
    if not red then
        return { protection_level = LEVELS.OBSERVE }
    end
    
    local config_json = red:get("aegis:config:" .. domain)
    red:set_keepalive(10000, 100)
    
    if config_json and config_json ~= ngx.null then
        local cfg = cjson.decode(config_json)
        return cfg or { protection_level = LEVELS.OBSERVE }
    end
    
    return { protection_level = LEVELS.OBSERVE }
end

-- Rate limiting check
function _M.check_rate_limit(ip, domain, limit)
    local red = get_redis()
    if not red then
        return true  -- Allow on Redis failure
    end
    
    local key = "aegis:rate:" .. domain .. ":" .. ip
    local current = red:incr(key)
    
    if current == 1 then
        red:expire(key, 1)  -- 1 second window
    end
    
    red:set_keepalive(10000, 100)
    
    return current <= limit
end

-- Bot fingerprint analysis
function _M.analyze_request()
    local headers = ngx.req.get_headers()
    local score = 0.0
    
    -- Check User-Agent
    local ua = headers["User-Agent"] or ""
    if ua == "" then
        score = score + 0.3
    elseif ua:match("^curl") or ua:match("^python") or ua:match("^wget") then
        score = score + 0.2
    end
    
    -- Check Accept headers
    if not headers["Accept"] then
        score = score + 0.1
    end
    if not headers["Accept-Language"] then
        score = score + 0.1
    end
    if not headers["Accept-Encoding"] then
        score = score + 0.1
    end
    
    -- Check for common bot patterns
    if headers["X-Requested-With"] == nil and ngx.var.request_method == "POST" then
        score = score + 0.1
    end
    
    -- Check referer for browsing pattern
    local referer = headers["Referer"] or ""
    local host = headers["Host"] or ""
    if referer == "" and ngx.var.uri ~= "/" then
        score = score + 0.1
    end
    
    return {
        score = score,
        is_bot = score >= config.bot_score_threshold,
        user_agent = ua,
    }
end

-- Generate invisible PoW challenge
function _M.generate_pow_challenge()
    local difficulty = 4  -- Leading zeros required
    local challenge = ngx.md5(ngx.now() .. ngx.var.remote_addr .. math.random())
    
    return {
        challenge = challenge,
        difficulty = difficulty,
    }
end

-- Verify challenge cookie
function _M.verify_challenge_cookie(ip)
    local cookie = ngx.var["cookie_" .. config.challenge_cookie_name]
    if not cookie then
        return false
    end
    
    -- Decode base64 token
    local token_json = ngx.decode_base64(cookie)
    if not token_json then
        return false
    end
    
    local token = cjson.decode(token_json)
    if not token or not token.n or not token.h or not token.t then
        return false
    end
    
    -- Check token age (max 1 hour)
    local now = ngx.now() * 1000
    if now - token.t > 3600000 then
        return false
    end
    
    -- Optionally: verify against Redis stored challenge
    local red = get_redis()
    if red then
        local stored_challenge = red:get("aegis:challenge:" .. ip)
        red:set_keepalive(10000, 100)
        
        -- Challenge exists and was solved - valid
        if stored_challenge and stored_challenge ~= ngx.null then
            -- Verify the hash starts with zeros
            if token.h:match("^0000") then
                return true
            end
        end
    end
    
    -- Fallback: trust the cookie if hash looks valid
    if token.h:match("^0000") then
        return true
    end
    
    return false
end

-- Serve JavaScript challenge page
function _M.serve_challenge()
    local challenge = _M.generate_pow_challenge()
    local ip = get_client_ip()
    
    -- Store challenge in Redis for verification
    local red = get_redis()
    if red then
        red:setex("aegis:challenge:" .. ip, 300, challenge.challenge)
        red:set_keepalive(10000, 100)
    end
    
    ngx.header["Content-Type"] = "text/html"
    ngx.header["Cache-Control"] = "no-store, no-cache, must-revalidate"
    ngx.status = 503
    
    ngx.say([[
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Check — Aegis.net</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%);
            color: #f4f4f5;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            text-align: center;
            padding: 3rem;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            backdrop-filter: blur(10px);
            max-width: 400px;
        }
        .shield {
            width: 64px;
            height: 64px;
            margin: 0 auto 1.5rem;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: pulse 2s ease-in-out infinite;
        }
        .shield svg { width: 32px; height: 32px; fill: white; }
        @keyframes pulse {
            0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.4); }
            50% { transform: scale(1.05); box-shadow: 0 0 20px 10px rgba(99, 102, 241, 0.1); }
        }
        h1 { font-size: 1.5rem; font-weight: 600; margin-bottom: 0.5rem; }
        .subtitle { color: #a1a1aa; margin-bottom: 2rem; }
        .progress-container {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 999px;
            height: 8px;
            overflow: hidden;
            margin-bottom: 1rem;
        }
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #6366f1, #8b5cf6);
            width: 0%;
            transition: width 0.3s ease;
            border-radius: 999px;
        }
        #status {
            color: #71717a;
            font-size: 0.875rem;
            font-family: 'Monaco', 'Consolas', monospace;
        }
        .powered {
            margin-top: 2rem;
            font-size: 0.75rem;
            color: #52525b;
        }
        .error { color: #ef4444; display: none; margin-top: 1rem; }
    </style>
</head>
<body>
    <div class="container">
        <div class="shield">
            <svg viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 10.99h7c-.53 4.12-3.28 7.79-7 8.94V12H5V6.3l7-3.11v8.8z"/></svg>
        </div>
        <h1>Checking your browser</h1>
        <p class="subtitle">This process is automatic. Please wait...</p>
        <div class="progress-container">
            <div class="progress-bar" id="progress"></div>
        </div>
        <p id="status">Initializing verification...</p>
        <p class="error" id="error">Verification failed. Please refresh the page.</p>
        <p class="powered">Protected by <strong>Aegis.net</strong></p>
    </div>
    
    <script>
    (function() {
        'use strict';
        
        const CHALLENGE = ']] .. challenge.challenge .. [[';
        const DIFFICULTY = ]] .. challenge.difficulty .. [[;
        const MAX_ITERATIONS = 5000000;
        
        const $progress = document.getElementById('progress');
        const $status = document.getElementById('status');
        const $error = document.getElementById('error');
        
        // SHA-256 using Web Crypto API
        async function sha256(message) {
            const msgBuffer = new TextEncoder().encode(message);
            const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        }
        
        // Check if hash meets difficulty (leading zeros)
        function meetsTarget(hash, difficulty) {
            for (let i = 0; i < difficulty; i++) {
                if (hash[i] !== '0') return false;
            }
            return true;
        }
        
        // Solve PoW challenge
        async function solve() {
            let nonce = 0;
            const startTime = Date.now();
            
            while (nonce < MAX_ITERATIONS) {
                const hash = await sha256(CHALLENGE + nonce);
                
                if (meetsTarget(hash, DIFFICULTY)) {
                    // Found solution!
                    $progress.style.width = '100%';
                    $status.textContent = 'Verified! Redirecting...';
                    
                    // Set verification cookie with solution
                    const token = btoa(JSON.stringify({
                        n: nonce,
                        h: hash.substring(0, 16),
                        t: Date.now()
                    }));
                    
                    document.cookie = '_aegis_verified=' + token + '; path=/; max-age=3600; SameSite=Strict; Secure';
                    
                    setTimeout(() => location.reload(), 500);
                    return;
                }
                
                nonce++;
                
                // Update progress every 1000 iterations
                if (nonce % 1000 === 0) {
                    const progress = Math.min((nonce / 50000) * 100, 95);
                    $progress.style.width = progress + '%';
                    $status.textContent = 'Verifying... ' + (nonce / 1000).toFixed(0) + 'k hashes';
                    
                    // Yield to browser
                    await new Promise(r => setTimeout(r, 0));
                }
            }
            
            // Failed to solve
            $error.style.display = 'block';
            $status.textContent = 'Verification timeout';
        }
        
        // Start solving after page loads
        if (window.crypto && window.crypto.subtle) {
            setTimeout(solve, 100);
        } else {
            // Fallback for non-HTTPS
            $status.textContent = 'Secure context required';
            $error.style.display = 'block';
        }
    })();
    </script>
</body>
</html>
    ]])
    
    ngx.exit(ngx.HTTP_OK)
end

-- Main access handler
function _M.access()
    local domain = ngx.var.host
    local client_ip = get_client_ip()
    
    -- Get domain config
    local cfg = _M.get_domain_config(domain)
    local level = cfg.protection_level or LEVELS.OBSERVE
    
    -- Level 0: Observe only
    if level == LEVELS.OBSERVE then
        return
    end
    
    -- Check whitelist
    if cfg.whitelist_ips then
        for _, ip in ipairs(cfg.whitelist_ips) do
            if ip == client_ip then
                return  -- Whitelisted, pass through
            end
        end
    end
    
    -- Level 4: Lockdown (whitelist only)
    if level >= LEVELS.LOCKDOWN then
        ngx.status = 403
        ngx.say("Access denied. Site is in lockdown mode.")
        ngx.exit(ngx.HTTP_FORBIDDEN)
    end
    
    -- Check blacklist
    if cfg.blacklist_ips then
        for _, ip in ipairs(cfg.blacklist_ips) do
            if ip == client_ip then
                ngx.status = 403
                ngx.say("Access denied")
                ngx.exit(ngx.HTTP_FORBIDDEN)
            end
        end
    end
    
    -- Rate limiting
    local rate_limit = config.rate_limit_default
    if level >= LEVELS.MEDIUM then
        rate_limit = config.rate_limit_strict
    end
    
    if not _M.check_rate_limit(client_ip, domain, rate_limit) then
        ngx.status = 429
        ngx.header["Retry-After"] = "1"
        ngx.say('{"error": "Rate limit exceeded"}')
        ngx.exit(ngx.HTTP_TOO_MANY_REQUESTS)
    end
    
    -- Bot analysis for Level 2+
    if level >= LEVELS.MEDIUM then
        local analysis = _M.analyze_request()
        
        if analysis.is_bot then
            -- Check if already verified with proper validation
            if not _M.verify_challenge_cookie(client_ip) then
                _M.serve_challenge()
            end
        end
    end
    
    -- Level 3: Challenge everyone
    if level >= LEVELS.HARD then
        if not _M.verify_challenge_cookie(client_ip) then
            _M.serve_challenge()
        end
    end
end

-- Log request for analytics
function _M.log()
    local client_ip = get_client_ip()
    local domain = ngx.var.host
    local status = ngx.status
    local request_time = ngx.var.request_time
    
    local log_entry = cjson.encode({
        timestamp = ngx.now(),
        domain = domain,
        client_ip = client_ip,
        method = ngx.var.request_method,
        uri = ngx.var.uri,
        status = status,
        request_time = tonumber(request_time),
        user_agent = ngx.var.http_user_agent,
        bytes_sent = ngx.var.bytes_sent,
    })
    
    -- Send to Redis for real-time processing
    local red = get_redis()
    if red then
        red:lpush("aegis:logs:" .. domain, log_entry)
        red:ltrim("aegis:logs:" .. domain, 0, 9999)  -- Keep last 10k entries
        red:set_keepalive(10000, 100)
    end
end

return _M
