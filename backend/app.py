import os
import datetime
import urllib.parse
import io
import csv
from flask import Flask, render_template, request, redirect, url_for, flash, Response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from sqlalchemy import func

# --- 1. CONFIGURAÇÃO DA APLICAÇÃO ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-dificil-de-adivinhar'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# --- 2. INICIALIZAÇÃO DE EXTENSÕES ---
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, faça o login para acessar esta página."
login_manager.login_message_category = 'info'

# --- 3. MODELOS DO BANCO DE DADOS ---
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

user_category_association = db.Table('user_category',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuario.id'), primary_key=True),
    db.Column('categoria_usuario_id', db.Integer, db.ForeignKey('categoria_usuario.id'), primary_key=True)
)

class CategoriaUsuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    nivel = db.Column(db.Integer, nullable=False, default=0) # Nível hierárquico
    usuarios = db.relationship('Usuario', secondary=user_category_association, back_populates='categorias')

class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False, server_default='False')
    categorias = db.relationship('CategoriaUsuario', secondary=user_category_association, back_populates='usuarios')

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    estoque = db.Column(db.Integer, default=0)
    imagem_url = db.Column(db.String(200), nullable=True)

class Configuracao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), unique=True, nullable=False)
    valor = db.Column(db.Text, nullable=True)

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    contato = db.Column(db.String(50), nullable=True)

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    data_pedido = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    valor_total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Recebido')
    itens = db.relationship('ItemPedido', backref='pedido', lazy=True, cascade="all, delete-orphan")
    cliente = db.relationship('Cliente', backref='pedidos')

class ItemPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    produto = db.relationship('Produto')

class CategoriaCurso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    cursos = db.relationship('Curso', backref='categoria', lazy=True)

class Curso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    link_video = db.Column(db.String(200), nullable=False)
    imagem_thumbnail = db.Column(db.String(200), nullable=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria_curso.id'), nullable=False)
    arquivo_anexo = db.Column(db.String(200), nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    categoria_permissao_id = db.Column(db.Integer, db.ForeignKey('categoria_usuario.id'), nullable=True)

# --- FUNÇÃO AUXILIAR ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- 4. ROTAS ---

# 4.1 Rotas Públicas e da Lanchonete
@app.route('/')
def home():
    return render_template('index.html')
@app.route('/historia')
def historia():
    return render_template('nossa-historia.html')
@app.route('/identidade')
def identidade():
    return render_template('nossa-identidade.html')
@app.route('/contato')
def contato():
    return render_template('contato.html')
@app.route('/lanchonete')
def lanchonete():
    produtos = Produto.query.all()
    aviso = Configuracao.query.filter_by(chave='aviso_lanchonete').first()
    status_lanchonete = Configuracao.query.filter_by(chave='lanchonete_status').first()
    return render_template('lanchonete.html', produtos=produtos, aviso_lanchonete=aviso, status_lanchonete=status_lanchonete)

@app.route('/finalizar-pedido', methods=['POST'])
def finalizar_pedido():
    dados = request.get_json()
    nome_cliente = dados['nome_cliente']
    carrinho = dados['carrinho']
    cliente = Cliente.query.filter_by(nome=nome_cliente).first()
    if not cliente:
        cliente = Cliente(nome=nome_cliente)
        db.session.add(cliente)
        db.session.commit()
    valor_total = sum(item['preco'] * item['quantidade'] for item in carrinho)
    novo_pedido = Pedido(cliente_id=cliente.id, valor_total=valor_total)
    db.session.add(novo_pedido)
    db.session.commit()
    for item in carrinho:
        produto = Produto.query.get(item['id'])
        if produto and produto.estoque >= item['quantidade']:
            novo_item = ItemPedido(pedido_id=novo_pedido.id, produto_id=produto.id, quantidade=item['quantidade'], preco_unitario=produto.preco)
            db.session.add(novo_item)
            produto.estoque -= item['quantidade']
    db.session.commit()
    return {'message': 'Pedido recebido com sucesso!'}

# 4.2 Rotas de Autenticação e Portal do Membro
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        usuario = Usuario.query.filter_by(username=username).first()
        if usuario and bcrypt.check_password_hash(usuario.password_hash, password):
            login_user(usuario)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Login inválido. Verifique seu nome de usuário e senha.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu com sucesso.', 'info')
    return redirect(url_for('home'))

from sqlalchemy import or_ # Garanta que esta importação está no topo do arquivo

# ... (outras importações) ...

@app.route('/admin/avisos', methods=['GET', 'POST'])
@login_required
def gerenciar_avisos():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        mensagem = request.form.get('mensagem')
        categoria_id = request.form.get('categoria_permissao_id')

        if not mensagem:
            flash('A mensagem do aviso не pode estar vazia.', 'danger')
        else:
            # Se categoria_id for uma string vazia (""), converte para None
            categoria_alvo_id = int(categoria_id) if categoria_id else None
            novo_aviso = Aviso(mensagem=mensagem, categoria_permissao_id=categoria_alvo_id)
            db.session.add(novo_aviso)
            db.session.commit()
            flash('Aviso criado com sucesso!', 'success')
        
        return redirect(url_for('gerenciar_avisos'))

    avisos = Aviso.query.order_by(Aviso.data_criacao.desc()).all()
    categorias_usuario = CategoriaUsuario.query.order_by(CategoriaUsuario.nome).all()
    return render_template('admin/gerenciar_avisos.html', avisos=avisos, categorias_usuario=categorias_usuario)

@app.route('/admin/avisos/excluir/<int:aviso_id>', methods=['POST'])
@login_required
def excluir_aviso(aviso_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    aviso = Aviso.query.get_or_404(aviso_id)
    db.session.delete(aviso)
    db.session.commit()
    flash('Aviso excluído com sucesso.', 'success')
    return redirect(url_for('gerenciar_avisos'))

@app.route('/dashboard')
@login_required
def dashboard():
    # --- Lógica de Permissão (Buscando o nível e as categorias do usuário) ---
    max_user_level = 0
    user_category_ids = []
    if current_user.categorias:
        max_user_level = max(cat.nivel for cat in current_user.categorias)
        user_category_ids = [cat.id for cat in current_user.categorias]

    categorias_acessiveis_ids = [
        cat.id for cat in CategoriaUsuario.query.filter(CategoriaUsuario.nivel <= max_user_level).all()
    ]

    # --- Busca de Cursos Permitidos ---
    cursos_permitidos = Curso.query.filter(
        or_(Curso.categoria_permissao_id == None, Curso.categoria_permissao_id.in_(categorias_acessiveis_ids))
    ).all()
    
    cursos_por_categoria = {}
    for curso in cursos_permitidos:
        if curso.categoria.nome not in cursos_por_categoria:
            cursos_por_categoria[curso.categoria.nome] = []
        cursos_por_categoria[curso.categoria.nome].append(curso)

    # --- Busca de Materiais Permitidos ---
    materiais_permitidos = MaterialDigital.query.filter(
        or_(MaterialDigital.categoria_permissao_id == None, MaterialDigital.categoria_permissao_id.in_(categorias_acessiveis_ids))
    ).all()

    materiais_por_categoria = {}
    for material in materiais_permitidos:
        if material.categoria.nome not in materiais_por_categoria:
            materiais_por_categoria[material.categoria.nome] = []
        materiais_por_categoria[material.categoria.nome].append(material)

    # --- LÓGICA DE BUSCA DE AVISO ---
    # Busca o aviso mais recente que seja para todos (NULL) ou para um dos grupos do usuário.
    aviso = Aviso.query.filter(
        or_(Aviso.categoria_permissao_id == None, Aviso.categoria_permissao_id.in_(user_category_ids))
    ).order_by(Aviso.data_criacao.desc()).first()

    # LINHA FALTANTE ADICIONADA AQUI
    # Ela cria a variável 'aviso_final' com base no que foi encontrado no banco.
    aviso_final = aviso.mensagem if aviso else "Nenhum aviso importante no momento."
    
    return render_template('dashboard_membro.html', 
                           cursos_por_categoria=cursos_por_categoria, 
                           materiais_por_categoria=materiais_por_categoria, 
                           aviso=aviso_final)

# >>> APAGUE ESTE BLOCO DE CÓDIGO ABAIXO <<<

class Aviso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mensagem = db.Column(db.Text, nullable=False)
    data_criacao = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    # Chave estrangeira para a categoria de usuário. Pode ser nulo (aviso geral).
    categoria_permissao_id = db.Column(db.Integer, db.ForeignKey('categoria_usuario.id'), nullable=True)
    categoria_permissao = db.relationship('CategoriaUsuario')



@app.route('/curso/<int:curso_id>')
@login_required
def ver_curso(curso_id):
    curso = Curso.query.get_or_404(curso_id)
    video_id = None
    try:
        url_data = urllib.parse.urlparse(curso.link_video)
        if "youtube.com" in url_data.hostname:
            query = urllib.parse.parse_qs(url_data.query)
            video_id = query["v"][0]
        elif "youtu.be" in url_data.hostname:
            video_id = url_data.path[1:]
    except:
        video_id = None
    if video_id:
        curso.embed_url = f'https://www.youtube.com/embed/{video_id}'
    else:
        curso.embed_url = None
    return render_template('ver_curso.html', curso=curso)

# 4.3 Rotas do Painel Administrativo
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('dashboard'))
    
    total_produtos = Produto.query.count()
    total_clientes = Cliente.query.count()
    total_pedidos = Pedido.query.count()
    total_usuarios = Usuario.query.count()
    
    # Query corrigida - LEFT JOIN para incluir categorias sem cursos
    dados_grafico = db.session.query(
        CategoriaCurso.nome, 
        func.count(Curso.id)
    ).outerjoin(Curso, CategoriaCurso.id == Curso.categoria_id)\
     .group_by(CategoriaCurso.id, CategoriaCurso.nome)\
     .order_by(CategoriaCurso.nome).all()
    
    chart_labels = [dado[0] for dado in dados_grafico]
    chart_data = [dado[1] for dado in dados_grafico]
    
    # Debug: verifique os dados no console
    print("Labels:", chart_labels)
    print("Data:", chart_data)
    
    return render_template('admin/admin_dashboard.html', 
                         total_produtos=total_produtos, 
                         total_clientes=total_clientes, 
                         total_pedidos=total_pedidos, 
                         total_usuarios=total_usuarios, 
                         chart_labels=chart_labels, 
                         chart_data=chart_data)

@app.route('/registrar', methods=['GET', 'POST'])
@login_required
def registrar():
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('dashboard'))
    categorias_usuario = CategoriaUsuario.query.order_by(CategoriaUsuario.nome).all()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('As senhas não coincidem!', 'danger')
            return redirect(url_for('registrar'))
        usuario_existente = Usuario.query.filter_by(username=username).first()
        if usuario_existente:
            flash('Este nome de usuário já está em uso.', 'danger')
            return redirect(url_for('registrar'))
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        novo_usuario = Usuario(username=username, password_hash=hashed_password)
        ids_categorias_selecionadas = request.form.getlist('categorias')
        categorias_selecionadas = CategoriaUsuario.query.filter(CategoriaUsuario.id.in_(ids_categorias_selecionadas)).all()
        novo_usuario.categorias = categorias_selecionadas
        db.session.add(novo_usuario)
        db.session.commit()
        flash('Usuário criado com sucesso!', 'success')
        return redirect(url_for('listar_usuarios_admin'))
    return render_template('admin/registrar.html', categorias_usuario=categorias_usuario)
    
@app.route('/alterar-senha', methods=['GET', 'POST'])
@login_required
def alterar_senha():
    if request.method == 'POST':
        senha_atual = request.form['senha_atual']
        nova_senha = request.form['nova_senha']
        confirmar_senha = request.form['confirmar_senha']
        if not bcrypt.check_password_hash(current_user.password_hash, senha_atual):
            flash('Sua senha atual está incorreta.', 'danger')
            return redirect(url_for('alterar_senha'))
        if nova_senha != confirmar_senha:
            flash('A nova senha e a confirmação não coincidem.', 'danger')
            return redirect(url_for('alterar_senha'))
        hashed_password = bcrypt.generate_password_hash(nova_senha).decode('utf-8')
        current_user.password_hash = hashed_password
        db.session.commit()
        flash('Sua senha foi alterada com sucesso!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('admin/alterar_senha.html')

@app.route('/configuracoes', methods=['GET', 'POST'])
@login_required
def configuracoes():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    aviso = Configuracao.query.filter_by(chave='aviso_lanchonete').first()
    status_lanchonete = Configuracao.query.filter_by(chave='lanchonete_status').first()
    if request.method == 'POST':
        valor_aviso = request.form.get('aviso')
        if aviso:
            aviso.valor = valor_aviso
        else:
            aviso = Configuracao(chave='aviso_lanchonete', valor=valor_aviso)
            db.session.add(aviso)
        db.session.commit()
        flash('Aviso da lanchonete atualizado com sucesso!', 'success')
        return redirect(url_for('configuracoes'))
    return render_template('admin/configuracoes.html', aviso=aviso, status_lanchonete=status_lanchonete)

@app.route('/mudar-status-lanchonete', methods=['POST'])
@login_required
def mudar_status_lanchonete():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    novo_status = request.form.get('novo_status')
    status_atual = Configuracao.query.filter_by(chave='lanchonete_status').first()
    if status_atual:
        status_atual.valor = novo_status
    else:
        status_atual = Configuracao(chave='lanchonete_status', valor=novo_status)
        db.session.add(status_atual)
    db.session.commit()
    flash(f'Lanchonete marcada como "{novo_status}"!', 'success')
    return redirect(url_for('configuracoes'))

@app.route('/admin/comunicacoes', methods=['GET', 'POST'])
@login_required
def enviar_comunicacao():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    links_whatsapp = []
    if request.method == 'POST':
        mensagem = request.form['mensagem']
        clientes = Cliente.query.filter(Cliente.contato != None, Cliente.contato != '').all()
        for cliente in clientes:
            numero_limpo = ''.join(filter(str.isdigit, cliente.contato))
            if not numero_limpo.startswith('55'):
                numero_limpo = '55' + numero_limpo
            mensagem_codificada = urllib.parse.quote(mensagem)
            link = f"https://wa.me/{numero_limpo}?text={mensagem_codificada}"
            links_whatsapp.append({'nome': cliente.nome, 'contato': cliente.contato, 'url': link})
    return render_template('admin/enviar_comunicacao.html', links_whatsapp=links_whatsapp)

@app.route('/admin/relatorio/usuarios.csv')
@login_required
def exportar_usuarios_csv():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    # Busca os usuários no banco
    usuarios = Usuario.query.all()
    # Cria um arquivo de texto em memória
    output = io.StringIO()
    writer = csv.writer(output)

    # Escreve o cabeçalho do CSV
    writer.writerow(['ID', 'Username', 'Is Admin'])
    # Escreve os dados de cada usuário
    for usuario in usuarios:
        writer.writerow([usuario.id, usuario.username, usuario.is_admin])

    # Prepara o arquivo para ser enviado
    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=relatorio_usuarios.csv"}
    )

@app.route('/admin/relatorio/produtos.csv')
@login_required
def exportar_produtos_csv():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    produtos = Produto.query.all()
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['ID', 'Nome', 'Categoria', 'Preco', 'Estoque'])
    for produto in produtos:
        writer.writerow([produto.id, produto.nome, produto.categoria, produto.preco, produto.estoque])

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=relatorio_produtos.csv"})

@app.route('/admin/relatorio/vendas_diarias.csv')
@login_required
def exportar_vendas_csv():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    vendas_por_dia = db.session.query(
        func.date(Pedido.data_pedido).label('dia'),
        func.sum(Pedido.valor_total).label('total_vendido'),
        func.count(Pedido.id).label('numero_pedidos')
    ).group_by(func.date(Pedido.data_pedido)).order_by(func.date(Pedido.data_pedido).desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Data', 'Total Vendido (R$)', 'Numero de Pedidos'])
    for venda in vendas_por_dia:
        writer.writerow([venda.dia, venda.total_vendido, venda.numero_pedidos])

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=relatorio_vendas_diarias.csv"})

# 4.4 Rotas de Gerenciamento
@app.route('/admin/usuarios')
@login_required
def listar_usuarios_admin():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    usuarios = Usuario.query.all()
    return render_template('admin/listar_usuarios.html', usuarios=usuarios)

@app.route('/admin/pagina/<string:page_key>', methods=['GET', 'POST'])
@login_required
def gerenciar_pagina(page_key):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))

    pagina = Configuracao.query.filter_by(chave=page_key).first()

    if request.method == 'POST':
        conteudo = request.form['conteudo']
        if pagina:
            pagina.valor = conteudo
        else:
            pagina = Configuracao(chave=page_key, valor=conteudo)
            db.session.add(pagina)
        db.session.commit()
        flash(f'Página "{page_key.replace("_", " ").title()}" atualizada com sucesso!', 'success')
        return redirect(url_for('gerenciar_pagina', page_key=page_key))

    return render_template('admin/gerenciar_pagina.html', pagina=pagina, page_key=page_key)

@app.route('/itinerario')
def itinerario():
    conteudo = Configuracao.query.filter_by(chave='itinerario').first()
    return render_template('pagina_generica.html', titulo="Itinerário de Vida Fraterna", conteudo=conteudo)

@app.route('/projetos')
def projetos():
    conteudo = Configuracao.query.filter_by(chave='projets').first()
    return render_template('pagina_generica.html', titulo="Projetos", conteudo=conteudo)

@app.route('/admin/usuario/<int:usuario_id>', methods=['GET', 'POST'])
@login_required
def gerenciar_usuario(usuario_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    usuario = Usuario.query.get_or_404(usuario_id)
    todas_categorias = CategoriaUsuario.query.all()
    
    if request.method == 'POST':
        ids_selecionados = [int(id) for id in request.form.getlist('categorias')]
        categorias_selecionadas = CategoriaUsuario.query.filter(CategoriaUsuario.id.in_(ids_selecionados)).all()
        usuario.categorias = categorias_selecionadas
        db.session.commit()
        flash(f'Permissões do usuário {usuario.username} atualizadas!', 'success')
        return redirect(url_for('listar_usuarios_admin'))
    
    return render_template('admin/gerenciar_usuario.html', usuario=usuario, todas_categorias=todas_categorias)

class Reuniao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    data_reuniao = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    sala_jitsi = db.Column(db.String(100), unique=True, nullable=False)
    presencas = db.relationship('Presenca', backref='reuniao', lazy=True, cascade="all, delete-orphan")

class Presenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    reuniao_id = db.Column(db.Integer, db.ForeignKey('reuniao.id'), nullable=False)
    data_presenca = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    usuario = db.relationship('Usuario')

class CategoriaMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    materiais = db.relationship('MaterialDigital', backref='categoria', lazy=True)

class MaterialDigital(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    imagem_capa = db.Column(db.String(200), nullable=True) # Arquivo da imagem de capa
    arquivo_pdf = db.Column(db.String(200), nullable=False) # O arquivo do livro/material
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria_material.id'), nullable=False)
    categoria_permissao_id = db.Column(db.Integer, db.ForeignKey('categoria_usuario.id'), nullable=True)

@app.route('/admin/usuario/alternar-admin/<int:id>', methods=['POST'])
@login_required
def alternar_status_admin(id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    usuario = Usuario.query.get_or_404(id)
    if usuario.id == current_user.id:
        flash('Você não pode alterar seu próprio status de administrador.', 'danger')
        return redirect(url_for('listar_usuarios_admin'))
    usuario.is_admin = not usuario.is_admin
    db.session.commit()
    flash(f'Status de administrador do usuário {usuario.username} foi alterado.', 'success')
    return redirect(url_for('listar_usuarios_admin'))

@app.route('/admin/usuario/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_usuario(id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    usuario_para_excluir = Usuario.query.get_or_404(id)
    if usuario_para_excluir.id == current_user.id:
        flash('Você não pode excluir sua própria conta.', 'danger')
        return redirect(url_for('listar_usuarios_admin'))
    db.session.delete(usuario_para_excluir)
    db.session.commit()
    flash(f'Usuário {usuario_para_excluir.username} foi excluído com sucesso.', 'success')
    return redirect(url_for('listar_usuarios_admin'))

@app.route('/admin/categorias')
@login_required
def listar_categorias():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    categorias = CategoriaCurso.query.all()
    return render_template('admin/listar_categorias.html', categorias=categorias)

@app.route('/admin/categorias/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_categoria():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        nome = request.form['nome']
        nova_categoria = CategoriaCurso(nome=nome)
        db.session.add(nova_categoria)
        db.session.commit()
        flash('Categoria criada com sucesso!', 'success')
        return redirect(url_for('listar_categorias'))
    return render_template('admin/adicionar_categoria.html')
    
@app.route('/admin/categorias/excluir/<int:categoria_id>', methods=['POST'])
@login_required
def excluir_categoria(categoria_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    categoria_para_excluir = CategoriaCurso.query.get_or_404(categoria_id)
    if categoria_para_excluir.cursos:
        flash('Não é possível excluir esta categoria, pois existem cursos associados a ela.', 'danger')
        return redirect(url_for('listar_categorias'))
    db.session.delete(categoria_para_excluir)
    db.session.commit()
    flash('Categoria de curso excluída com sucesso!', 'success')
    return redirect(url_for('listar_categorias'))

# --- CRUD de Categorias de Usuário (Permissões) ---
@app.route('/admin/permissoes')
@login_required
def listar_categorias_usuario():
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('dashboard'))
    
    categorias = CategoriaUsuario.query.order_by(CategoriaUsuario.nivel).all()
    return render_template('admin/listar_categorias_usuario.html', categorias=categorias)

@app.route('/admin/permissoes/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_categoria_usuario():
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        nivel = int(request.form['nivel'])
        
        nova_categoria = CategoriaUsuario(nome=nome, nivel=nivel)
        db.session.add(nova_categoria)
        db.session.commit()
        
        flash('Categoria de permissão criada com sucesso!', 'success')
        return redirect(url_for('listar_categorias_usuario'))
    
    return render_template('admin/adicionar_categoria_usuario.html')

# --- CRUD de Categorias de Materiais (Biblioteca) ---

@app.route('/admin/materiais/categorias')
@login_required
def listar_categorias_material():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    categorias = CategoriaMaterial.query.all()
    return render_template('admin/listar_categorias_material.html', categorias=categorias)

@app.route('/admin/materiais/categorias/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_categoria_material():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        nome = request.form['nome']
        if not CategoriaMaterial.query.filter_by(nome=nome).first():
            nova_categoria = CategoriaMaterial(nome=nome)
            db.session.add(nova_categoria)
            db.session.commit()
            flash('Categoria de material criada com sucesso!', 'success')
        else:
            flash('Essa categoria já existe.', 'warning')
        return redirect(url_for('listar_categorias_material'))
    return render_template('admin/adicionar_categoria_material.html')
    
@app.route('/admin/materiais/categorias/excluir/<int:categoria_id>', methods=['POST'])
@login_required
def excluir_categoria_material(categoria_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    categoria_para_excluir = CategoriaMaterial.query.get_or_404(categoria_id)
    if categoria_para_excluir.materiais:
        flash('Não é possível excluir esta categoria, pois existem materiais associados a ela.', 'danger')
        return redirect(url_for('listar_categorias_material'))
    db.session.delete(categoria_para_excluir)
    db.session.commit()
    flash('Categoria de material excluída com sucesso!', 'success')
    return redirect(url_for('listar_categorias_material'))

@app.route('/admin/permissoes/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_categoria_usuario(id):
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('dashboard'))
    
    categoria = CategoriaUsuario.query.get_or_404(id)
    
    if request.method == 'POST':
        categoria.nome = request.form['nome']
        categoria.nivel = int(request.form['nivel'])
        db.session.commit()
        flash('Categoria de permissão atualizada com sucesso!', 'success')
        return redirect(url_for('listar_categorias_usuario'))
    
    return render_template('admin/editar_categoria_usuario.html', categoria=categoria)

@app.route('/admin/permissoes/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_categoria_usuario(id):
    if not current_user.is_admin:
        flash('Você não tem permissão para acessar esta página.', 'danger')
        return redirect(url_for('dashboard'))
    
    categoria = CategoriaUsuario.query.get_or_404(id)
    
    if categoria.usuarios:
        flash('Não é possível excluir esta categoria, pois existem usuários associados a ela.', 'danger')
    else:
        db.session.delete(categoria)
        db.session.commit()
        flash('Categoria de permissão excluída com sucesso.', 'success')
    
    return redirect(url_for('listar_categorias_usuario'))

@app.route('/admin/cursos')
@login_required
def listar_cursos():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    cursos = Curso.query.all()
    return render_template('admin/listar_cursos.html', cursos=cursos)

@app.route('/admin/cursos/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_curso():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    categorias = CategoriaCurso.query.order_by(CategoriaCurso.nome).all()
    categorias_usuario = CategoriaUsuario.query.all()
    if request.method == 'POST':
        titulo = request.form['titulo']
        link_video = request.form['link_video']
        categoria_id = request.form['categoria_id']
        descricao = request.form.get('descricao')
        categoria_permissao_id = request.form.get('categoria_permissao_id')
        nome_arquivo_thumb = None
        if 'imagem_thumbnail' in request.files:
            file_thumb = request.files['imagem_thumbnail']
            if file_thumb and file_thumb.filename != '' and allowed_file(file_thumb.filename):
                secure_name = secure_filename(file_thumb.filename)
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                nome_arquivo_thumb = f"thumb_{timestamp}_{secure_name}"
                file_thumb.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo_thumb))
        nome_arquivo_anexo = None
        if 'arquivo_anexo' in request.files:
            file_anexo = request.files['arquivo_anexo']
            if file_anexo and file_anexo.filename != '':
                secure_name = secure_filename(file_anexo.filename)
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                nome_arquivo_anexo = f"anexo_{timestamp}_{secure_name}"
                file_anexo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo_anexo))
        novo_curso = Curso(titulo=titulo, link_video=link_video, categoria_id=categoria_id, imagem_thumbnail=nome_arquivo_thumb, arquivo_anexo=nome_arquivo_anexo, descricao=descricao, categoria_permissao_id=categoria_permissao_id if categoria_permissao_id else None)
        db.session.add(novo_curso)
        db.session.commit()
        flash('Curso adicionado com sucesso!', 'success')
        return redirect(url_for('listar_cursos'))
    return render_template('admin/adicionar_curso.html', categorias=categorias, categorias_usuario=categorias_usuario)

@app.route('/admin/cursos/editar/<int:curso_id>', methods=['GET', 'POST'])
@login_required
def editar_curso(curso_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    curso = Curso.query.get_or_404(curso_id)
    categorias = CategoriaCurso.query.order_by(CategoriaCurso.nome).all()
    categorias_usuario = CategoriaUsuario.query.all()
    if request.method == 'POST':
        curso.titulo = request.form['titulo']
        curso.link_video = request.form['link_video']
        curso.categoria_id = request.form['categoria_id']
        curso.descricao = request.form['descricao']
        categoria_permissao_id = request.form.get('categoria_permissao_id')
        curso.categoria_permissao_id = categoria_permissao_id if categoria_permissao_id else None
        db.session.commit()
        flash('Curso atualizado com sucesso!', 'success')
        return redirect(url_for('listar_cursos'))
    return render_template('admin/editar_curso.html', curso=curso, categorias=categorias, categorias_usuario=categorias_usuario)

@app.route('/admin/cursos/excluir/<int:curso_id>', methods=['POST'])
@login_required
def excluir_curso(curso_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    curso = Curso.query.get_or_404(curso_id)
    if curso.imagem_thumbnail:
        path = os.path.join(app.config['UPLOAD_FOLDER'], curso.imagem_thumbnail)
        if os.path.exists(path):
            os.remove(path)
    if curso.arquivo_anexo:
        path = os.path.join(app.config['UPLOAD_FOLDER'], curso.arquivo_anexo)
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(curso)
    db.session.commit()
    flash('Curso excluído com sucesso!', 'success')
    return redirect(url_for('listar_cursos'))

@app.route('/produtos')
@login_required
def listar_produtos():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    todos_produtos = Produto.query.order_by(Produto.id.desc()).all()
    return render_template('admin/listar_produtos.html', produtos=todos_produtos)

@app.route('/adicionar-produto', methods=['GET', 'POST'])
@login_required
def adicionar_produto():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        nome = request.form['nome']
        categoria = request.form['categoria']
        preco = float(request.form['preco'])
        estoque = int(request.form['estoque'])
        filename = None
        if 'imagem_file' in request.files:
            file = request.files['imagem_file']
            if file and file.filename != '' and allowed_file(file.filename):
                secure_name = secure_filename(file.filename)
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"{timestamp}_{secure_name}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        novo_produto = Produto(nome=nome, categoria=categoria, preco=preco, estoque=estoque, imagem_url=filename)
        db.session.add(novo_produto)
        db.session.commit()
        flash('Produto adicionado com sucesso!', 'success')
        return redirect(url_for('listar_produtos'))
    return render_template('admin/adicionar_produto.html')

@app.route('/editar-produto/<int:produto_id>', methods=['GET', 'POST'])
@login_required
def editar_produto(produto_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    produto = Produto.query.get_or_404(produto_id)
    if request.method == 'POST':
        produto.nome = request.form['nome']
        produto.categoria = request.form['categoria']
        produto.preco = float(request.form['preco'])
        produto.estoque = int(request.form['estoque'])
        if 'imagem_file' in request.files:
            file = request.files['imagem_file']
            if file and file.filename != '' and allowed_file(file.filename):
                if produto.imagem_url:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], produto.imagem_url)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                secure_name = secure_filename(file.filename)
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                filename = f"{timestamp}_{secure_name}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                produto.imagem_url = filename
        db.session.commit()
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('listar_produtos'))
    return render_template('admin/editar_produto.html', produto=produto)

@app.route('/excluir-produto/<int:produto_id>', methods=['POST'])
@login_required
def excluir_produto(produto_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    produto = Produto.query.get_or_404(produto_id)
    if produto.imagem_url:
        path = os.path.join(app.config['UPLOAD_FOLDER'], produto.imagem_url)
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(produto)
    db.session.commit()
    flash('Produto excluído com sucesso!', 'success')
    return redirect(url_for('listar_produtos'))

@app.route('/clientes')
@login_required
def listar_clientes():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    todos_clientes = Cliente.query.order_by(Cliente.nome).all()
    return render_template('admin/listar_clientes.html', clientes=todos_clientes)

@app.route('/adicionar-cliente', methods=['GET', 'POST'])
@login_required
def adicionar_cliente():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        nome = request.form['nome']
        contato = request.form.get('contato')
        novo_cliente = Cliente(nome=nome, contato=contato)
        db.session.add(novo_cliente)
        db.session.commit()
        flash('Cliente adicionado com sucesso!', 'success')
        return redirect(url_for('listar_clientes'))
    return render_template('admin/adicionar_cliente.html')

@app.route('/editar-cliente/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(cliente_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    cliente = Cliente.query.get_or_404(cliente_id)
    if request.method == 'POST':
        cliente.nome = request.form['nome']
        cliente.contato = request.form.get('contato')
        db.session.commit()
        flash('Cliente atualizado com sucesso!', 'success')
        return redirect(url_for('listar_clientes'))
    return render_template('admin/editar_cliente.html', cliente=cliente)

@app.route('/excluir-cliente/<int:cliente_id>', methods=['POST'])
@login_required
def excluir_cliente(cliente_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    cliente = Cliente.query.get_or_404(cliente_id)
    db.session.delete(cliente)
    db.session.commit()
    flash('Cliente excluído com sucesso!', 'success')
    return redirect(url_for('listar_clientes'))

@app.route('/pedidos')
@login_required
def listar_pedidos():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    todos_pedidos = Pedido.query.order_by(Pedido.data_pedido.asc()).all()
    return render_template('admin/listar_pedidos.html', pedidos=todos_pedidos)

@app.route('/mudar-status-pedido/<int:pedido_id>', methods=['POST'])
@login_required
def mudar_status_pedido(pedido_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    pedido = Pedido.query.get_or_404(pedido_id)
    novo_status = request.form['novo_status']
    if novo_status in ['Em Produção', 'Disponível para Retirada', 'Concluído']:
        pedido.status = novo_status
        db.session.commit()
        flash(f'Status do Pedido #{pedido.id} alterado para "{novo_status}".', 'success')
    else:
        flash('Status inválido.', 'danger')
    return redirect(url_for('listar_pedidos'))

@app.route('/excluir-pedido/<int:pedido_id>', methods=['POST'])
@login_required
def excluir_pedido(pedido_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    pedido = Pedido.query.get_or_404(pedido_id)
    db.session.delete(pedido)
    db.session.commit()
    flash(f'Pedido #{pedido.id} foi excluído com sucesso.', 'success')
    return redirect(url_for('listar_pedidos'))

@app.route('/admin/materiais')
@login_required
def listar_materiais():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    materiais = MaterialDigital.query.order_by(MaterialDigital.id.desc()).all()
    return render_template('admin/listar_materiais.html', materiais=materiais)

@app.route('/admin/materiais/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_material():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    # Busca as categorias para preencher os menus do formulário
    categorias_material = CategoriaMaterial.query.order_by(CategoriaMaterial.nome).all()
    categorias_usuario = CategoriaUsuario.query.all()

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form.get('descricao')
        categoria_id = request.form['categoria_id']
        categoria_permissao_id = request.form.get('categoria_permissao_id')
        
        # --- Lógica de Upload de Arquivos ---
        imagem_capa = request.files.get('imagem_capa')
        arquivo_pdf = request.files.get('arquivo_pdf')

        if not arquivo_pdf or arquivo_pdf.filename == '':
            flash('O arquivo PDF é obrigatório!', 'danger')
            return redirect(request.url)

        nome_arquivo_capa = None
        if imagem_capa and allowed_file(imagem_capa.filename):
            secure_name = secure_filename(imagem_capa.filename)
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            nome_arquivo_capa = f"capa_{timestamp}_{secure_name}"
            imagem_capa.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo_capa))

        secure_name_pdf = secure_filename(arquivo_pdf.filename)
        timestamp_pdf = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        nome_arquivo_pdf = f"pdf_{timestamp_pdf}_{secure_name_pdf}"
        arquivo_pdf.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo_pdf))
        # --- Fim da Lógica de Upload ---

        novo_material = MaterialDigital(
            titulo=titulo,
            descricao=descricao,
            categoria_id=categoria_id,
            imagem_capa=nome_arquivo_capa,
            arquivo_pdf=nome_arquivo_pdf,
            categoria_permissao_id=categoria_permissao_id if categoria_permissao_id else None
        )

        db.session.add(novo_material)
        db.session.commit()

        flash('Material adicionado com sucesso!', 'success')
        return redirect(url_for('listar_materiais'))

    return render_template('admin/adicionar_material.html', categorias_material=categorias_material, categorias_usuario=categorias_usuario)

# --- 5. INICIALIZAÇÃO DA APLICAÇÃO ---
if __name__ == '__main__':
    # Verifica se está rodando na Hostinger (ambiente de produção)
    if 'PORT' in os.environ:
        # Configurações para produção
        app.run(host='0.0.0.0', port=int(os.environ['PORT']), debug=False)
    else:
        # Configurações para desenvolvimento
        app.run(debug=True)