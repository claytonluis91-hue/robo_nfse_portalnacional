import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import time
import os

# --- CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira coisa) ---
st.set_page_config(page_title="Robô XML NFS-e", page_icon="🤖")

# --- FUNÇÃO PARA CONFIGURAR O NAVEGADOR NA NUVEM ---
def get_driver():
    chrome_options = Options()
    
    # As flags abaixo são OBRIGATÓRIAS para rodar no Streamlit Cloud
    chrome_options.add_argument("--headless")  # Roda sem interface gráfica (invisível)
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Instala o driver compatível com o Chromium (Linux do servidor)
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# --- LÓGICA DO ROBÔ ---
def iniciar_robo(cnpj_digitado, usuario_digitado, senha_digitada):
    driver = None
    status_placeholder = st.empty() # Cria um espaço vazio para mensagens
    
    try:
        status_placeholder.info("Iniciando o navegador na nuvem... Aguarde.")
        driver = get_driver()
        
        status_placeholder.info("Acessando o Portal Nacional...")
        driver.get("https://www.nfse.gov.br/EmissorNacional/Login")
        
        # Espera um pouco para garantir que carregou
        time.sleep(5)
        
        # Tira um print para provar que acessou
        st.image(driver.get_screenshot_as_png(), caption="Tela Atual do Robô", use_column_width=True)
        st.success("O site abriu! Se você vê a imagem acima, o Selenium funcionou.")

        # --- AQUI ENTRARIA O PREENCHIMENTO DOS DADOS ---
        # (Por enquanto vamos parar aqui para garantir que o site abre)

    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")
    finally:
        if driver:
            driver.quit()

# --- TELA DO SISTEMA (INTERFACE) ---
st.title("🤖 Automação NFS-e Nacional")
st.markdown("Sistema de Extração Automática de XMLs")

# Criação dos campos (Isso corrige o NameError)
cnpj = st.text_input("CNPJ do Cliente")
usuario = st.text_input("Usuário/CPF")
senha = st.text_input("Senha do Portal", type="password")

# Botão para iniciar
if st.button("Iniciar"):
    if not cnpj or not senha:
        st.warning("Preencha todos os campos antes de iniciar.")
    else:
        iniciar_robo(cnpj, usuario, senha)
