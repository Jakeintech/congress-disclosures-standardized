#!/bin/bash
# Build script for admin.js that injects authorized IPs from environment variables
# Usage: ADMIN_ALLOWED_IPS="ip1,ip2" ./scripts/build_admin.sh
# Or: Load from .env file (source .env first)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ADMIN_JS="$PROJECT_ROOT/website/admin.js"
ENV_FILE="$PROJECT_ROOT/.env"

# Try to load from .env file if it exists and ADMIN_ALLOWED_IPS is not set
if [ -z "$ADMIN_ALLOWED_IPS" ] && [ -f "$ENV_FILE" ]; then
    # Source .env file (handles quoted values)
    set -a
    source "$ENV_FILE" 2>/dev/null || true
    set +a
fi

# Check if ADMIN_ALLOWED_IPS is set
if [ -z "$ADMIN_ALLOWED_IPS" ]; then
    echo "❌ Error: ADMIN_ALLOWED_IPS environment variable not set"
    echo "   Set it as: export ADMIN_ALLOWED_IPS=\"ip1,ip2,ip3\""
    echo "   Or create a .env file with: ADMIN_ALLOWED_IPS=\"ip1,ip2,ip3\""
    exit 1
fi

# Parse IPs (comma-separated, trim whitespace)
IFS=',' read -ra IP_ARRAY <<< "$ADMIN_ALLOWED_IPS"
IP_COUNT=0

# Build the IP array string
IP_ARRAY_STRING=""
for ip in "${IP_ARRAY[@]}"; do
    ip=$(echo "$ip" | xargs)  # trim whitespace
    if [ -n "$ip" ]; then
        if [ -n "$IP_ARRAY_STRING" ]; then
            IP_ARRAY_STRING="$IP_ARRAY_STRING,\n"
        fi
        IP_ARRAY_STRING="${IP_ARRAY_STRING}    '${ip}'"
        ((IP_COUNT++))
    fi
done

if [ $IP_COUNT -eq 0 ]; then
    echo "❌ Error: No valid IPs found in ADMIN_ALLOWED_IPS"
    exit 1
fi

echo "📝 Injecting $IP_COUNT authorized IP(s) into admin.js..."

# Create backup
cp "$ADMIN_JS" "$ADMIN_JS.bak"

# Replace the entire AUTHORIZED_IPS array block
# Use Python for more reliable string replacement
python3 << EOF
import re
import sys

# Read the file
with open("$ADMIN_JS", 'r') as f:
    content = f.read()

# Build the new array string
ips = """$IP_ARRAY_STRING"""

# Pattern to match the entire array definition (from const to closing bracket)
pattern = r'const AUTHORIZED_IPS = \[.*?\];'

# Replacement with new IPs
replacement = f'''const AUTHORIZED_IPS = [
{ips}
];'''

# Replace
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back
with open("$ADMIN_JS", 'w') as f:
    f.write(new_content)
EOF

echo "✅ Admin.js updated with authorized IPs"
echo "   IPs: $ADMIN_ALLOWED_IPS"
