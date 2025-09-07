
from pathlib import Path
import logging
from src.middle_office.leitura_banco import controle_duplicidade

from src.middle_office import configuracao

logger = logging.getLogger(__file__)

def reiniciar_tabelas_de_controle(con = configuracao.CONEXAO_PADRAO):
    controle_duplicidade.__resetar_tabela_controle()
    logger.info("Dados apagados das tabelas de controle")

def apagar_csvs_gerados(pasta = 'outputs'):
    "'Apaga' os CSVs gerados, renomeando a pasta de output para `pasta`_backup"
    Path(pasta).rename(pasta+'_backup')
    logger.info("CVSs gerados movidos para a pasta de backup")



def reiniciar_todos_os_dados():
    reiniciar_tabelas_de_controle()
    apagar_csvs_gerados()

if __name__ == '__main__':
    configuracao.setup_logging()
    reiniciar_todos_os_dados()