import sqlite3
import os

import dotenv
import logging
from contextlib import contextmanager


dotenv.load_dotenv()

# Fator de precisão do banco (evitar imprecisão do float)
CASAS_DECIMAIS_PRECISAO = 1000000


# Configurações do banco
DB = "data/arx.db"

CONEXAO_PADRAO = sqlite3.connect(DB)

# Tratamento da variável de ambiente
# Para funcionar os testes em app.py, pode-se usar o with set_env
# para sobrescrever no código as variáveis de ambiente
# feito de maneira segura, via context manager
@contextmanager
def set_env(var, value):
    old_value = os.environ.get(var)
    os.environ[var] = value
    try:
        yield
    finally:
        # restora a variável de ambiente antiga
        if old_value is None:
            del os.environ[var]
        else:
            os.environ[var] = old_value

# Lê a variável de ambiente HORA_CORTE
# Retorna None se não estiver definida
def get_hora_corte():
    return os.getenv("HORA_CORTE")

# Configuração do logging
def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        handlers=[
            logging.StreamHandler(), 
            logging.FileHandler("logs/app.log"),
        ]
    )
