import sqlite3
#from configuracao import CONEXAO_PADRAO
import logging
import datetime
import pandas as pd
from typing import Optional, Tuple, List
from decimal import Decimal

from src.middle_office.configuracao import CONEXAO_PADRAO, CASAS_DECIMAIS_PRECISAO


# Função de IO do BD

def pegar_dados_brutos_do_dia(data: datetime.date,
                        con: sqlite3.Connection = CONEXAO_PADRAO
                        ) -> pd.DataFrame:
    # A query faz uma pré seleção dos dados brutos, já filtrando pela data
    # delegando os group bys e filtro por hora pro resto da aplicação
    query_select_dados_brutos = f"""select m.id_movimento, 
                                    m.tipo,
                                    m.valor,
                                    m.datahora_mov,
                                    l.fundo_name as 'Nome_Fundo_FIC',
                                    l2.fundo_name as 'Nome_Fundo_Master'
                                    from movements m
                                    left join fic_master_map f on m.fic_id = f.fic_id
                                    left join fundo l on l.id = m.fic_id
                                    left join fundo l2 on l2.id = f.master_id
                                    where date(datahora_mov) = ?;
                                    """    
    
    # Transformando para dataframe para sem mais conveniente trabalhar
    df = pd.read_sql_query(query_select_dados_brutos,
                             con=con,
                             params=(data,)
                             )
    
    # Evitar imprecisão do float, fazer contas com o valor de 6 casas decimais, como inteiro e depois dividir de volta
    df["valor_inteiro"] = (df["valor"].astype(str).map(Decimal) * CASAS_DECIMAIS_PRECISAO).astype("int64")

    return df

# Funções puras de transformação do DataFrame

def _filtar_dados(data_processo: str,
                df_input: pd.DataFrame,
                ids_movimento_ja_processados_dia: Tuple[int],
                hora_corte: Optional[str] = None
                 ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    movimentos_dia = df_input.copy()

    movimentos_dia['datahora_mov'] = pd.to_datetime(movimentos_dia['datahora_mov'])

    # Filtra movimentos já processados para evitar duplicidade
    movs_nao_processados = movimentos_dia[~movimentos_dia['id_movimento'].isin(ids_movimento_ja_processados_dia)]

    # Filtra pela HORA_CORTE, se existir
    hora_corte_usada = hora_corte if hora_corte else "23:59:59"
    corte_datetime = pd.to_datetime(f"{data_processo} {hora_corte_usada}")

    movs_para_processar = movs_nao_processados[movs_nao_processados['datahora_mov'] <= corte_datetime]

    # Verifica se ainda há movimentos a serem processados depois do corte
    movs_pendentes = movs_nao_processados[movs_nao_processados['datahora_mov'] > corte_datetime]

    return movs_para_processar, movs_pendentes

def _consolidar_movimentacoes(movs_para_processar: pd.DataFrame) -> pd.DataFrame:
    if movs_para_processar.empty:
        consolidado = pd.DataFrame()
    else:
        consolidado = movs_para_processar.groupby(
            # Relação FIC para Master é N:1, ou seja, 
            # cada FIC pertence a um único Master,
            # embora um Master possa ter muitos FICs, 
            # portanto pode ser feito o group by assim sem temer duplicidade
            ['Nome_Fundo_FIC', 'Nome_Fundo_Master', 'tipo']
        ).agg(
            valor_inteiro=('valor_inteiro', 'sum'), # usando valor em centavos (int) para evitar imprecisao
            # Guarda os IDs para logar na tabela de controle
            id_movimento=('id_movimento', lambda x: tuple(x))
        ).reset_index()   

        # converte novamente para o valor esperado pelo resto do processo
        consolidado["valor"] = consolidado["valor_inteiro"] / CASAS_DECIMAIS_PRECISAO 


    return consolidado

# Função pura principal de orquestração da consolidação dos movimentos

def consolidar_movimentacoes(data_processo: str,
                            df_bruto_dia: pd.DataFrame,
                            ids_movimento_ja_processados_dia: Tuple[int],
                            hora_corte: Optional[str] = None
                            ) -> Tuple[pd.DataFrame, List[str]]:
    movimentos_dia = df_bruto_dia.copy()

    # Filtragem
    movs_para_processar, movs_pendentes = _filtar_dados(data_processo,
                                                        movimentos_dia,
                                                       ids_movimento_ja_processados_dia,
                                                       hora_corte
                                                       )

    # Consolidação
    consolidado = _consolidar_movimentacoes(movs_para_processar)

    # Geração das Mensagens de log
    mensagens = []
    mensagem_hora_corte = f"com corte às {hora_corte}" if hora_corte else "sem hora de corte definida, pegando do dia inteiro"
    mensagens.append(f"--- Processamento para {data_processo} {mensagem_hora_corte}---")
    
    mensagens.append(f"Movimentos lidos totais no dia: {len(movimentos_dia)}")
    mensagens.append(f"Movimentos do dia já processados anteriormente: {len(ids_movimento_ja_processados_dia)}")
    mensagens.append(f"Novos movimentos a processar nesta janela: {len(movs_para_processar)}")
    
    if consolidado.empty:
        mensagens.append("Sem dados consolidados nesta janela")

    else:
        total_aplicacao = consolidado.loc[consolidado['tipo'] == 'Aplicacao', 'valor'].sum()
        total_resgate = consolidado.loc[consolidado['tipo'] == 'Resgate', 'valor'].sum()
        
        mensagens.append(f"Total consolidado (Aplicação): {total_aplicacao:,.2f}")
        mensagens.append(f"Total consolidado (Resgate): {total_resgate:,.2f}")

    if not movs_pendentes.empty:
        mensagens.append(f"ALERTA: Existem {len(movs_pendentes)} movimentos após a hora de corte que AINDA devem ser processados em uma próxima janela.")
    else:
        mensagens.append("Todos os movimentos do dia foram incluídos neste processamento.")


    return consolidado, mensagens
