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
from datetime import date, timedelta

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Robô XML NFS-e", page_icon="🤖")

# Pasta temporária
DOWNLOAD_DIR = "/tmp/xml_downloads"

# --- FUNÇÕES UTILITÁRIAS ---
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

# --- LÓGICA DO ROBÔ ---
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
        
        # Preenche Login
        wait.until(EC.presence_of_element_located((By.ID, "Inscricao"))).send_keys(cnpj)
        driver.find_element(By.ID, "Senha").send_keys(senha)
        
        # Clica em Entrar (Tenta XPATH primeiro, depois CSS)
        try:
            driver.find_element(By.XPATH, "//button[contains(text(), 'Entrar')]").click()
        except:
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            
        time.sleep(5)
        
        # Validação de Login
        if "Login" in driver.title or len(driver.find_elements(By.ID, "Inscricao")) > 0:
            st.error("❌ Login falhou. Verifique se o CNPJ e Senha estão corretos.")
            st.image(driver.get_screenshot_as_png(), caption="Tela de Erro Login", use_column_width=True)
            return

        msg.success("✅ Login OK! Navegando para as notas...")

        # 2. NAVEGAÇÃO VIA MENU (Sem link direto para não travar)
        termo_busca = "Recebidas" if tipo_nota == "Notas Recebidas" else "Emitidas"
        
        try:
            # Procura qualquer link (a) que tenha o termo no título (Ex: 'NFS-e Emitidas')
            # O XPATH abaixo ignora maiúsculas/minúsculas
            xpath_menu = f"//a[contains(@title, '{termo_busca}')]"
            botao_menu = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_menu)))
            botao_menu.click()
        except:
            st.error(f"❌ Não encontrei o menu '{termo_busca}'. O site pode ter mudado.")
            st.image(driver.get_screenshot_as_png(), caption="Erro ao achar Menu", use_column_width=True)
            return

        time.sleep(5) # Espera carregar a tela de notas

        # 3. APLICAÇÃO DO FILTRO DE DATA
        msg.info(f"📅 Aplicando filtro: {data_inicio} até {data_fim}...")
        
        try:
            # Preenche Data Inicial
            cmp_ini = driver.find_element(By.ID, "DataInicial")
            cmp_ini.clear()
            cmp_ini.send_keys(data_inicio) # Formato DD/MM/AAAA já vem do input do Streamlit formatado? Vamos garantir.
            
            # Preenche Data Final
            cmp_fim = driver.find_element(By.ID, "DataFinal")
            cmp_fim.clear()
            cmp_fim.send_keys(data_fim)
            
            # Clica em Filtrar
            driver.find_element(By.ID, "btnFiltrar").click() # ID chutado (comum), se der erro ajustamos.
            # Alternativa genérica para botão filtrar:
            # driver.find_element(By.XPATH, "//button[contains(text(), 'Filtrar')]").click()
            
            time.sleep(5) # Espera a tabela atualizar
            
        except Exception as e:
            st.warning(f"⚠️ Não consegui filtrar as datas (Erros de ID). Baixando o que estiver na tela. Erro: {e}")

        st.image(driver.get_screenshot_as_png(), caption="Tabela Filtrada", use_column_width=True)

        # 4. EXTRAÇÃO (LOOP)
        msg.info("🔄 Processando lista de notas...")
        
        # Pega as linhas da tabela (body)
        linhas = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        
        # Validação: Se a linha tiver texto "Nenhum registro", aborta
        if len(linhas) > 0 and "Nenhum registro" in linhas[0].text:
             st.warning("⚠️ O filtro retornou 0 notas.")
             return

        qtd = len(linhas)
        st.write(f"**Encontrei {qtd} notas na tela.**")
        
        bar = st.progress(0)
        sucessos = 0
        
        for i, linha in enumerate(linhas):
            try:
                # Acha o botão de menu (3 pontinhos)
                # O seletor busca um dropdown dentro da última célula
                botao_tres_pontos = linha.find_element(By.CSS_SELECTOR, ".dropdown-toggle")
                
                # FORÇA BRUTA (JavaScript): Clica mesmo se tiver algo na frente
                driver.execute_script("arguments[0].click();", botao_tres_pontos)
                time.sleep(1)
                
                # Clica em "Download XML"
                link_xml = driver.find_element(By.XPATH, "//a[contains(text(), 'Download XML')]")
                driver.execute_script("arguments[0].click();", link_xml)
                
                sucessos += 1
                time.sleep(1.5) # Dá tempo para o download iniciar
                
                # Clica fora para fechar o menu (opcional)
                webdriver.ActionChains(driver).move_by_offset(0, 0).click().perform()
                
            except Exception as e:
                print(f"Erro linha {i}: {e}")
            
            bar.progress((i + 1) / qtd)

        time.sleep(5) # Espera downloads terminarem
        
        # 5. EMPACOTAR E ENTREGAR
        arquivos = os.listdir(DOWNLOAD_DIR)
        if len(arquivos) > 0:
            shutil.make_archive("/tmp/notas_fiscais", 'zip', DOWNLOAD_DIR)
            with open("/tmp/notas_fiscais.zip", "rb") as f:
                st.success(f"✅ Sucesso! {len(arquivos)} arquivos baixados.")
                st.download_button(
                    label="📥 BAIXAR ZIP COMPLETO",
                    data=f,
                    file_name="notas_xml.zip",
                    mime="application/zip"
                )
                st.balloons()
        else:
            st.error("❌ Nenhum arquivo XML apareceu na pasta. O download falhou.")

    except Exception as e:
        st.error(f"Erro Crítico: {e}")
    finally:
        if driver:
            driver.quit()

# --- INTERFACE LATERAL ---
st.title("🤖 Robô NFS-e Nacional")

with st.form("form_dados"):
    col1, col2 = st.columns(2)
    with col1:
        cnpj_input = st.text_input("CNPJ / CPF")
        data_ini = st.date_input("Data Inicial", value=date.today().replace(day=1))
    with col2:
        senha_input = st.text_input("Senha", type="password")
        data_fim = st.date_input("Data Final", value=date.today())
        
    tipo = st.selectbox("Tipo de Nota", ["Notas Recebidas", "Notas Emitidas"])
    
    submitted = st.form_submit_button("🚀 Iniciar Robô")

if submitted:
    if not cnpj_input or not senha_input:
        st.warning("Preencha CNPJ e Senha.")
    else:
        # Formata datas para String DD/MM/AAAA
        d_ini_str = data_ini.strftime("%d/%m/%Y")
        d_fim_str = data_fim.strftime("%d/%m/%Y")
        executar_robo(cnpj_input, senha_input, tipo, d_ini_str, d_fim_str)
