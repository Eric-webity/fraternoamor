import os
import re
import ast
from bs4 import BeautifulSoup

# Funções auxiliares para extrair classes (pode colocar no início do arquivo)
def extrair_classes_html(arquivo_html):
    """Extrai todas as classes únicas de um arquivo HTML."""
    try:
        with open(arquivo_html, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
        classes = set()
        for tag in soup.find_all(True, class_=True):
            for cls in tag.get('class', []):
                classes.add(cls)
        return classes
    except Exception as e:
        print(f"  [AVISO] Não foi possível ler o arquivo HTML '{arquivo_html}': {e}")
        return set()

def extrair_classes_css(arquivo_css):
    """Extrai todos os seletores de classe de um arquivo CSS."""
    try:
        with open(arquivo_css, 'r', encoding='utf-8') as f:
            content = f.read()
        classes = set(re.findall(r'\.([a-zA-Z0-9_-]+)', content))
        return classes
    except FileNotFoundError:
        print(f"  [ERRO] Arquivo CSS principal '{arquivo_css}' não encontrado.")
        return None

# --- SUAS FUNÇÕES EXISTENTES (simuladas aqui) ---
def print_file_structure():
    print("\n--- 1. Estrutura de Arquivos do Projeto ---")
    # Sua lógica para imprimir a árvore de diretórios
    print("...")

def check_folders():
    print("\n--- 2. Verificando Estrutura de Pastas ---")
    # Sua lógica para verificar as pastas
    print("  [OK] Pasta 'static' encontrada.")
    # ... etc

def check_app_py_integrity():
    print("\n--- 3. Verificando Integridade do app.py ---")
    # Sua lógica para verificar a sintaxe do app.py
    print("  [OK] Arquivo 'app.py' carregado sem erros de sintaxe.")

def check_routes_and_templates():
    print("\n--- 4. Verificando Rotas e Templates ---")
    # Sua lógica para verificar as rotas e templates
    print("  [ERRO] Template 'admin/adicionar_categoria_material.html' referenciado no app.py NÃO EXISTE...")
    # ... etc

# --- NOVA FUNÇÃO PARA VERIFICAÇÃO HTML/CSS ---
def check_html_css_consistency(templates_dir='templates', css_file='static/css/estilos.css'):
    """Verifica todos os arquivos HTML em busca de classes não definidas no CSS."""
    print("\n--- 5. Verificando Consistência HTML/CSS ---")
    
    classes_css = extrair_classes_css(css_file)
    if classes_css is None:
        return # Interrompe se o arquivo CSS não for encontrado

    print(f"  Encontradas {len(classes_css)} definições de classe no arquivo '{css_file}'.")
    print("  Analisando arquivos de template...")

    problemas_encontrados = False
    
    # Percorre todos os arquivos e subpastas dentro de 'templates'
    for root, _, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                html_path = os.path.join(root, file)
                classes_html = extrair_classes_html(html_path)
                
                classes_faltando = classes_html - classes_css
                
                if classes_faltando:
                    problemas_encontrados = True
                    # Mostra o caminho relativo para ficar mais limpo
                    caminho_relativo = os.path.relpath(html_path, templates_dir)
                    print(f"\n  [AVISO] No arquivo '{caminho_relativo}':")
                    print(f"    - Classes usadas mas não definidas no CSS: {', '.join(sorted(list(classes_faltando)))}")

    if not problemas_encontrados:
        print("\n  [OK] Todas as classes usadas nos templates HTML parecem ter uma definição no CSS.")
    
    return not problemas_encontrados

# --- FUNÇÃO PRINCIPAL (ATUALIZADA) ---
def main():
    print("Iniciando verificação avançada do projeto Fraterno Amor...")
    
    # Suas chamadas existentes
    print_file_structure()
    check_folders()
    check_app_py_integrity()
    check_routes_and_templates()

    # Adicionando a nova verificação
    css_ok = check_html_css_consistency()

    print("\n--- Diagnóstico Final ---")
    # Lógica final para exibir o status
    # (Você pode integrar o `css_ok` na sua lógica de erro final)
    print("  Concluído.")


if __name__ == "__main__":
    main()