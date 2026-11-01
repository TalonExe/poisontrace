# Launch PoisonTrace

From the `Project` directory, set the local encryption key and run:

```powershell
$env:POISONTRACE_SECRETS_KEY = "<local Fernet key>"
.venv\Scripts\python.exe scripts\launch.py
```

On macOS or Linux:

```bash
export POISONTRACE_SECRETS_KEY="<local Fernet key>"
.venv/bin/python scripts/launch.py
```

The launcher starts the API at `http://127.0.0.1:8000` and the Vite dashboard at `http://127.0.0.1:5173`. It forwards both service logs and stops both services when you press `Ctrl+C`.

Create a local Fernet key once with:

```text
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

The launcher does not create credentials or API keys. Provider credentials remain managed by PoisonTrace's local encrypted credential store.
