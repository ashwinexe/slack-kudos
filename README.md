# Slack Kudos Bot
Made for Devfolio

A lightweight Slack bot for giving and tracking kudos. Makes appreciation visible, personal, and meaningful.

## Features

- **`/kudos @user`** - Give kudos in any thread. The bot summarizes the thread context and:
  - Posts a compact message to the `#kudos` channel
  - Sends a private DM to the receiver with their stats

- **`/kudos me`** - View your personal kudos history via DM:
  - This month's count
  - All-time count
  - Recent kudos with context

## Setup

### 1. Create a Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App**
2. Choose **From scratch** and name it "Kudos" (or your preferred name)
3. Select your workspace

### 2. Configure Bot Permissions

Navigate to **OAuth & Permissions** and add these **Bot Token Scopes**:

| Scope | Purpose |
|-------|---------|
| `commands` | Handle slash commands |
| `chat:write` | Post messages |
| `channels:history` | Read public channel threads |
| `groups:history` | Read private channel threads |
| `im:write` | Send DMs |
| `users:read` | Resolve user names |

### 3. Create the Slash Command

Navigate to **Slash Commands** and click **Create New Command**:

- **Command:** `/kudos`
- **Request URL:** Your server URL + `/slack/events` (e.g., `https://your-app.railway.app/slack/events`)
- **Short Description:** Give kudos to a teammate
- **Usage Hint:** `@user` or `me`

### 4. Enable Socket Mode (for development)

1. Go to **Socket Mode** and enable it
2. Generate an **App-Level Token** with `connections:write` scope
3. Save this token as `SLACK_APP_TOKEN`

### 5. Install to Workspace

1. Go to **Install App** and click **Install to Workspace**
2. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### 6. Create a #kudos Channel

Create a channel called `#kudos` (or any name) where public kudos messages will be posted. Copy the channel ID from the URL or channel details.

## Environment Variables

Create a `.env` file (for local development):

```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token
OPENAI_API_KEY=sk-your-openai-key
KUDOS_CHANNEL_ID=C0123456789
```

| Variable | Where to find it |
|----------|------------------|
| `SLACK_BOT_TOKEN` | OAuth & Permissions → Bot User OAuth Token |
| `SLACK_SIGNING_SECRET` | Basic Information → App Credentials |
| `SLACK_APP_TOKEN` | Basic Information → App-Level Tokens |
| `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `KUDOS_CHANNEL_ID` | Right-click channel → View channel details → Copy ID |

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot (Socket Mode)
python app.py
```

## Deploy to Railway

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app) and create a new project
3. Connect your GitHub repo
4. Add the environment variables in Railway dashboard
5. Railway will auto-deploy on push

**Important:** For production, remove `SLACK_APP_TOKEN` to use HTTP mode instead of Socket Mode. Update your Slack app's Request URL to point to your Railway URL.

### Procfile (optional)

If Railway doesn't auto-detect the start command, add a `Procfile`:

```
web: python app.py
```

## Usage

### Give kudos (in a thread)
```
/kudos @teammate
```

The bot will:
1. Read and summarize the thread
2. Post to #kudos: "@you gave kudos to @teammate for fixing the auth bug"
3. DM the receiver with their updated stats

### View your kudos
```
/kudos me
```

You'll receive a DM with your kudos history.

## Architecture

```
app.py          → Main bot logic, slash command handlers
db.py           → SQLite database operations
summarizer.py   → OpenAI thread summarization
messages.py     → Message templates (DM/public)
kudos.db        → SQLite database (auto-created)
```

## License

MIT
