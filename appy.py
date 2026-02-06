import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import time

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Robô XML NFS-e", page_icon="🤖", layout="centered")

# --- 2. FUNÇÃO PARA LIGAR O NAVEGADOR (MOTOR) ---
def get_driver():
    chrome_options = Options()
    # Configurações obrigatórias para rodar na nuvem do Streamlit
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# --- 3. A LÓGICA DO ROBÔ ---
def executar_robo(cnpj_digitado, usuario_digitado, senha_digitada):
    driver = None
    place_msg = st.empty() # Lugar para mensagens de status
    
    try:
        place_msg.info("⏳ Iniciando o navegador... aguarde.")
        driver = get_driver()
        
        # Acessa o site
        place_msg.info("🌍 Acessando o Portal Nacional...")
        driver.get("https://www.nfse.gov.br/EmissorNacional/Login")
        time.sleep(5) # Espera carregar
        
        # Mostra a primeira foto (Antes de preencher)
        st.write("### 📸 Passo 1: Acesso ao Portal")
        st.image(driver.get_screenshot_as_png(), caption="Tela de Login Carregada", use_column_width=True)
        
        # --- TENTATIVA DE LOGIN ---
        place_msg.info("✍️ Preenchendo dados de acesso...")
        
        # Tenta achar e preencher CNPJ/CPF
        try:
            # Tenta pelo ID "Inscricao" (comum) ou "CPFCNPJ"
            campo_user = driver.find_element(By.ID, "Inscricao") 
            campo_user.clear()
            campo_user.send_keys(cnpj_digitado)
        except:
            st.warning("⚠️ Não encontrei o campo de CNPJ com ID 'Inscricao'. Tentando genérico...")

        # Tenta achar e preencher SENHA
        try:
            campo_senha = driver.find_element(By.ID, "Senha")
            campo_senha.clear()
            campo_senha.send_keys(senha_digitada)
        except:
            st.warning("⚠️ Não encontrei o campo de Senha.")

        # Tenta clicar no botão ENTRAR
        place_msg.info("🖱️ Clicando em Entrar...")
        try:
            # Procura o botão de login (usando seletor CSS para pegar o botão da área de login)
            # Geralmente é um button com type="submit"
            botao = driver.find_element(By.XPATH, "//button[contains(text(), 'Entrar')]")
            botao.click()
        except:
            st.error("❌ Não consegui clicar no botão 'Entrar'.")

        # Espera o site processar o login
        time.sleep(5)
        
        # Mostra a segunda foto (Depois de tentar entrar)
        st.write("### 📸 Passo 2: Resultado do Login")
        st.image(driver.get_screenshot_as_png(), caption="Tela após clicar em Entrar", use_column_width=True)
        
        place_msg.success("✅ Processo de tentativa de login finalizado!")

    except Exception as e:
        st.error(f"❌ Erro crítico no robô: {e}")
    finally:
        if driver:
            driver.quit()

# --- 4. A TELA DO USUÁRIO (O que você vê) ---
st.title("🤖 Robô NFS-e Nacional")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    cnpj_input = st.text_input("CNPJ / CPF")
    usuario_input = st.text_input("Usuário (Opcional)")
with col2:
    senha_input = st.text_input("Senha", type="password")

if st.button("🚀 Iniciar Robô", type="primary"):
    if not cnpj_input or not senha_input:
        st.warning("Preencha CNPJ e Senha antes de começar!")
    else:
        executar_robo(cnpj_input, usuario_input, senha_input)
