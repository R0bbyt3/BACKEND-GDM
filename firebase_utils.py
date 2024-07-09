import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime 
from utils import convert_to_float
import os

# Inicializar o Firebase
firebase_config = {
    "type": os.getenv('FIREBASE_TYPE'),
    "project_id": os.getenv('FIREBASE_PROJECT_ID'),
    "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
    "private_key": os.getenv('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
    "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
    "client_id": os.getenv('FIREBASE_CLIENT_ID'),
    "auth_uri": os.getenv('FIREBASE_AUTH_URI'),
    "token_uri": os.getenv('FIREBASE_TOKEN_URI'),
    "auth_provider_x509_cert_url": os.getenv('FIREBASE_AUTH_PROVIDER_CERT_URL'),
    "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_CERT_URL'),
    "universe_domain": os.getenv('FIREBASE_UNIVERSE_DOMAIN')
}

cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred)

db = firestore.client()

def check_and_add_school_year(ano_escolar):
    """
    Verifica se o ano escolar já existe no Firestore.
    Se não existir, adiciona um novo ano escolar.

    Args:
        ano_escolar (str): Ano escolar a ser verificado.

    Returns:
        str: ID do documento do ano escolar.
    """
    ano_escolar_ref = db.collection('Ano_Escola').where('ano_escola', '==', ano_escolar).limit(1).get()
    if ano_escolar_ref:
        return ano_escolar_ref[0].id
    else:
        ano_escolar_data = {'ano_escola': ano_escolar, 'ano_atual': datetime.now().year}
        ano_escolar_doc = db.collection('Ano_Escola').add(ano_escolar_data)
        return ano_escolar_doc[1].id
    
def check_and_add_user(login, senha, ano_escolar_id, nome):
    """
    Verifica se o usuário já existe no Firestore. 
    Se não existir, adiciona um novo usuário.

    Args:
        login (str): Login do usuário.
        senha (str): Senha do usuário.
        ano_escolar_id (str): ID do ano escolar associado ao usuário.
        nome (str): Nome do usuário.

    Returns:
        bool: True se o usuário foi adicionado, False se já existia.
    """
    data = {'login': login, 'senha': senha, 'nome': nome}
    login = data['login']
    senha = data['senha']
    nome = data['nome']
    
    user_ref = db.collection('Usuario').document(login)
    user_doc = user_ref.get()
    if not user_doc.exists:
        user_data = {'id': login, 'senha': senha, 'ano_escola_id': ano_escolar_id, 'nome': nome}
        user_ref.set(user_data)
        return True
    return False

def save_to_firestore(login, materia_nome, boletim, titulo, peso, maximo, nota_valor, media_atual, ano_escolar_id, periodo, calculo, pequeno_nome):
    """
    Salva informações de notas e médias no Firestore.

    Args:
        login (str): Login do usuário.
        materia_nome (str): Nome da matéria.
        boletim (str): Identificação do boletim.
        titulo (str): Título do componente.
        peso (float): Peso do componente.
        maximo (float): Nota máxima do componente.
        nota_valor (float): Valor da nota obtida.
        media_atual (float): Média atual do usuário na matéria.
        ano_escolar_id (str): ID do ano escolar.
        periodo (str): Período da nota.
        calculo (str): Método de cálculo da nota.
        pequeno_nome (str): Nome curto do componente.
    """
    # Gerar ID único para a matéria
    materia_id = f"{ano_escolar_id}_{materia_nome}"

    # Adicionar/Verificar Matéria
    materia_ref = db.collection('Materia').document(materia_id)
    if not materia_ref.get().exists:
        materia_ref.set({'nome': materia_nome, 'ano_escola_id': ano_escolar_id, 'calculo': calculo})

    # Adicionar/Verificar Trimestre
    trimestre_ref = db.collection('Trimestre').document(boletim)
    if not trimestre_ref.get().exists:
        trimestre_ref.set({'descricao': boletim})

    # Adicionar/Verificar Componente
    componente_data = {
        'materia_id': materia_ref.id,
        'trimestre_id': trimestre_ref.id,
        'titulo': titulo,
        'pequeno_nome': pequeno_nome,
        'peso': peso,
        'maximo': maximo
    }
    componente_id = f'{materia_id}_{titulo}_{pequeno_nome}'
    componente_ref = db.collection('Componente_Materia').document(componente_id)
    if not componente_ref.get().exists:
        componente_ref.set(componente_data)

    # Adicionar Nota
    nota_data = {
        'usuario_id': login,
        'componente_materia_id': componente_ref.id,
        'nota': nota_valor,
        'periodo': periodo  # Adicionando o período à nota
    }
    nota_ref = db.collection('Nota').document(f'{login}_{componente_ref.id}_{periodo}')
    nota_ref.set(nota_data)

    # Adicionar Média Atual
    media_ref = db.collection('Media_Atual').document(f'{login}_{materia_id}_{boletim}')
    media_data = {
        'usuario_id': login,
        'materia_id': materia_ref.id,
        'trimestre_id': trimestre_ref.id,
        'media': convert_to_float(media_atual)
    }
    media_ref.set(media_data)

    # Adicionar/Verificar Calculo
    calculo_ref = db.collection('Calculo_Materia_Periodo').document(f'{materia_id}_{periodo}')
    if not calculo_ref.get().exists:
        calculo_ref.set({'materia_id': materia_ref.id, 'trimestre_id': trimestre_ref.id, 'calculo': calculo})

def get_ano_escola_id_usuario(login):
    """
    Obtém o ID do ano escolar e o nome associado ao login do usuário.

    Args:
        login (str): Login do usuário.

    Returns:
        tuple: ID do ano escolar e nome do usuário ou (None, None) se não encontrado.
    """
    data = {'login': login}
    login = data['login']
    
    try:
        user_ref = db.collection('Usuario').document(login)
        user_doc = user_ref.get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            ano_escola_id = user_data['ano_escola_id']
            nome = user_data.get('nome', 'Usuário')
            return ano_escola_id, nome
        else:
            return None, None
    except Exception as e:
        return None, None

def get_periodos_materias(ano_escola_id):
    """
    Obtém os períodos (trimestres) e matérias associados ao ano escolar.

    Args:
        ano_escola_id (str): ID do ano escolar.

    Returns:
        tuple: Dicionário de trimestres e dicionário de matérias.
    """
    try:
        trimestres_ref = db.collection('Trimestre').stream()
        trimestres = {doc.id: doc.to_dict()['descricao'] for doc in trimestres_ref}

        materias_ref = db.collection('Materia').where('ano_escola_id', '==', ano_escola_id).stream()
        materias = {doc.id: doc.to_dict()['nome'] for doc in materias_ref}

        calculos_ref = db.collection('Calculo_Materia_Periodo').stream()
        calculos = {doc.id: doc.to_dict() for doc in calculos_ref}

        return trimestres, materias, calculos
    except Exception as e:
        return None, None, None

def get_componentes_materia(materia_id):
    """
    Obtém os componentes de uma matéria específica.

    Args:
        materia_id (str): ID da matéria.

    Returns:
        dict: Dicionário de componentes da matéria.
    """
    try:
        componentes_ref = db.collection('Componente_Materia').where('materia_id', '==', materia_id).stream()
        componentes = {doc.id: doc.to_dict() for doc in componentes_ref}
        return componentes
    except Exception as e:
        return None

def get_medias_aluno(usuario_id):
    """
    Obtém as médias de um aluno específico.

    Args:
        usuario_id (str): ID do usuário.

    Returns:
        dict: Dicionário de médias do aluno, agrupadas por período e matéria.
    """
    data = {'usuario_id': usuario_id}
    usuario_id = data['usuario_id']

    try:
        medias_ref = db.collection('Media_Atual').where('usuario_id', '==', usuario_id).stream()
        medias = {}
        for doc in medias_ref:
            media_data = doc.to_dict()
            periodo = media_data.get('trimestre_id')
            materia = media_data.get('materia_id')
            if periodo not in medias:
                medias[periodo] = {}
            medias[periodo][materia] = media_data
        return medias
    except Exception as e:
        return None

def get_notas_aluno(usuario_id):
    """
    Obtém as notas de um aluno específico.

    Args:
        usuario_id (str): ID do usuário.

    Returns:
        dict: Dicionário de notas do aluno, agrupadas por período.
    """
    data = {'usuario_id': usuario_id}
    usuario_id = data['usuario_id']

    try:
        notas_ref = db.collection('Nota').where('usuario_id', '==', usuario_id).stream()
        notas = {}
        for doc in notas_ref:
            nota_data = doc.to_dict()
            periodo = nota_data.get('periodo')
            if periodo not in notas:
                notas[periodo] = []
            notas[periodo].append(nota_data)
        return notas
    except Exception as e:
        return None
