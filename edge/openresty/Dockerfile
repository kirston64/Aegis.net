FROM openresty/openresty:alpine

# Install dependencies (Redis client for Lua is usually included, but ensure we have everything)
RUN apk add --no-cache curl

# Create directory for our module
RUN mkdir -p /usr/local/openresty/lualib/aegis

# Copy configuration
COPY nginx.conf /usr/local/openresty/nginx/conf/nginx.conf

# Copy Lua scripts (will be mounted in dev, but good to have)
COPY aegis.lua /usr/local/openresty/lualib/aegis/aegis.lua

# Expose ports
EXPOSE 80 443

# Command is default from base image
