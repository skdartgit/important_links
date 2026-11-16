#!/data/data/com.termux/files/usr/bin/bash
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    python -m venv .venv
fi

source .venv/bin/activate

if ! python -c "import flask" >/dev/null 2>&1; then
    pip install -r requirements.txt
fi

echo ""
echo "======================================"
echo "       IMPORTANT LINKS IS RUNNING"
echo "======================================"
echo "Open in your phone browser:"
echo "http://127.0.0.1:5000"
echo ""
echo "Admin Login:"
echo "Username: admin"
echo "Password: 12345"
echo ""
echo "Press CTRL+C to stop the server."
echo "======================================"

python app.py
