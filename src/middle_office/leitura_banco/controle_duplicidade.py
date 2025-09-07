
import sqlite3
import pandas as pd
from typing import Tuple, Optional
import logging
import datetime



from src.middle_office import configuracao

logger = logging.getLogger(__file__)

def __resetar_tabela_controle(con: sqlite3.Connection = configuracao.CONEXAO_PADRAO):
    """Função somente para dev, apaga os dados da tabela de controle"""
    cursor = con.cursor()
    cursor.execute("""
        DELETE FROM boletas_geradas 
    """)
    con.commit()
    logger.debug("Dados da tabela de controle deletados!")


def criar_tabela_controle(con: sqlite3.Connection = configuracao.CONEXAO_PADRAO):
    """Cria a tabela de controle de duplicidade se ela não existir."""
    cursor = con.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS boletas_geradas (
            id_movimento INTEGER NOT NULL,
            data_geracao date NOT NULL,
            PRIMARY KEY (id_movimento, data_geracao)
        )
    """)
    con.commit()
    logger.debug("Tabela de controle criada")

def criar_tabela_controle_csvs(con: sqlite3.Connection = configuracao.CONEXAO_PADRAO):
    cursor = con.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS controle_csvs(
            uiid_csv TEXT  NOT NULL,
            data_processo date NOT NULL,
            modulo_variacao_movimentacao REAL NULL,
            hora_corte TEXT NULL,
            PRIMARY KEY (uiid_csv, data_processo)
        )
    """)
    con.commit()
    logger.debug("Tabela de controle de CSVs criada")

def inserir_ids_movimentos_processados(df_consolidado: pd.DataFrame,
                                       data_processo: str,
                                        con: sqlite3.Connection = configuracao.CONEXAO_PADRAO
                                       ) -> None:
    """
    Grava os IDs dos movimentos já processados na tabela de controle para evitar duplicidade.
    """

    # Usando or ignore para não dar erros de PK, já que o proposito da tabela é 
    # de consultar nela IDs já processados, se por acaso um ID já existente for 
    # inserido nela, não é necessário dar erro aqui 
    insert_ids = "insert OR IGNORE into  boletas_geradas (id_movimento, data_geracao) VALUES (?, ?);"

    if df_consolidado.empty:
        logger.warning("Sem ids movimentacao a inserir")
        return
    
    # Transformando as colunas de id movimento do df_consolidado em uma lista de ids sem duplicata
    lista_ids_movimentos_df = df_consolidado['id_movimento'].to_list()
    
    ids_movimento = tuple(set(id_mov for tupla in lista_ids_movimentos_df for id_mov in tupla))

    params = [(id_mov, data_processo) for id_mov in ids_movimento]


    con.executemany(insert_ids, params)
    con.commit()
    logger.debug(f"{len(ids_movimento)} ids movimentos inseridos para a data {data_processo}")

def inserir_uiid_csv_controle(
                              uuid: str,
                              data_processo: str,
                              modulo_variacao_movimentacao: float,
                              hora_corte: Optional[str] = None ,
                              con: sqlite3.Connection = configuracao.CONEXAO_PADRAO,
                              ):
    """
    Grava o ID do CSV dos movimentos já processados na tabela de controle para reconciliação.
    """    
    criar_tabela_controle_csvs(con)
    insert = """insert into  controle_csvs 
    (uiid_csv, data_processo, modulo_variacao_movimentacao, hora_corte) 
    VALUES (?, ?, ?, ?);"""

    
    con.execute(insert, (uuid, data_processo, modulo_variacao_movimentacao, hora_corte))
    con.commit()



def pegar_ids_movimento_ja_processados_dia(data_processo: str,
                                           con: sqlite3.Connection = configuracao.CONEXAO_PADRAO
                                           ) -> Tuple[int]:
    """Busca os IDs dos movimentos que já foram incluídos em boletas no dia."""
    query = "SELECT id_movimento FROM boletas_geradas WHERE date(data_geracao) = ?"
    # Certificando que tabela de controle existe
    criar_tabela_controle(con=con)
    processed_df = pd.read_sql_query(query, con, params=(data_processo,))
    return tuple(processed_df['id_movimento'].tolist())

def pegar_csvs_gerados(data_processo: str,
                       con: sqlite3.Connection = configuracao.CONEXAO_PADRAO
                       ) -> Tuple[str]:
    """Busca os IDs dos CSVs que já foram boletados."""
    query = "SELECT uiid_csv FROM controle_csvs WHERE date(data_processo) = ?"
    criar_tabela_controle_csvs(con=con)

    processed_df = pd.read_sql_query(query, con, params=(data_processo,))
    return tuple(processed_df['uiid_csv'].tolist())
