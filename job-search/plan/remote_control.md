# Remote Control — CLI AI Sessions from Phone

**Goal:** Control Claude Code, Codex CLI, Gemini CLI sessions on this server from a phone.

---

## 1. Claude Code Remote Control (Official)

Shipped February 2026. Bridges your local terminal session to claude.ai/code, iOS app, or Android app. Code never leaves your machine — phone is just a window.

```bash
# Start remote control
claude remote-control     # from terminal
/remote-control           # from within a session (or /rc)

# Shows QR code + URL — scan from phone
```

| Aspect | Detail |
|--------|--------|
| **How it works** | WebSocket relay between local terminal and claude.ai/code |
| **Phone access** | Browser (claude.ai/code), Claude iOS app, Claude Android app |
| **What carries over** | Full conversation, filesystem, MCP servers, tools, project config |
| **Security** | End-to-end encrypted, code stays on your machine |
| **Limits** | One remote connection per session, 10-min timeout on disconnect |

### Plan availability

| Plan | Status | Price |
|------|--------|-------|
| **Max** ($100-200/mo) | Available now | $100/mo (5x usage) or $200/mo (20x usage) |
| **Pro** ($20/mo) | Rolling out gradually | $20/mo |
| **Team/Enterprise** | Not yet available | — |

### Auto-enable for all sessions

```bash
claude /config
# -> Enable Remote Control for all sessions: true
```

### Trade-offs

- (+) Zero setup beyond Claude Code v2.1.52+
- (+) Full context preservation — pick up exactly where you left off
- (+) Works on any device with a browser
- (-) Requires Max plan (Pro rollout TBD)
- (-) Terminal must stay open on server
- (-) Network drop > 10 min kills session

---

## 2. Community Claude Code Remote (Telegram/Discord/Slack)

Open-source projects that bridge Claude Code to messaging apps:

| Project | Channel | How it works |
|---------|---------|-------------|
| [Claude-Code-Remote](https://github.com/JessyTsui/Claude-Code-Remote) | Email, Discord, Telegram, LINE | Start tasks locally, get notifications, reply with commands |
| [claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram) | Telegram | Full remote access via Telegram bot with session persistence |
| [afk-code](https://github.com/clharman/afk-code) | Slack, Discord, Telegram | Monitor and interact with sessions from messaging apps |

### How they work

Uses Claude Code **hooks** (shell commands triggered on tool calls) + messaging bot APIs:
1. Claude Code runs locally on your server
2. Hook sends output to Telegram/Discord/Slack bot
3. You reply in the messaging app
4. Bot feeds your reply back to Claude Code

### Setup (example: Telegram)

```bash
# 1. Create a Telegram bot via @BotFather
# 2. Clone the project
git clone https://github.com/RichardAtCT/claude-code-telegram
# 3. Configure bot token + your Telegram user ID
# 4. Run the bridge
```

### Trade-offs

- (+) Works on any plan (Pro included)
- (+) Async: fire-and-forget, get notified when done
- (+) Use an app you already have (Telegram/Slack/Discord)
- (+) Perfect for long-running tasks (pipeline runs)
- (-) DIY setup (bot tokens, API keys, hooks config)
- (-) Security depends on your bot configuration
- (-) Not as seamless as official remote control

---

## 3. Other AI CLI Tools — Remote Status

| Tool | Native Remote | Workaround |
|------|--------------|------------|
| **OpenAI Codex CLI** | None | SSH or web terminal (see section 4) |
| **Gemini CLI** | None (feature requested: [#21559](https://github.com/google-gemini/gemini-cli/issues/21559)) | SSH or web terminal |
| **Aider** | None | SSH or web terminal |
| **Cursor** | None (desktop only) | VS Code tunnels as alternative |

**Bottom line:** Claude Code is the only AI CLI with native remote control as of March 2026. All others need general-purpose terminal access.

---

## 4. General Terminal Remote Access

These work with **any CLI tool** (Claude Code, Codex, Gemini, your pipeline, anything).

### 4a. SSH from Phone

**iOS apps:**

| App | Price | Key Feature |
|-----|-------|-------------|
| **Termius** | Free (basic) | Cross-platform, syncs hosts, Mosh + SFTP |
| **Blink Shell** | ~$16 one-time | Mosh support (survives network drops), power-user favorite |
| **WebSSH** | $12.99 one-time | SSH + SFTP + Telnet + port forwarding |

**Android apps:**

| App | Price | Key Feature |
|-----|-------|-------------|
| **Termius** | Free (basic) | Same cross-platform sync as iOS |
| **JuiceSSH** | Free | Plugin system, AWS integration, great UX |

### Critical: Persistent sessions with tmux

Without `tmux`/`screen`, closing SSH kills your process. Always use:

```bash
# On server
tmux new -s claude       # start named session
claude                   # run Claude Code inside tmux

# On phone (SSH in)
tmux attach -t claude    # reattach to running session

# Detach without killing: Ctrl+B then D
```

### Mosh — Mobile Shell (better than SSH for phones)

```bash
# Install on server
apt install mosh

# Connect from phone (Blink Shell or Termius support Mosh)
mosh user@server         # survives Wi-Fi switches, roaming, sleep
```

Mosh advantages over SSH:
- Survives network changes (Wi-Fi -> cellular)
- Local echo (feels instant even on slow connections)
- Reconnects automatically after sleep

### Trade-offs

- (+) Works with any CLI tool
- (+) Mature, battle-tested
- (+) Full terminal control
- (-) Phone keyboard is painful for terminal work
- (-) Need SSH port open or VPN

---

### 4b. Web Terminals (Browser-Based)

#### ttyd — Lightweight Terminal Sharing

```bash
# Install
apt install ttyd

# Share terminal with auth
ttyd -p 7681 -c user:password bash

# Access from phone browser: https://your-ip:7681
```

| Aspect | Detail |
|--------|--------|
| **What it does** | Shares terminal over WebSocket, xterm.js in browser |
| **Auth** | Basic auth (`-c user:pass`), or put behind reverse proxy |
| **Security** | Add SSL: `ttyd --ssl --ssl-cert cert.pem --ssl-key key.pem` |
| **Best for** | Quick, lightweight browser access |

#### code-server — VS Code in Browser

```bash
# Install
curl -fsSL https://code-server.dev/install.sh | sh

# Run
code-server --bind-addr 0.0.0.0:8080 /root/search
```

| Aspect | Detail |
|--------|--------|
| **What it does** | Full VS Code IDE in browser, including integrated terminal |
| **Auth** | Password in `~/.config/code-server/config.yaml` |
| **Best for** | Full IDE + terminal experience from phone |
| **Trade-off** | Heavier than ttyd, phone screen cramped for full IDE |

#### VS Code Remote Tunnels (Zero Config Networking)

```bash
# On server
code tunnel    # authenticate with GitHub, get tunnel URL

# On phone: open vscode.dev -> connect to tunnel
```

| Aspect | Detail |
|--------|--------|
| **How it works** | Microsoft-hosted relay, no ports to open, no firewall config |
| **Auth** | GitHub account |
| **Best for** | Works through any firewall/NAT without config |
| **Trade-off** | Depends on Microsoft's tunnel service |

---

### 4c. Secure Tunnels (Expose Without Opening Ports)

#### Cloudflare Tunnel

```bash
# Install
curl -fsSL https://get.cloudflare.dev | sh

# Expose ttyd or code-server
cloudflared tunnel --url http://localhost:7681
```

- Gets a public HTTPS URL without opening any ports
- Add Cloudflare Access for SSO/2FA authentication
- Enterprise-grade security

#### Tailscale (Private Mesh VPN)

```bash
# Install on server + phone
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up

# SSH from phone using Tailscale IP (private, encrypted)
ssh user@100.x.y.z
```

- Creates a private mesh network between your devices
- No ports to open, works through NAT
- Free for personal use (up to 100 devices)

---

## 5. Recommended Setup (For Your Use Case)

You want to control this server + AI CLI sessions from your phone, on a Pro plan.

### Immediate (works today)

```
Phone (Termius/Blink) --SSH/Mosh--> Server --tmux--> Claude Code / Codex / Pipeline
```

**Setup time:** 10 minutes
1. Install Termius or Blink Shell on phone
2. Install Mosh on server: `apt install mosh`
3. Always run AI tools inside `tmux`
4. SSH/Mosh from phone, `tmux attach`

### Better (add async notifications)

```
Phone (Telegram) <--bot--> Claude-Code-Remote <--hooks--> Claude Code on server
```

**Setup time:** 30 minutes
- Fire-and-forget: "run the pipeline", get notified when done
- Reply from Telegram to continue the conversation
- Works on Pro plan, no Max needed

### Best (when Pro gets remote control)

```
Phone (Claude iOS app) --E2E encrypted--> Claude Code on server
```

**Setup time:** 0 minutes (just `/rc` in terminal)
- Native experience, full context preservation
- Watch for Pro plan rollout announcement

### For non-Claude tools (Codex, Gemini, pipeline)

```
Phone (browser) --HTTPS--> Cloudflare Tunnel ---> ttyd ---> tmux session
```

**Setup time:** 20 minutes
- Works with any CLI tool
- Secure (Cloudflare handles HTTPS + auth)
- No ports to open

---

## Quick Comparison

| Approach | Works With | Plan | Setup | UX on Phone |
|----------|-----------|------|-------|-------------|
| Claude Remote Control | Claude Code only | Max (Pro soon) | 0 min | Best |
| Telegram bot bridge | Claude Code only | Any | 30 min | Good (async) |
| SSH + tmux + Mosh | Any CLI tool | Any | 10 min | Functional |
| ttyd + Cloudflare | Any CLI tool | Any | 20 min | Good |
| VS Code Tunnel | Any CLI tool | Any | 15 min | Good (IDE) |
| code-server | Any CLI tool | Any | 15 min | Good (IDE) |

---

## Sources

- [Claude Code Remote Control docs](https://code.claude.com/docs/en/remote-control)
- [Claude-Code-Remote (GitHub)](https://github.com/JessyTsui/Claude-Code-Remote)
- [afk-code (GitHub)](https://github.com/clharman/afk-code)
- [claude-code-telegram (GitHub)](https://github.com/RichardAtCT/claude-code-telegram)
- [Gemini CLI remote feature request](https://github.com/google-gemini/gemini-cli/issues/21559)
- [ttyd — terminal over web](https://github.com/tsl0922/ttyd)
- [VS Code Remote Tunnels](https://code.visualstudio.com/docs/remote/tunnels)
- [Tailscale](https://tailscale.com/)
- [Mosh — mobile shell](https://mosh.org/)
