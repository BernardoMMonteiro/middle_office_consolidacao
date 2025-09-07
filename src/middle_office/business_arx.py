from __future__ import annotations
from typing import List, Tuple
import pandas as pd

from src.middle_office.configuracao import get_hora_corte
from src.middle_office.consolidacao.consolidar_movs import consolidar_movimentacoes, pegar_dados_brutos_do_dia
from src.middle_office.leitura_banco.controle_duplicidade import (pegar_ids_movimento_ja_processados_dia
                                                                  ,inserir_ids_movimentos_processados
                                                                  )
from src.middle_office.consolidacao.gerar_arquivos import gerar_csvs_boletagem

def _gerar_dados(data_processo: str,
                hora_corte: str) -> Tuple[pd.DataFrame, List[str]]:
    # Coleta dos dados brutos do dia
    df_bruto_dia = pegar_dados_brutos_do_dia(data_processo)
    ids_movimentacao_ja_processados_do_dia = pegar_ids_movimento_ja_processados_dia(data_processo)

    # Coração do projeto, chamar a função de consolidação, faz o IO do banco
    # e via pandas faz as agregações e mensagens de logging
    df_consolidado, mensagens = consolidar_movimentacoes(data_processo, df_bruto_dia,
                             ids_movimentacao_ja_processados_do_dia,
                             hora_corte
                             )
    
    return df_consolidado, mensagens

def processar_movimentacoes(data_processo: str) -> List[str]:
    hora_corte_ambiente = get_hora_corte()

    _, mensagens = _gerar_dados(data_processo, hora_corte_ambiente)
    
    return mensagens


def gerar_arquivos_boleta(data_processo: str, caminho_saida: str) -> None: 
    # Evitei mexer na assinatura das funções, mas se possível, 
    # iria fazer processar_movimentacoes retornar o dataframe e as mensagens,s
    # com esta função chamando processar_movimentacoes e rodando as funções adicionais
    # de IO no final, para evitar duplicação de código
    hora_corte_ambiente = get_hora_corte()

    df_consolidado, mensagens = _gerar_dados(data_processo, hora_corte_ambiente)

    if df_consolidado.empty:
        return
    
    # Funções de IO, gera os arquivos e insere no BD os ids processados, para evitar duplicidade
    gerar_csvs_boletagem(df_consolidado, data_processo, caminho_saida, hora_corte_ambiente)
    inserir_ids_movimentos_processados(df_consolidado, data_processo)
