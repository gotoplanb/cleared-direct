# IFR Trainer

Web-based instrument flying proficiency game for GA pilots. Practice radio comms, ATC interaction, instrument scan, checklist discipline, and aeronautical decision making.

**Live:** https://cleared-direct-ec2f6fee8c5e.herokuapp.com/

<img src="docs/qr-code.png" alt="QR code to live app" width="200">

## Local Development

```bash
# Create venv and install deps
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Run migrations (postgres on orginator-postgres-dev, port 5455)
.venv/bin/python manage.py migrate

# Load scenario data
.venv/bin/python manage.py load_scenario fixtures/scenarios/night_ifr_kojm.yaml

# Start dev server
.venv/bin/python manage.py runserver 8301
```

## Deployment

Pushes to `main` auto-deploy to Heroku via GitHub Actions.

- **App:** cleared-direct
- **Database:** Shared postgres on pinnacle-proto-db (tables prefixed `ifr_`)
- **Secret:** `HEROKU_API_KEY` in GitHub repo secrets (expires March 2027)
