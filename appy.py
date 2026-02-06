import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import time
import os
import shutil

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Robô XML NFS-e", page_icon="🤖")

# Pasta temporária no servidor para salvar os XMLs
DOWNLOAD_DIR = "/tmp/xml_downloads"

# --- FUNÇÃO PARA LIMPAR A PASTA ANTES DE COMEÇAR ---
def limpar_pasta():
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR)

# --- CONFIGURAÇÃO DO DRIVER COM PASTA DE DOWNLOAD ---
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Configura o Chrome para salvar arquivos automaticamente na nossa pasta
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# --- LÓGICA PRINCIPAL ---
def executar_robo(cnpj, senha, tipo_nota):
    driver = None
    msg = st.empty()
    limpar_pasta() # Limpa downloads antigos
    
    try:
        # 1. LOGIN
        msg.info("🚀 Acessando portal...")
        driver = get_driver()
        driver.get("https://www.nfse.gov.br/EmissorNacional/Login")
        
        wait = WebDriverWait(driver, 15)
        
        # Preenche Login
        wait.until(EC.presence_of_element_located((By.ID, "Inscricao"))).send_keys(cnpj)
        driver.find_element(By.ID, "Senha").send_keys(senha)
        
        # Clica em Entrar
        try:
            driver.find_element(By.XPATH, "//button[contains(text(), 'Entrar')]").click()
        except:
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            
        time.sleep(5)
        
        # Verifica sucesso do login
        if "Login" in driver.title:
            st.error("❌ Login falhou. Verifique a senha.")
            st.image(driver.get_screenshot_as_png(), caption="Tela de Erro", use_column_width=True)
            return

        # 2. NAVEGAÇÃO
        # O print mostra titles: "NFS-e Emitidas" ou vamos assumir "NFS-e Recebidas"
        titulo_menu = "NFS-e Recebidas" if tipo_nota == "Notas Recebidas" else "NFS-e Emitidas"
        msg.info(f"🔎 Buscando menu: {titulo_menu}...")
        
        try:
            # Busca pelo título do ícone (conforme seu print)
            menu_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"a[title='{titulo_menu}']")))
            menu_link.click()
        except:
            st.warning("Não achei pelo título, tentando ícone genérico...")
            driver.get("https://www.nfse.gov.br/EmissorNacional/Nfse/Recebidas" if tipo_nota == "Notas Recebidas" else "https://www.nfse.gov.br/EmissorNacional/Nfse/Emitidas")

        time.sleep(5)
        st.image(driver.get_screenshot_as_png(), caption="Lista de Notas", use_column_width=True)

        # 3. EXTRAÇÃO (LOOP NA TABELA)
        msg.info("🔄 Identificando notas na tabela...")
        
        # Encontrar todas as linhas da tabela
        linhas = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        qtd = len(linhas)
        
        if qtd == 0:
            st.warning("⚠️ Nenhuma nota encontrada neste período (Padrão: 30 dias).")
        else:
            st.success(f"Encontrei {qtd} notas! Iniciando download...")
            bar = st.progress(0)
            
            for i, linha in enumerate(linhas):
                try:
                    # Passo A: Clicar nos "3 pontinhos" (última coluna da linha)
                    # Geralmente é um botão dentro do último TD
                    botao_menu = linha.find_element(By.CSS_SELECTOR, "td:last-child div[role='button'], td:last-child button, td:last-child a")
                    # Scroll para garantir que o botão está visível
                    driver.execute_script("arguments[0].scrollIntoView();", botao_menu)
                    time.sleep(0.5)
                    botao_menu.click()
                    time.sleep(1) # Espera o menu abrir
                    
                    # Passo B: Clicar em "Download XML" no menu que abriu
                    # Usamos XPATH para achar o texto exato "Download XML"
                    link_xml = driver.find_element(By.XPATH, "//a[contains(text(), 'Download XML')]")
                    link_xml.click()
                    
                    # Espera o download começar
                    time.sleep(2)
                    
                    # Fecha o menu clicando fora (opcional, mas evita erros)
                    webdriver.ActionChains(driver).move_by_offset(0, 0).click().perform()
                    
                except Exception as e:
                    print(f"Erro na nota {i+1}: {e}")
                
                bar.progress((i + 1) / qtd)

            time.sleep(5) # Garante que o último download terminou
            
            # 4. PACOTE FINAL (ZIP)
            msg.info("📦 Compactando arquivos...")
            arquivos = os.listdir(DOWNLOAD_DIR)
            if len(arquivos) > 0:
                # Cria o zip
                shutil.make_archive("/tmp/notas_fiscais", 'zip', DOWNLOAD_DIR)
                
                with open("/tmp/notas_fiscais.zip", "rb") as f:
                    st.download_button(
                        label="📥 BAIXAR TODAS AS NOTAS (ZIP)",
                        data=f,
                        file_name="notas_xml.zip",
                        mime="application/zip"
                    )
                st.balloons()
            else:
                st.error("Nenhum arquivo foi baixado. O layout do site pode ter mudado.")

    except Exception as e:
        st.error(f"Erro Crítico: {e}")
    finally:
        if driver:
            driver.quit()

# --- INTERFACE ---
st.title("🤖 Robô NFS-e Nacional")
st.info("O robô baixará as notas dos últimos 30 dias (padrão do portal).")

col1, col2 = st.columns(2)
with col1:
    cnpj_input = st.text_input("CNPJ / CPF")
    senha_input = st.text_input("Senha", type="password")
with col2:
    tipo = st.selectbox("Tipo de Nota", ["Notas Recebidas", "Notas Emitidas"])

if st.button("🚀 Iniciar Robô"):
    if not cnpj_input or not senha_input:
        st.warning("Preencha CNPJ e Senha.")
    else:
        executar_robo(cnpj_input, senha_input, tipo)
