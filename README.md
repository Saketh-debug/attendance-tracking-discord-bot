This bot is built using Python, discord.py, and PostgreSQL as the backend database. Discord categories represent class sections, and every student is stored in the database with a fixed section. When a teacher types roll numbers like 3,7,12 in a section’s attendance channel, the bot automatically marks everyone present and those numbers absent for the day. It supports simple commands such as !sectionpdf to generate a daily attendance PDF, !studentstats to get a full student statistics report, !lowattendance 75 to list and tag students below a given percentage, and !exportexcel to download a complete Excel workbook with section-wise attendance history. The stack makes the system fast, reliable, and easy to use in real classrooms.

## Render deployment

This repo includes `render.yaml` for deploying the bot as a free Render Web Service.

Render settings:

```txt
Build Command: pip install -r requirements.txt
Start Command: python bot.py
```

Required environment variables:

```txt
DISCORD_TOKEN
DB_NAME
DB_USER
DB_PASS
DB_HOST
DB_PORT
```

Do not commit a real `.env` file. Use `.env.example` as the template for local setup, and add the real values in the Render dashboard.

The bot exposes these health endpoints for uptime checks:

```txt
/
/health
```

To reduce free-tier sleeping, configure an external uptime monitor such as UptimeRobot or Better Stack to ping:

```txt
https://your-render-service-name.onrender.com/health
```

Use a 5-10 minute interval. Render free web services can still restart, and free Postgres databases have their own limits, so this setup is best for hobby/testing use rather than critical production use.
