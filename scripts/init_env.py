import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
example = ROOT / ".env.example"
target = ROOT / ".env"


def main() -> None:
    if target.exists():
        print(f"Environment already exists: {target}")
        return
    content = example.read_text(encoding="utf-8")
    content = content.replace("SECRET_KEY=change-me-with-python-scripts-init-env", f"SECRET_KEY={secrets.token_urlsafe(48)}")
    target.write_text(content, encoding="utf-8")
    print(f"Created {target}")
    print("Add GEMINI_API_KEY and change BOOTSTRAP_ADMIN_PASSWORD before starting the stack.")


if __name__ == "__main__":
    main()
