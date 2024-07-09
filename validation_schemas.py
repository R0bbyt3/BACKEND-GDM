from marshmallow import Schema, fields, validate, ValidationError
from utils import strip_whitespace

class UserSchema(Schema):
    """
    Esquema de validação para os dados do usuário.
    
    Campos:
        login: Campo obrigatório que deve ser um número de 8 dígitos.
        senha: Campo obrigatório que deve ter entre 6 e 25 caracteres.
    """
    login = fields.Str(
        required=True,
        validate=validate.Regexp(r'^\d{8}$', error="Usuário deve ser um número com 8 caracteres")
    )
    senha = fields.Str(
        required=True,
        validate=validate.Length(min=6, max=25, error="Senha deve ter entre 6 e 25 caracteres")
    )

def validate_input(data, schema):
    """
    Valida os dados de entrada usando um esquema fornecido.

    Args:
        data (dict): Os dados a serem validados.
        schema (Schema): O esquema do marshmallow a ser usado para validação.

    Returns:
        None se os dados forem válidos.
        dict com mensagens de erro se os dados forem inválidos.
    """
    # Remove espaços em branco dos campos 'login' e 'senha'
    data = strip_whitespace(data, ['login', 'senha'])
    
    try:
        # Carrega e valida os dados usando o esquema fornecido
        schema().load(data)
        return None
    except ValidationError as err:
        # Retorna as mensagens de erro se a validação falhar
        return err.messages
