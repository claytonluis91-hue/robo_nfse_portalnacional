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
        try:
            shutil.rmtree(DOWNLOAD_DIR)
        except:
            pass
    os.makedirs(DOWNLOAD_DIR)

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # CONFIGURAÇÕES "NUCLEARES" PARA PERMITIR DOWNLOAD NA NUVEM
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_settings.popups": 0,
        "profile.default_content_setting_values.automatic_downloads": 1,
        "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,
        "excludeSwitches": ["enable-automation"],
        "useAutomationExtension": False
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# Função mágica para preencher datas
def forcar_data_js(driver, elemento_id, data_valor):
    try:
        driver.execute_script(f"document.getElementById('{elemento_id}').value = '{data_valor}';")
    except:
        pass

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
        
        # Verificação básica de erro
        if len(driver.find_elements(By.CLASS_NAME, "validation-summary-errors")) > 0:
            st.error("Erro no Login: Verifique usuário e senha.")
            return

        msg.success("✅ Login OK! Buscando menu...")

        # 2. NAVEGAÇÃO
        termo_url = "Emitidas" if tipo_nota == "Notas Emitidas" else "Recebidas"
        try:
            driver.execute_script(f"document.querySelector(\"a[href*='{termo_url}']\").click()")
        except:
             st.error("Não achei o menu. O site mudou?")
             return

        time.sleep(4) 

        # 3. FILTRO DE DATA
        msg.info(f"📅 Filtrando...")
        try:
            forcar_data_js(driver, "DataInicial", data_inicio)
            forcar_data_js(driver, "DataFinal", data_fim)
            time.sleep(1)
            driver.find_element(By.CSS_SELECTOR, "button[type='submit'], #btnFiltrar").click()
            time.sleep(4)
        except Exception as e:
            st.warning(f"Aviso no filtro: {e}")

        # 4. EXTRAÇÃO (A MUDANÇA ESTÁ AQUI)
        msg.info("🔄 Baixando XMLs...")
        linhas = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        
        qtd = len(linhas)
        st.write(f"Encontradas: {qtd} notas.")
        
        if qtd == 0:
            st.warning("Nenhuma nota para baixar.")
            return

        bar = st.progress(0)
        
        for i, linha in enumerate(linhas):
            try:
                # 1. Abre o Menu
                botao_menu = linha.find_element(By.CSS_SELECTOR, ".dropdown-toggle")
                driver.execute_script("arguments[0].click();", botao_menu)
                time.sleep(1)
                
                # 2. ESTRATÉGIA LINK DIRETO (Mais confiável que clicar)
                link_xml = driver.find_element(By.XPATH, "//a[contains(text(), 'XML')]")
                url_download = link_xml.get_attribute('href')
                
                if url_download and "javascript" not in url_download:
                    # Se for um link real, navega até ele para forçar o download
                    driver.get(url_download)
                    # Volta para a página anterior para continuar o loop
                    driver.back()
                    time.sleep(2) 
                    # Re-localiza as linhas pois a página recarregou
                    linhas = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                else:
                    # Se for JavaScript, clica normal
                    driver.execute_script("arguments[0].click();", link_xml)
                    time.sleep(2)
                
            except Exception as e:
                print(f"Erro linha {i}: {e}")
            bar.progress((i + 1) / qtd)

        time.sleep(5) # Espera final
        
        # 5. DIAGNÓSTICO DE ARQUIVOS
        arquivos = os.listdir(DOWNLOAD_DIR)
        
        # Debug: Mostra o que tem na pasta (se tiver algo com nome estranho, saberemos)
        if len(arquivos) == 0:
            st.warning("Pasta vazia. Tentando procurar na raiz...")
            arquivos_raiz = [f for f in os.listdir("/tmp") if f.endswith(".xml")]
            if len(arquivos_raiz) > 0:
                # Move para a pasta certa
                for f in arquivos_raiz:
                    shutil.move(os.path.join("/tmp", f), DOWNLOAD_DIR)
                arquivos = os.listdir(DOWNLOAD_DIR)

        if len(arquivos) > 0:
            shutil.make_archive("/tmp/notas_fiscais", 'zip', DOWNLOAD_DIR)
            with open("/tmp/notas_fiscais.zip", "rb") as f:
                st.success(f"✅ SUCESSO! {len(arquivos)} arquivos recuperados!")
                st.download_button("📥 BAIXAR ZIP AGORA", f, "notas.zip", "application/zip")
                st.balloons()
        else:
            st.error("❌ Os arquivos não foram salvos. O Google Chrome bloqueou o download na nuvem.")
            st.write("Dica: Tente rodar este script localmente no seu PC (VS Code), pois na nuvem o bloqueio de segurança é muito alto.")

    except Exception as e:
        st.error(f"Erro Crítico: {e}")
    finally:
        if driver:
            driver.quit()

# --- FORMULÁRIO ---
st.title("🤖 Robô NFS-e v6.0")
with st.form("form_dados"):
    col1, col2 = st.columns(2)
    with col1:
        cnpj_input = st.text_input("CNPJ / CPF")
        data_ini = st.date_input("Data Inicial", value=date.today().replace(day=1))
    with col2:
        senha_input = st.text_input("Senha", type="password")
        data_fim = st.date_input("Data Final", value=date.today())
    tipo = st.selectbox("Tipo de Nota", ["Notas Emitidas", "Notas Recebidas"])
    if st.form_submit_button("🚀 Executar"):
        if cnpj_input and senha_input:
            executar_robo(cnpj_input, senha_input, tipo, data_ini.strftime("%d/%m/%Y"), data_fim.strftime("%d/%m/%Y"))
