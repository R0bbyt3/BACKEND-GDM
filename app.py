from flask import Flask, request, jsonify, session
from flask_cors import CORS
import logging
from flask_wtf.csrf import CSRFProtect, generate_csrf
from markupsafe import escape
from validation_schemas import UserSchema, validate_input
from firebase_utils import (
    check_and_add_school_year,
    check_and_add_user,
    get_ano_escola_id_usuario,
    get_periodos_materias,
    get_componentes_materia,
    get_medias_aluno,
    get_notas_aluno,
    db
)
from selenium_utils import init_driver, perform_login, extract_grades
import os

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')
csrf = CSRFProtect(app)
CORS(app)

# Configuração do logger para incluir mensagens de debug
logging.basicConfig(level=logging.INFO)

# Variável para controle de debug
DEBUG_MODE = os.getenv('DEBUG_MODE', 'True') == 'True'

def debug_log(message):
    """Função para logs de depuração detalhados"""
    if DEBUG_MODE:
        logging.info(message)

def login_user(login):
    session['user'] = login
    session.permanent = True  # A sessão expira após um período de inatividade

def logout_user():
    session.pop('user', None)

def is_logged_in():
    return 'user' in session

def get_logged_in_user():
    return session.get('user')

# Adiciona cabeçalhos de segurança
@app.after_request
def set_security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    if request.is_secure:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

@app.route('/')
def home():
    return "Hello, World!"

# Rota para fornecer o token CSRF
@app.route('/csrf-token', methods=['GET'])
def csrf_token():
    token = generate_csrf()
    return jsonify(csrf_token=token)

# Rota para criar conta
@app.route('/create_account', methods=['POST'])
@csrf.exempt  # Exemplo de como desativar CSRF para uma rota específica (não recomendado)
def create_account():
    # Recebe os dados JSON do cliente
    data = request.json
    debug_log(f"Dados recebidos para criação de conta: {data}")
    
    # Valida os dados recebidos
    validation_errors = validate_input(data, UserSchema)
    if (validation_errors):
        debug_log(f"Erros de validação: {validation_errors}")
        return jsonify({"success": False, "message": validation_errors}), 400

    login = escape(data.get('login'))
    senha = escape(data.get('senha'))

    driver = init_driver()

    try:
        debug_log("Iniciando processo de criação de conta...")
        ano_escolar, nome = perform_login(driver, login, senha)  # Extraindo ano escolar e nome
        debug_log(f"Credenciais válidas, procedendo com a criação de conta com ano escolar: {ano_escolar} e nome: {nome}")

        ano_escolar_id = check_and_add_school_year(ano_escolar)
        debug_log(f"Ano escolar ID obtido: {ano_escolar_id}")

        if check_and_add_user(login, senha, ano_escolar_id, nome):
            data = extract_grades(driver, login, ano_escolar_id)
            message = "Conta criada com sucesso, notas extraídas e salvas."
            success = True
            debug_log("Conta criada e dados extraídos com sucesso.")
        else:
            message = "Conta já existe."
            success = False
            data = None
            debug_log("Conta já existe no sistema.")
    except Exception as e:
        message = f"Erro: {e}"
        success = False
        data = None
        logging.error(f"Erro durante a criação de conta: {e}")
    finally:
        driver.quit()

    return jsonify({"success": success, "message": message, "data": data})

# Rota para login
@app.route('/login', methods=['POST'])
@csrf.exempt  # Desativar CSRF para a rota de login
def login_route():
    # Recebe os dados JSON do cliente
    data = request.json
    debug_log(f"Dados recebidos para login: {data}")
    
    # Valida os dados recebidos
    validation_errors = validate_input(data, UserSchema)
    if validation_errors:
        debug_log(f"Erros de validação: {validation_errors}")
        return jsonify({"success": False, "message": validation_errors}), 400

    login = escape(data.get('login'))
    senha = escape(data.get('senha'))

    try:
        user_ref = db.collection('Usuario').document(login)
        user_doc = user_ref.get()
        if user_doc.exists and user_doc.to_dict()['senha'] == senha:
            login_user(login)
            message = "Login bem-sucedido."
            success = True
            ano_escola_id = user_doc.to_dict()['ano_escola_id']
            debug_log(f"Login bem-sucedido para usuário: {login}, ano_escola_id: {ano_escola_id}")
        else:
            message = "Usuário ou senha inválidos."
            success = False
            ano_escola_id = None
            debug_log("Usuário ou senha inválidos.")
    except Exception as e:
        message = f"Erro: {e}"
        success = False
        ano_escola_id = None
        logging.error(f"Erro durante o login: {e}")

    return jsonify({"success": success, "message": message, "ano_escola_id": ano_escola_id})

# Rota para logout
@app.route('/logout', methods=['POST'])
def logout():
    if not is_logged_in():
        return jsonify({"success": False, "message": "Usuário não autenticado."}), 401
    
    logout_user()
    return jsonify({"success": True, "message": "Logout bem-sucedido."})

# Rota para atualizar informações
@app.route('/update_info', methods=['POST'])
@csrf.exempt  # Desativar CSRF para a rota de atualização de informações
def update_info():
    if not is_logged_in():
        return jsonify({"success": False, "message": "Usuário não autenticado."}), 401
    
    # Recebe os dados JSON do cliente
    data = request.json
    login = escape(data.get('login'))
    senha = escape(data.get('senha'))
    ano_escolar = escape(data.get('ano_escolar'))
    ano_atual = escape(data.get('ano_atual'))

    debug_log(f"Iniciando atualização de informações para: login={login}, ano_escolar={ano_escolar}, ano_atual={ano_atual}")

    driver = init_driver()

    try:
        debug_log("Iniciando processo de atualização de informações...")
        perform_login(driver, login, senha)
        debug_log("Login bem-sucedido, redirecionado para a página principal...")

        ano_escolar_id = check_and_add_school_year(ano_escolar)
        debug_log(f"Ano escolar ID obtido: {ano_escolar_id}")

        data = extract_grades(driver, login, ano_escolar_id)
        message = "Informações atualizadas com sucesso."
        success = True
        debug_log("Informações atualizadas com sucesso.")
    except Exception as e:
        message = f"Erro: {e}"
        success = False
        data = None
        logging.error(f"Erro durante a atualização de informações: {e}")
    finally:
        driver.quit()

    return jsonify({"success": success, "message": message, "data": data})

@app.route('/get_user_data', methods=['POST'])
def get_user_data():
    if not is_logged_in():
        return jsonify({"success": False, "message": "Usuário não autenticado."}), 401

    try:
        # Recebe os dados JSON do cliente
        data = request.get_json()
        login = escape(data['login'])
        
        debug_log(f"Recebendo dados do usuário: {login}")
        
        ano_escolar_id, nome = get_ano_escola_id_usuario(login)
        debug_log(f"ano_escolar_id para o usuário {login}: {ano_escolar_id}, nome: {nome}")
        if not ano_escolar_id:
            return jsonify({"status": "error", "message": "Ano escolar não encontrado para o usuário"}), 404
        
        trimestres, materias, calculos = get_periodos_materias(ano_escolar_id)
        debug_log(f"Trimestres obtidos: {trimestres}\n\n")
        debug_log(f"Matérias obtidas: {materias}\n\n")
        
        notas = get_notas_aluno(login)
        debug_log(f"Notas obtidas: {notas}\n\n")
        
        medias = get_medias_aluno(login)
        debug_log(f"Médias obtidas: {medias}\n\n")

        componentes = {}
        for materia_id in materias.keys():
            componentes_materia = get_componentes_materia(materia_id)
            if componentes_materia:
                componentes.update(componentes_materia)
        debug_log(f"Componente obtidos: {componentes}\n\n")

        return jsonify({
            "status": "success",
            "trimestres": trimestres,
            "materias": materias,
            "notas": notas,
            "medias": medias,
            "componentes": componentes,
            "calculos": calculos,
            "nome": nome  
        })
    except Exception as e:
        logging.error(f"Erro durante a obtenção de dados do usuário: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=DEBUG_MODE)
