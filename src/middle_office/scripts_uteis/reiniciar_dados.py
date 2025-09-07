
from pathlib import Path
import logging
from datetime import datetime
import sqlite3

from src.middle_office import configuracao

logger = logging.getLogger(__name__)

def __resetar_tabela_controle(con: sqlite3.Connection = configuracao.CONEXAO_PADRAO):
    """Função somente para dev, apaga os dados da tabela de controle"""
    cursor = con.cursor()
    cursor.execute("""
        DELETE FROM boletas_geradas 
    """)
    con.commit()
    logger.info("Dados da tabela de controle deletados!")

def __reiniciar_tabela_de_controle_csvs(con = configuracao.CONEXAO_PADRAO):
    """Função somente para dev, apaga os dados da tabela de controle de CSVs"""
    cursor = con.cursor()
    cursor.execute("""
        DELETE FROM controle_csvs 
    """)
    con.commit()
    logger.info("Dados apagados das tabelas de controle de CSV")

def apagar_csvs_gerados(pasta = 'outputs'):
    "'Apaga' os CSVs gerados, renomeando a pasta de output para `pasta`_backup_datahora"
    Path(pasta).rename(pasta+'_backup_'+datetime.now().strftime("%H%M%S"))
    logger.info("CVSs gerados movidos para a pasta de backup")

def reiniciar_todos_os_dados():
    __resetar_tabela_controle()
    __reiniciar_tabela_de_controle_csvs()
    apagar_csvs_gerados()

if __name__ == '__main__':
    configuracao.setup_logging()
    reiniciar_todos_os_dados()