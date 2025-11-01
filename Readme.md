# Faculdade 
    Cesar School

# Curso
    Segurança da Informação

# Período
    2025.2

# Disciplina
    Projeto 2

# Professor de Projeto 2
    Marlon Silva Ferreira

# Professor de Programação Orientada a Objeto
    João Victor Tinoco de Souza Abreu

# Equipe
    Artur Torres Lima Cavalcanti
    Carlos Vinicius Alves de Figueiredo
    Eduardo Henrique Ferreira Fonseca Barbosa
    Gabriel de Medeiros Almeida
    Mauro Sérgio Rezende da Silva
    Silvio Barros Tenório

# Projeto
    Automatizar a criação de conteúdos para comunicar projetos e respectivos resultados.

# Cliente
    MC Sonae

# Comandos
    - Cria ambiente virtual
        python -m venv venv

    - Ativar ambiente virtual
        * Linux/Mac:
            source venv/bin/activate
        * Windows:
            venv/Scripts/activate

    - Atualizar o pip
        python.exe -m pip install --upgrade pip

    - Lista os pacotes instalados
        pip freeze

    - Gerar arquivo requirements.txt
        pip freeze > requirements.txt

    - Recuperar venv com requirements.txt
        pip install -r ./requirements.txt

    - Instalar as Bibliotecas
        + Flet
            pip install flet
          Para criar um app Flet do zero:
            flet create
        + Flet Webview
            pip install flet-webview  
        + Dotenv (Ambiente variáveis - Lê pares de valores-chave de um arquivo .env)
            pip install python-dotenv
        + PyJWT (JSON Web Token)
            pip install PyJWT
        + Docling
            pip install docling
    
# Arquivos Python
    - app_mcsonae.py            => Arquivo main da App MC Sonae
    - utilidades.py             => Arquivo de Utilidades 

# Executar APP
    Linux:
        export FLET_SECRET_KEY="$2b$12$lEqyKxLYq5QQFjC5XF/uke1VfU1VKwI/DIlraQAAuJsK29hinWEOe"
    Windows:
        set FLET_SECRET_KEY=$2b$12$lEqyKxLYq5QQFjC5XF/uke1VfU1VKwI/DIlraQAAuJsK29hinWEOe
    flet run app_mcsonae.py --web

# CUDA 
    - Versão:
        12.9
    - Comandos: 
        nvcc --version
        nvidia-smi
    - No meu notebook com Windows 11 (instalar depois )
        pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu129
    
    - Testes:
        python -c "import torch; print(torch.__version__)"
        python -c "from docling.document_converter import DocumentConverter; print('Docling OK!')"
