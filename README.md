# Self-Deployable Kindle Eightsleep Interface

Minimal FastAPI control panel for an Eight Sleep cover, intended for deployment on Modal and use from a Kindle browser.

## Demo

https://github.com/user-attachments/assets/e0a53fb0-e8d2-4252-a88c-40caa5fa466e

## Self-deploy

1. Clone the repo and pull the submodule.

```bash
git clone https://github.com/zsiegel92/eightctl-web.git
cd eightctl-web
git submodule update --init --recursive
```

2. Create the virtualenv, activate it, and install dependencies.

```bash
uv venv
source .venv/bin/activate
uv sync
```

3. Create the Modal secret with the only login allowed for the app.

```bash
uv run python -m modal secret create --force eightsleep-web \
  PY_EIGHTCTL_EMAIL="you@example.com" \
  PY_EIGHTCTL_PASSWORD="your-plaintext-password"
```

4. Deploy to Modal.

```bash
uv run python -m modal deploy main.py
```

The app reads `PY_EIGHTCTL_EMAIL` and `PY_EIGHTCTL_PASSWORD` from the `eightsleep-web` Modal secret. Those same values are used both for the web login form and for `py-eightctl` to authenticate to Eight Sleep.
