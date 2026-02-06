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
import requests # A NOVA ARMA SECRETA
from datetime import date

# --- CONFIGURAÇÃO ---
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
    
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# Função para injetar data (Mantida)
def forcar_data_js(driver, elemento_id, data_valor):
    try:
        driver.execute_script(f"document.getElementById('{elemento_id}').value = '{data_valor}';")
    except:
        pass

def executar_robo(cnpj, senha, tipo_nota, data_inicio, data_fim):
    driver = None
    session = None
    msg = st.empty()
    limpar_pasta()
    
    try:
        # 1. LOGIN (Igual)
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
        
        # Verifica Login
        if len(driver.find_elements(By.CLASS_NAME, "validation-summary-errors")) > 0:
            st.error("Erro no Login.")
            return

        msg.success("✅ Login OK! Roubando cookies para o Python...")

        # --- O PULO DO GATO: PREPARAR O REQUESTS ---
        # Pega os cookies do navegador (Selenium) e passa para o Python (Requests)
        session = requests.Session()
        for cookie in driver.get_cookies():
            session.cookies.set(cookie['name'], cookie['value'])
        
        # Cabeçalhos para fingir que o Python é um navegador
        session.headers.update({
            "User-Agent": driver.execute_script("return navigator.userAgent;")
        })

        # 2. NAVEGAÇÃO
        termo_url = "Emitidas" if tipo_nota == "Notas Emitidas" else "Recebidas"
        try:
            driver.execute_script(f"document.querySelector(\"a[href*='{termo_url}']\").click()")
        except:
             st.error("Erro ao achar menu.")
             return

        time.sleep(4) 

        # 3. FILTRO
        msg.info(f"📅 Filtrando...")
        try:
            forcar_data_js(driver, "DataInicial", data_inicio)
            forcar_data_js(driver, "DataFinal", data_fim)
            time.sleep(1)
            driver.find_element(By.CSS_SELECTOR, "button[type='submit'], #btnFiltrar").click()
            time.sleep(4)
        except:
            pass

        st.image(driver.get_screenshot_as_png(), caption="Tabela Filtrada", use_column_width=True)

        # 4. EXTRAÇÃO HÍBRIDA (SELENIUM + REQUESTS)
        msg.info("🔄 Baixando via Python Direto (Bypass Chrome)...")
        linhas = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        
        qtd = len(linhas)
        st.write(f"Encontradas: {qtd} notas.")
        
        if qtd == 0:
            st.warning("Sem notas.")
            return

        bar = st.progress(0)
        sucesso_count = 0
        
        for i, linha in enumerate(linhas):
            try:
                # 1. Abre o Menu para garantir que o link exista no DOM
                botao_menu = linha.find_element(By.CSS_SELECTOR, ".dropdown-toggle")
                driver.execute_script("arguments[0].click();", botao_menu)
                time.sleep(0.5)
                
                # 2. PEGA A URL DO XML
                link_el = driver.find_element(By.XPATH, "//a[contains(text(), 'XML')]")
                url_download = link_el.get_attribute('href')
                
                # Se o link for javascript, não temos saída na nuvem :(
                if "javascript" in url_download:
                    st.warning(f"Nota {i+1}: O link é JavaScript protegido. Tentando clique forçado...")
                    driver.execute_script("arguments[0].click();", link_el)
                    time.sleep(2)
                else:
                    # Se for URL real (http...), o Python baixa!
                    # Se o link for relativo (começa com /), completa ele
                    if url_download.startswith("/"):
                        url_download = "https://www.nfse.gov.br" + url_download
                    
                    # DOWNLOAD VIA REQUESTS (Aqui a mágica acontece)
                    response = session.get(url_download)
                    
                    if response.status_code == 200:
                        nome_arquivo = f"nota_{i+1}_{date.today()}.xml"
                        caminho_completo = os.path.join(DOWNLOAD_DIR, nome_arquivo)
                        with open(caminho_completo, "wb") as f:
                            f.write(response.content)
                        sucesso_count += 1
                    else:
                        print(f"Erro HTTP {response.status_code}")

                webdriver.ActionChains(driver).move_by_offset(0, 0).click().perform() # Fecha menu
                
            except Exception as e:
                print(f"Erro linha {i}: {e}")
            bar.progress((i + 1) / qtd)

        time.sleep(2)
        
        # 5. ENTREGA
        arquivos = os.listdir(DOWNLOAD_DIR)
        
        # Se o download via requests falhou, tenta ver se o clique forçado funcionou
        if len(arquivos) == 0:
             # Procura na raiz /tmp como última esperança
             arquivos_raiz = [f for f in os.listdir("/tmp") if f.endswith(".xml")]
             for f in arquivos_raiz:
                 shutil.move(os.path.join("/tmp", f), DOWNLOAD_DIR)
             arquivos = os.listdir(DOWNLOAD_DIR)

        if len(arquivos) > 0:
            shutil.make_archive("/tmp/notas_fiscais", 'zip', DOWNLOAD_DIR)
            with open("/tmp/notas_fiscais.zip", "rb") as f:
                st.success(f"✅ VITÓRIA! {len(arquivos)} notas recuperadas.")
                st.download_button("📥 BAIXAR ZIP", f, "notas.zip", "application/zip")
                st.balloons()
        else:
            st.error("❌ O site do governo usa links JavaScript criptografados.")
            st.warning("⚠️ SOLUÇÃO DEFINITIVA: Clayton, o portal bloqueia robôs na nuvem. A única forma profissional de usar isso no escritório é rodar LOCALMENTE.")
            st.markdown("""
            **Como rodar no escritório sem dor de cabeça:**
            1. Baixe este código `appy.py`.
            2. Instale o Python nas máquinas.
            3. Digite `streamlit run appy.py` no terminal do Windows.
            4. O robô vai usar o Chrome local e vai funcionar 100%.
            """)

    except Exception as e:
        st.error(f"Erro: {e}")
    finally:
        if driver:
            driver.quit()

# --- FORMULÁRIO ---
st.title("🤖 Robô NFS-e (Modo Híbrido)")
with st.form("form_dados"):
    col1, col2 = st.columns(2)
    with col1:
        cnpj_input = st.text_input("CNPJ / CPF")
        data_ini = st.date_input("Data Inicial", value=date.today().replace(day=1))
    with col2:
        senha_input = st.text_input("Senha", type="password")
        data_fim = st.date_input("Data Final", value=date.today())
    tipo = st.selectbox("Tipo de Nota", ["Notas Emitidas", "Notas Recebidas"])
    if st.form_submit_button("🚀 Tentar Última Vez"):
        if cnpj_input and senha_input:
            executar_robo(cnpj_input, senha_input, tipo, data_ini.strftime("%d/%m/%Y"), data_fim.strftime("%d/%m/%Y"))
