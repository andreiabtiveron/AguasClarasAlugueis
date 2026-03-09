from extracao_infra import obter_infra_aguas_claras
from scraper_imoveis import scrape_aguas_claras
from geocodificacao import calcular_indices_reais
from modelagem import MotorUrbano
from mapa import gerar_mapa_aguas_claras


def executar_projeto():

    print("Iniciando análise urbana")

    print("Extraindo infraestrutura urbana")
    servicos_reais = obter_infra_aguas_claras()

    print("Raspando anúncios")
    df_bruto = scrape_aguas_claras(num_imoveis=50)

    if df_bruto.empty:
        print("Nenhum imóvel encontrado. Verifique o scraper.")
        return

    print("Geocodificando imóveis...")
    df_geo = calcular_indices_reais(df_bruto, servicos_reais)

    if df_geo.empty:
        print("Nenhum endereço geocodificado.")
        return

    print("Calculando acessibilidade urbana...")
    motor = MotorUrbano()

    df_processado = motor.calcular_acessibilidade(df_geo, servicos_reais)

    df_final = motor.gerar_scores_finais(df_processado)

    print("Gerando mapa...")
    gerar_mapa_aguas_claras(df_final, servicos_reais)

    print("Projeto finalizado!")


if __name__ == "__main__":
    executar_projeto()