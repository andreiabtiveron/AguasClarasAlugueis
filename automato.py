"""
Modelagem formal por Autômato Finito Determinístico (AFD)
=========================================================

Este módulo formaliza, do ponto de vista de Teoria da Computação, o processo
de recomendação imobiliária orientada à qualidade de vida proposto no trabalho.

A orientação do trabalho exige que a análise do problema parta de um modelo de
autômato finito. Aqui modelamos o *pipeline de decisão imobiliária* como uma
linguagem formal: cada execução válida do sistema é uma palavra reconhecida por
um AFD. Sequências fora de ordem (ex.: rankear antes de construir o grafo) ou
dados inválidos levam a um estado de erro (estado-armadilha), de onde não há
retorno e a palavra é rejeitada.

Definição formal do autômato
----------------------------
Um AFD é uma 5-tupla  M = (Q, Sigma, delta, q0, F).

Q (estados):
    q0  INICIO            - nenhum dado coletado
    q1  INFRA_COLETADA    - facilities urbanas extraídas
    q2  IMOVEIS_COLETADOS - anúncios de imóveis coletados
    q3  GEOCODIFICADO     - imóveis e facilities com coordenadas válidas
    q4  GRAFO_CONSTRUIDO  - grafo imóvel-facility com pesos calculados
    q5  RANKING_GERADO    - ranking/recomendação produzido (estado de aceitação)
    qE  ERRO              - estado-armadilha (dado inválido ou ordem incorreta)

Sigma (alfabeto) - eventos atômicos do processo:
    'c' - coletar infraestrutura urbana (facilities)
    'i' - coletar imóveis
    'g' - geocodificar / validar coordenadas
    'b' - construir grafo e calcular pesos relacionais
    'r' - gerar ranking / recomendação
    'x' - evento de erro (dado inválido, falha de coleta)

q0 (estado inicial): INICIO
F  (estados de aceitação): { RANKING_GERADO }

Linguagem reconhecida
---------------------
    L(M) = { c i g b r }

isto é, a única palavra aceita corresponde à execução completa e em ordem do
pipeline: coletar infra -> coletar imóveis -> geocodificar -> construir grafo ->
gerar ranking. Qualquer prefixo é um processo incompleto (não aceito); qualquer
desvio cai em qE (rejeição). Trata-se de uma linguagem finita e, portanto,
regular - adequada a um AFD.

Formalização dos critérios computacionais
-----------------------------------------
Seja I o conjunto de imóveis e F o conjunto de facilities. Define-se a função
de pontuação (eq. 2 da orientação):

    score(i) = alpha*E(i) + beta*S(i) + gamma*H(i) + delta*L(i) - lambda*C(i)

onde E, S, H, L são, respectivamente, acesso a educação, saúde,
comércio/serviços e lazer; e C é o custo de moradia. Os pesos
(alpha, beta, gamma, delta, lambda) dependem do perfil-alvo (ver perfis em
modelagem_grafo.py). A obtenção de E, S, H, L vem da modelagem em grafo
(acessibilidade gravitacional por categoria).
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Definição simbólica do autômato
# ---------------------------------------------------------------------------

ESTADOS = {
    "INICIO": "q0",
    "INFRA_COLETADA": "q1",
    "IMOVEIS_COLETADOS": "q2",
    "GEOCODIFICADO": "q3",
    "GRAFO_CONSTRUIDO": "q4",
    "RANKING_GERADO": "q5",
    "ERRO": "qE",
}

ALFABETO = {"c", "i", "g", "b", "r", "x"}

ESTADO_INICIAL = "INICIO"

ESTADOS_ACEITACAO = {"RANKING_GERADO"}

# Função de transição delta: (estado, símbolo) -> estado.
# Transições não listadas levam implicitamente ao estado ERRO (armadilha).
TRANSICOES = {
    ("INICIO", "c"): "INFRA_COLETADA",
    ("INFRA_COLETADA", "i"): "IMOVEIS_COLETADOS",
    ("IMOVEIS_COLETADOS", "g"): "GEOCODIFICADO",
    ("GEOCODIFICADO", "b"): "GRAFO_CONSTRUIDO",
    ("GRAFO_CONSTRUIDO", "r"): "RANKING_GERADO",
}


@dataclass
class AutomatoPipeline:
    """AFD que reconhece execuções válidas do pipeline de recomendação."""

    estado: str = ESTADO_INICIAL
    historico: list = field(default_factory=list)

    def transitar(self, simbolo):
        """Aplica delta(estado, simbolo) e retorna o novo estado."""

        if simbolo not in ALFABETO:
            raise ValueError(f"Símbolo '{simbolo}' fora do alfabeto {ALFABETO}")

        # Estado ERRO é armadilha: permanece em ERRO.
        if self.estado == "ERRO":
            self.historico.append((simbolo, "ERRO"))
            return "ERRO"

        novo = TRANSICOES.get((self.estado, simbolo), "ERRO")

        self.historico.append((simbolo, novo))

        self.estado = novo

        return novo

    def aceita(self, palavra):
        """Retorna True se a palavra pertence a L(M)."""

        self.resetar()

        for simbolo in palavra:
            self.transitar(simbolo)

        return self.estado in ESTADOS_ACEITACAO

    def resetar(self):
        self.estado = ESTADO_INICIAL
        self.historico = []


def tabela_transicoes():
    """Devolve a tabela de transição como lista de tuplas (origem, símbolo, destino).

    Inclui explicitamente as transições para o estado ERRO, útil para
    documentação e geração de figuras no artigo.
    """

    linhas = []

    for origem in ESTADOS:

        if origem == "ERRO":
            continue

        for simbolo in sorted(ALFABETO):

            destino = TRANSICOES.get((origem, simbolo), "ERRO")

            linhas.append((origem, simbolo, destino))

    return linhas


def imprimir_tabela():
    """Imprime a tabela de transição em formato legível (para o artigo)."""

    print(f"{'ESTADO':<20} {'SÍMBOLO':<10} {'DESTINO'}")
    print("-" * 45)

    for origem, simbolo, destino in tabela_transicoes():
        print(f"{origem:<20} {simbolo:<10} {destino}")


# ---------------------------------------------------------------------------
# Formalização dos critérios computacionais (eq. 2 da orientação)
# ---------------------------------------------------------------------------

def score_formal(E, S, H, L, C, pesos):
    """Calcula score(i) = a*E + b*S + g*H + d*L - lmbda*C.

    Parâmetros
    ----------
    E, S, H, L : acesso a educação, saúde, comércio/serviços e lazer (>= 0).
    C          : custo de moradia normalizado (>= 0).
    pesos      : dict com chaves 'alpha', 'beta', 'gamma', 'delta', 'lambda'.
    """

    return (
        pesos["alpha"] * E
        + pesos["beta"] * S
        + pesos["gamma"] * H
        + pesos["delta"] * L
        - pesos["lambda"] * C
    )


if __name__ == "__main__":

    print("=== Autômato Finito do Pipeline de Recomendação ===\n")
    print(f"Q       = {set(ESTADOS)}")
    print(f"Sigma   = {ALFABETO}")
    print(f"q0      = {ESTADO_INICIAL}")
    print(f"F       = {ESTADOS_ACEITACAO}\n")

    imprimir_tabela()

    print("\n=== Teste de reconhecimento de palavras ===\n")

    casos = [
        "cigbr",   # execução completa e em ordem -> ACEITA
        "cig",     # processo incompleto -> rejeita
        "cibgr",   # ordem trocada (grafo antes de geocodificar) -> rejeita
        "cigbx",   # erro no fim -> rejeita
        "rcigb",   # rankear primeiro -> rejeita
    ]

    afd = AutomatoPipeline()

    for palavra in casos:

        resultado = "ACEITA" if afd.aceita(palavra) else "rejeita"

        print(f"  '{palavra:<6}' -> estado final {afd.estado:<18} [{resultado}]")
