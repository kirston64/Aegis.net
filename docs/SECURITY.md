# Aegis CLI - Security Documentation

## Overview

Aegis CLI is the exclusive management interface for configuring and controlling Aegis.net DDoS protection. All critical operations (domain management, rate limiting, protection level changes) are **only** accessible through this secure CLI tool.

The web dashboard is **read-only** and provides monitoring capabilities only.

## Security Architecture

### Multi-Layer Authentication

1. **SSH Key Authentication**
   - 4096-bit RSA or Ed25519 keys
   - Public keys must be pre-authorized on Control Plane
   - No password fallback

2. **TOTP Two-Factor Authentication (2FA)**
   - Time-based one-time passwords (RFC 6238)
   - 30-second time window
   - Compatible with Google Authenticator, Authy, etc.

3. **IP Whitelisting**
   - Only pre-configured IPs can connect
   - Configured in Control Plane settings
   - Separate audit log for all connection attempts

4. **Session Management**
   - JWT-based sessions with 30-minute timeout
   - Automatic expiration
   - No session persistence across restarts

## Setup Instructions

### 1. Initial Setup

Run the 2FA setup script to generate SSH keys and TOTP secret:

```bash
cd cli
python setup_2fa.py
```

This will:
- Generate a 4096-bit RSA key pair at `~/.ssh/aegis_cli`
- Create a TOTP secret at `~/.aegis/totp_secret`
- Display a QR code to scan with your authenticator app
- Show your SSH public key

### 2. Register Your Public Key

Send your SSH public key to the Control Plane administrator. They must add it to the `AUTHORIZED_CLI_KEYS` setting in the Control Plane configuration.

Your public key is located at: `~/.ssh/aegis_cli.pub`

### 3. Configure IP Whitelist

Ask the administrator to add your IP address to the `WHITELISTED_IPS` setting in the Control Plane configuration.

## Usage

### Connect to Control Plane

```bash
python cli/aegis_cli.py connect <control-plane-host>
```

You will be prompted for your TOTP code. Enter the 6-digit code from your authenticator app.

### Domain Management

#### List all domains
```bash
aegis-cli domain list
```

#### Add a new domain
```bash
aegis-cli domain add example.com --origin https://origin.example.com --protection 1
```

#### Remove a domain
```bash
aegis-cli domain remove example.com
```

### Rate Limiting Configuration

#### Set rate limits for a domain
```bash
aegis-cli ratelimit set example.com \
  --rps 1000 \
  --rpm 50000 \
  --per-ip-rps 10 \
  --per-ip-rpm 500 \
  --burst 20
```

Parameters:
- `--rps`: Global requests per second limit
- `--rpm`: Global requests per minute limit
- `--per-ip-rps`: Per-IP requests per second limit
- `--per-ip-rpm`: Per-IP requests per minute limit
- `--burst`: Burst allowance (number of requests above limit allowed temporarily)

#### View rate limiting configuration
```bash
aegis-cli ratelimit show example.com
```

### Protection Level Management

Set protection level (1-5, where 5 is maximum):

```bash
aegis-cli protection set example.com 3
```

Protection levels:
- **1**: Minimal - Basic bot filtering only
- **2**: Low - JavaScript challenge for suspicious IPs
- **3**: Medium - Active JavaScript challenges + CAPTCHA for high-risk
- **4**: High - Aggressive filtering, CAPTCHA for most traffic
- **5**: Maximum - I'm Under Attack mode, CAPTCHA for all

### Statistics

View real-time statistics:

```bash
aegis-cli stats example.com
```

### Audit Log

View recent security and configuration events:

```bash
aegis-cli audit
```

## Configuration Presets

### For Gaming Servers (GTA 5 RP, Minecraft, etc.)

```bash
aegis-cli ratelimit set game.example.com \
  --rps 5000 \
  --rpm 200000 \
  --per-ip-rps 50 \
  --per-ip-rpm 2000 \
  --burst 100
```

### For Web APIs

```bash
aegis-cli ratelimit set api.example.com \
  --rps 1000 \
  --rpm 50000 \
  --per-ip-rps 10 \
  --per-ip-rpm 500 \
  --burst 20
```

### For Static Websites

```bash
aegis-cli ratelimit set website.example.com \
  --rps 500 \
  --rpm 20000 \
  --per-ip-rps 5 \
  --per-ip-rpm 200 \
  --burst 10
```

## Security Best Practices

### SSH Key Management

1. **Protect Your Private Key**
   - Never share your private key (`~/.ssh/aegis_cli`)
   - Use file permissions: `chmod 600 ~/.ssh/aegis_cli`
   
2. **Key Rotation**
   - Rotate keys every 90 days
   - Run setup again and notify administrator to update authorized keys

### TOTP Management

1. **Backup Your Secret**
   - Save the TOTP secret securely (it's in `~/.aegis/totp_secret`)
   - Store backup codes if provided
   
2. **Multiple Devices**
   - You can add the same TOTP secret to multiple authenticator apps
   - Useful for backup in case you lose your primary device

### Access Control

1. **Use VPN**
   - Connect through VPN when accessing from public networks
   - Ensure your VPN exit IP is whitelisted

2. **Regular Audit**
   - Review audit logs regularly: `aegis-cli audit`
   - Check for any unauthorized access attempts

3. **Session Hygiene**
   - Sessions expire after 30 minutes of inactivity
   - Always verify you're connected: check the welcome message

## Troubleshooting

### "SSH key not authorized"

Your public key is not in the Control Plane's `AUTHORIZED_CLI_KEYS` list. Contact the administrator to add it.

### "Invalid TOTP token"

- Check that your system time is synchronized (TOTP is time-based)
- Make sure you're using the correct TOTP secret
- Try the next code if the current one is about to expire

### "IP address not whitelisted"

Your current IP is not in the `WHITELISTED_IPS` list. Contact the administrator to add it.

### "Session expired"

Your session has timed out (30 minutes). Reconnect:

```bash
aegis-cli connect <control-plane-host>
```

## Recovery Procedures

### Lost TOTP Access

1. Contact Control Plane administrator
2. They can temporarily disable 2FA for your account
3. Run setup again: `python cli/setup_2fa.py`
4. Notify administrator to re-enable 2FA

### Lost SSH Key

1. Run setup again: `python cli/setup_2fa.py`
2. Send new public key to administrator
3. Administrator updates `AUTHORIZED_CLI_KEYS`

## Memory Optimization (4GB RAM Constraint)

The rate limiting system is optimized for servers with limited memory:

1. **HyperLogLog for Unique IP Tracking**
   - Uses ~12KB per domain instead of MBs
   - 99.9% accuracy

2. **Automatic Counter Expiration**
   - Old counters auto-expire after 2-5 minutes
   - No manual cleanup needed

3. **Limits on Configuration Size**
   - Max 10,000 IPs per whitelist/blacklist
   - Max 1M requests per second (per limit type)

## Support

For issues or questions:
- Check audit logs: `aegis-cli audit`
- Review this documentation
- Contact your Control Plane administrator
