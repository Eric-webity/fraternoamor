#!/bin/bash
echo "🚀 Iniciando Fraternoamor..."
cd backend
gunicorn app:app --bind 0.0.0.0:$PORT

