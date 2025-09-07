"""Reconciliação no final do dia: verificar se todas as boletas que deveriam ser geradas foram de
 fato geradas"""
from pathlib import Path
import pandas as pd
import glob
import sqlite3
import numpy as np

from src.middle_office import configuracao
from src.middle_office.leitura_banco import controle_duplicidade

from typing import List, Tuple, Dict

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

def pegar_csvs_de_fato_gerados_do_dia(dia_reconciliar: str, 
                      pasta_csvs: str = 'outputs') -> List[str]:
    
    lista_csvs = glob.glob(str(Path(pasta_csvs) / f'boleta*{dia_reconciliar}*'))

    return lista_csvs

def ler_agregar_csvs_dia(arquivos: List[str]) -> Tuple[pd.DataFrame, pd.DataFrame]:

    csvs_ativo = []
    csvs_passivo = []
    for caminho_csv in arquivos:
        if 'boleta_ativo' in caminho_csv:
            df = pd.read_csv(caminho_csv, delimiter=";")
            df = _formatar_numero_df(df, 'Valor')
            csvs_ativo.append(df)
        elif 'boleta_passivo' in caminho_csv:
            df = pd.read_csv(caminho_csv, delimiter=r"\t")
            df = _formatar_numero_df(df, 'VALOR')

            csvs_passivo.append(df)

    return pd.concat(csvs_ativo), pd.concat(csvs_passivo)


def verificar_se_csvs_foram_gerados(dia_reconciliar: str,
                                    con: sqlite3.Connection = configuracao.CONEXAO_PADRAO,
                                    fator_precisao: int = configuracao.CASAS_DECIMAIS_PRECISAO
                                    ) -> Dict[str, bool|float]:
    
    ids_csvs = controle_duplicidade.pegar_csvs_gerados(dia_reconciliar,
                                            con=con)
    
    csvs_gerados = pegar_csvs_de_fato_gerados_do_dia(dia_reconciliar=dia_reconciliar)

    # Primeira checagem bruta; número de CSVs batem
    numero_csvs_bate =  len(ids_csvs) == len(csvs_gerados)

    # Checagem dos valores
    ativo, passivo = ler_agregar_csvs_dia(csvs_gerados)
    delta_ativo = ativo["valor_numerico"].sum() if not ativo.empty else 0
    delta_passivo = passivo["valor_numerico"].sum() if not passivo.empty else 0
    diff_deltas = (delta_ativo - delta_passivo) / fator_precisao
    # tolerância numérica devido ao arrendodamento que ocorre na hora de gerar os dados do ativo
    # (arrendonda de 6 casas decimais para 2)
    tolerancia = 1e-2  # diferença menor que 0,01 (1 centavo)

    valores_batem = abs(diff_deltas) < tolerancia
    

    return {
        "numero_csvs_bate": numero_csvs_bate,
        "csvs_esperados": len(ids_csvs),
        "csvs_gerados": len(csvs_gerados),
        "delta_ativo": delta_ativo,
        "delta_passivo": delta_passivo,
        "diff_deltas": diff_deltas,
        "valores_batem": valores_batem,
    }


if __name__ == '__main__':
    validacao = verificar_se_csvs_foram_gerados('2025-08-29')
    print(validacao)