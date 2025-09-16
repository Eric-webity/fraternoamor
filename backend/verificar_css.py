import re
from bs4 import BeautifulSoup

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
    except FileNotFoundError:
        print(f"Erro: Arquivo HTML '{arquivo_html}' não encontrado.")
        return None

def extrair_classes_css(arquivo_css):
    """Extrai todos os seletores de classe de um arquivo CSS."""
    try:
        with open(arquivo_css, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Regex para encontrar seletores de classe (ex: .minha-classe, .outra-classe)
        # Ignora pseudo-classes como :hover
        classes = set(re.findall(r'\.([a-zA-Z0-9_-]+)', content))
        return classes
    except FileNotFoundError:
        print(f"Erro: Arquivo CSS '{arquivo_css}' não encontrado.")
        return None

def comparar_arquivos(html_file, css_file):
    """Compara as classes do HTML com as do CSS e reporta as que faltam."""
    print("Iniciando a verificação...")
    
    classes_html = extrair_classes_html(html_file)
    classes_css = extrair_classes_css(css_file)

    if classes_html is None or classes_css is None:
        print("Verificação interrompida devido a erro na leitura dos arquivos.")
        return

    print(f"\nEncontradas {len(classes_html)} classes únicas no HTML.")
    print(f"Encontradas {len(classes_css)} definições de classe no CSS.")
    
    # Compara as classes do HTML com as definidas no CSS
    classes_faltando = classes_html - classes_css
    
    print("\n--- Resultado da Análise ---")
    if not classes_faltando:
        print("✅ Todas as classes usadas no HTML parecem ter uma definição no CSS.")
    else:
        print(f"⚠️ Atenção! As seguintes {len(classes_faltando)} classes são usadas no HTML, mas não foram encontradas no CSS:")
        for cls in sorted(list(classes_faltando)):
            print(f"  - {cls}")
    print("--------------------------")

if __name__ == "__main__":
    comparar_arquivos('dashboard_membro.html', 'estilos.css')