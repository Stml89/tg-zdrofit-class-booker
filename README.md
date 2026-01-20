# Zdrofit Class Booker Bot

Telegram bot for monitoring available group classes at Zdrofit fitness centers with automatic notifications.

## Features

- **Telegram Integration** - Manage filters and notifications through Telegram
- **Class Monitoring** - Automatic availability checks every 60 minutes
- **Flexible Filters** - Filter by gyms, trainers, class types, time and weekdays
- **Notifications** - Instant alerts when free spots appear
- **Security** - Password encryption for all users

## Quick Start

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py
```

### Scheduling

CronTrigger(minute="*/5") - every 5min
CronTrigger(minute="0,30") - every 30min
CronTrigger(minute="0", hour="*/2") - every 2h

## Bot Commands

| Command | Description |
|---------|---------|
| `/start` | Start page |
| `/login` | Login to your Zdrofit account |
| `/filters` | Manage filters |
| `/bookings` | View bookings |
| `/past_classes` | View past classes |
| `/logout` | Logout |

## Docker Setup

### Using Docker Compose

```bash
# Start the bot
sudo docker compose build --no-cache && sudo docker compose up -d

# View logs
sudo docker compose logs -f zdrofit-bot

# Stop the bot
docker compose down
```

### Manual Docker Build

```bash
# Build the image
docker build -t zdrofit-bot .

# Run the container
docker run -d \
  --name zdrofit-bot \
  --restart unless-stopped \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  zdrofit-bot
```

## Testing

```bash
# Run all tests
python -m unittest discover tests/ -v

# Run specific module
python -m unittest tests.test_filters -v
```

## Database

### Table Structure

- **users** - User credentials
- **user_filters** - Saved filters
- **available_classes** - Found available classes
- **bookings** - Booked classes
- **filter_catalog** - Filter parameters cache

### SQLite CLI

```bash
sqlite3 data/bot.db

# Commands:
.tables                  # List tables
.schema users            # Show table structure
SELECT * FROM users;     # View data
.exit
```

```bash
# Commands:
manage_db init           # Init database 
manage_db stats          # Show database statistics
manage_db reset          # Reset database state
```

### Programmatic Access

```python
from src.database.db import Database
from src.database.models import User, UserFilter

db = Database()

# Add user
user = User(telegram_id=123, zdrofit_email="user@mail.com", zdrofit_password="pwd")
db.add_user(user)

# Save filter
filter = UserFilter(user_id=123, club_id=7, zone_id="10", timetable_id="20")
db.add_filter(filter)

# Get available classes
classes = db.get_unnotified_classes(user_id=123)
```

## Architecture

```
src/
├── api/              # Zdrofit API client
├── database/         # SQLite operations
├── scheduler/        # Periodic checks
├── telegram_bot/     # Telegram handlers and notifications
└── utils/            # Utilities and logging
```

## Future Plans

- [ ] Support another fitness clubs
- [ ] Implement auto apply to a class
- [ ] Web interface
- [ ] Export to Google Calendar
- [ ] Usage statistics
- [ ] Telegram Mini App

## Configuration

Environment variables in `.env`:
- `TELEGRAM_BOT_TOKEN` - Bot token
- `LOG_LEVEL` - Logging level (DEBUG/INFO/ERROR)

Configuration files:
- `config/config.py` - Main settings
- `.crypto_key` - Encryption key (do not commit!)

## Troubleshooting

```bash
ps aux | grep -E "python|main.py" | grep -v grep

kill -9 <process id>
```