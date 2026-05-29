from extracao_infra import obter_infra_aguas_claras
from scraper_imoveis import scrape_aguas_claras
from geocodificacao import calcular_indices_reais
from modelagem import MotorUrbano
from mapa import gerar_mapa_aguas_claras

from automato import AutomatoPipeline
from modelagem_grafo import (
    PERFIS,
    normalizar_imoveis,
    normalizar_facilities,
    construir_grafo,
    rankear_por_perfil,
    calcular_centralidades,
)
from persistencia import persistir_tudo


def executar_projeto():

    print("Iniciando análise urbana")

    # O autômato (Teoria da Computação) valida a ordem das etapas do pipeline.
    # Cada etapa concluída emite um símbolo; ao final a palavra deve ser aceita.
    afd = AutomatoPipeline()

    print("Extraindo infraestrutura urbana")
    servicos_reais = obter_infra_aguas_claras()
    afd.transitar("c")

    print("Raspando anúncios")
    df_bruto = scrape_aguas_claras(num_imoveis=50)

    if df_bruto.empty:
        print("Nenhum imóvel encontrado. Verifique o scraper.")
        return

    afd.transitar("i")

    print("Geocodificando imóveis...")
    df_geo = calcular_indices_reais(df_bruto, servicos_reais)

    if df_geo.empty:
        print("Nenhum endereço geocodificado.")
        afd.transitar("x")
        return

    afd.transitar("g")

    # --- Modelagem em grafos (ponto central do trabalho) ---
    print("Construindo grafo imóvel-facility...")
    df_imoveis = normalizar_imoveis(df_geo)
    df_facilities = normalizar_facilities(servicos_reais)

    G = construir_grafo(df_imoveis, df_facilities)
    afd.transitar("b")

    print(f"Grafo: {G.number_of_nodes()} nós, {G.number_of_edges()} arestas")

    # persiste o modelo relacional completo (CSV + SQLite + dicionário de dados)
    persistir_tudo(df_bruto, df_facilities, G)

    print("Gerando rankings por perfil...")
    rankings = {}

    for perfil in PERFIS:
        rk = rankear_por_perfil(G, df_imoveis, perfil=perfil)
        rk.to_csv(f"ranking_{perfil}.csv")
        rankings[perfil] = rk
        print(f"  perfil '{perfil}': top imóvel = {rk.index[0]}")

    centralidades = calcular_centralidades(G, perfil="familia")
    centralidades.to_csv("centralidades.csv")

    afd.transitar("r")

    if afd.estado not in {"RANKING_GERADO"}:
        print(f"Pipeline inválido (estado {afd.estado}).")
        return

    # --- Índices clássicos + mapa (mantém a visualização existente) ---
    print("Calculando acessibilidade urbana...")
    motor = MotorUrbano()
    df_processado = motor.calcular_acessibilidade(df_geo, servicos_reais)
    df_final = motor.gerar_scores_finais(df_processado)

    print("Gerando mapa...")
    gerar_mapa_aguas_claras(df_final, servicos_reais)

    print("Projeto finalizado! (pipeline aceito pelo autômato)")


if __name__ == "__main__":
    executar_projeto()
