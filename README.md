# 📚 tg2kindle — Setup, Usage & Deployment Guide

This guide consolidates deployment and debugging of the `tg2kindle` Telegram-to-Kindle bot.

---

## 🚀 Overview

A Telegram bot that lets users send documents to their Kindle via email — fully automated, free to run, and CI/CD-enabled with GitHub Actions.

---

## ✅ Features

- Document forwarding from Telegram to Kindle
- Personalized sender/receiver setup
- Mailgun integration
- Fallback defaults via `.env`
- GitHub Actions deployment with rollback + Telegram alerts
- Zero-cost hosting using Oracle Cloud Free Tier
- Systemd integration

---

## 🧪 Local Setup Instructions

To get the bot running locally or on a fresh VM:

### 1. Clone the Repository

```bash
git clone https://github.com/bushuyeu/tg2kindle.git
cd tg2kindle
```

### 2. Prepare the Python Environment

```bash
python3.12 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> Make sure you’re using Python 3.12 or later.

### 3. Create Your `.env` File

```bash
touch .env
```

Then fill it out with your own values:

```env
MAILGUN_API_KEY=your-mailgun-api-key
MAILGUN_DOMAIN=yourdomain.com
SENDER_EMAIL=bot@yourdomain.com
RECIPIENT_EMAIL=yourname@kindle.com
TELEGRAM_API_KEY=your-telegram-api-key
```

---

## 🤖 Telegram Bot Commands

- `/start` – Initialize the bot
- `/help` – Show usage instructions
- `/setsender <email>` – Set sender email
- `/newreceiver <label> <email>` – Add a recipient
- `/viewreceivers` – List all recipients
- `/removereceiver <label>` – Remove a recipient
- `/sendto <label>` – Send last uploaded file to given recipient

---

## ⚙️ Environment Defaults

If no user-specific config exists, the following from `.env` will be used:

```env
SENDER_EMAIL=XXXXX@domain.com
RECIPIENT_EMAIL=XXXXXX@kindle.com
```

These map to a Mailgun-managed domain, email address and Kindle device email address respectively.

---

## 🗂 user_data.json Example

```json
{
  "385520681": {
    "sender_email": "p@bushuyeu.com",
    "receivers": {
      "me": "bushuyeu@kindle.com",
      "work": "work@kindle.com"
    }
  }
}
```

---

## 🛠 Mailgun Setup

1. Register at mailgun.com
2. Verify your domain
3. Use the API key and domain in `.env`
4. Whitelist the Kindle address in Amazon

---

## 🤖 Telegram Bot Setup

1. Create via [@BotFather](https://t.me/BotFather)
2. Save token to `.env`
3. Run `/start` in the bot chat

---

## 📣 Telegram Alerts Bot

1. Create a separate bot via BotFather
2. Save token as `TG_BOT_TOKEN`
3. Use `/start` in chat
4. Fetch chat ID with:

```bash
curl -s https://api.telegram.org/bot<token>/getUpdates
```

Add to GitHub Secrets:

- `TG_BOT_TOKEN`
- `TG_CHAT_ID`

---

## ☁️ Oracle Cloud VM Setup (Zero Cost)

1. Create free-tier Oracle Cloud account
2. Choose region `us-sanjose-1`
3. Image: Ubuntu 20.04
4. Shape: VM.Standard.A1.Flex (1 CPU, 1 GB RAM)
5. Add your SSH key

Install Python & dependencies:

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv git
```

---

## 📂 Systemd Setup

Create `/etc/systemd/system/telegram-bot.service`:

```ini
[Unit]
Description=Telegram Bot Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/tg2kindle
ExecStart=/home/ubuntu/tg2kindle/env/bin/python /home/ubuntu/tg2kindle/main.py
Restart=always
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
```

---

## 🚀 GitHub Actions: Deploy with Rollback & Alerts

To enable automated deployment from GitHub to your server, you'll need to set up GitHub Actions in your repository. Here’s how:

### 📁 Step-by-step Setup

1. **Create the required folders**:

   ```bash
   mkdir -p .github/workflows
   ```

2. **Add a deployment workflow file**:
   Inside `.github/workflows/`, create a file named `deploy.yml`. You can copy the example deployment script provided earlier.

3. **Add GitHub Secrets**:
   Navigate to your repo on GitHub:

   - Go to **Settings** → **Secrets and variables** → **Actions**
   - Click **New repository secret**
   - Add the following secrets:
     | Name | Description |
     |-------------------|------------------------------------|
     | `SSH_PRIVATE_KEY` | Your private SSH key (no passphrase) |
     | `SERVER_USER` | Typically `ubuntu` for Oracle Cloud |
     | `SERVER_HOST` | Your VM's public IP or hostname |
     | `TG_BOT_TOKEN` | Telegram bot token for alerts |
     | `TG_CHAT_ID` | Your Telegram user ID |

4. **Push to Main**:
   Once your workflow and secrets are in place, push any change to the `main` branch. GitHub Actions will:
   - SSH into your VM
   - Pull the latest code
   - Restart the systemd service
   - Roll back and notify you via Telegram if anything fails

> You can view Actions runs under the **Actions** tab in your GitHub repository.

## ✅ Conclusion

This bot is designed for zero-cost, always-on Kindle delivery from Telegram with self-healing and alerting built in.

Happy automating! 📬

---
