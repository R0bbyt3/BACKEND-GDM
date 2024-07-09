from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging
from firebase_utils import save_to_firestore
from utils import convert_to_float, capitalize_component_name

DEBUG = True  # Define se o modo de debug está ativo ou não

def debug_log(message):
    if DEBUG:
        print(f"DEBUG: {message}")

def find_link_by_text(driver, text):
    """
    Encontra um link na página pelo texto.

    Args:
        driver (webdriver): Instância do WebDriver.
        text (str): Texto do link a ser encontrado.

    Returns:
        WebElement: Elemento do link encontrado.
    """
    debug_log(f"Procurando link com texto: {text}")
    return driver.find_element(By.XPATH, f"//a[contains(text(), '{text}')]")

def init_driver():
    """
    Inicializa o driver do Chrome com opções pré-definidas.

    Returns:
        webdriver: Instância do WebDriver do Chrome.
    """
    debug_log("Inicializando driver do Chrome")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--remote-debugging-port=9222')  # Necessário para rodar no Heroku
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    debug_log("Driver do Chrome inicializado")
    return driver

def extract_school_year(driver):
    """
    Extrai o ano escolar da página de boletim.

    Args:
        driver (webdriver): Instância do WebDriver.

    Returns:
        str: Ano escolar extraído.
    """
    debug_log("Extraindo ano escolar da página de boletim")
    driver.get('https://www.escola1.info/site/Servicos/Essencial/Boletim/BoletimNovo.asp')
    select_element = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.NAME, 'DropGradeAluno')))
    selected_option = select_element.find_element(By.CSS_SELECTOR, 'option[selected]')
    full_text = selected_option.text  # Aqui pegamos o texto completo
    ano_escolar = full_text.split('|')[1].strip()  # Extraímos a parte após a barra
    debug_log(f"Ano escolar extraído: {ano_escolar}")
    return ano_escolar

def perform_login(driver, login, senha):
    """
    Realiza o login no site especificado e extrai o ano escolar e o nome do usuário.

    Args:
        driver (webdriver): Instância do WebDriver.
        login (str): Nome de usuário.
        senha (str): Senha do usuário.

    Returns:
        tuple: Ano escolar e nome do usuário extraídos após o login.
    """
    debug_log(f"Iniciando login para o usuário: {login}, com a senha: {senha}")
    driver.get('https://www.escola1.info/cruzeiro/')
    debug_log("Página de login carregada")
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, 'txtLogin'))).send_keys(login)
    debug_log("Login inserido")
    driver.find_element(By.ID, 'txtSenha').send_keys(senha)
    debug_log("Senha inserida")
    driver.find_element(By.ID, 'LinkButton3').click()
    WebDriverWait(driver, 30).until(EC.url_contains("site/Principal"))
    debug_log("Login realizado com sucesso")
    
    # Certifique-se de que está na página correta
    driver.get('https://www.escola1.info/site/Principal/Main_Princ_Shared.asp')
    nome_usuario = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'td.MensgBVTDsup b'))).text
    debug_log(f"Nome do usuário extraído: {nome_usuario}")
    
    # Redireciona para a página de boletim
    boletim_base_url = 'https://www.escola1.info/site/Servicos/Essencial/Boletim/BoletimNovo.asp'
    driver.get(boletim_base_url)
    debug_log("Página de boletim carregada")
    
    # Extraindo ano escolar após login
    ano_escolar = extract_school_year(driver)
    
    return ano_escolar, nome_usuario

def extract_grades(driver, login, ano_escolar_id):
    """
    Extrai as notas dos boletins.

    Args:
        driver (webdriver): Instância do WebDriver.
        login (str): Nome de usuário.
        ano_escolar_id (str): ID do ano escolar.

    Returns:
        list: Dados dos boletins extraídos.
    """
    debug_log("Iniciando extração de notas")
    boletim_base_url = 'https://www.escola1.info/site/Servicos/Essencial/Boletim/BoletimNovo.asp'
    driver.get(boletim_base_url)
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a.SubNotas')))
    debug_log("Página de boletins carregada")
    
    boletins = ['NPT', 'NST', 'NTT']
    data = []
    for boletim in boletins:
        try:
            debug_log(f"Extraindo notas do boletim: {boletim}")
            link = find_link_by_text(driver, boletim)
            onclick_value = link.get_attribute("onclick")
            link_code = onclick_value.split("param=")[1].split('&')[0]
            boletim_url = f'https://www.escola1.info/site/Servicos/Essencial/Boletim/BoletimParcial.asp?param={link_code}'
            driver.get(boletim_url)
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table[name="Conteudo"]')))
            
            boletim_data = extract_subject_data(driver, login, ano_escolar_id, boletim)
            data.append(boletim_data)
            driver.get(boletim_base_url)
            debug_log(f"Notas do boletim {boletim} extraídas com sucesso")
        except Exception as e:
            logging.warning(f"Falha ao extrair notas do boletim {boletim}: {e}")
            debug_log(f"Erro ao extrair notas do boletim {boletim}: {e}")
            driver.get(boletim_base_url)
    return data

def extract_subject_data(driver, login, ano_escolar_id, boletim):
    debug_log(f"Extraindo dados das matérias do boletim: {boletim}")
    materias = driver.find_elements(By.CSS_SELECTOR, 'table.Tab1Grade[id="NOTA"]')
    boletim_data = []
    for materia in materias:
        materia_titulo = materia.find_element(By.CSS_SELECTOR, 'td[class="Tab1Titulo"]').text
        materia_nome = " ".join(materia_titulo.split(" - ")[1:-1])
        debug_log(f"Extraindo dados da matéria: {materia_nome}")
        
        calculo = materia.find_element(By.CSS_SELECTOR, 'td[class="Tab1subTitulo"]').text
        debug_log(f"Calculo extraído para a matéria {materia_nome}: {calculo}")
        
        componentes = materia.find_elements(By.CSS_SELECTOR, 'td[class="Tab3TituloCol"]')
        notas = materia.find_elements(By.CSS_SELECTOR, 'td[class="Tab1Texto"]')

        media_atual = notas[-1].text.strip()
        componentes = componentes[:-1]
        notas = notas[:-1]

        materia_data = {
            "materia_nome": materia_nome,
            "componentes": []
        }

        for comp, nota in zip(componentes, notas):
            componente_info = comp.get_attribute("title").split('\n')
            titulo = capitalize_component_name(componente_info[0])  # Padronizando nome do componente
            pequeno_nome = comp.get_attribute('innerHTML').split('<br>')[0].strip()  # Pegando o nome antes da tag <br>
            peso = convert_to_float(componente_info[1].split(':')[1])
            maximo = convert_to_float(componente_info[2].split(':')[1])
            nota_valor = convert_to_float(nota.text.strip()) if nota.text.strip() else -1

            debug_log(f"Salvando componente: {titulo}, nota: {nota_valor}, pequeno nome: {pequeno_nome}")

            componente_data = {
                'titulo': titulo,
                'pequeno_nome': pequeno_nome,
                'peso': peso,
                'maximo': maximo,
                'nota': nota_valor
            }

            save_to_firestore(login, materia_nome, boletim, titulo, peso, maximo, nota_valor, media_atual, ano_escolar_id, boletim, calculo, pequeno_nome)
            materia_data["componentes"].append(componente_data)
        
        boletim_data.append(materia_data)
        debug_log(f"Dados da matéria {materia_nome} extraídos e salvos com sucesso")

    return boletim_data
