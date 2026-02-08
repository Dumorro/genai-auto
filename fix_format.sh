#!/bin/bash
# Auto-fix formatação e style

cd ~/Documents/Repos/genai-auto

# Instalar ferramentas se necessário
pip install -q ruff black isort

# 1. Auto-fix com ruff (safe fixes only)
echo "🔧 Running ruff --fix..."
ruff check src/ tests/ --fix --select I,W,UP --unsafe-fixes

# 2. Format com black
echo "🎨 Running black..."
black src/ tests/

# 3. Sort imports com isort
echo "📦 Running isort..."
isort src/ tests/

echo "✅ Auto-formatting complete!"
