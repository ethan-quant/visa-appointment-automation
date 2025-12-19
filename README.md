# Visa Appointment Automation (Kenya + South Africa)

Portfolio / educational version of two country-specific Python automation tools used to **monitor visa appointment availability** and **send alerts** when slots appear.

> **Safety note:** The default configuration is **DRY_RUN** (demo mode). This repository is intended for educational purposes and process-automation demonstration. Always follow the terms of service and applicable laws for any website you interact with.

## Background
International student-athletes often face significant delays in securing U.S. visa
appointments due to limited availability and highly dynamic scheduling systems.
Missed appointment windows can directly impact enrollment timelines and athletic
eligibility.

This project was developed to explore how automation and monitoring systems can
help surface time-sensitive opportunities in constrained environments while
minimizing risk and unintended actions.

## Repo structure

- `kenya/` – Kenya-specific workflow implementation
- `south_africa/` – South Africa-specific workflow implementation
- `.env.example` – sample environment variables (no secrets)
- `examples/visa.log.redacted` – sample log output (sanitized)

## Quick start

1. Create and activate a virtual environment
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create your local `.env` from the template:
   ```bash
   cp .env.example .env
   ```
4. Run an implementation:
   ```bash
   python kenya/main.py
   # or
   python south_africa/main.py
   ```

## Configuration

All sensitive values (credentials, notification targets) must live in a local `.env` file **that is never committed**. See `.gitignore`.

## What this demonstrates

- Python automation (Selenium)
- Robust error handling and retries
- Logging/monitoring mindset
- Environment-based configuration
- Safeguards to prevent unintended irreversible actions (demo mode)

