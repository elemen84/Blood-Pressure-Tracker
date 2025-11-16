# Blood Pressure Tracker

A Discord bot designed to track, analyze, and visualize blood pressure data using Python, `discord.py`, SQLite, `pandas`, and `matplotlib`.

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd blood_pressure_bot
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Variables:**
    The bot requires two environment variables to run:
    * `DISCORD_TOKEN_TA`: Your Discord bot token.
    * `ALERT_CHANNEL_ID`: The ID of the Discord channel where daily alerts will be posted.

    You can set these in your shell or use a `.env` file (if you set up a loader).


4.  **Bot Setup (Crucial)**

    * Create application in Discord Developer Portal
    * Enable PRESENCE INTENT and MESSAGE CONTENT INTENT
    * Use OAuth2 URL Generator with permissions: Send Messages, Attach Files, Read Message History, Add Reactions


4.  **Run the Bot:**
    ```bash
    python bot.py
    ```

## Usage Commands

The bot uses the prefix `!` for all commands.

| Command | Usage | Description |
| :--- | :--- | :--- |
| `!register <sys> <dia> <slot> [date]` | `!register 120 80 m 15-11-25` | Registers a new BP reading. Slots: `m` (morning), `a` (afternoon), `n` (night). Date is optional (`dd-mm-yy`). |
| `!last [count]` | `!last 10` | Shows the last 5 (or `<count>`) blood pressure records. |
| `!edit <sys> <dia> <slot> <date>` | `!edit 125 85 m 15-11-25` | Edits an existing record for a specific date/slot. Requires confirmation. |
| `!delete` | `!delete` | Deletes the very last recorded entry (based on timestamp). Requires confirmation. |
| `!export` | `!export` | Exports all recorded data to a CSV file. |
| `!graph [days]` | `!graph 7` | Generates a graph for the last 7 (or `<days>`) days of readings. |
| `!graph_m [days]` | `!graph_m 30` | Generates a graph for morning readings only. (`!graph_a`, `!graph_n` for others). |
| `!graph_month <MM-YY>` | `!graph_month 11-25` | Generates a graph of daily averages for a specific month. (`!graph_month_m`, etc.) |
| `!data [days]` | `!data 14` | Shows a table of daily average BP for the last 14 (or `<days>`) days. |
| `!data_month <MM-YY>` | `!data_month 11-25` | Shows a table of daily average BP for a specific month. (`!data_month_m`, etc.) |

## Scheduled Tasks

* **Daily Alert:** Checks the average blood pressure over the last 10 days at **8:00 AM** (Europe/Madrid time). If the average exceeds **135/85** mmHg, it posts an alert and a graph to the configured `ALERT_CHANNEL_ID`.
* **Daily Backup:** Creates a backup of the `blood_pressure.db` file in the `./backup` directory and cleans up old backups (keeps the last 7).

---

## Example Outputs

### Data Table (`!data_m 7`)

```markdown
📋 Blood Pressure Data - Last 7 Days (Morning Slot)
Date        Systolic    Diastolic
-----------------------------------
15-11-25    120         80
14-11-25    118         79
13-11-25    125         82
...
-----------------------------------
AVERAGE     121         80