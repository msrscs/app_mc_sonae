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
        + Dotenv (Ambiente variáveis - Lê pares de valores-chave de um arquivo .env)
          pip install python-dotenv
        + PyJWT (JSON Web Token)
          pip install PyJWT
        + Docling
            pip install docling


        + token count
            pip install token-count

            
# Arquivos Python
    - app_mcsonae.py            => Arquivo main da App MC Sonae
    - utilidades.py             => Arquivo de Utilidades 

# Executar APP
    flet run app_mcsonae.py --web








