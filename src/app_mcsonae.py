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
# Arquivo: app_mcsonae.py                               #
# Equipe:                                               #
#           Artur Torres Lima Cavalcanti                #
#           Carlos Vinicius Alves de Figueiredo         #
#           Eduardo Henrique Ferreira Fonseca Barbosa   #
#           Gabriel de Medeiros Almeida                 #
#           Mauro Sérgio Rezende da Silva               #
#           Silvio Barros Tenório                       #
# Versão: 1.0                                           #
# Data: 14/11/2025                                      #
######################################################### 

import jwt # Adicionado para decodificar JWTs
from datetime import datetime, timezone # Adicionado para verificar a expiração do token
import flet as ft
import httpx
from typing import Optional
from dotenv import load_dotenv
from zoneinfo import ZoneInfo # Adicionado para conversão de fuso horário
import os
import re
import random
from utilidades import gerar_senha_forte, envia_email
from docling.document_converter import DocumentConverter
from google import genai
# import urllib.parse
import base64

##################################################
# Carrega Variaveis de Ambiente
##################################################

load_dotenv()
CHAVE_API_GEMINI = os.getenv('CHAVE_API_GEMINI')
CHAVE_API_BREVO  = os.getenv('CHAVE_API_BREVO')
URL_API_MCSONAE = os.getenv('URL_API_MCSONAE')
FLET_SECRET_KEY = os.getenv('FLET_SECRET_KEY')
SERVIDOR_WEB = os.getenv('SERVIDOR_WEB')

##################################################
# Paleta de Cores
##################################################
COR_1 = "#021E73"
COR_2 = "#5B7AD9"
COR_3 = "#9EB6FF"
COR_4 = "#D1DDFF"
COR_5 = "#FFFFFF"

##################################################
# Cliente da API
##################################################

class ApiClient:
    # Cliente para interagir com a API FastAPI MC Sonae.
    def __init__(self, page: ft.Page, base_url=URL_API_MCSONAE):
        self.page = page
        self.base_url = base_url
        self.client = httpx.Client(base_url=self.base_url) # type: ignore

    # Tenta autenticar na API /token. 
    def login(self, email: str, password: str) -> tuple[bool, str]:
        try:
            response = self.client.post(
                "/token",
                data={"username": email, "password": password}
            )
            
            response.raise_for_status() 
            
            token_data = response.json()
            access_token = token_data.get("access_token")

            if access_token:
                # Armazena o token no armazenamento local do navegador
                self.page.client_storage.set("auth_token", access_token)
                return True, "Login bem-sucedido!"
            else:
                return False, "Token não encontrado na resposta."

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return False, "Email ou senha incorretos."
            return False, f"Erro HTTP: {e.response.status_code}"
        except httpx.RequestError as e:
            return False, f"Erro de conexão com a API: {e}"

    # Remove o token de autenticação.
    def logout(self):
        self.page.client_storage.remove("auth_token")

    # Recupera o token armazenado.
    def get_token(self) -> Optional[str]:
        # return self.page.client_storage.get("auth_token")
        token = self.page.client_storage.get("auth_token")
        if not token:
            return None
        
        try:
            # Decodifica o token sem verificar a assinatura para obter os claims.
            # A verificação da assinatura é feita pelo servidor.
            # Aqui, estamos interessados apenas no tempo de expiração ('exp').
            decoded_token = jwt.decode(token, options={"verify_signature": False})
            
            expiration_timestamp = decoded_token.get("exp")
            if expiration_timestamp:
                expiration_datetime = datetime.fromtimestamp(expiration_timestamp, tz=timezone.utc)
                current_datetime = datetime.now(timezone.utc)
                
                if current_datetime >= expiration_datetime:
                    print("Token expirado no cliente. Removendo token.")
                    self.logout() # Remove o token expirado do armazenamento local
                    return None
            return token
        except Exception as e:
            print(f"Erro ao decodificar ou verificar token: {e}")
            self.logout() # Remove token inválido ou malformado
            return None
        
    # Retorna um cliente httpx pré-configurado com o header de Autorização.
    def get_authenticated_client(self) -> Optional[httpx.Client]:
        token = self.get_token()
        if not token:
            self.page.go("/login")
            return None
        
        headers = {"Authorization": f"Bearer {token}"}
        return httpx.Client(base_url=self.base_url, headers=headers) # type: ignore

    # Busca a lista de usuários do endpoint GET /usuarios/.
    def get_users(self, search_term: Optional[str] = None) -> Optional[list]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return None
        
        try:
            params = {}
            if search_term:
                params["filtro"] = search_term
            response = auth_client.get("/usuarios/", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Erro ao buscar usuários: {e}")
            if e.response.status_code == 401:
                self.page.go("/login") # Token inválido ou expirado
            return None
        except httpx.RequestError as e:
            print(f"Erro de conexão: {e}")
            return None

    # Busca usuário me do endpoint GET /usuarios/me.
    def get_usuarios_me(self) -> Optional[dict]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            
            self.page.go("/login")
            return None
        
        try:
            # Chama GET /usuarios/me/
            response = auth_client.get("/usuarios/me")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Erro ao buscar usuário: {e}")
            if e.response.status_code == 401:
                self.logout()
                self.page.go("/login") # Token inválido ou expirado
            return None
        except httpx.RequestError as e:
            print(f"Erro de conexão: {e}")
            return None
    
    # Busca os tipos de usuário do endpoint GET /tipo/.
    def get_tipos_usuario(self) -> Optional[list]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return None
        
        try:
            response = auth_client.get("/tipo/")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Erro ao buscar tipos de usuário: {e}")
            if e.response.status_code == 401:
                self.page.go("/login")
            return None
        except httpx.RequestError as e:
            print(f"Erro de conexão: {e}")
            return None

    # Busca um usuário pelo ID.
    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return None
        
        try:
            response = auth_client.get(f"/usuarios/{user_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Erro ao buscar usuário {user_id}: {e}")
            if e.response.status_code == 401:
                self.page.go("/login")
            return None
        except httpx.RequestError as e:
            print(f"Erro de conexão: {e}")
            return None

    # Cria um novo usuário.
    def create_user(self, user_data: dict) -> tuple[bool, str]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return False, "Não autenticado."
        
        try:
            response = auth_client.post("/usuarios/", json=user_data)
            response.raise_for_status()
            return True, "Usuário criado com sucesso!"
        except httpx.HTTPStatusError as e:
            return False, f"Erro ao criar usuário: {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Erro de conexão: {e}"

    # Atualiza um usuário existente.
    def update_user(self, user_id: int, user_data: dict) -> tuple[bool, str]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return False, "Não autenticado."
        
        try:
            response = auth_client.put(f"/usuarios/{user_id}", json=user_data)
            response.raise_for_status()
            return True, "Usuário atualizado com sucesso!"
        except httpx.HTTPStatusError as e:
            return False, f"Erro ao atualizar usuário: {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Erro de conexão: {e}"

    # Deleta um usuário.
    def delete_user(self, user_id: int) -> tuple[bool, str]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return False, "Não autenticado."
        
        try:
            response = auth_client.delete(f"/usuarios/{user_id}")
            response.raise_for_status()
            return True, "Usuário deletado com sucesso!"
        except httpx.HTTPStatusError as e:
            return False, f"Erro ao deletar usuário: {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Erro de conexão: {e}"

    # Busca as permissões de usuário do endpoint GET /permissao/.
    def get_permissoes_usuario(self) -> Optional[list]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return None
        
        try:
            response = auth_client.get("/permissao/")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Erro ao buscar permissões de usuário: {e}")
            if e.response.status_code == 401:
                self.page.go("/login")
            return None
        except httpx.RequestError as e:
            print(f"Erro de conexão: {e}")
            return None

    # Resetar senha do usuário.
    def reset_user(self, user_id: int) -> tuple[bool, str, Optional[dict]]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return False, "Não autenticado.", None
        
        try:
            response = auth_client.put(f"/usuarios/reset/{user_id}")
            response.raise_for_status()
            return True, "Senha do usuário resetada com sucesso!", response.json()
        except httpx.HTTPStatusError as e:
            return False, f"Erro ao resetar senha do usuário: {e.response.text}", None
        except httpx.RequestError as e:
            return False, f"Erro de conexão: {e}", None

    # Muda senha do usuário.
    def update_senha_user(self, user_id: int, user_data: dict) -> tuple[bool, str]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return False, "Não autenticado."
        
        try:
            response = auth_client.put(f"/usuarios/change_password/{user_id}", json=user_data)
            response.raise_for_status()
            return True, "Senha do usuário atualizada com sucesso!"
        except httpx.HTTPStatusError as e:
            return False, f"Erro ao atualizar a senha do usuário: {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Erro de conexão: {e}"

    # Busca um prompt geral pelo ID.
    def get_prompt_geral(self, prompt_id: int) -> Optional[dict]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return None
        
        try:
            response = auth_client.get(f"/promptgeral/{prompt_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Erro ao buscar prompt geral {prompt_id}: {e}")
            if e.response.status_code == 401:
                self.page.go("/login")
            return None
        except httpx.RequestError as e:
            print(f"Erro de conexão: {e}")
            return None

    # Atualiza um prompt geral existente.
    def update_prompt_geral(self, prompt_id: int, user_data: dict) -> tuple[bool, str]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return False, "Não autenticado."
        
        try:
            response = auth_client.put(f"/promptgeral/{prompt_id}", json=user_data)
            response.raise_for_status()
            return True, "Prompt Geral atualizado com sucesso!"
        except httpx.HTTPStatusError as e:
            return False, f"Erro ao atualizar prompt geral: {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Erro de conexão: {e}"

    # Busca a lista de projetos do endpoint GET /projetos/.
    def get_projetos(self, search_term: Optional[str] = None) -> Optional[list]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return None
        
        try:
            params = {}
            if search_term:
                params["filtro"] = search_term
            response = auth_client.get("/projetos/", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Erro ao buscar projetos: {e}")
            if e.response.status_code == 401:
                self.page.go("/login") # Token inválido ou expirado
            return None
        except httpx.RequestError as e:
            print(f"Erro de conexão: {e}")
            return None

    # Busca um projeto pelo ID.
    def get_projeto_by_id(self, projeto_id: int) -> Optional[dict]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return None
        
        try:
            response = auth_client.get(f"/projetos/{projeto_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Erro ao buscar projeto {projeto_id}: {e}")
            if e.response.status_code == 401:
                self.page.go("/login")
            return None
        except httpx.RequestError as e:
            print(f"Erro de conexão: {e}")
            return None

    # Cria um novo projeto.
    def create_projeto(self, projeto_data: dict) -> tuple[bool, str]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return False, "Não autenticado."
        
        try:
            response = auth_client.post("/projetos/", json=projeto_data)
            response.raise_for_status()
            return True, "Projeto criado com sucesso!"
        except httpx.HTTPStatusError as e:
            return False, f"Erro ao criar projeto: {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Erro de conexão: {e}"

    # Atualiza um projeto existente.
    def update_projeto(self, projeto_id: int, projeto_data: dict) -> tuple[bool, str]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return False, "Não autenticado."
        
        try:
            response = auth_client.put(f"/projetos/{projeto_id}", json=projeto_data)
            response.raise_for_status()
            return True, "Projeto atualizado com sucesso!"
        except httpx.HTTPStatusError as e:
            return False, f"Erro ao atualizar projeto: {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Erro de conexão: {e}"

    # Deleta um usuário.
    def delete_projeto(self, projeto_id: int) -> tuple[bool, str]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return False, "Não autenticado."
        
        try:
            response = auth_client.delete(f"/projetos/{projeto_id}")
            response.raise_for_status()
            return True, "Projeto deletado com sucesso!"
        except httpx.HTTPStatusError as e:
            return False, f"Erro ao deletar projeto: {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Erro de conexão: {e}"

    # Cria um arquivo no repositório do projeto.
    def create_repositorio(self, repositorio_data: dict) -> tuple[bool, str]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return False, "Não autenticado."
        
        try:
            response = auth_client.post("/repositorio/", json=repositorio_data)
            response.raise_for_status()
            return True, "Arquivo anexado ao repositório do Projeto com sucesso!"
        except httpx.HTTPStatusError as e:
            return False, f"Erro ao anexar arquivo ao repositório do projeto: {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Erro de conexão: {e}"

    # Busca a lista de projetos do endpoint GET /repositorio/.
    def get_repositorios(self, search_term: int = 0) -> Optional[list]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return None
        
        try:
            params = {}
            if search_term is None:
                search_term = 0
            params["filtro"] = search_term
            response = auth_client.get("/repositorio/", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Erro ao buscar repositorios: {e}")
            if e.response.status_code == 401:
                self.page.go("/login") # Token inválido ou expirado
            return None
        except httpx.RequestError as e:
            print(f"Erro de conexão: {e}")
            return None

    # Deleta um repositório.
    def delete_repositorio(self, repositorio_id: int) -> tuple[bool, str]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return False, "Não autenticado."
        
        try:
            response = auth_client.delete(f"/repositorio/{repositorio_id}")
            response.raise_for_status()
            return True, "Repositório deletado com sucesso!"
        except httpx.HTTPStatusError as e:
            return False, f"Erro ao deletar repositório: {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Erro de conexão: {e}"

    # Busca um prompt usuario pelo ID.
    def get_prompt_usuario(self, limit: int = 1000) -> Optional[list]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return None
        
        try:
            params = {}
            params["limit"] = limit
            response = auth_client.get("/promptusuario/", params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Erro ao buscar prompt usuário: {e}")
            if e.response.status_code == 401:
                self.page.go("/login") # Token inválido ou expirado
            return None
        except httpx.RequestError as e:
            print(f"Erro de conexão: {e}")
            return None

    # Cria um arquvivo no repositório do projeto.
    def create_prompt_usuario(self, prompt_data: dict) -> tuple[bool, str]:
        auth_client = self.get_authenticated_client()
        if not auth_client:
            return False, "Não autenticado."
        
        try:
            response = auth_client.post("/promptusuario/", json=prompt_data)
            response.raise_for_status()
            return True, "Prompt do usuário criado  com sucesso!"
        except httpx.HTTPStatusError as e:
            return False, f"Erro ao criar prompt do usuário: {e.response.text}"
        except httpx.RequestError as e:
            return False, f"Erro de conexão: {e}"

##################################################
# Definição das Telas (Views)
##################################################

# SnackBar para feedback ao usuário
def show_snackbar(page: ft.Page, message: str, color: str = ft.Colors.GREEN):    
    page.snack_bar.content = ft.Text(message) # type: ignore
    page.snack_bar.bgcolor = color # type: ignore
    page.snack_bar.open = True # type: ignore
    page.update()

# Cria a AppBar padrão com o nome do usuário e botão Logout.
def create_appbar(page: ft.Page, api: ApiClient, titulo: str = "App MC Sonae", leading_control: Optional[ft.Control] = None) -> ft.AppBar:
    me = api.get_usuarios_me()
    if me is None:
        me = {}
    
    leading_with = 100
    leading_items = []
    if leading_control:
        leading_items.append(leading_control)
        leading_items.append(ft.Container(
            content=ft.Image(src="logo1.png", width=50, height=50),
            padding=ft.padding.only(left=5)
        ))
    else:
        leading_items.append(ft.Container(
            content=ft.Image(src="logo1.png", width=50, height=50),
            padding=ft.padding.only(left=10)
        ))
        leading_with = 56

    return ft.AppBar(
        leading=ft.Row(controls=leading_items),
        leading_width=leading_with,
        title=ft.Text(titulo),
        bgcolor=COR_1,
        color=ft.Colors.WHITE,
        actions=[
            ft.Container(
                content=ft.Row([
                    ft.Column([
                        # ft.Text(f"Id: {me.get('usuarioid', 'N/A')}", size=10, height=13), # type: ignore
                        # ft.Text(f"Nome: {me.get('nome', 'N/A')}", size=10, height=13), # type: ignore
                        # ft.Text(f"Email: {me.get('email', 'N/A')}", size=10, height=13), # type: ignore
                        # ft.Text(f"Tipo: {me.get('tipou', {}).get('tipo', 'N/A')}", size=10, height=13), # type: ignore
                        # ], spacing=1),
                        ft.Text(f"{me.get('nome', 'N/A')}"), # type: ignore
                        ], spacing=1, alignment=ft.MainAxisAlignment.CENTER),

                    ft.IconButton(
                        ft.Icons.PERSON,
                        tooltip="Mudar Senha Usuário",
                        icon_color=ft.Colors.WHITE,
                        on_click=lambda _: page.go(f"/mudar/senha/{me.get('usuarioid', 'N/A')}")
                        ),
                    ft.IconButton(
                        ft.Icons.LOGOUT,
                        tooltip="Logout",
                        icon_color=ft.Colors.WHITE,
                        on_click=lambda _: (
                            api.logout(),
                            page.go("/login")
                        )
                    )
                ], 
                spacing=2,
                ),
                padding=ft.padding.only(right=20)
            ),
        ]
    )

# Renderiza a Tela de Logon.
def view_login(page: ft.Page, api: ApiClient) -> ft.View:
    email_field = ft.TextField(
        label="Email",
        hint_text="user@mcsonae.pt",
        width=300,
        autofocus=True
    )
    
    password_field = ft.TextField(
        label="Senha",
        password=True, 
        can_reveal_password=True, 
        width=300
    )
   
    error_text = ft.Text(value="", color=ft.Colors.RED)

    def on_login_click(e):
        email = email_field.value
        password = password_field.value
        
        if not email or not password:
            error_text.value = "Preencha ambos os campos."
            page.update()
            return

        success, message = api.login(email, password)
        
        if success:
            page.go("/menu")
        else:
            error_text.value = message
            page.update()

    return ft.View(
        route="/login",
        controls=[
            ft.AppBar(title=ft.Text("App MC Sonae"), 
                      color=ft.Colors.WHITE, 
                      bgcolor=COR_1, 
                      leading=ft.Container(
                            content=ft.Image(src="logo1.png", width=50, height=50),
                            padding=ft.padding.only(left=5)
                    )),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Image(src="logo.png"),
                        email_field,
                        password_field,
                        ft.ElevatedButton(
                            text="Login",
                            style=button_style,
                            on_click=on_login_click,
                            icon=ft.Icons.LOGIN,
                            width=300
                        ),
                        error_text,
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20,
                ),
                alignment=ft.alignment.center,
                expand=True,
            )
        ]
    )

# Renderiza a Tela de Menu.
def view_menu(page: ft.Page, api: ApiClient) -> ft.View:
    
    permissoes = {
        "Administrador": ["/consultar", "/projetos", "/repositorio", "/promptgeral", "/usuarios"],
        "Supervisor": ["/consultar", "/projetos", "/repositorio"],
        "Usuário": ["/consultar"],
    }
    menu_items_disponiveis = [
        {"title": "Consultar Projeto", "subtitle": "Pesquisar e Visualizar Projeto", "icon": ft.Icons.SEARCH, "route": "/consultar"},
        {"title": "Cadastro de Projetos", "subtitle": "Administrar Projetos", "icon": ft.Icons.ACCOUNT_TREE, "route": "/projetos"},
        {"title": "Anexar Arquivos ao Repositório", "subtitle": "Anexar Arquivos ao Repositório do Projeto", "icon": ft.Icons.ATTACH_FILE, "route": "/repositorio"},
        {"title": "Prompt Geral", "subtitle": "Alterar Prompt Geral da IA para Geração de Conteúdos", "icon": ft.Icons.CALL_TO_ACTION, "route": "/promptgeral"},
        {"title": "Cadastro de Usuários", "subtitle": "Gerenciar os Usuários do Sistema", "icon": ft.Icons.PEOPLE, "route": "/usuarios"},
    ]

    me = api.get_usuarios_me()
    user_type = me.get('tipou', {}).get('tipo', 'N/A') if me else 'N/A' # type: ignore

    def create_menu_card(title: str, subtitle: str, icon_name: str, route: str) -> ft.ElevatedButton:
        return ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Icon(name=icon_name, size=32, color=ft.Colors.WHITE),
                    ft.Text(value=title, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10
            ),
            on_click=lambda _: page.go(route),
            style=button_style,
            width=400,
            height=50,
            tooltip=subtitle
        )

    rotas_permitidas = permissoes.get(user_type, [])
    menu_controls = [
        ft.Text("Menu", style=ft.TextThemeStyle.HEADLINE_LARGE)
    ]
    for item in menu_items_disponiveis:
        if item["route"] in rotas_permitidas:
            menu_card = create_menu_card(item["title"], item["subtitle"], item["icon"], item["route"])
            menu_controls.append(menu_card) # type: ignore

    app_bar = create_appbar(page, api, titulo="App MC Sonae - Menu",leading_control=None)

    return ft.View(
        route="/menu",
        appbar=app_bar,
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=menu_controls,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=15
                ),
                alignment=ft.alignment.center,
                padding=20
            )
        ]
    )

# Renderiza a tela de detalhes de um usuário.
def view_usuario_detail(page: ft.Page, api: ApiClient, user_id: int) -> ft.View:
    user = api.get_user_by_id(user_id)
    permissoes = api.get_permissoes_usuario()

    if not user:
        return ft.View(
            route=f"/usuarios/{user_id}",
            appbar=create_appbar(page, api),
            controls=[ft.Text("Usuário não encontrado.")]
        )

    cor = ft.Colors.BLACK
    if user.get("status") == "Ativo": # type: ignore
        cor = ft.Colors.GREEN_900
    elif user.get("status") == "Bloqueado": # type: ignore
        cor = ft.Colors.ORANGE_900
    elif user.get("status") == "Cancelado": # type: ignore
        cor = ft.Colors.RED_900

    detailsa = [ft.Text("Visualizar Usuário",style=ft.TextThemeStyle.HEADLINE_MEDIUM),
        ft.Text(f"Id: {user.get('usuarioid')}", weight=ft.FontWeight.BOLD, size=22),
        ft.Text(f"Nome: {user.get('nome')}", size=20),
        ft.Text(f"Email: {user.get('email')}", size=20),
        ft.Text(f"Tipo: {user.get('tipou', {}).get('tipo')}", size=20),
        ft.Text(f"Status: {user.get('status')}", size=20, color=cor, weight=ft.FontWeight.BOLD),
        ft.Text(f"Permissões: ", size=20),
    ]
    for permissao in permissoes:  # type: ignore
        if permissao.get("tipoid") == user.get('tipoid'):
             detailsa.append(ft.Text(f"         + {permissao.get('politica', {}).get('descricao')}", size=20),)
    details = ft.Column(spacing=10, alignment=ft.MainAxisAlignment.CENTER, controls=detailsa)

    app_bar = create_appbar(
        page, api,
        titulo="App MC Sonae - Cadastro de Usuários - Visualizar Usuários",
        leading_control=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/usuarios"), tooltip="Voltar")
    )

    return ft.View(
        route=f"/usuarios/{user_id}",
        appbar=app_bar,
        controls=[
            ft.Container(
                content=details,
                padding=20,
                alignment=ft.alignment.center,
            )
        ]
    )

# Renderiza a Tela de Cadastro de Usuários (Lista).
def view_usuarios_list(page: ft.Page, api: ApiClient) -> ft.View:
    search_term = None
    if page.route and "?" in page.route:
        params = dict(p.split("=") for p in page.route.split("?")[1].split("&"))
        search_term = params.get("filtro")

    users_data = api.get_users(search_term=search_term)
    procura_usuarios_field = ft.TextField(
        hint_text="Pesquisar usuários...", 
        expand=True, 
        value=search_term,
        on_submit=lambda e: search_users()
    )

    # Cria uma instância do AlertDialog que será reutilizada.
    delete_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirma Apagar"),
        content=ft.Text(""),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: close_dialog()),
            ft.FilledButton("Apagar", style=button_style,on_click=lambda _: ...), # O on_click será atualizado dinamicamente
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # Cria uma instância do AlertDialog que será reutilizada.
    reset_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirma Reset de Senha do Usuário"),
        content=ft.Text(""),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: close_dialog()),
            ft.FilledButton("Resetar", style=button_style,on_click=lambda _: ...), # O on_click será atualizado dinamicamente
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # Adiciona o diálogo à camada de sobreposição da página.
    page.overlay.append(delete_dialog)
    page.overlay.append(reset_dialog)
    
    def open_delete_dialog(user_to_delete):
        def on_delete_confirm(e):
            success, message = api.delete_user(user_to_delete.get("usuarioid"))
            if success:
                show_snackbar(page, message, ft.Colors.GREEN)
                search_users() # Chama a função de pesquisa para recarregar a lista
            else:
                show_snackbar(page, message, ft.Colors.RED)
            delete_dialog.open = False
            page.update()
        
        # Atualiza o conteúdo e as ações do diálogo existente
        delete_dialog.content = ft.Text(f"Tem certeza que deseja apagar o usuário {user_to_delete.get('nome')}?")
        # O botão "Apagar" precisa ter sua ação (on_click) atualizada para o usuário correto.
        delete_dialog.actions[1].on_click = on_delete_confirm # type: ignore
        delete_dialog.open = True
        page.update()

    def open_reset_dialog(user_to_reset):
        def on_reset_confirm(e):
            success, message, user = api.reset_user(user_to_reset.get("usuarioid"))
            senha_gerada = user.get("senha_gerada") if user else None
            if senha_gerada:
                envia_email(user.get("nome"), user.get("email"), senha_gerada, CHAVE_API_BREVO) # type: ignore
            if success:
                show_snackbar(page, message, ft.Colors.GREEN)
                search_users() # Chama a função de pesquisa para recarregar a lista
            else:
                show_snackbar(page, message, ft.Colors.RED)
            reset_dialog.open = False
            page.update()
        
        # Atualiza o conteúdo e as ações do diálogo existente
        reset_dialog.content = ft.Text(f"Tem certeza que deseja resetar a senha do usuário {user_to_reset.get('nome')}?")
        # O botão "Apagar" precisa ter sua ação (on_click) atualizada para o usuário correto.
        reset_dialog.actions[1].on_click = on_reset_confirm # type: ignore
        reset_dialog.open = True
        page.update()

    def close_dialog():
        delete_dialog.open = False
        reset_dialog.open = False
        page.update()

    def search_users():
        term = procura_usuarios_field.value
        if term:
            page.go(f"/usuarios/?filtro={term}")
        else:
            page.go(f"/usuarios/")
    
    def criar_celula(conteudo, largura=None, alinhamento=ft.alignment.center_left):
        return ft.Container(
            content=conteudo,
            width=largura,
            padding=10,
            alignment=alinhamento,
        )

    cabecalho = ft.Row(
        controls=[
            criar_celula(ft.Text("Id", weight=ft.FontWeight.BOLD, color=COR_5), 150, ft.alignment.top_center),
            criar_celula(ft.Text("Nome", weight=ft.FontWeight.BOLD, color=COR_5), 350, ft.alignment.top_center),
            criar_celula(ft.Text("Email", weight=ft.FontWeight.BOLD, color=COR_5), 200, ft.alignment.top_center),
            criar_celula(ft.Text("Tipo", weight=ft.FontWeight.BOLD, color=COR_5), 150, ft.alignment.top_center),
            criar_celula(ft.Text("Status", weight=ft.FontWeight.BOLD, color=COR_5), 150, ft.alignment.top_center),
            criar_celula(ft.Text("", weight=ft.FontWeight.BOLD, color=COR_5), 200, ft.alignment.top_center),
        ],
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.START
    )

    # Corpo da tabela com scroll
    linhas = []
    zebrado = False
    if users_data:
        for usu in users_data:
            cor = ft.Colors.BLACK
            if usu.get("status") == "Ativo": # type: ignore
                # cor = ft.Colors.GREEN_900
                cor = ft.Colors.GREEN
            elif usu.get("status") == "Bloqueado": # type: ignore
                # cor = ft.Colors.ORANGE_900
                cor = ft.Colors.ORANGE
            elif usu.get("status") == "Cancelado": # type: ignore
                # cor = ft.Colors.RED_900
                cor = ft.Colors.RED
            if zebrado:
                cor_zebrado = COR_3
                # cor_zebrado = "#A2BCE0"
                # cor_zebrado = "#F17E69"
            else:
                cor_zebrado = ft.Colors.WHITE
            zebrado = not zebrado
            linhas.append(
                ft.Container(
                    ft.Row(
                        controls=[
                            criar_celula(ft.Text(usu.get("usuarioid"), weight=ft.FontWeight.BOLD), 150, ft.alignment.top_center),
                            criar_celula(
                                ft.Text(
                                    usu.get("nome"),
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    tooltip=usu.get("nome"),
                                    selectable=True,
                                ), 
                                350
                            ),
                            criar_celula(ft.Text(usu.get("email")), 200, ft.alignment.top_center),
                            criar_celula(ft.Text(usu.get("tipou", {}).get("tipo")), 150, ft.alignment.top_center),
                            criar_celula(ft.Text(usu.get("status"), color=cor, weight=ft.FontWeight.BOLD), 150, ft.alignment.top_center),
                            criar_celula(
                                            ft.Row(
                                                controls=[
                                                    ft.IconButton(
                                                        ft.Icons.VISIBILITY,
                                                        icon_color=ft.Colors.BLACK,
                                                        tooltip="Visualiza Usuário",
                                                        on_click=lambda e, u=usu: page.go(f"/usuarios/{u.get('usuarioid')}")
                                                    ),  
                                                    ft.IconButton(
                                                        ft.Icons.EDIT_SHARP,
                                                        icon_color=ft.Colors.BLACK,
                                                        tooltip="Edita Usuário",
                                                        on_click=lambda e, u=usu: page.go(f"/usuarios/editar/{u.get('usuarioid')}")
                                                    ),
                                                    ft.IconButton(
                                                        ft.Icons.REMOVE_SHARP,
                                                        icon_color=ft.Colors.BLACK,
                                                        tooltip="Apaga Usuário",
                                                        on_click=lambda e, u=usu: open_delete_dialog(u)
                                                    ),
                                                    ft.IconButton(
                                                        ft.Icons.LOCK_RESET,
                                                        icon_color=ft.Colors.BLACK,
                                                        tooltip="Reseta Senha Usuário",
                                                        on_click=lambda e, u=usu: open_reset_dialog(u)
                                                    ),
                                                ],
                                                alignment=ft.MainAxisAlignment.CENTER,  # Centraliza horizontalmente
                                            ),
                                200, ft.alignment.top_center
                            )
                        ],
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.START
                    ),
                    bgcolor=cor_zebrado,
                    padding=0,
                    border=ft.border.only(
                        top=ft.border.BorderSide(1, COR_1),
                    )
                )
            )
    # Tabela completa
    tabela = ft.Column(
        controls=[
            # Cabeçalho fixo
            ft.Container(
                cabecalho,
                bgcolor=COR_1,
                # padding=10,
                padding=ft.padding.only(left=10, right=10, top=10, bottom=10),
                border=ft.border.only(
                    top=ft.border.BorderSide(1, COR_1),
                    left=ft.border.BorderSide(1, COR_1),
                    right=ft.border.BorderSide(1, COR_1)
                )
            ),
            # Corpo com scroll
            ft.Container(
                content=ft.ListView(
                    controls=linhas,
                    expand=True,
                    spacing=0,
                    padding=0,
                ),
                border=ft.border.only(
                    bottom=ft.border.BorderSide(1, ft.Colors.BLACK),
                    left=ft.border.BorderSide(1, ft.Colors.BLACK),
                    right=ft.border.BorderSide(1, ft.Colors.BLACK)
                ),
                expand=True
            )
        ],
        spacing=0,
        # expand=True
        width=1200
    )

    app_bar = create_appbar(
        page, api,
        titulo="App MC Sonae - Cadastro de Usuários",
        leading_control=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/menu"), tooltip="Voltar")
    )

    procura_usuarios_field = ft.TextField(hint_text="Pesquisar usuários...", expand=True, value=search_term)

    return ft.View(
        route="/usuarios",
        appbar=app_bar,
        controls=[
            ft.Column(
                [
                    ft.Row(
                        [
                            procura_usuarios_field, 
                            ft.ElevatedButton(
                                "Pesquisar",
                                icon=ft.Icons.SEARCH,
                                style=button_style,
                                tooltip="Pesquisar usuários pelo nome",
                                on_click=lambda e: search_users()
                            )
                        ]
                    ),
                    ft.ElevatedButton(
                        "Novo usuário",
                        icon=ft.Icons.ADD,
                        style=button_style,
                        tooltip="Criar novo usuário",
                        on_click=lambda _: page.go("/usuarios/novo")
                    ),
                    ft.Divider(),
                    # ft.Row([users_table], scroll=ft.ScrollMode.ALWAYS)
                    # ft.Column(
                    #     controls=[
                    #         ft.Container(
                    #             tabela,
                    #             expand=True,
                    #             border_radius=0,
                    #         ),
                    #     ],
                    #     expand=True,
                    # )
                    ft.Row(
                        controls=[
                            tabela
                        ],
                        expand=True,
                        scroll=ft.ScrollMode.AUTO,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    )
                ],
                expand=True
            ),
        ],
        padding=20
    )

# Renderiza a Tela de Cadastro/ Edição de Usuários.
def view_usuario_form(page: ft.Page, api: ApiClient, user_id: Optional[int] = None) -> ft.View:
    is_editing = user_id is not None
    user_data = api.get_user_by_id(user_id) if is_editing else {}
    
    tipos_usuario = api.get_tipos_usuario() or []
    tipos_options = [ft.dropdown.Option(key=tipo['tipoid'], text=tipo['tipo']) for tipo in tipos_usuario]

    nome_field = ft.TextField(label="Nome", value=user_data.get("nome", "") if is_editing else "") # type: ignore
    email_field = ft.TextField(label="Email", value=user_data.get("email", "") if is_editing else "") # type: ignore
    # password_field = ft.TextField(label="Senha", password=True, can_reveal_password=True, visible=not is_editing)
    tipo_dropdown = ft.dropdown.Dropdown(
        label="Tipo de Usuário",
        options=tipos_options,
        width=300,
        value=user_data.get("tipou", {}).get("tipoid") if is_editing else None # type: ignore
    )
    status_dropdown = ft.dropdown.Dropdown(
        label="Status",
        options=[
            ft.dropdown.Option("Ativo"),
            ft.dropdown.Option("Bloqueado"),
            ft.dropdown.Option("Cancelado"),
        ],
        width=300,
        value=user_data.get("status", "") # type: ignore 
    )

    # Coleta os dados do formulário
    def on_save_click(e):
        senha_forte = gerar_senha_forte() 
        data = {
            "email": email_field.value,
            "nome": nome_field.value,
            "tipoid": tipo_dropdown.value,
            "status": status_dropdown.value,
            "senha": senha_forte,
        }

        if is_editing:
            # Lógica de atualização
            success, message = api.update_user(user_id, data) # type: ignore
        else:
            # Lógica de criação
            # data["senha"] = password_field.value
            success, message = api.create_user(data)
            if success:
               envia_email(nome_field.value, email_field.value, senha_forte, CHAVE_API_BREVO)

        if success:
            show_snackbar(page, message, ft.Colors.GREEN)
            page.go("/usuarios")
        else:
            show_snackbar(page, message, ft.Colors.RED)

    app_bar = create_appbar(
        page, api,
        titulo="App MC Sonae - Cadastro de Usuários - Novo Usuário" if not is_editing else "App MC Sonae - Cadastro de Usuários - Editar Usuário",
        leading_control=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/usuarios"), tooltip="Voltar")
    )

    return ft.View(
        route=f"/usuarios/editar/{user_id}" if is_editing else "/usuarios/novo",
        appbar=app_bar,
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Editar Usuário" if is_editing else "Novo Usuário",
                            style=ft.TextThemeStyle.HEADLINE_MEDIUM
                        ),
                        nome_field,
                        email_field,
                        # password_field,
                        tipo_dropdown,
                        status_dropdown,
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    "Salvar",
                                    icon=ft.Icons.SAVE,
                                    style=button_style,
                                    on_click=on_save_click
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.END
                        )
                    ],
                    spacing=15
                ),
                padding=20,
                width=600,
                alignment=ft.alignment.center
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

# Renderiza a Tela de Cadastro/ Edição de Usuários.
def view_mudar_senha_usuario_form(page: ft.Page, api: ApiClient, user_id: int) -> ft.View:
    user_data = api.get_usuarios_me()
    
    nome = user_data.get("nome", "") # type: ignore
    email = user_data.get("email", "") # type: ignore
    tipoid = user_data.get("tipoid") # type: ignore
    status = user_data.get("status") # type: ignore

    nomet = ft.Text(f"Nome: {nome}")
    emailt = ft.Text(f"Email: {email}")

    # senha_atual_valida = False
    senha_nova_valida = False
    senha_nova_confirmar_valida = False


    # Validar Mudar Senha
    def validar_mudar_senha():
        # nonlocal senha_atual_valida
        nonlocal senha_nova_valida
        nonlocal senha_nova_confirmar_valida
        mudar_senha_validado = all([
            # senha_atual_valida,
            senha_nova_valida,
            senha_nova_confirmar_valida
        ])
        bt_mudar_senha.disabled = not mudar_senha_validado

    # Validar Senha Atual
    # def validar_senha_atual(e):
        # nonlocal senha_atual_valida
        # # nonlocal email
      
        # # success, message = api.login(email, tf_senha_atual.value if None else "")
        
        # senha_atual_valida = True

        # # erros = []
        # # if not success:
        # #     erros.append("A senha atual inválida")
        # # if erros:
        # #     tf_senha_atual.error_text = "\n".join(erros)
        # #     cl_validacao_senha_atual.controls = [
        # #         ft.Row([
        # #             ft.Icon(ft.Icons.CHECK if senha_atual_valida else ft.Icons.CLOSE, # type: ignore
        # #             color="green" if senha_atual_valida else "red"), # type: ignore
        # #             ft.Text("Senha inválida")
        # #         ]),
        # #     ]
        # # else:
        # #     tf_senha_nova.error_text = None
        # #     cl_validacao_senha_atual.controls = [
        # #         ft.Row([
        # #             ft.Icon(ft.Icons.CHECK_CIRCLE, color="green"),
        # #             ft.Text("Senha atual Ok!", weight=ft.FontWeight.BOLD)
        # #         ]),
        # #     ]

        # # cl_validacao_senha_atual.update()
        # validar_mudar_senha()   
        # page.update()

    # Validar Senha Nova
    def validar_senha_nova(e):
        nonlocal senha_nova_valida
        senha_nova_valida = False
        senha_nova = tf_senha_nova.value
        erros = []
        # Verifica cada requisito individualmente
        if len(senha_nova) < 12: # type: ignore 
            erros.append("Mínimo 12 caracteres")
        if not re.search(r'[A-Z]', senha_nova): # type: ignore
            erros.append("Pelo menos 1 letra maiúscula")
        if not re.search(r'[a-z]', senha_nova): # type: ignore
            erros.append("Pelo menos 1 letra minúscula")
        if not re.search(r'[0-9]', senha_nova): # type: ignore
            erros.append("Pelo menos 1 número")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', senha_nova): # type: ignore
            erros.append("Pelo menos 1 símbolo especial")

        if erros:
            tf_senha_nova.error_text = "\n".join(erros)
            # Exibe quais requisitos foram atendidos
            cl_validacao_indicadores.controls = [
                ft.Row([
                    ft.Text("A senha deve conter", color="grey")
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.CHECK if len(senha_nova) >= 8 else ft.Icons.CLOSE, # type: ignore
                    color="green" if len(senha_nova) >= 8 else "red"), # type: ignore
                    ft.Text("8+ caracteres")
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.CHECK if re.search(r'[A-Z]', senha_nova) else ft.Icons.CLOSE, # type: ignore
                    color="green" if re.search(r'[A-Z]', senha_nova) else "red"), # type: ignore
                    ft.Text("Letra maiúscula")
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.CHECK if re.search(r'[a-z]', senha_nova) else ft.Icons.CLOSE, # type: ignore
                        color="green" if re.search(r'[a-z]', senha_nova) else "red"), # type: ignore
                    ft.Text("Letra minúscula")
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.CHECK if re.search(r'[0-9]', senha_nova) else ft.Icons.CLOSE, # type: ignore
                        color="green" if re.search(r'[0-9]', senha_nova) else "red"), # type: ignore
                    ft.Text("Número")
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.CHECK if re.search(r'[!@#$%^&*(),.?":{}|<>]', senha_nova) else ft.Icons.CLOSE, # type: ignore
                        color="green" if re.search(r'[!@#$%^&*(),.?":{}|<>]', senha_nova) else "red"), # type: ignore
                    ft.Text("Símbolo especial")
                ])
            ]
        else:
            tf_senha_nova.error_text = None
            senha_nova_valida = True
            cl_validacao_indicadores.controls = [
                ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color="green"),
                    ft.Text("Senha forte!", weight=ft.FontWeight.BOLD)
                ]),
            ]

        cl_validacao_indicadores.update()
        validar_mudar_senha()
        page.update()
        validar_senha_nova_confirmar(e)

    # Validar Senha Nova Confirmar
    def validar_senha_nova_confirmar(e):
        nonlocal senha_nova_confirmar_valida
        senha_nova_confirmar_valida = False
        senha_nova = tf_senha_nova.value
        senha_nova_confirmar = tf_senha_nova_confirmar.value
        errosc = []
        # Verifica cada requisito individualmente
        if len(senha_nova_confirmar) < 8: # type: ignore 
            errosc.append("Mínimo 8 caracteres")
        if not re.search(r'[A-Z]', senha_nova_confirmar): # type: ignore
            errosc.append("Pelo menos 1 letra maiúscula")
        if not re.search(r'[a-z]', senha_nova_confirmar): # type: ignore
            errosc.append("Pelo menos 1 letra minúscula")
        if not re.search(r'[0-9]', senha_nova_confirmar): # type: ignore
            errosc.append("Pelo menos 1 número")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', senha_nova_confirmar): # type: ignore
            errosc.append("Pelo menos 1 símbolo especial")
        if not senha_nova == senha_nova_confirmar:
            errosc.append("Confirma Senha")

        if errosc:
            tf_senha_nova_confirmar.error_text = "\n".join(errosc)
            # Exibe quais requisitos foram atendidos
            cl_validacao_indicadores_confirmar.controls = [
                ft.Row([
                    ft.Text("A senha deve conter", color="grey")
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.CHECK if len(senha_nova_confirmar) >= 8 else ft.Icons.CLOSE, # type: ignore
                    color="green" if len(senha_nova_confirmar) >= 8 else "red"), # type: ignore
                    ft.Text("8+ caracteres")
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.CHECK if re.search(r'[A-Z]', senha_nova_confirmar) else ft.Icons.CLOSE, # type: ignore
                    color="green" if re.search(r'[A-Z]', senha_nova_confirmar) else "red"), # type: ignore
                    ft.Text("Letra maiúscula")
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.CHECK if re.search(r'[a-z]', senha_nova_confirmar) else ft.Icons.CLOSE, # type: ignore
                        color="green" if re.search(r'[a-z]', senha_nova_confirmar) else "red"), # type: ignore
                    ft.Text("Letra minúscula")
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.CHECK if re.search(r'[0-9]', senha_nova_confirmar) else ft.Icons.CLOSE, # type: ignore
                        color="green" if re.search(r'[0-9]', senha_nova_confirmar) else "red"), # type: ignore
                    ft.Text("Número")
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.CHECK if re.search(r'[!@#$%^&*(),.?":{}|<>]', senha_nova_confirmar) else ft.Icons.CLOSE, # type: ignore
                        color="green" if re.search(r'[!@#$%^&*(),.?":{}|<>]', senha_nova_confirmar) else "red"), # type: ignore
                    ft.Text("Símbolo especial")
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.CHECK if senha_nova_confirmar == senha_nova else ft.Icons.CLOSE,
                        color="green" if senha_nova_confirmar == senha_nova else "red"),
                    ft.Text("Confirma Senha")
                ])
            ]
        else:
            tf_senha_nova_confirmar.error_text = None
            senha_nova_confirmar_valida = True
            cl_validacao_indicadores_confirmar.controls = [
                ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color="green"),
                    ft.Text("Senha Confirmada!", weight=ft.FontWeight.BOLD)
                ]),
            ]

        cl_validacao_indicadores_confirmar.update()
        validar_mudar_senha()
        page.update()

    # tf_senha_atual = ft.TextField(label="Senha Atual", password=True, can_reveal_password=True, on_change=validar_senha_atual)
    # cl_validacao_senha_atual = ft.Column(spacing=5)
    tf_senha_nova = ft.TextField(label="Nova Senha", password=True, can_reveal_password=True, on_change=validar_senha_nova)
    cl_validacao_indicadores = ft.Column(spacing=5)
    tf_senha_nova_confirmar = ft.TextField(label="Confirmar a Senha", password=True, can_reveal_password=True, on_change=validar_senha_nova_confirmar)
    cl_validacao_indicadores_confirmar = ft.Column(spacing=5)
    lb_erro_muda_senha = ft.Text("", color=ft.Colors.RED)
 
    # Coleta os dados do formulário
    def on_save1_click(e):

        data = {
            "email": email,
            "nome": nome,
            "tipoid": tipoid,
            "status": status,
            "senha": tf_senha_nova.value,
        }

        # success, message = api.login(email, tf_senha_atual.value if None else "")

        # if success:
        #     success, message = api.update_user(user_id, data) # type: ignore

        #     if success:
        #         show_snackbar(page, message, ft.Colors.GREEN)
        #         page.go("/menu")
        #     else:
        #         show_snackbar(page, message, ft.Colors.RED)
        # else:
        #     show_snackbar(page, message, ft.Colors.RED)

        success, message = api.update_senha_user(user_id, data) # type: ignore

        if success:
            show_snackbar(page, message, ft.Colors.GREEN)
            page.go("/menu")
        else:
            show_snackbar(page, message, ft.Colors.RED)

    app_bar = create_appbar(
        page, api,
        titulo="App MC Sonae - Mudar Senha do Usuário", 
        leading_control=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/menu"), tooltip="Voltar")
    )

    bt_mudar_senha = ft.ElevatedButton("Mudar Senha", style=button_style, on_click=on_save1_click, disabled=True, icon=ft.Icons.SAVE)

    return ft.View(
        route=f"/usuarios/senha/{user_id}",
        appbar=app_bar,
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Mudar Senha do Usuário", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                        nomet,
                        emailt,
                        # ft.Text(" "),
                        # tf_senha_atual,
                        # cl_validacao_senha_atual,
                        ft.Text(" "),
                        tf_senha_nova, 
                        cl_validacao_indicadores, 
                        tf_senha_nova_confirmar, 
                        cl_validacao_indicadores_confirmar,
                        lb_erro_muda_senha,

                        ft.Row(
                            [
                                bt_mudar_senha,
                                # ft.ElevatedButton(
                                #     "Salvar",
                                #     icon=ft.Icons.SAVE,
                                #     style=button_style,
                                #     on_click=on_save_click
                                # ),
                            ],
                            alignment=ft.MainAxisAlignment.END
                        )
                    ],
                    spacing=15
                ),
                padding=20,
                width=600,
                alignment=ft.alignment.center
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

# Renderiza a Tela de Edição de Prompt Geral.
def view_promtgeral_form(page: ft.Page, api: ApiClient, prompt_id: int) -> ft.View:
    prompt_data = api.get_prompt_geral(prompt_id)
    
    responsavel = prompt_data.get('usuario', {}).get("nome", "") # type: ignore
    promptid = prompt_data.get("promptid") # type: ignore
    prompt = prompt_data.get("prompt") # type: ignore
    datahora = prompt_data.get("datahora") # type: ignore
    
    datahora = str(datahora)
    if datahora.endswith('Z'):
        datahora = datahora[:-1] + '+00:00'
    # 1. Converte a string ISO para um objeto datetime (que estará em UTC)
    objeto_datetime = datetime.fromisoformat(datahora)
    # 2. Converte o objeto datetime de UTC para o fuso horário de Recife (America/Recife, UTC-3)
    datahora_recife = objeto_datetime.astimezone(ZoneInfo("America/Recife"))
    datahora_br = datahora_recife.strftime('%d/%m/%Y %H:%M:%S')

    # tf_promptid = ft.TextField(label="Id", read_only=True, value=promptid)
    tf_responsavel = ft.TextField(label="Responsável", read_only=True, value=responsavel)
    tf_datahora = ft.TextField(label="Data/Hora", read_only=True, value=datahora_br)
    tf_prompt = ft.TextField(label="Prompt", value=prompt, multiline=True, expand=True, max_lines=15)
 
    # Coleta os dados do formulário
    def on_save2_click(e):
        # Gera a data e hora atual no formato ISO 8601 UTC
        data_hora_utc = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

        data = {
            "prompt": tf_prompt.value,
            "usuarioid": 0,
            "datahora": data_hora_utc,
        }

        success, message = api.update_prompt_geral(prompt_id, data) # type: ignore

        if success:
            show_snackbar(page, message, ft.Colors.GREEN)
            page.go("/menu")
        else:
            show_snackbar(page, message, ft.Colors.RED)

    app_bar = create_appbar(
        page, api,
        titulo="App MC Sonae - Prompt Geral", 
        leading_control=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/menu"), tooltip="Voltar")
    )

    bt_salvar = ft.ElevatedButton("Salvar", style=button_style, on_click=on_save2_click, icon=ft.Icons.SAVE)

    return ft.View(
        route=f"/promptgeral/{prompt_id}",
        appbar=app_bar,
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Prompt Geral", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                        # tf_promptid,
                        tf_responsavel,
                        tf_datahora,
                        tf_prompt,
                        ft.Row(
                            [
                                bt_salvar,
                            ],
                            alignment=ft.MainAxisAlignment.END
                        )
                    ],
                    spacing=15
                ),
                padding=20,
                width=800,
                alignment=ft.alignment.center
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

# Renderiza a tela de detalhes de um projeto.
def view_projeto_detail(page: ft.Page, api: ApiClient, projeto_id: int) -> ft.View:
    pj = api.get_projeto_by_id(projeto_id)

    if not pj:
        return ft.View(
            route=f"/projetos/{projeto_id}",
            appbar=create_appbar(page, api),
            controls=[ft.Text("Projeto não encontrado.")]
        )

    cor = ft.Colors.BLACK
    if pj.get("status") == "Ativo": # type: ignore
        cor = ft.Colors.GREEN
    elif pj.get("status") == "Encerrado": # type: ignore
        cor = ft.Colors.RED

    detailsa = [ft.Text("Visualizar Projeto",style=ft.TextThemeStyle.HEADLINE_MEDIUM),
        ft.Text(f"Id: {pj.get('projetoid')}", weight=ft.FontWeight.BOLD, size=22),
        ft.Text(f"Projeto: {pj.get('projeto')}", size=20),
        ft.Text(f"Status: {pj.get('status')}", size=20, color=cor, weight=ft.FontWeight.BOLD),
    ]
    details = ft.Column(spacing=10, alignment=ft.MainAxisAlignment.CENTER, controls=detailsa)

    # ### Repositório
    search_term = pj.get('projetoid')
    search_term = search_term if search_term is not None else 0
    rep_data = api.get_repositorios(search_term=search_term) # type: ignore

    # Cria o controle Markdown que será atualizado e exibido no diálogo.
    markdown_content_control = ft.Markdown(
        "",
        selectable=True,
        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
        on_tap_link=lambda e: page.launch_url(e.data),  # type: ignore
    )

    # Cria uma instância do AlertDialog para visualizar o Markdown.
    markdown_view_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Conteúdo do Repositório"),
        content=ft.Container(
            content=ft.Column([markdown_content_control], scroll=ft.ScrollMode.AUTO, expand=True),
            width=800,
            height=600,
        ),
        actions=[ft.TextButton("Fechar", style=button_style, on_click=lambda _: close_markdown_dialog(markdown_view_dialog))],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # Cria uma instância do AlertDialog que será reutilizada.
    delete_rep_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirma Apagar"),
        content=ft.Text(""),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: close_rep_dialog()),
            ft.FilledButton("Apagar", style=button_style,on_click=lambda _: ...), # O on_click será atualizado dinamicamente
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # Adiciona o diálogo à camada de sobreposição da página.
    page.overlay.append(delete_rep_dialog)
    page.overlay.append(markdown_view_dialog)
    
    def open_delete_rep_dialog(rep_to_delete):
        def on_delete_rep_confirm(e):
            success, message = api.delete_repositorio(rep_to_delete.get("repositorioid"))
            if success:
                show_snackbar(page, message, ft.Colors.GREEN)
                search_rep() # Chama a função de pesquisa para recarregar a lista
            else:
                show_snackbar(page, message, ft.Colors.RED)
            delete_rep_dialog.open = False
            page.update()
        
        # Atualiza o conteúdo e as ações do diálogo existente
        delete_rep_dialog.content = ft.Text(f"Tem certeza que deseja apagar o repositório {rep_to_delete.get('repositorioid')}?")
        delete_rep_dialog.actions[1].on_click = on_delete_rep_confirm # type: ignore
        delete_rep_dialog.open = True
        page.update()

    def close_rep_dialog():
        delete_rep_dialog.open = False
        page.update()

    def open_markdown_dialog(rep_item):
        # Atualiza o conteúdo do controle Markdown e abre o diálogo.
        markdown_content_control.value = rep_item.get("markdown", "### Nenhum conteúdo para exibir.")
        markdown_view_dialog.content.update() # type: ignore
        markdown_view_dialog.open = True
        markdown_view_dialog.update() # Atualiza apenas o diálogo (para abrir)

    def close_markdown_dialog(dialog: ft.AlertDialog):
        dialog.open = False
        dialog.update() # Atualiza apenas o diálogo (para fechar)

    def search_rep():
        page.go(f"/projetos/{projeto_id}?refresh={random.randint(0, 100000)}")
        
    def criar_rep_celula(conteudo, largura=None, alinhamento=ft.alignment.center_left):
        return ft.Container(
            content=conteudo,
            width=largura,
            padding=10,
            alignment=alinhamento,
        )

    cabecalho = ft.Row(
        controls=[
            criar_rep_celula(ft.Text("Repositório", weight=ft.FontWeight.BOLD, color=COR_5), 150, ft.alignment.top_center),
            criar_rep_celula(ft.Text("Data Hora", weight=ft.FontWeight.BOLD, color=COR_5), 200, ft.alignment.top_center),
            criar_rep_celula(ft.Text("Projeto", weight=ft.FontWeight.BOLD, color=COR_5), 350, ft.alignment.top_center),
            criar_rep_celula(ft.Text("Usuário", weight=ft.FontWeight.BOLD, color=COR_5), 200, ft.alignment.top_center),
            criar_rep_celula(ft.Text("Tipo Arq.", weight=ft.FontWeight.BOLD, color=COR_5), 100, ft.alignment.top_center),
            criar_rep_celula(ft.Text("", weight=ft.FontWeight.BOLD, color=COR_5), 150, ft.alignment.top_center),
        ],
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.START
    )

    # Corpo da tabela com scroll
    linhas = []
    zebrado = False
    if rep_data:
        for rep in rep_data:
            if zebrado:
                cor_zebrado = COR_3
                # cor_zebrado = "#A2BCE0"
                # cor_zebrado = "#F17E69"
            else:
                cor_zebrado = ft.Colors.WHITE
            zebrado = not zebrado
            datahora = rep.get("datahora") # type: ignore
            datahora = str(datahora)
            if datahora.endswith('Z'):
                datahora = datahora[:-1] + '+00:00'
            # 1. Converte a string ISO para um objeto datetime (que estará em UTC)
            objeto_datetime = datetime.fromisoformat(datahora)
            # 2. Converte o objeto datetime de UTC para o fuso horário de Recife (America/Recife, UTC-3)
            datahora_recife = objeto_datetime.astimezone(ZoneInfo("America/Recife"))
            datahora_br = datahora_recife.strftime('%d/%m/%Y %H:%M:%S')

            linhas.append(
                ft.Container(
                    ft.Row(
                        controls=[
                            criar_rep_celula(ft.Text(rep.get("repositorioid"), weight=ft.FontWeight.BOLD), 150, ft.alignment.top_center),
                            criar_rep_celula(
                                ft.Text(
                                    datahora_br,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    selectable=True,
                                ), 
                                200
                            ),
                            criar_rep_celula(
                                ft.Text(
                                    rep.get('projeto', {}).get("projeto"),
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    tooltip=rep.get('projeto', {}).get("projeto"),
                                    selectable=True,
                                ), 
                                350
                            ),
                            criar_rep_celula(
                                ft.Text(
                                    rep.get("usuario", {}).get("nome"),
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    tooltip=rep.get("usuario", {}).get("nome"),
                                    selectable=True,
                                ), 
                                200
                            ),
                            criar_rep_celula(ft.Text(rep.get("tipoarquivo")), 100, ft.alignment.top_center),
                            criar_rep_celula(
                                            ft.Row(
                                                controls=[
                                                    ft.IconButton(
                                                        ft.Icons.VISIBILITY,
                                                        icon_color=ft.Colors.BLACK,
                                                        tooltip="Visualiza Repositório",
                                                        on_click=lambda e, u=rep: open_markdown_dialog(u)
                                                    ),  
                                                    ft.IconButton(
                                                        ft.Icons.REMOVE_SHARP,
                                                        icon_color=ft.Colors.BLACK,
                                                        tooltip="Apaga Repositório",
                                                        on_click=lambda e, u=rep: open_delete_rep_dialog(u)
                                                    ),
                                                ],
                                                alignment=ft.MainAxisAlignment.CENTER,  # Centraliza horizontalmente
                                            ),
                                150, ft.alignment.top_center
                            )
                        ],
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.START
                    ),
                    bgcolor=cor_zebrado,
                    padding=0,
                    border=ft.border.only(
                        top=ft.border.BorderSide(1, COR_1),
                    )
                )
            )
    # Tabela completa
    tabela = ft.Column(
        controls=[
            # Cabeçalho fixo
            ft.Container(
                cabecalho,
                bgcolor=COR_1,
                # padding=10,
                padding=ft.padding.only(left=10, right=10, top=10, bottom=10),
                border=ft.border.only(
                    top=ft.border.BorderSide(1, COR_1),
                    left=ft.border.BorderSide(1, COR_1),
                    right=ft.border.BorderSide(1, COR_1)
                )
            ),
            # Corpo com scroll
            ft.Container(
                content=ft.ListView(
                    controls=linhas,
                    expand=True,
                    spacing=0,
                    padding=0,
                ),
                border=ft.border.only(
                    bottom=ft.border.BorderSide(1, ft.Colors.BLACK),
                    left=ft.border.BorderSide(1, ft.Colors.BLACK),
                    right=ft.border.BorderSide(1, ft.Colors.BLACK)
                ),
                expand=True
            )
        ],
        spacing=0,
        # expand=True
        width=1150,
    )

    app_bar = create_appbar(
        page, api,
        titulo="App MC Sonae - Cadastro de Projetos - Visualizar Projeto",
        leading_control=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/projetos"), tooltip="Voltar")
    )

    return ft.View(
        route=f"/projetos/{projeto_id}",
        appbar=app_bar,
        controls=[
            ft.Container(
                content=details,
                padding=20,
                alignment=ft.alignment.center_left,
            ),
            ft.Divider(),
            ft.Column(
                [
                    ft.Row(
                        controls=[
                            tabela,
                        ],
                        expand=True,
                        scroll=ft.ScrollMode.AUTO,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    )

                ],
                expand=True
            ),
        ]
    )

# Renderiza a Tela de Cadastro de Projetos (Lista).
def view_projetos_list(page: ft.Page, api: ApiClient) -> ft.View:
    search_term = None
    if page.route and "?" in page.route:
        params = dict(p.split("=") for p in page.route.split("?")[1].split("&"))
        search_term = params.get("filtro")

    projetos_data = api.get_projetos(search_term=search_term)
    procura_projetos_field = ft.TextField(
        hint_text="Pesquisar projetos...", 
        expand=True, 
        value=search_term,
        on_submit=lambda e: search_projetos()
    )

    # Cria uma instância do AlertDialog que será reutilizada.
    delete_pj_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirma Apagar"),
        content=ft.Text(""),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda _: close_pj_dialog()),
            ft.FilledButton("Apagar", style=button_style,on_click=lambda _: ...), # O on_click será atualizado dinamicamente
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # Adiciona o diálogo à camada de sobreposição da página.
    page.overlay.append(delete_pj_dialog)
    
    def open_delete_pj_dialog(projeto_to_delete):
        def on_delete_pj_confirm(e):
            success, message = api.delete_projeto(projeto_to_delete.get("projetoid"))
            if success:
                show_snackbar(page, message, ft.Colors.GREEN)
                search_projetos() # Chama a função de pesquisa para recarregar a lista
            else:
                show_snackbar(page, message, ft.Colors.RED)
            delete_pj_dialog.open = False
            page.update()
        
        # Atualiza o conteúdo e as ações do diálogo existente
        delete_pj_dialog.content = ft.Text(f"Tem certeza que deseja apagar o projeto {projeto_to_delete.get('projeto')}?")
        # O botão "Apagar" precisa ter sua ação (on_click) atualizada para o usuário correto.
        delete_pj_dialog.actions[1].on_click = on_delete_pj_confirm # type: ignore
        delete_pj_dialog.open = True
        page.update()

    def close_pj_dialog():
        delete_pj_dialog.open = False
        page.update()

    def search_projetos():
        term = procura_projetos_field.value
        if term:
            page.go(f"/projetos/?filtro={term}")
        else:
            page.go("/projetos/")
    
    def criar_pj_celula(conteudo, largura=None, alinhamento=ft.alignment.center_left):
        return ft.Container(
            content=conteudo,
            width=largura,
            padding=10,
            alignment=alinhamento,
        )

    cabecalho = ft.Row(
        controls=[
            criar_pj_celula(ft.Text("Id", weight=ft.FontWeight.BOLD, color=COR_5), 150, ft.alignment.top_center),
            criar_pj_celula(ft.Text("Projeto", weight=ft.FontWeight.BOLD, color=COR_5), 350, ft.alignment.top_center),
            criar_pj_celula(ft.Text("Status", weight=ft.FontWeight.BOLD, color=COR_5), 150, ft.alignment.top_center),
            criar_pj_celula(ft.Text("", weight=ft.FontWeight.BOLD, color=COR_5), 200, ft.alignment.top_center),
        ],
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.START
    )

    # Corpo da tabela com scroll
    linhas = []
    zebrado = False
    if projetos_data:
        for pj in projetos_data:
            cor = ft.Colors.BLACK
            if pj.get("status") == "Ativo": # type: ignore
                cor = ft.Colors.GREEN
            elif pj.get("status") == "Encerrado": # type: ignore
                cor = ft.Colors.RED
            if zebrado:
                cor_zebrado = COR_3
                # cor_zebrado = "#A2BCE0"
                # cor_zebrado = "#F17E69"
            else:
                cor_zebrado = ft.Colors.WHITE
            zebrado = not zebrado
            linhas.append(
                ft.Container(
                    ft.Row(
                        controls=[
                            criar_pj_celula(ft.Text(pj.get("projetoid"), weight=ft.FontWeight.BOLD), 150, ft.alignment.top_center),
                            criar_pj_celula(
                                ft.Text(
                                    pj.get("projeto"),
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    tooltip=pj.get("nome"),
                                    selectable=True,
                                ), 
                                350
                            ),
                            criar_pj_celula(ft.Text(pj.get("status"), color=cor, weight=ft.FontWeight.BOLD), 150, ft.alignment.top_center),
                            criar_pj_celula(
                                            ft.Row(
                                                controls=[
                                                    ft.IconButton(
                                                        ft.Icons.VISIBILITY,
                                                        icon_color=ft.Colors.BLACK,
                                                        tooltip="Visualiza Projeto",
                                                        on_click=lambda e, u=pj: page.go(f"/projetos/{u.get('projetoid')}")
                                                    ),  
                                                    ft.IconButton(
                                                        ft.Icons.EDIT_SHARP,
                                                        icon_color=ft.Colors.BLACK,
                                                        tooltip="Edita Projeto",
                                                        on_click=lambda e, u=pj: page.go(f"/projetos/editar/{u.get('projetoid')}")
                                                    ),
                                                    ft.IconButton(
                                                        ft.Icons.REMOVE_SHARP,
                                                        icon_color=ft.Colors.BLACK,
                                                        tooltip="Apaga Projeto",
                                                        on_click=lambda e, u=pj: open_delete_pj_dialog(u)
                                                    ),
                                                ],
                                                alignment=ft.MainAxisAlignment.CENTER,  # Centraliza horizontalmente
                                            ),
                                200, ft.alignment.top_center
                            )
                        ],
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.START
                    ),
                    bgcolor=cor_zebrado,
                    padding=0,
                    border=ft.border.only(
                        top=ft.border.BorderSide(1, COR_1),
                    )
                )
            )
    # Tabela completa
    tabela = ft.Column(
        controls=[
            # Cabeçalho fixo
            ft.Container(
                cabecalho,
                bgcolor=COR_1,
                # padding=10,
                padding=ft.padding.only(left=10, right=10, top=10, bottom=10),
                border=ft.border.only(
                    top=ft.border.BorderSide(1, COR_1),
                    left=ft.border.BorderSide(1, COR_1),
                    right=ft.border.BorderSide(1, COR_1)
                )
            ),
            # Corpo com scroll
            ft.Container(
                content=ft.ListView(
                    controls=linhas,
                    expand=True,
                    spacing=0,
                    padding=0,
                ),
                border=ft.border.only(
                    bottom=ft.border.BorderSide(1, ft.Colors.BLACK),
                    left=ft.border.BorderSide(1, ft.Colors.BLACK),
                    right=ft.border.BorderSide(1, ft.Colors.BLACK)
                ),
                expand=True
            )
        ],
        spacing=0,
        # expand=True
        width=850,
    )

    app_bar = create_appbar(
        page, api,
        titulo="App MC Sonae - Cadastro de Projetos",
        leading_control=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/menu"), tooltip="Voltar")
    )

    procura_projetos_field = ft.TextField(hint_text="Pesquisar projetos...", expand=True, value=search_term)

    return ft.View(
        route="/projetos",
        appbar=app_bar,
        controls=[
            ft.Column(
                [
                    ft.Row(
                        [
                            procura_projetos_field, 
                            ft.ElevatedButton(
                                "Pesquisar",
                                icon=ft.Icons.SEARCH,
                                style=button_style,
                                tooltip="Pesquisar projetos",
                                on_click=lambda e: search_projetos()
                            )
                        ]
                    ),
                    ft.ElevatedButton(
                        "Novo projeto",
                        icon=ft.Icons.ADD,
                        style=button_style,
                        tooltip="Criar novo projeto",
                        on_click=lambda _: page.go("/projetos/novo")
                    ),
                    ft.Divider(),
                    # ft.Row([users_table], scroll=ft.ScrollMode.ALWAYS)
                    # ft.Column(
                    #     controls=[
                    #         ft.Container(
                    #             tabela,
                    #             expand=True,
                    #             border_radius=0,
                    #         ),
                    #     ],
                    #     expand=True,
                    # )
                    ft.Row(
                        controls=[
                            tabela,
                        ],
                        expand=True,
                        scroll=ft.ScrollMode.AUTO,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                    )

                ],
                expand=True
            ),
        ],
        padding=20
    )

# Renderiza a Tela de Cadastro/ Edição de Projetos.
def view_projeto_form(page: ft.Page, api: ApiClient, projeto_id: Optional[int] = None) -> ft.View:
    is_editing = projeto_id is not None
    projeto_data = api.get_projeto_by_id(projeto_id) if is_editing else {}
    
    projeto_field = ft.TextField(label="Projeto", value=projeto_data.get("projeto", "") if is_editing else "") # type: ignore
    status_dropdown = ft.dropdown.Dropdown(
        label="Status",
        options=[
            ft.dropdown.Option("Ativo"),
            ft.dropdown.Option("Encerrado"),
        ],
        width=300,
        value=projeto_data.get("status", "") # type: ignore 
    )

    # Coleta os dados do formulário
    def on_save4_click(e):
        data = {
            "projeto": projeto_field.value,
            "status": status_dropdown.value,
        }

        if is_editing:
            # Lógica de atualização
            success, message = api.update_projeto(projeto_id, data) # type: ignore
        else:
            # Lógica de criação
            success, message = api.create_projeto(data)

        if success:
            show_snackbar(page, message, ft.Colors.GREEN)
            page.go("/projetos")
        else:
            show_snackbar(page, message, ft.Colors.RED)

    app_bar = create_appbar(
        page, api,
        titulo="App MC Sonae - Cadastro de Projetos - Novo Projeto" if not is_editing else "App MC Sonae - Cadastro de Projetos - Editar Projeto",
        leading_control=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/projetos"), tooltip="Voltar")
    )

    return ft.View(
        route=f"/projetos/editar/{projeto_id}" if is_editing else "/projetos/novo",
        appbar=app_bar,
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Editar Projeto" if is_editing else "Novo Projeto",
                            style=ft.TextThemeStyle.HEADLINE_MEDIUM
                        ),
                        projeto_field,
                        status_dropdown,
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    "Salvar",
                                    icon=ft.Icons.SAVE,
                                    style=button_style,
                                    on_click=on_save4_click
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.END
                        )
                    ],
                    spacing=15
                ),
                padding=20,
                width=600,
                alignment=ft.alignment.center
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

# def view_placeholder(page: ft.Page, api: ApiClient, title: str, route: str) -> ft.View:
#     """ Uma tela genérica para rotas ainda não implementadas. """
#     return ft.View(
#         route=route,
#         appbar=create_appbar(page, api),
#         controls=[
#             ft.Container(
#                 content=ft.Column(
#                     [
#                         ft.Text(title, style=ft.TextThemeStyle.HEADLINE_MEDIUM),
#                         ft.Text("Esta página está em construção."),
#                         ft.ElevatedButton("Voltar ao Menu", on_click=lambda _: page.go("/menu"))
#                     ],
#                     horizontal_alignment=ft.CrossAxisAlignment.CENTER,
#                     alignment=ft.MainAxisAlignment.CENTER
#                 ),
#                 expand=True
#             )
#         ]
#     )

# Renderiza a Tela de Anexar Arquivos ao Repositório.
def view_repositorio_form(page: ft.Page, api: ApiClient) -> ft.View:
    extensao_validas = ["pdf", "docx", "xlsx"]
    projetos = api.get_projetos()
    projetos_options = []
    if projetos is not None:
        for projeto in projetos:
            if projeto.get("status") == "Ativo": # type: ignore
                projetos_options.append(ft.dropdown.Option(key=projeto.get("projetoid"), text=projeto.get("projeto")))

    projeto_dropdown = ft.dropdown.Dropdown(
        label="Projeto",
        options=projetos_options,
        width=500,
    )

    progresso = ft.ProgressRing(value=0, width=20, height=20, color=COR_1, visible=False)
    progresso_status = ft.Text("", color=COR_1, weight=ft.FontWeight.BOLD)
    progresso_ok = ft.Icon(name=ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN_400, size=30, visible=False)
    indicador = ft.ProgressRing(width=60, height=60, color=COR_1, visible=False)
    extensao=""
    upload_url = ""

    def pick_files_result(e: ft.FilePickerResultEvent):
        nonlocal extensao
        nonlocal upload_url
        progresso_status.value = ""
        progresso.value = 0
        progresso.visible = True
        progresso_ok.visible = False
        progresso.update()  
        progresso_status.update()
        progresso_ok.update()
        extensao = e.files[0].name.split(".")[-1].lower() if e.files else ""
        selected_files.value = (
            e.files[0].name if e.files else "Cancelado!"
        )
        selected_files.update()
        # Criar lista de arquivos para upload com uma URL de destino
        if e.files:
            arquivo_upload = e.files[0]
            upload_url = page.get_upload_url(arquivo_upload.name, 600)
            upload_file = ft.FilePickerUploadFile(
                    arquivo_upload.name,
                    upload_url=upload_url
                ) 
            pick_files_dialog.upload([upload_file])  # Envia apenas um
    
    def on_upload(e: ft.FilePickerUploadEvent):
        if e.progress is not None:
            progresso.value = e.progress
            progresso_status.value = f"[{e.progress * 100:.0f}%]"
            if e.progress == 1.0:
                progresso_status.value = "[Upload finalizado]"
                progresso.visible = False
                progresso_ok.visible = True
                progresso_status.visible = False
        progresso_ok.update()
        progresso_status.update()
        progresso.update()

    pick_files_dialog = ft.FilePicker(on_result=pick_files_result, on_upload=on_upload)
    selected_files = ft.Text()
    
    page.overlay.append(pick_files_dialog)

    bt_arquivo = ft.Row(
            [
                ft.ElevatedButton(
                    "Selecionar Arquivo",
                    icon=ft.Icons.UPLOAD_FILE,
                    color=ft.Colors.WHITE,
                    style=button_style,
                    on_click=lambda _: pick_files_dialog.pick_files(
                        allow_multiple=False, allowed_extensions=extensao_validas
                    ),
                ),
                selected_files,
            ]
        )

    # Coleta os dados do formulário
    def on_anexar_click(e):

        if not selected_files.value or selected_files.value == "Cancelado!":
            show_snackbar(page, "Nenhum arquivo foi selecionado ou o upload foi cancelado.", ft.Colors.RED)
            return
        if extensao not in extensao_validas:
            show_snackbar(page, "Extensão do arquivo inválida.", ft.Colors.RED)
            return 
        if projeto_dropdown.value is None:
            show_snackbar(page, "Projeto inválido.", ft.Colors.RED)
            return 

        indicador.visible = True
        indicador.update()

        try:
            diretorio_base = os.path.dirname(os.path.abspath(__file__))
            caminho_do_arquivo_local = os.path.join(diretorio_base, "uploads", selected_files.value)

            converter = DocumentConverter()
            result = converter.convert(source=caminho_do_arquivo_local)

            docling_txt = result.document.export_to_markdown()
        except Exception as ex:
            show_snackbar(page, f"Erro ao processar o arquivo: {ex}", ft.Colors.RED)
            indicador.visible = False
            indicador.update()
            return

        # print(docling_txt)

        # docling_txt = ""
        # Gera a data e hora atual no formato ISO 8601 UTC
        data_hora_utc = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')

        data = {
            "markdown": docling_txt,
            "tipoarquivo": extensao,
            "projetoid": projeto_dropdown.value,
            "usuarioid": 0,
            "datahora": data_hora_utc,
        }

        success, message = api.create_repositorio(data) # type: ignore

        if success:
            show_snackbar(page, message, ft.Colors.GREEN)
            page.go("/menu")
        else:
            show_snackbar(page, message, ft.Colors.RED)

    app_bar = create_appbar(
        page, api,
        titulo="App MC Sonae - Anexar Arquivo no Repositório do Projeto", 
        leading_control=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/menu"), tooltip="Voltar")
    )

    bt_anexar = ft.ElevatedButton("Anexar Arquivo", style=button_style, on_click=on_anexar_click, icon=ft.Icons.ATTACH_FILE)

    return ft.View(
        route=f"/repositorio",
        appbar=app_bar,
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Anexar Arquivo no Repositório do Projeto", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                        projeto_dropdown,
                        ft.Row(
                            [
                                bt_arquivo,
                                progresso,
                                progresso_status,
                                progresso_ok,
                            ],
                            alignment=ft.MainAxisAlignment.START
                        ),
                        ft.Row(
                            [
                                bt_anexar,
                            ],
                            alignment=ft.MainAxisAlignment.END
                        ),
                        ft.Row(
                            [
                                indicador,
                            ],
                            alignment=ft.MainAxisAlignment.CENTER
                        )
                    ],
                    spacing=15
                ),
                padding=20,
                width=800,
                alignment=ft.alignment.center
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

# Renderiza a Tela de Consulta Projeto.
def view_consulta_projeto_form(page: ft.Page, api: ApiClient) -> ft.View:
    projetos = api.get_projetos()

    projetos_options = []
    if projetos is not None:
        for projeto in projetos:
            if projeto.get("status") == "Ativo": # type: ignore
                projetos_options.append(ft.dropdown.Option(key=projeto.get("projetoid"), text=projeto.get("projeto")))

    projeto_dropdown = ft.dropdown.Dropdown(
        label="Projeto",
        options=projetos_options,
        width=500,
    )

    indicador = ft.ProgressRing(width=60, height=60, color=COR_1, visible=False)
    tf_prompt = ft.TextField(label="Prompt Usuário", multiline=True, expand=True, max_lines=5)
    link_control = ft.Markdown("", on_tap_link=lambda e: page.launch_url(e.data, web_window_name="blank")) # type: ignore

    def criar_pu_celula(conteudo, largura=None, alinhamento=ft.alignment.center_left):
        return ft.Container(
            content=conteudo,
            width=largura,
            padding=10,
            alignment=alinhamento,
        )

    cabecalho = ft.Row(
        controls=[
            criar_pu_celula(ft.Text("Data Hora", weight=ft.FontWeight.BOLD, color=COR_5), 200, ft.alignment.top_center),
            criar_pu_celula(ft.Text("Prompt Usuário", weight=ft.FontWeight.BOLD, color=COR_5), 350, ft.alignment.top_center),
            criar_pu_celula(ft.Text("", weight=ft.FontWeight.BOLD, color=COR_5), 50, ft.alignment.top_center),
        ],
        spacing=0,
        vertical_alignment=ft.CrossAxisAlignment.START
    )

    def muda_prompt_usuario(pu_item):
        tf_prompt.value = pu_item.get("prompt")
        tf_prompt.update()
        close_prompt_usuario_dialog(prompt_usuario_view_dialog)
 
    tabela = None

    def popula_prompt_usuario(e):
        nonlocal tabela
        pu_data = api.get_prompt_usuario(limit=10) # type: ignore

        # Corpo da tabela com scroll
        linhas = []
        zebrado = False
        if pu_data:
            for pu in pu_data:
                if zebrado:
                    cor_zebrado = COR_3
                else:
                    cor_zebrado = ft.Colors.WHITE
                zebrado = not zebrado
                datahora = pu.get("datahora") # type: ignore
                datahora = str(datahora)
                if datahora.endswith('Z'):
                    datahora = datahora[:-1] + '+00:00'
                # 1. Converte a string ISO para um objeto datetime (que estará em UTC)
                objeto_datetime = datetime.fromisoformat(datahora)
                # 2. Converte o objeto datetime de UTC para o fuso horário de Recife (America/Recife, UTC-3)
                datahora_recife = objeto_datetime.astimezone(ZoneInfo("America/Recife"))
                datahora_br = datahora_recife.strftime('%d/%m/%Y %H:%M:%S')

                linhas.append(
                    ft.Container(
                        ft.Row(
                            controls=[
                                criar_pu_celula(
                                    ft.Text(
                                        datahora_br,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        selectable=True,
                                    ), 
                                    200
                                ),
                                criar_pu_celula(
                                    ft.Text(
                                        pu.get('prompt'),
                                        max_lines=2,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                        tooltip=pu.get('prompt'),
                                        selectable=True,
                                    ), 
                                    350
                                ),
                                criar_pu_celula(
                                                ft.Row(
                                                    controls=[
                                                        ft.IconButton(
                                                            ft.Icons.BADGE,
                                                            icon_color=ft.Colors.BLACK,
                                                            tooltip="Muda Prompt Visualiza Repositório",
                                                            on_click=lambda e, u=pu: muda_prompt_usuario(u)
                                                        )
                                                    ],
                                                    alignment=ft.MainAxisAlignment.CENTER,  # Centraliza horizontalmente
                                                ),
                                    150, ft.alignment.top_center
                                )
                            ],
                            spacing=0,
                            vertical_alignment=ft.CrossAxisAlignment.START
                        ),
                        bgcolor=cor_zebrado,
                        padding=0,
                        border=ft.border.only(
                            top=ft.border.BorderSide(1, COR_1),
                        )
                    )
                )

        # Tabela completa
        tabela = ft.Column(
            controls=[
                # Cabeçalho fixo
                ft.Container(
                    cabecalho,
                    bgcolor=COR_1,
                    # padding=10,
                    padding=ft.padding.only(left=10, right=10, top=10, bottom=10),
                    border=ft.border.only(
                        top=ft.border.BorderSide(1, COR_1),
                        left=ft.border.BorderSide(1, COR_1),
                        right=ft.border.BorderSide(1, COR_1)
                    )
                ),
                # Corpo com scroll
                ft.Container(
                    content=ft.ListView(
                        controls=linhas,
                        expand=True,
                        spacing=0,
                        padding=0,
                    ),
                    border=ft.border.only(
                        bottom=ft.border.BorderSide(1, ft.Colors.BLACK),
                        left=ft.border.BorderSide(1, ft.Colors.BLACK),
                        right=ft.border.BorderSide(1, ft.Colors.BLACK)
                    ),
                    expand=True
                )
            ],
            spacing=0,
            # expand=True
            width=600,
        )

        prompt_usuario_view_dialog.content.content = tabela # type: ignore

        open_prompt_usuario_dialog()

    prompt_usuario_view_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Prompt do Usuário"),
        content=ft.Container(
            content=tabela,
            width=800,
            height=600,
        ),
        actions=[ft.TextButton("Fechar", style=button_style, on_click=lambda _: close_prompt_usuario_dialog(prompt_usuario_view_dialog))],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.overlay.append(prompt_usuario_view_dialog)

    def open_prompt_usuario_dialog():
        prompt_usuario_view_dialog.content.update() # type: ignore
        prompt_usuario_view_dialog.open = True
        prompt_usuario_view_dialog.update() # Atualiza apenas o diálogo (para abrir)

    def close_prompt_usuario_dialog(dialog: ft.AlertDialog):
        dialog.open = False
        dialog.update()

    def on_consultar_click(e):
        link_control.value = ""
        link_control.update()

        # Testes
        # file_name = SERVIDOR_WEB+"resultado_gemini.html" # type: ignore
        # # file_name = "resultado_gemini.html"
        # # file_name = "https://www.google.com"
        # # file_url = f"/assets/{file_name}"
        # file_url = file_name
        # link_control.value = f"[Clique aqui para ver o resultado]({file_url})"
        # link_control.update()

        if projeto_dropdown.value is None:
            show_snackbar(page, "Projeto inválido.", ft.Colors.RED)
            return 
        indicador.visible = True
        indicador.update()
        try:
            promptgeral = api.get_prompt_geral(prompt_id=1)
            if promptgeral is None:
                show_snackbar(page, "Prompt Geral inválido.", ft.Colors.RED)
                return 
            
            projeto_id_selecionado = projeto_dropdown.value
            projeto_texto_selecionado = "Nome do Projeto não encontrado"
            for opt in projetos_options:
                if opt.key == int(projeto_id_selecionado):
                    projeto_texto_selecionado = opt.text
                    break

            repositorio = api.get_repositorios(search_term=projeto_id_selecionado) # type: ignore
            if repositorio is None:
                show_snackbar(page, "Não existem repositórios para este projeto.", ft.Colors.RED)
                return 
            comando = f"# Projeto: {projeto_id_selecionado, projeto_texto_selecionado}\n"
            comando += "# Prompt Geral: \n"
            comando += promptgeral.get("prompt") + "\n" # type: ignore
            if tf_prompt.value:
                comando += "# Prompt Usuário: \n"
                comando += tf_prompt.value + "\n"
            comando += "# Repositórios: \n"
            for repo in repositorio:
                comando += repo.get("markdown") + "\n"

            print(f"Prompt: {len(comando.encode('utf-8'))} bytes")

            if tf_prompt.value:
               data_hora_utc = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
               data = {
                    "prompt": tf_prompt.value,
                    "usuarioid": 0,
                    "datahora": data_hora_utc,
               }
               success, message = api.create_prompt_usuario(data) # type: ignore

            print("Início Consulta a API Gemini")

            client = genai.Client(api_key=CHAVE_API_GEMINI)

            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=comando
            )

            # print(response.text)

            if response.text:
                print(f"Resposta IA: {len(response.text.encode('utf-8'))} bytes")
                # resultado_html = response.text
                resultado_html = response.text.replace("```html", "").replace("```", "").strip()

                diretorio_base = os.path.dirname(os.path.abspath(__file__))
                file_name = "resultado_gemini.html"
                static_file_path = os.path.join(diretorio_base, "assets", file_name)
                
                print(static_file_path)

                with open(static_file_path, "w", encoding="utf-8") as f:
                    f.write(resultado_html)

                file_url = f"{SERVIDOR_WEB}{file_name}"

                link_control.value = f"[Clique aqui para ver o resultado]({file_url})"
                link_control.update()

                # b64_html = base64.b64encode(resultado_html.replace("```html", "").replace("```", "").strip().encode('utf-8')).decode('utf-8')
                # data_uri = f"data:text/html;base64,{b64_html}"

                # page.launch_url(data_uri)
                # page.update()

                # html_encoded = urllib.parse.quote(resultado_html.'replace("```html", "").replace("```", "").strip'())
                # link_control.value = f"[Clique aqui para ver o resultado](data:text/html,{b64_html})"
                # link_control.value = f"[Clique aqui para ver o resultado]({data_uri})"
                # link_control.update()
            else:
                show_snackbar(page, "Erro ao consultar o processo.", ft.Colors.RED)
                return

            print("Fim Consulta a API Gemini")

            indicador.visible = False
            indicador.update()

        except Exception as ex:
            indicador.visible = False
            indicador.update()
            print(f"Erro ao consultar o processo: {ex}")
            show_snackbar(page, f"Erro ao consultar o processo: {ex}", ft.Colors.RED)
            indicador.visible = False
            indicador.update()
            return

    app_bar = create_appbar(
        page, api,
        titulo="App MC Sonae - Consultar Projeto", 
        leading_control=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/menu"), tooltip="Voltar")
    )

    bt_consultar = ft.ElevatedButton("Consultar Projeto", style=button_style, on_click=on_consultar_click, icon=ft.Icons.SCREEN_SEARCH_DESKTOP)
    bt_promptusuario = ft.ElevatedButton("...", tooltip="Escolher Prompt Usuário", style=button_style, on_click=popula_prompt_usuario)

    return ft.View(
        route=f"/consultar",
        appbar=app_bar,
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Anexar Consultar Projeto", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                        projeto_dropdown,
                        ft.Row(
                            [
                                tf_prompt,
                                bt_promptusuario,
                            ],
                            alignment=ft.MainAxisAlignment.END
                        ),
                        ft.Row(
                            [
                                bt_consultar,
                            ],
                            alignment=ft.MainAxisAlignment.END
                        ),
                        ft.Row(
                            [
                                indicador,
                            ],
                            alignment=ft.MainAxisAlignment.CENTER
                        ),
                        ft.Row(
                            [
                                link_control,
                            ],
                            alignment=ft.MainAxisAlignment.CENTER
                        ),
                    ],
                    spacing=15
                ),
                padding=20,
                width=800,
                alignment=ft.alignment.center
            )
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

##################################################
# Roteador Principal
##################################################

def main(page: ft.Page):
    page.title = "App MC Sonae"

    page.theme_mode = ft.ThemeMode.LIGHT

    # Adiciona o SnackBar à página. Ele será reutilizado em toda a aplicação.
    page.snack_bar = ft.SnackBar(content=ft.Text(""), bgcolor=ft.Colors.GREEN) # type: ignore
    page.overlay.append(page.snack_bar) # type: ignore


    api = ApiClient(page)

    # Define o estilo global dos botões
    global button_style

    button_style = ft.ButtonStyle(
        color={
            ft.ControlState.DEFAULT: ft.Colors.WHITE,
            ft.ControlState.DISABLED: ft.Colors.with_opacity(0.38, ft.Colors.BLACK),
            ft.ControlState.HOVERED: ft.Colors.WHITE,
            ft.ControlState.PRESSED: ft.Colors.WHITE,
        },
        icon_color={
            ft.ControlState.DEFAULT: ft.Colors.WHITE,
            ft.ControlState.DISABLED: ft.Colors.with_opacity(0.38, ft.Colors.BLACK),
            ft.ControlState.HOVERED: ft.Colors.WHITE,
            ft.ControlState.PRESSED: ft.Colors.WHITE,
        },
        bgcolor={
            ft.ControlState.DEFAULT: COR_1,
            ft.ControlState.DISABLED: ft.Colors.with_opacity(0.12, COR_1),
            ft.ControlState.HOVERED: ft.Colors.with_opacity(0.8, COR_1),
            ft.ControlState.PRESSED: ft.Colors.with_opacity(0.5, COR_1),
        },
        overlay_color=ft.Colors.with_opacity(0.12, ft.Colors.WHITE),
        side={
            ft.ControlState.DEFAULT: ft.BorderSide(1, ft.Colors.BLACK),
            ft.ControlState.DISABLED: ft.BorderSide(1, ft.Colors.with_opacity(0.38, ft.Colors.BLACK)),
            ft.ControlState.HOVERED: ft.BorderSide(2, ft.Colors.BLACK),
            ft.ControlState.PRESSED: ft.BorderSide(5, ft.Colors.BLACK),
        },
        elevation={
            ft.ControlState.DEFAULT: 0,
            ft.ControlState.HOVERED: 0,
            ft.ControlState.PRESSED: 0,
        },
        shape=ft.StadiumBorder(),
        padding=ft.padding.symmetric(horizontal=16, vertical=8),
        animation_duration=200,
    )

    def route_change(route):
        token = api.get_token()
        if not token and page.route != "/login":
            page.go("/login")
            return

        # Separa a rota principal da query string para evitar erros de parsing
        path = page.route.split("?")[0]

        # Constrói a pilha de views com base na rota
        troute = ft.TemplateRoute(path)
        page.views.clear()

        # --- Roteamento ---
        if troute.match("/login"):
            page.views.append(view_login(page, api))
        elif token:
            page.views.append(view_menu(page, api))
            if troute.match("/usuarios/novo"):
                # page.views.append(view_usuarios_list(page, api))
                page.views.append(view_usuario_form(page, api))
            elif troute.match("/usuarios/editar/:id"):
                user_id = int(troute.id) # type: ignore
                page.views.append(view_usuario_form(page, api, user_id=user_id))
            elif troute.match("/usuarios"): # Genérico, mas sem ID
                page.views.append(view_usuarios_list(page, api))
            elif troute.match("/usuarios/:id"): # Genérico com ID, deve vir depois de /usuarios
                user_id = int(troute.id) # type: ignore
                page.views.append(view_usuarios_list(page, api))
                page.views.append(view_usuario_detail(page, api, user_id=user_id))
            elif troute.match("/mudar/senha/:id"):
                user_id = int(troute.id) # type: ignore
                page.views.append(view_mudar_senha_usuario_form(page, api, user_id=user_id))
            if troute.match("/projetos/novo"):
                page.views.append(view_projeto_form(page, api))
            elif troute.match("/projetos/editar/:id"):
                projeto_id = int(troute.id) # type: ignore
                page.views.append(view_projeto_form(page, api, projeto_id=projeto_id))
            elif troute.match("/projetos"): # Genérico, mas sem ID
                page.views.append(view_projetos_list(page, api))
            elif troute.match("/projetos/:id"): # Genérico com ID, deve vir depois de /usuarios
                projeto_id = int(troute.id) # type: ignore
                page.views.append(view_projetos_list(page, api))
                page.views.append(view_projeto_detail(page, api, projeto_id=projeto_id))
            elif troute.match("/repositorio"):
                page.views.append(view_repositorio_form(page, api))
            elif troute.match("/consultar"):
                # page.views.append(view_placeholder(page, api, "Consultar Projeto", "/consultar"))
                page.views.append(view_consulta_projeto_form(page, api))
            elif troute.match("/promptgeral"):
                page.views.append(view_promtgeral_form(page, api, prompt_id=1))

            # Adicione outras rotas aqui...

        else:
            # Se logado e rota desconhecida, vai para o menu
            if token:
                page.go("/menu")
            # Se não logado, vai para o login
            else:
                 page.go("/login")

        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route) # type: ignore

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    
    # Inicia a aplicação. Verifica se já existe um token.
    if api.get_token():
        page.go("/menu")
    else:
        page.go("/login")

# Executar a Aplicação
if __name__ == "__main__":
    ft.app(
        target=main, 
        view=ft.AppView.WEB_BROWSER,
        port=8550,
        upload_dir="uploads",
        assets_dir="assets"
    )