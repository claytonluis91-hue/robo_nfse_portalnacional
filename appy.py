from selenium.webdriver.common.by import By  # Importação necessária para achar os elementos

def iniciar_robo(cnpj_digitado, usuario_digitado, senha_digitada):
    driver = None
    status_placeholder = st.empty() 
    
    try:
        status_placeholder.info("Iniciando o navegador na nuvem... Aguarde.")
        driver = get_driver()
        
        status_placeholder.info("Acessando o Portal Nacional...")
        driver.get("https://www.nfse.gov.br/EmissorNacional/Login")
        time.sleep(5) # Espera carregar visualmente
        
        st.image(driver.get_screenshot_as_png(), caption="1. Tela Inicial", use_column_width=True)

        # --- PREENCHIMENTO DOS DADOS ---
        status_placeholder.info("Preenchendo credenciais...")
        
        # 1. Tenta encontrar o campo CNPJ/CPF (Geralmente o ID é 'Inscricao')
        try:
            campo_cnpj = driver.find_element(By.ID, "Inscricao")
            campo_cnpj.clear()
            campo_cnpj.send_keys(cnpj_digitado)
        except:
            st.error("Não achei o campo de CNPJ (ID 'Inscricao'). O site pode ter mudado.")

        # 2. Tenta encontrar o campo SENHA (Geralmente o ID é 'Senha')
        try:
            campo_senha = driver.find_element(By.ID, "Senha")
            campo_senha.clear()
            campo_senha.send_keys(senha_digitada)
        except:
            st.error("Não achei o campo de Senha.")

        # 3. Clica no botão ENTRAR
        # Procuramos um botão que tenha o texto "Entrar" para garantir que é o certo
        try:
            botoes = driver.find_elements(By.TAG_NAME, "button")
            botao_clicado = False
            for btn in botoes:
                if "Entrar" in btn.text and "gov.br" not in btn.text.lower():
                    btn.click()
                    botao_clicado = True
                    break
            
            if not botao_clicado:
                st.warning("Tentei clicar, mas não achei um botão escrito apenas 'Entrar'.")
        except Exception as e:
            st.warning(f"Erro ao tentar clicar: {e}")

        status_placeholder.info("Login enviado. Verificando resultado...")
        time.sleep(5) # Espera o site processar o login
        
        # --- RESULTADO ---
        st.image(driver.get_screenshot_as_png(), caption="2. Tela Pós-Login (Verifique se entrou)", use_column_width=True)
        st.success("Processo finalizado! Veja na imagem acima se apareceu o painel do usuário ou mensagem de erro.")

    except Exception as e:
        st.error(f"Erro crítico: {e}")
    finally:
        if driver:
            driver.quit()
