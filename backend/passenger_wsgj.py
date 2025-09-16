import sys
import os

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(__file__))

# Importa sua aplicação Flask
from app import app as application

# Opcional: Configurações específicas para produção
if __name__ == "__main__":
    application.run()