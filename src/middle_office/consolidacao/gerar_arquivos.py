import pandas as pd
import logging
from pathlib import Path
from typing import Optional

import uuid

from src.middle_office.leitura_banco import controle_duplicidade

logger = logging.getLogger(__name__)

# Funções de formatação puras

def _formatar_df_ativo(df_input: pd.DataFrame, data_processo: str) -> pd.DataFrame:
    ativo_df = df_input.copy()
    
    data_formatada_br = pd.to_datetime(data_processo).strftime('%d/%m/%Y')

    ativo_df['Data'] = data_formatada_br
    ativo_df['Tipo'] = ativo_df['tipo'].str.capitalize()
    ativo_df['Valor'] = ativo_df['valor'].map('{:.2f}'.format)
    
    ativo_final = ativo_df[['Data', 'Nome_Fundo_FIC', 'Nome_Fundo_Master', 'Tipo', 'Valor']]
    ativo_final = ativo_final.rename(columns={'Nome_Fundo_FIC': 'FIC', 'Nome_Fundo_Master': 'Master'})
    
    return ativo_final

def _formatar_df_passivo(df_input: pd.DataFrame, data_processo: str) -> pd.DataFrame:
    passivo_df = df_input.copy()
    data_formatada_us = pd.to_datetime(data_processo).strftime('%m/%d/%Y')

    passivo_df['DATE'] = data_formatada_us
    passivo_df['MOVIMENTO'] = passivo_df['tipo'].apply(lambda x: 'RecebeAplicacao' if x == 'Aplicacao' else 'RecebeResgate')
    passivo_df['VALOR'] = passivo_df['valor'].map('{:.6f}'.format)

    passivo_final = passivo_df[['VALOR', 'DATE', 'Nome_Fundo_Master', 'Nome_Fundo_FIC', 'MOVIMENTO']]
    passivo_final = passivo_final.rename(columns={'Nome_Fundo_Master': 'MASTER', 'Nome_Fundo_FIC': 'FIC'})

    return passivo_final

# Função principal de IO

def gerar_csvs_boletagem(consolidado_df: pd.DataFrame,
                        data_processo: str,
                        caminho_saida: str,
                        hora_corte: Optional[str] = None
                        ):
    """Gera os arquivos de saída Ativo (CSV) e Passivo (TSV)."""
    
    # Gerar um id único para colocar no nome do arquivo
    # Poderia ser a hora de execução do programa, porém 
    # violaria o requisito do programa não depender de estado global
    # além daqueles listados 
    # (Também não usei a hora de corte pois é possível o usuário
    # não fornecer, e gerar o CSV só do dia pode sobreescrever em horários diferentes)
    marcador_unico_csv = uuid.uuid4()

    if consolidado_df.empty:
        logger.warning("Nenhuma boleta nova para gerar.")
        return


    path_saida = Path(caminho_saida)
    path_saida.mkdir(exist_ok=True)

    modulo_variacao_movimentacao = consolidado_df['valor'].sum()

    # Inserindo na tabela de controle que o CSV deveria ter sido gerado
    controle_duplicidade.inserir_uiid_csv_controle(str(marcador_unico_csv),
                                                   data_processo,
                                                   modulo_variacao_movimentacao,
                                                   hora_corte
                                                   )

    # --- Arquivo Ativo ---
    ativo_final = _formatar_df_ativo(consolidado_df, data_processo)

    caminho_ativo = path_saida / f"boleta_ativo_{data_processo}_{marcador_unico_csv}.csv"
    ativo_final.to_csv(caminho_ativo, sep=';', index=False)
    logger.info(f"Arquivo Ativo gerado em: {caminho_ativo}")

    # --- Arquivo Passivo ---
    passivo_final = _formatar_df_passivo(consolidado_df, data_processo)

    caminho_passivo = path_saida / f"boleta_passivo_{data_processo}_{marcador_unico_csv}.tsv"
    passivo_final.to_csv(caminho_passivo, sep='\t', index=False)
    logger.info(f"Arquivo Passivo gerado em: {caminho_passivo}")