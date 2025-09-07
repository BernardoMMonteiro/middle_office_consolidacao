"""Reconciliação no final do dia: verificar se todas as boletas que deveriam ser geradas foram de
 fato geradas"""
from pathlib import Path
import pandas as pd
import glob
import sqlite3
import numpy as np
import logging

from src.middle_office import configuracao
from src.middle_office.leitura_banco import controle_duplicidade

from typing import List, Tuple, Dict

logger = logging.getLogger(__name__)

def _formatar_numero_df(df_input: pd.DataFrame,
                        coluna_valor: str,
                        fator_precisao: int = configuracao.CASAS_DECIMAIS_PRECISAO
                        ) -> pd.DataFrame:
    df = df_input.copy()
    df['valor_numerico'] = (
                            df[coluna_valor]
                            .astype(float)                      # converte pra número
                        )
    df['valor_numerico'] = (df["valor_numerico"]  * fator_precisao).astype("int64")
    
    return df

def pegar_valores_banco(dia: str,
                        con: sqlite3.Connection = configuracao.CONEXAO_PADRAO,
                        ) -> Tuple[int, int]:
    query_total_dia = """
        SELECT SUM(valor)
        FROM movements
        WHERE 
        date(datahora_mov) = ?;"""
        
    query_processados_dia = """
                        SELECT SUM(valor)
                        FROM movements
                        WHERE 
                        id_movimento IN (SELECT id_movimento 
                        FROM boletas_geradas WHERE data_geracao = ?);"""
    
    # Total do dia
    cursor = con.cursor()
    cursor.execute(query_total_dia, (dia,))
    soma_sql_float_dia = cursor.fetchone()[0]

    cursor.execute(query_processados_dia, (dia,))
    soma_sql_float_ids = cursor.fetchone()[0]

    # Converter para inteiro com a mesma precisão para uma comparação exata
    soma_sql_int_data = soma_sql_float_dia * configuracao.CASAS_DECIMAIS_PRECISAO
    soma_sql_int_id = soma_sql_float_ids * configuracao.CASAS_DECIMAIS_PRECISAO

    return soma_sql_int_data, soma_sql_int_id


def pegar_csvs_de_fato_gerados_do_dia(dia_reconciliar: str, 
                      pasta_csvs: str = 'outputs') -> List[str]:
    
    lista_csvs = glob.glob(str(Path(pasta_csvs) / f'boleta*{dia_reconciliar}*'))

    return lista_csvs

def ler_agregar_csvs_dia(arquivos: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:

    csvs_ativo = []
    csvs_passivo = []
    for caminho_csv in arquivos:
        if 'boleta_ativo' in caminho_csv:
            df = pd.read_csv(caminho_csv, delimiter=";", engine='python')
            df = _formatar_numero_df(df, 'Valor')
            csvs_ativo.append(df)
        elif 'boleta_passivo' in caminho_csv:
            df = pd.read_csv(caminho_csv, delimiter=r"\t", engine='python')
            df = _formatar_numero_df(df, 'VALOR')

            csvs_passivo.append(df)

    return pd.concat(csvs_ativo), pd.concat(csvs_passivo)


def reconciliar_csvs(dia_reconciliar: str,
                    con: sqlite3.Connection = configuracao.CONEXAO_PADRAO,
                    fator_precisao: int = configuracao.CASAS_DECIMAIS_PRECISAO
                    ) -> Dict[str, bool|float]:
    """Função orquestradora exemplo de reconciliação a rodar no final do dia.
    Atualmente checa:
        1. Número de CSVs gerados bate com número esperado
        2. Valor das movimentações bate entre ativo e passivo
        3. Se soma dos valores no BD batem entre o total do dia vs total via ids processados
        4. Se soma do BD do total do dia bate com CSV
        5. Se soma do BD do total do dia via id bate com CSV

    Numa versão final poderia checar:
    - contagem de IDs movimentos processados vs esperados
    - quebrar validações por tipo ou encaixar os sinais para dectectar erros de atribuição
    - checagem se há ainda ids movimentos a processar 
        (já é informado no log do app, mas seria interessante aqui também)
    - batimento com alguma fonte externa?

    """
    logger.info(f'--- Iniciando reconciliação para dia {dia_reconciliar} ---')
    

    # Obter estado ESPERADO do banco
    ids_csvs = controle_duplicidade.pegar_csvs_gerados(dia_reconciliar,
                                            con=con)
    # (multiplicando por 2 pois existem dois csvs por id, ativo e passivo)
    csvs_esperados = len(ids_csvs) * 2 

    soma_sql_int_data, soma_sql_int_id = pegar_valores_banco(dia_reconciliar,
                                                            con=con
                                                            )

    # Obter estado REAL do filesystem
    csvs_gerados = pegar_csvs_de_fato_gerados_do_dia(dia_reconciliar=dia_reconciliar)

    # Primeira checagem bruta; número de CSVs batem 
    numero_csvs_bate =  csvs_esperados == len(csvs_gerados)

    # Checagem dos valores entre os dois CSVs
    ativo, passivo = ler_agregar_csvs_dia(csvs_gerados)
    delta_ativo = ativo["valor_numerico"].sum() if not ativo.empty else 0
    delta_passivo = passivo["valor_numerico"].sum() if not passivo.empty else 0
    diff_deltas = (delta_ativo - delta_passivo) / fator_precisao
    # tolerância numérica devido ao arrendodamento que ocorre na hora de gerar os dados do ativo
    # (arrendonda de 6 casas decimais para 2)
    tolerancia = 1e-1  # diferença menor que 0,1 (10 centavo)

    valores_batem_entre_csvs = bool(abs(diff_deltas) < tolerancia)
    
    # A checagem mais importante: o valor nos CSVs bate com o valor que o DB diz que foi processado?
    # (pegando o dado do CSV passivo já que ele é mais preciso)
    diff_banco_csv  = soma_sql_int_data == delta_passivo
    tolerancia_banco = 1e-3 # diferença menor que 0,001 (0.1 centavo)

    valores_csv_banco_batem = bool(abs(diff_banco_csv) < tolerancia_banco)

    # Checagem todos os movimentos do dia foram processados via soma das movimentacoes
    todos_movimentos_processados = soma_sql_int_data == soma_sql_int_id

    return {
        "numero_csvs_bate": numero_csvs_bate,
        "csvs_esperados": csvs_esperados,
        "csvs_gerados": len(csvs_gerados),
        "soma_valor_csv_ativo": float(delta_ativo) / configuracao.CASAS_DECIMAIS_PRECISAO,
        "soma_valor_csv_passivo": float(delta_passivo) / configuracao.CASAS_DECIMAIS_PRECISAO,
        "diff_deltas_entre_csvs": diff_deltas,
        "valores_batem_entre_csv": valores_batem_entre_csvs,
        "valores_csv_vs_banco_batem": valores_csv_banco_batem,
        "soma_valor_processado_banco": float(soma_sql_int_id) / configuracao.CASAS_DECIMAIS_PRECISAO,
        "todos_movimentos_dia_processados": todos_movimentos_processados,
        "soma_valor_total_banco": float(soma_sql_int_data) / configuracao.CASAS_DECIMAIS_PRECISAO,
    }

def main():
    # Exemplo de execução de reconciliação

    configuracao.setup_logging()
    validacao = reconciliar_csvs('2025-08-29')

    # Exemplo do relatório, poderia ser melhorado
    logger.info("Resultado da validação da reconciliação:")
    logger.info(validacao)

    # Relatório 'automatizado' genérico
    algum_erro = False
    for chave, valor in validacao.items():
        if not valor:
            logger.warning(f"Erro genérico de reconciliação, checar outros logs ou o resultado bruto acima:"+
                           f" {chave}")
            algum_erro = True


    # Relatório de erros especificos
    if not validacao.get('numero_csvs_bate'):
        logger.warning("Número de CSVs esperado não b5ate com o gerado, verificar!")
        logger.warning(f'{validacao.get('csvs_esperados')=}')
        logger.warning(f'{validacao.get('csvs_gerados')=}')

    if not algum_erro:
        logger.info('Resultado passou em todos os testes de validação!')


if __name__ == '__main__':
    main()
