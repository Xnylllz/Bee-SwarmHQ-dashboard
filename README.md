# Bee Swarm / Natro Dashboard for macOS

A modular desktop dashboard app for macOS built with Python, `customtkinter`, `discord.py`, SQLite, Pillow, and `python-dotenv`.

## Features

- Dynamic account tabs stored in SQLite
- Discord bot listener running in a background thread
- One-click `?start`, `?pause`, `?stop`, and `?hr` command buttons per account tab
- Announcement ingestion with relevance sorting
- Dedicated Hourly Reports page for Natro hourly image posts
- Roblox account linking for per-tab circular avatar headshots
- Parsing for Natro-style stat updates
- Modern dark / black default UI with customizable accent color
- Nine switchable font presets with both basic and more stylized readable options
- Background image upload with dim and blur controls
- Simulated glass-style panels for a modern layered look
- Live stats cards, history search, recent image gallery, and trend chart
- Compare page for viewing multiple accounts side by side
- Full app config export/import for moving tabs and settings between installs
- Local caching of Discord attachments
- Background-running mode that can keep Discord syncing after you close the main window
- Optional macOS menu bar helper for quick restore and quit actions
- Launch-at-login support through a macOS LaunchAgent
- Native macOS notifications for hourly reports and offline alerts
- In-app Setup Guide page for first-run onboarding
- PyInstaller-based standalone macOS `.app` packaging support
- DMG build script and GitHub Actions build workflow
- Keyboard shortcuts for quick use: `Cmd+R` refresh, `Cmd+,` settings, `Esc` back to dashboard
- Expandable project structure for future graphs, alerts, compare, and gallery pages

## Project Structure

```text
app/
  core/
  data/
  discord_client/
  parsing/
  services/
  ui/
    components/
    pages/
  utils/
assets/
cache/
data/
tests/
```

## macOS Setup

1. Create and activate a virtual environment:

```bash
cd /Users/xny/Documents/Codex/2026-04-17-build-me-a-full-desktop-dashboard
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the environment template:

```bash
cp .env.example .env
```

4. Put your Discord bot token in `.env`.

5. Start the app:

```bash
python3 -m app.main
```

## Full Setup Tutorial

### 1. Create your Discord bot

- Go to the Discord Developer Portal.
- Create a bot or use your existing bot.
- Turn on `MESSAGE CONTENT INTENT`.
- Invite the bot to your server.
- Give it:
  - read access to the update channels
  - read access to the hourly-report channels
  - send-message access in the command channel if you want Bee HQ to send `?start`, `?pause`, `?stop`, or `?hr`

### 2. Enable Discord developer mode

- In Discord, open `User Settings -> Advanced`.
- Turn on `Developer Mode`.
- You can now right click a channel and choose `Copy Channel ID`.
- You can also right click the source bot/app and choose `Copy User ID` if you want strict source filtering.

### 3. Start Bee HQ and open the Guide page

- On first run, Bee HQ will open the in-app Setup Guide automatically if the bot token or channel links are still missing.
- You can also open it later from the `Guide` button in the top navigation.

### 4. Save the Discord token

- Open `Settings`.
- Paste the token into `Bot Token`.
- Click `Save Discord Settings`.

### 5. Create one tab per macro/account

- Click `+ New Tab`.
- Fill in:
  - `Tab Name`
  - `Account Label`
  - `Roblox Username` if you want the round avatar
  - `Update Channel ID`
  - `Command Channel ID` if commands should go somewhere else
  - `Announcement Channel ID` if announcements are separate
- Save the tab.

### 6. Route each Discord channel to the matching tab

The intended setup is:

- `Discord channel A -> App tab A`
- `Discord channel B -> App tab B`
- `Discord channel C -> App tab C`

If a channel has extra chatter:

- set `Source Bot Name or User ID`
- keep `Only Ingest Bot Messages` on

That makes the routing much cleaner.

### 7. Hourly reports

- If Natro already posts automatic hourly images in the update channel, Bee HQ will capture them automatically.
- Open the `Hourly` page to see them.
- The app labels them with readable times such as `Hourly Report: 9:00 PM`.

### 8. Background behavior

- If `Keep Running In Background When Window Closes` is on, closing the window does not fully quit Bee HQ.
- Bee HQ can keep syncing Discord in the background.
- If `Enable macOS Menu Bar Helper` is on and `rumps` is installed, you can restore or quit Bee HQ from the menu bar.

### 9. If Bee HQ was fully closed overnight

- Bee HQ does not listen live while fully closed.
- But when you reopen it, startup catch-up can pull recent missed messages back into the app.
- This is especially useful for missed hourly reports.
- The catch-up window is controlled by `Catch Up Missed Updates On Launch (hours)` in Settings.

### 10. Optional quality-of-life settings

In `Settings -> Advanced`, you can also turn on:

- `Enable macOS Desktop Notifications`
- `Launch Bee HQ At Login`
- `Keep Running In Background When Window Closes`
- `Enable macOS Menu Bar Helper If Available`

In `Settings -> Appearance`, you can customize:

- theme preset
- font preset
- accent color
- uploaded background image
- gradient background
- transparent panel look

### 11. Daily use

- Open the app.
- Pick the account tab you want.
- Use the command buttons to send:
  - `?start`
  - `?pause`
  - `?stop`
  - `?hr`
- Watch live updates on the Dashboard page.
- Watch automatic hourly screenshots on the Hourly page.
- Open the Compare page to see which account is strongest at a glance.

## Upload To GitHub

From the project folder:

```bash
cd /Users/xny/Documents/Codex/2026-04-17-build-me-a-full-desktop-dashboard
git init
git add .
git commit -m "Initial Bee HQ dashboard app"
```

Then create an empty GitHub repository in your browser, and run:

```bash
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

If GitHub prompts for authentication, use either:

- GitHub Desktop
- the `gh` CLI
- a personal access token if Git asks for a password

Important:

- do not commit your real `.env` if it contains your Discord bot token
- keep `.env.example` in the repo, but keep your real `.env` local

## Build A Standalone macOS App

If you want Bee HQ as a real `.app` bundle:

```bash
cd /Users/xny/Documents/Codex/2026-04-17-build-me-a-full-desktop-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-build.txt
chmod +x scripts/build_macos_app.sh
./scripts/build_macos_app.sh
```

That should create:

```bash
dist/BeeHQ.app
```

To build a DMG too:

```bash
chmod +x scripts/build_macos_dmg.sh
./scripts/build_macos_dmg.sh
```

That should create:

```bash
dist/BeeHQ-macOS.dmg
```

Packaged app note:

- when Bee HQ runs as a packaged app, it stores writable files under `~/Library/Application Support/BeeHQ`
- that includes the local database, cache, exports, and `.env`

## Build On GitHub Automatically

This repo now includes:

```text
.github/workflows/build-macos.yml
```

After you push to GitHub:

1. Open the repo on GitHub.
2. Go to `Actions`.
3. Open `Build macOS App`.
4. Run it, or let it run automatically on pushes to `main`.
5. Download the generated artifacts:
   - `BeeHQ-app`
   - `BeeHQ-dmg`

## Download From GitHub And Run It

On another Mac:

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m app.main
```

Then:

1. Put your Discord bot token into `.env` or into Settings after launch.
2. Re-create or import your config.

If you exported your Bee HQ config from the first Mac:

1. Open Bee HQ on the new Mac.
2. Go to `Settings`.
3. Click `Import App Config`.
4. Choose the exported JSON file.

That restores your tabs and app settings much faster than rebuilding everything manually.

## Download The Built App From GitHub Actions

If you do not want to build from source:

1. Open your GitHub repo.
2. Go to `Actions`.
3. Open the latest successful `Build macOS App` run.
4. Download the `BeeHQ-dmg` artifact.
5. Open the DMG and drag `BeeHQ.app` into `Applications`.

If macOS warns that the app is unsigned, that is expected for a local/self-built app until you sign and notarize it.
You can usually open it by right clicking the app and choosing `Open`.

## Discord Bot Notes

- Enable the `MESSAGE CONTENT INTENT` for your Discord bot in the Discord developer portal.
- Invite the bot to the server and give it read access to the channels you want to watch.
- If you want the dashboard to send macro commands, the bot also needs permission to send messages in the linked command channels.
- You can also enter or update the token in the app settings screen.

## Test With Fake Data

You can seed the local database without Discord:

```bash
python3 -m app.main --seed-demo
```

## Current Implementation Notes

- The glass mode is a macOS-friendly simulated glass look using tinted panels over a background image. `tkinter` does not provide true per-widget alpha glass rendering, so the effect is styled rather than native transparent blur.
- If `rumps` is installed, the optional macOS menu bar helper can show a small menu bar app with quick Show/Quit actions while Bee HQ keeps syncing in the background.
- Launch at login is implemented with a user LaunchAgent plist in `~/Library/LaunchAgents`.
- Standalone macOS packaging is provided through `PyInstaller` in `packaging/BeeHQ.spec`.
- Attachment caching works for Discord CDN URLs when the bot has access and the local machine has network access.
- Drag-to-reorder tabs is implemented in the sidebar via move mode controls for reliability in `customtkinter`.
- Frequent live update messages and standalone hourly-report replies are both parsed into a merged dashboard snapshot, so a newer manual `?hr` reply does not wipe out the richer live stats cards.
- Hourly image posts like `"[09:00:00] Hourly Report"` are captured into their own page per account when they arrive through the linked Discord channel.
- If the app was fully closed overnight, startup catch-up can still sync recent missed hourly reports into the Hourly page, including the attached image and the report time label.
- Each app tab can be tied to one Discord update channel, and you can optionally set a source bot name or user ID so only that bot's messages are ingested for the tab.
- Each tab can also store a Roblox username; the app resolves the profile through Roblox's official user lookup and avatar headshot APIs and shows the result as a circular cached profile image.
