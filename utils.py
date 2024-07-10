import re

def convert_to_float(value):
    """
    Converte um valor para float, substituindo vírgulas por pontos.

    Args:
        value (str): O valor a ser convertido.

    Returns:
        float: O valor convertido em float, ou None se ocorrer um erro.
    """
    try:
        return float(value.replace(',', '.'))
    except ValueError:
        return None
        
def capitalize_component_name(value):
    """
    Capitaliza a primeira letra de cada palavra em uma string, deixando as outras letras em minúsculo.

    Args:
        value (str): A string a ser capitalizada.

    Returns:
        str: A string com a primeira letra de cada palavra capitalizada.
    """
    if not isinstance(value, str):
        return value
    
    # Dividir a string em palavras e capitalizar cada uma
    words = re.findall(r'\b\w+\b', value)
    capitalized_words = [word.capitalize() for word in words]
    return ' '.join(capitalized_words)
