"""Synthetic production-browser supervisor. Test routes never enter the shipped app."""
import gc
import os
from pathlib import Path
import subprocess
import sys
import time
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cryptography.fernet import Fernet
from poisontrace.production import RuntimeConfig, build_application, initialize_admin


def child():
    import uvicorn
    clock_file = Path(os.environ['POISONTRACE_TEST_CLOCK_FILE'])
    def clock():
        return time.time() + float(clock_file.read_text())
    app = build_application(clock=clock)
    tls = dict(ssl_certfile=os.environ['POISONTRACE_TEST_CERT'], ssl_keyfile=os.environ['POISONTRACE_TEST_KEY']) if os.environ['POISONTRACE_PROFILE'] == 'hosted' else {}
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=4176, log_level="error", timeout_graceful_shutdown=5, proxy_headers=False, **tls))
    restart = False

    @app.post('/__test_advance')
    def advance():
        clock_file.write_text(str(float(clock_file.read_text()) + 28800))
        return {'advanced': True}

    @app.post("/__test_pid")
    def process_identity():
        return {"pid": os.getpid()}

    @app.post("/__test_restart")
    def restart_server():
        nonlocal restart
        restart = True
        server.should_exit = True
        return {"restarting": True}

    @app.post("/__test_shutdown")
    def stop():
        server.should_exit = True
        return {"stopping": True}

    server.run()
    gc.collect()
    return 75 if restart else 0


if __name__ == "__main__":
    if "--child" in sys.argv:
        sys.exit(child())
    project = Path(__file__).resolve().parents[2]
    scratch = Path(os.environ['POISONTRACE_VERIFY_STATE']) if os.environ.get('POISONTRACE_VERIFY_STATE') else project / ".scratch" / "production-browser"
    scratch.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=scratch) as directory:
        # Only explicitly supplied synthetic configuration reaches the subprocess.
        env = {key: value for key, value in os.environ.items() if not key.startswith(("POISONTRACE_", "OPENAI_", "GOOGLE_", "GEMINI_"))}
        env.update(POISONTRACE_PROFILE=os.environ.get("POISONTRACE_TEST_CONTENT_PROFILE", "local"), POISONTRACE_DATA_ROOT=directory,
                   POISONTRACE_FRONTEND_ROOT=str(project / "frontend/dist"),
                   POISONTRACE_SECRETS_KEY=Fernet.generate_key().decode())
        clock_file = Path(directory)/'test-clock'
        clock_file.write_text('0')
        env['POISONTRACE_TEST_CLOCK_FILE'] = str(clock_file)
        env['POISONTRACE_PUBLIC_ORIGIN'] = 'https://127.0.0.1:4176'
        if env['POISONTRACE_PROFILE'] == 'hosted':
            from datetime import datetime, timedelta, timezone
            from ipaddress import ip_address
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            name = x509.Name([x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, 'Synthetic localhost')])
            now = datetime.now(timezone.utc)
            cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
                    .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1))
                    .not_valid_after(now+timedelta(days=1)).add_extension(x509.SubjectAlternativeName([x509.IPAddress(ip_address('127.0.0.1'))]), critical=False)
                    .sign(key, hashes.SHA256()))
            cert_file, key_file = Path(directory)/'synthetic-cert.pem', Path(directory)/'synthetic-key.pem'
            cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            key_file.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
            env.update(POISONTRACE_TEST_CERT=str(cert_file), POISONTRACE_TEST_KEY=str(key_file))
        config = RuntimeConfig.from_environment(env)
        initialize_admin(config, "synthetic-operator", "synthetic-operator-passcode")
        gc.collect()
        while True:
            process = subprocess.Popen([sys.executable, __file__, "--child"], env=env)
            try:
                code = process.wait()
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=15)
            if code != 75:
                sys.exit(code)
