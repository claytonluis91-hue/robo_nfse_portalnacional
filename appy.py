import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import os

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Robô XML NFS-e", page_icon="🤖")
st.title("🤖 Automação de Downloads - NFS-e Nacional")
st.markdown("Informe os dados abaixo para iniciar a raspagem dos XMLs.")

# --- INTERFACE NO STREAMLIT ---
with st.sidebar:
    st.header("Configurações de Acesso")
    cnpj = st.text_input("CNPJ do Cliente")
    usuario = st.text_input("Usuário/CPF")
    senha = st.text_input("Senha do Portal", type="password")
    
    # Pasta onde os XMLs serão salvos localmente
    pasta_destino = st.text_input("Caminho da Pasta (Ex: C:/Notas)", value=os.getcwd() + "/downloads")

# --- LÓGICA DO ROBÔ ---
def iniciar_robo(cnpj, user, pwd, pasta):
    # Configurações do Navegador
    chrome_options = Options()
    # chrome_options.add_argument("--headless") # Descomente para rodar sem abrir a janela
    
    # Configura de download automático para a pasta escolhida
    prefs = {"download.default_directory": pasta.replace("/", "\\")}
    chrome_options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        st.info("Acessando o Portal Nacional...")
        driver.get("https://www.nfse.gov.br/EmissorNacional/Login")

        # 1. Preenchimento do Login (Exemplo de seletores genéricos, precisam ser validados no site)
        # Nota: Os IDs abaixo são ilustrativos, precisam ser confirmados inspecionando o portal
        wait.until(EC.presence_of_element_located((By.ID, "Inscricao"))).send_keys(cnpj)
        driver.find_element(By.ID, "Usuario").send_keys(user)
        driver.find_element(By.ID, "Senha").send_keys(pwd)
        
        st.warning("Por favor, resolva o Captcha no navegador (se houver) e clique em Entrar.")
        
        # O robô aguarda você logar e a página de Dashboard aparecer
        wait.until(EC.url_contains("Home")) 
        st.success("Login realizado com sucesso!")

        # 2. Navegação para Notas Recebidas
        # Aqui entrará a lógica de clicar nos menus e disparar os downloads
        st.info("Aguardando comandos de navegação para download...")
        
        # Exemplo: Localizar botões de download e clicar
        # botoes_download = driver.find_elements(By.CLASS_NAME, "btn-download")
        # for btn in botoes_download:
        #     btn.click()
        #     time.sleep(1)

    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")
    finally:
        st.info("Processo finalizado. Feche o navegador quando desejar.")
        # driver.quit()

# --- BOTÃO DE EXECUÇÃO ---
if st.button("Iniciar Download em Lote"):
    if not cnpj or not senha:
        st.error("Por favor, preencha o CNPJ e a Senha.")
    else:
        if not os.path.exists(pasta_destino):
            os.makedirs(pasta_destino)
        iniciar_robo(cnpj, usuario, senha, pasta_destino)
