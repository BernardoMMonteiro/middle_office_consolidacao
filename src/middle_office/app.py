import os
from datetime import datetime
import logging
from .business_arx import processar_movimentacoes, gerar_arquivos_boleta
from .configuracao import set_env, setup_logging, get_hora_corte

logger = logging.getLogger(__name__)

def rodar(datahora: str, gerar_arquivos: bool):
    setup_logging()    
    dt = datetime.fromisoformat(datahora)
    data = dt.strftime("%Y-%m-%d")
    hora = dt.strftime("%H:%M:%S")


    # sobrescrevendo a variável de ambiente em .env para testar
    # (somente fiz isso para não mudar muito a estrutura do app.py fornecido
    # e para permitir testar rapidamente datas diferentes, em produção o recomendado 
    # seria ser fornecida a data em um .env ou configurada automaticamente pelo Windows)
    with set_env('HORA_CORTE', hora):
        logger.info(f"\n\n=== Rodada (DATA={data}, HORA={get_hora_corte()}, gerar={gerar_arquivos}) ===")

        mensagens = processar_movimentacoes(data)
        for msg in mensagens:
            if 'ALERTA' in msg:
                logger.warning(msg)
            else:
                logger.info(msg)

        if gerar_arquivos:
            outdir = "outputs"
            gerar_arquivos_boleta(data, outdir)


def main():
    rodar("2025-08-29 11:30:34", False)
    rodar("2025-08-29 12:05:15", True)
    rodar("2025-08-29 13:47:07", True)
    rodar("2025-08-29 14:05:56", False)
    rodar("2025-08-29 14:55:18", True)


if __name__ == "__main__":
    main()
