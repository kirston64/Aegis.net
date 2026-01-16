# Aegis.net Nginx Edge Node Dockerfile

FROM nginx:alpine

# Install curl for health checks
RUN apk add --no-cache curl

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create directory for dynamic site configs
RUN mkdir -p /etc/nginx/conf.d/sites

# Expose HTTP and HTTPS
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
