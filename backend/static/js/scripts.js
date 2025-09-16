document.addEventListener('DOMContentLoaded', function() {

    // =======================================================
    // EFEITO DE DIGITAÇÃO NO HERO
    // =======================================================
    const heroTitle = document.getElementById('hero-title');
    if (heroTitle) {
        const text = "Bem-vindo à Comunidade Fraterno Amor";
        let index = 0;
        heroTitle.innerHTML = ""; // Limpa o título antes de começar

        function type() {
            if (index < text.length) {
                heroTitle.textContent += text.charAt(index);
                index++;
                setTimeout(type, 90); // Velocidade da digitação
            } else {
                heroTitle.classList.add('typing-done');
            }
        }
        type();
        
        const style = document.createElement('style');
        style.innerHTML = `#hero-title.typing-done::after { display: none; }`;
        document.head.appendChild(style);
    }

    // =======================================================
    // EFEITO DE ANIMAÇÃO AO ROLAR (SCROLL REVEAL)
    // =======================================================
    const fadeInSections = document.querySelectorAll('.fade-in-section');
    if (fadeInSections.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });
        fadeInSections.forEach(section => observer.observe(section));
    }

    // =======================================================
    // LÓGICA DE FILTRO DE CATEGORIA DA LANCHONETE
    // =======================================================
    const filtersContainer = document.querySelector('.category-filters');
    if (filtersContainer) {
        const filterButtons = document.querySelectorAll('.filter-btn');
        const productCards = document.querySelectorAll('.product-card');

        filterButtons.forEach(button => {
            button.addEventListener('click', function() {
                filterButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');
                const selectedCategory = this.dataset.category;
                productCards.forEach(card => {
                    const cardCategory = card.dataset.category.toLowerCase();
                    if (selectedCategory === 'todos' || cardCategory === selectedCategory) {
                        card.style.display = 'flex';
                    } else {
                        card.style.display = 'none';
                    }
                });
            });
        });
    }

    // =======================================================
    // LÓGICA DO CARRINHO DE COMPRAS
    // =======================================================
    const carrinhoSidebar = document.getElementById('carrinho-sidebar');
    if (carrinhoSidebar) {
        let carrinho = [];
        const botoesPedir = document.querySelectorAll('.btn-pedir');
        const listaCarrinho = document.getElementById('carrinho-itens');
        const totalCarrinhoEl = document.getElementById('carrinho-total-preco');
        
        const btnFinalizar = document.getElementById('btn-finalizar-pedido');
        const nomeModal = document.getElementById('nome-cliente-modal');
        const formNomeCliente = document.getElementById('form-nome-cliente');
        const inputNomeCliente = document.getElementById('input-nome-cliente');
        const closeButtonNome = document.querySelector('.close-button-nome');

        botoesPedir.forEach(botao => {
            botao.addEventListener('click', function() {
                if(this.hasAttribute('disabled')) return;
                const id = this.dataset.produtoId;
                const nome = this.dataset.produtoNome;
                const preco = parseFloat(this.dataset.produtoPreco);
                adicionarAoCarrinho(id, nome, preco);
            });
        });

        if (btnFinalizar) {
            btnFinalizar.addEventListener('click', function() {
                if (carrinho.length === 0) {
                    alert('Seu carrinho está vazio!');
                    return;
                }
                nomeModal.style.display = 'block';
            });
        }

        if (formNomeCliente) {
            formNomeCliente.addEventListener('submit', function(event) {
                event.preventDefault();
                const nomeCliente = inputNomeCliente.value;
                if (nomeCliente.trim() === '') {
                    alert('Por favor, digite seu nome.');
                    return;
                }
                fetch('/finalizar-pedido', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nome_cliente: nomeCliente, carrinho: carrinho })
                })
                .then(response => response.json())
                .then(data => {
                    console.log('Sucesso:', data);
                    const numeroWhatsapp = '5583998000756';
                    let mensagem = `Olá! Meu nome é *${nomeCliente}* e gostaria de fazer o seguinte pedido:\n\n`;
                    let total = 0;
                    carrinho.forEach(item => {
                        mensagem += `*${item.quantidade}x* - ${item.nome}\n`;
                        total += item.preco * item.quantidade;
                    });
                    mensagem += `\n*Total:* R$ ${total.toFixed(2)}`;
                    const mensagemCodificada = encodeURIComponent(mensagem);
                    const whatsappUrl = `https://wa.me/${numeroWhatsapp}?text=${mensagemCodificada}`;
                    window.open(whatsappUrl, '_blank');
                    
                    carrinho = [];
                    atualizarCarrinhoDisplay();
                    nomeModal.style.display = 'none';
                    inputNomeCliente.value = '';
                })
                .catch((error) => {
                    console.error('Erro:', error);
                    alert('Ocorreu um erro ao enviar o pedido. Tente novamente.');
                });
            });
        }
        
        if (closeButtonNome) {
            closeButtonNome.addEventListener('click', () => nomeModal.style.display = 'none');
        }

        function adicionarAoCarrinho(id, nome, preco) {
            const itemExistente = carrinho.find(item => item.id === id);
            if (itemExistente) {
                itemExistente.quantidade++;
            } else {
                carrinho.push({ id, nome, preco, quantidade: 1 });
            }
            atualizarCarrinhoDisplay();
        }

        function atualizarCarrinhoDisplay() {
            listaCarrinho.innerHTML = '';
            if (carrinho.length === 0) {
                listaCarrinho.innerHTML = '<li class="carrinho-vazio">Seu carrinho está vazio.</li>';
                totalCarrinhoEl.textContent = 'R$ 0.00';
                return;
            }
            let total = 0;
            carrinho.forEach(item => {
                const li = document.createElement('li');
                li.innerHTML = `<span>${item.nome} (x${item.quantidade})</span><span>R$ ${(item.preco * item.quantidade).toFixed(2)}</span>`;
                listaCarrinho.appendChild(li);
                total += item.preco * item.quantidade;
            });
            totalCarrinhoEl.textContent = `R$ ${total.toFixed(2)}`;
        }
    }

    // =======================================================
    // LÓGICA PARA O MENU MOBILE
    // =======================================================
    const menuToggle = document.getElementById('mobile-menu');
    const navMenu = document.querySelector('header nav');
    if (menuToggle && navMenu) {
        menuToggle.addEventListener('click', () => navMenu.classList.toggle('active'));
    }

    // =======================================================
    // LÓGICA PARA O MODAL DE IMAGEM
    // =======================================================
    const imageModal = document.getElementById('gallery-modal');
    if (imageModal) {
        const modalImg = document.getElementById('modal-image');
        const closeButton = imageModal.querySelector('.close-button');
        const imagesToExpand = document.querySelectorAll('.modal-trigger');
        imagesToExpand.forEach(img => {
            img.addEventListener('click', function() {
                imageModal.style.display = 'block';
                modalImg.src = this.src;
            });
        });
        if(closeButton) {
            closeButton.addEventListener('click', () => imageModal.style.display = 'none');
        }
        window.addEventListener('click', (event) => {
            if (event.target == imageModal) {
                imageModal.style.display = 'none';
            }
        });
    }

    // =======================================================
    // LÓGICA PARA O FORMULÁRIO DE CONTATO
    // =======================================================
    const contactForm = document.querySelector('#main-contact-form');
    if (contactForm) {
        contactForm.addEventListener('submit', function(event) {
            event.preventDefault();
            alert('Mensagem enviada com sucesso! (Simulação)');
            contactForm.reset();
        });
    }

    // =======================================================
    // LÓGICA DE BUSCA NO DASHBOARD DE MEMBRO (CÓDIGO CORRIGIDO E INTEGRADO)
    // =======================================================
    const caixaBusca = document.getElementById('caixa-busca');
    if (caixaBusca) {
        caixaBusca.addEventListener('keyup', function() {
            const termoBusca = caixaBusca.value.toLowerCase();
            
            // Primeiro, filtra os cards e seções de trilha
            document.querySelectorAll('.trilha-section').forEach(function(secao) {
                const todosOsCards = secao.querySelectorAll('.curso-card');
                let trilhaTemResultados = false;

                todosOsCards.forEach(function(card) {
                    const tituloCard = card.querySelector('h4').textContent.toLowerCase();
                    if (tituloCard.includes(termoBusca)) {
                        card.style.display = 'flex';
                        trilhaTemResultados = true;
                    } else {
                        card.style.display = 'none';
                    }
                });

                if (trilhaTemResultados) {
                    secao.style.display = 'block';
                } else {
                    secao.style.display = 'none';
                }
            });
            
            // Depois, verifica quais títulos principais devem ser exibidos
            document.querySelectorAll('.main-section-title').forEach(title => {
                let proximaSecao = title.nextElementSibling;
                let temTrilhaVisivel = false;
                
                while(proximaSecao && !proximaSecao.classList.contains('main-section-title')) {
                    if(proximaSecao.classList.contains('trilha-section') && proximaSecao.style.display !== 'none') {
                        temTrilhaVisivel = true;
                        break; // Para a verificação assim que achar uma trilha visível
                    }
                    proximaSecao = proximaSecao.nextElementSibling;
                }
                
                if(temTrilhaVisivel) {
                    title.style.display = 'block';
                } else {
                    title.style.display = 'none';
                }
            });
        });
    }

}); // Fim do 'DOMContentLoaded'