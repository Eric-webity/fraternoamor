#!/bin/bash
echo "🚀 Instalando dependências do Fraternoamor..."
cd backend
pip install --upgrade pip
pip install -r requirements.txt
echo "📦 Iniciando aplicação..."
gunicorn app:app --bind 0.0.0.0:$PORT