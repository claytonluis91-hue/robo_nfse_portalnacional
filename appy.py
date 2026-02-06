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
from datetime import date

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Robô XML NFS-e", page_icon="🤖")
DOWNLOAD_DIR = "/tmp/xml_downloads"

def limpar_pasta():
    if os.path.exists(DOWNLOAD_DIR):
        shutil.rmtree(DOWNLOAD_DIR)
    os.makedirs(DOWNLOAD_DIR)

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
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

def executar_robo(cnpj, senha, tipo_nota, data_inicio, data_fim):
    driver = None
    msg = st.empty()
    limpar_pasta()
    
    try:
        # 1. LOGIN
        msg.info("🚀 Acessando portal...")
        driver = get_driver()
        driver.get("https://www.nfse.gov.br/EmissorNacional/Login")
        wait = WebDriverWait(driver, 20)
        
        wait.until(EC.presence_of_element_located((By.ID, "Inscricao"))).send_keys(cnpj)
        driver.find_element(By.ID, "Senha").send_keys(senha)
        
        try:
            driver.find_element(By.XPATH, "//button[contains(text(), 'Entrar')]").click()
        except:
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            
        time.sleep(5)
        
        if "Login" in driver.title or len(driver.find_elements(By.ID, "Inscricao")) > 0:
            st.error("❌ Login falhou. Verifique a senha.")
            st.image(driver.get_screenshot_as_png(), caption="Erro Login", use_column_width=True)
            return

        msg.success("✅ Login OK! Buscando menu de notas...")

        # 2. NAVEGAÇÃO (AQUI ESTAVA O ERRO)
        # Vamos buscar pelo LINK (href) que contém a palavra chave, é mais seguro que o título.
        termo_url = "Emitidas" if tipo_nota == "Notas Emitidas" else "Recebidas"
        
        try:
            # CSS Selector: procura qualquer <a> cujo href contenha a palavra (Ex: /Nfse/Emitidas)
            seletor_link = f"a[href*='{termo_url}']"
            
            # Tenta achar o botão
            botao_menu = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_link)))
            
            # Clica nele
            botao_menu.click()
            msg.info(f"Clicado no menu {termo_url} com sucesso!")
            
        except Exception as e:
            st.warning(f"⚠️ Clique normal falhou. Tentando modo forçado... Erro: {e}")
            # Tenta forçar o clique via JavaScript se o Selenium não conseguir
            try:
                driver.execute_script(f"document.querySelector(\"a[href*='{termo_url}']\").click()")
            except:
                st.error("❌ Realmente não consegui clicar no menu. O site mudou a estrutura dos links.")
                st.image(driver.get_screenshot_as_png(), caption="Falha no Menu", use_column_width=True)
                return

        time.sleep(5) 

        # 3. FILTRO DE DATA
        msg.info(f"📅 Filtrando de {data_inicio} até {data_fim}...")
        try:
            driver.find_element(By.ID, "DataInicial").clear()
            driver.find_element(By.ID, "DataInicial").send_keys(data_inicio)
            
            driver.find_element(By.ID, "DataFinal").clear()
            driver.find_element(By.ID, "DataFinal").send_keys(data_fim)
            
            # Clica no botão Filtrar (ícone de filtro ou botão com texto Filtrar)
            # Geralmente é um button com type='submit' dentro do form de filtro
            driver.find_element(By.CSS_SELECTOR, "button[type='submit'], #btnFiltrar").click()
            time.sleep(4)
        except:
            st.warning("⚠️ Erro ao preencher datas. Baixando o que estiver visível.")

        st.image(driver.get_screenshot_as_png(), caption="Tabela de Notas", use_column_width=True)

        # 4. EXTRAÇÃO
        msg.info("🔄 Baixando XMLs...")
        linhas = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        
        if len(linhas) > 0 and "Nenhum registro" in linhas[0].text:
             st.warning("⚠️ Nenhuma nota encontrada neste período.")
             return

        qtd = len(linhas)
        st.write(f"Encontradas: {qtd} notas.")
        bar = st.progress(0)
        
        for i, linha in enumerate(linhas):
            try:
                # 1. Clica nos 3 pontinhos (Dropdown)
                botao_menu = linha.find_element(By.CSS_SELECTOR, ".dropdown-toggle")
                driver.execute_script("arguments[0].click();", botao_menu)
                time.sleep(0.5)
                
                # 2. Clica no Download XML
                # Busca o link que tem o texto 'Download XML' visível agora
                link_xml = driver.find_element(By.XPATH, "//a[contains(text(), 'Download XML')]")
                driver.execute_script("arguments[0].click();", link_xml)
                
                time.sleep(1.5)
                webdriver.ActionChains(driver).move_by_offset(0, 0).click().perform() # Fecha menu
            except Exception as e:
                print(f"Erro linha {i}: {e}")
            bar.progress((i + 1) / qtd)

        time.sleep(3)
        
        # 5. DOWNLOAD FINAL
        arquivos = os.listdir(DOWNLOAD_DIR)
        if len(arquivos) > 0:
            shutil.make_archive("/tmp/notas_fiscais", 'zip', DOWNLOAD_DIR)
            with open("/tmp/notas_fiscais.zip", "rb") as f:
                st.success(f"✅ Sucesso! {len(arquivos)} notas baixadas.")
                st.download_button("📥 BAIXAR ZIP", f, "notas.zip", "application/zip")
                st.balloons()
        else:
            st.error("❌ Nenhum arquivo baixado.")

    except Exception as e:
        st.error(f"Erro Crítico: {e}")
    finally:
        if driver:
            driver.quit()

# --- FORMULÁRIO ---
st.title("🤖 Robô NFS-e Nacional")
with st.form("form_dados"):
    col1, col2 = st.columns(2)
    with col1:
        cnpj_input = st.text_input("CNPJ / CPF")
        data_ini = st.date_input("Data Inicial", value=date.today().replace(day=1))
    with col2:
        senha_input = st.text_input("Senha", type="password")
        data_fim = st.date_input("Data Final", value=date.today())
    tipo = st.selectbox("Tipo de Nota", ["Notas Emitidas", "Notas Recebidas"]) # Mudei a ordem para testar Emitidas primeiro
    if st.form_submit_button("🚀 Iniciar Robô"):
        if cnpj_input and senha_input:
            executar_robo(cnpj_input, senha_input, tipo, data_ini.strftime("%d/%m/%Y"), data_fim.strftime("%d/%m/%Y"))
        else:
            st.warning("Preencha os dados.")
