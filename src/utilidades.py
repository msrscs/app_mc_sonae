######################################################### 
# Faculdade: Cesar School                               #
# Curso: Segurança da Informação                        #
# Período: 2025.2                                       #
# Disciplina: Projeto 2                                 #
# Professor de Projeto 2: Marlon Silva Ferreira         #
# Professor de POO: João Victor Tinoco de Souza Abreu   #
# Projeto: Automatizar a criação de conteúdos para      #
#          comunicar projetos e respectivos resultados. #
# Descrição: APP WEB MC Sonae                           #
# Arquivo: utilidades.py                                #
# Equipe:                                               #
#           Artur Torres Lima Cavalcanti                #
#           Carlos Vinicius Alves de Figueiredo         #
#           Eduardo Henrique Ferreira Fonseca Barbosa   #
#           Gabriel de Medeiros Almeida                 #
#           Mauro Sérgio Rezende da Silva               #
#           Silvio Barros Tenório                       #
# Versão: 1.0                                           #
# Data: 26/10/2025                                      #
######################################################### 

import random
import string
import requests

# Gerar Senha Forte
def gerar_senha_forte(tamanho=12):
    # Definindo os conjuntos de caracteres
    letras_minusculas = string.ascii_lowercase
    letras_maiusculas = string.ascii_uppercase
    numeros = string.digits
    # simbolos = string.punctuation
    # simbolos = '[!@#$%^&*(),.?":{}|<>]'
    simbolos = '[!@#$%^&*(),.?:{}|]'

    # Garantindo pelo menos um caractere de cada categoria
    senha = [
        random.choice(letras_minusculas),
        random.choice(letras_maiusculas),
        random.choice(numeros),
        random.choice(simbolos)
    ]

    # Preenchendo o restante da senha com caracteres aleatórios de todas as categorias
    todos_caracteres = letras_minusculas + letras_maiusculas + numeros + simbolos
    senha.extend(random.choice(todos_caracteres) for _ in range(tamanho - 4))

    # Embaralhando os caracteres para maior aleatoriedade
    random.shuffle(senha)

    # Convertendo a lista em string
    return ''.join(senha)

# Enviar Email com a Senha para o Usuário
def envia_email(nome, email_destinatario, senha, chave_api_brevo):
    try:

        # Configurações
        URL = "https://api.brevo.com/v3/smtp/email"
        
        # Cabeçalhos da requisição
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": chave_api_brevo
        }

        # Corpo do e-mail (JSON)
        payload = {
            "sender": {
                "name": "App MC Sonae",
                "email": "denuncia.bullying.anonima@gmail.com"  # Domínio verificado na Brevo
            },
            "to": [{"email": f"{email_destinatario}"}],
            "subject": "Assunto do E-mail",
            "htmlContent": f"<h1>Olá! {nome}</h1><p>Segue a senha para acessar o App MC Sonae:<p>Email: <strong>{email_destinatario}</strong><p>Senha: <strong>{senha}</strong><p>",
            "textContent": "Senha App MC Sonae"
        }

        # Enviar e-mail
        response = requests.post(URL, headers=headers, json=payload)

        if response.status_code == 201:
            print("E-mail enviado com sucesso!")
            return True
        else:
            print(f"Erro: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(e)
        return False