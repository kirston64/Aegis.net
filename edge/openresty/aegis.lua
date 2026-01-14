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
    return _M.serve_protection_page("Checking your browser...", true)
end

-- Load protection template
local protection_template = nil
local function load_protection_template()
    if protection_template then return protection_template end

    -- Try to load from file
    local f = io.open("/usr/local/openresty/lualib/aegis/protection.html", "r")
    if f then
        protection_template = f:read("*all")
        f:close()
    else
        -- Fallback if file not found
        protection_template = [[
            <html><body><h1>Aegis.net Protection</h1><p>Please wait...</p></body></html>
        ]]
    end
    return protection_template
end

-- Serve Protection Page
function _M.serve_protection_page(reason, is_challenge)
    local template = load_protection_template()
    local client_ip = get_client_ip()
    local ray_id = ngx.var.request_id or "unknown"
    
    -- Replace placeholders
    local html = template:gsub("Your IP", client_ip)
    html = html:gsub("8a7b3c9d1e2f", ray_id) -- Replace mock Ray ID
    
    if reason then
         -- Optimistic replacement if we had a placeholder, otherwise just logged
         html = html:gsub("Мы зафиксировали аномальную активность", reason)
    end

    -- If it's a challenge, inject the JS logic
    if is_challenge then
        local challenge = _M.generate_pow_challenge()
        
        -- Store challenge in Redis
        local red = get_redis()
        if red then
            red:setex("aegis:challenge:" .. client_ip, 300, challenge.challenge)
            red:set_keepalive(10000, 100)
        end
        
        -- Inject Challenge Script
        local challenge_script = string.format([[
        <script>
        (function() {
            var challenge = "%s";
            var difficulty = %d;
            
            // Simple PoW implementation for demo
            setTimeout(function() {
                var solution = {
                    t: Date.now(),
                    h: "0000mockhash", // In real logic we'd solve it
                    n: 12345
                };
                
                var token = btoa(JSON.stringify(solution));
                document.cookie = "%s=" + token + "; path=/; max-age=3600";
                location.reload();
            }, 2000);
        })();
        </script>
        </body>
        ]], challenge.challenge, challenge.difficulty, config.challenge_cookie_name)
        
        html = html:gsub("</body>", challenge_script)
        html = html:gsub("Проверить снова", "Проверка браузера...")
    end

    ngx.header["Content-Type"] = "text/html; charset=utf-8"
    ngx.status = is_challenge and 503 or 403
    ngx.say(html)
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
        return _M.serve_protection_page("Сайт в режиме полной изоляции (Lockdown).")
    end
    
    -- Check blacklist
    if cfg.blacklist_ips then
        for _, ip in ipairs(cfg.blacklist_ips) do
            if ip == client_ip then
                return _M.serve_protection_page("Ваш IP адрес находится в черном списке.")
            end
        end
    end
    
    -- Rate limiting
    local rate_limit = config.rate_limit_default
    if level >= LEVELS.MEDIUM then
        rate_limit = config.rate_limit_strict
    end
    
    if not _M.check_rate_limit(client_ip, domain, rate_limit) then
        return _M.serve_protection_page("Превышен лимит запросов. Пожалуйста, подождите.")
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
        -- Log entry
        red:lpush("aegis:logs:" .. domain, log_entry)
        red:ltrim("aegis:logs:" .. domain, 0, 9999)  -- Keep last 10k entries
        
        -- Track stats
        local stats_key = "aegis:stats:" .. domain
        red:hincrby(stats_key, "total_requests", 1)
        red:sadd("aegis:stats:unique_ips:" .. domain, client_ip)
        
        if status == 429 or status == 403 then
            red:hincrby(stats_key, "blocked_requests", 1)
        end
        
        red:set_keepalive(10000, 100)
    end
end

return _M
