"""
Gera o diagrama de estados do Autômato Finito Determinístico (AFD)
==================================================================

Produz a figura 'diagrama_automato.png' usada na seção de Modelagem formal do
artigo. Desenha a cadeia principal de transições válidas
(q0 -> q1 -> q2 -> q3 -> q4 -> q5) e o estado-armadilha qE, alimentado por
qualquer símbolo inesperado.

Execução:  ./venv/bin/python diagrama_automato.py
"""

import matplotlib
matplotlib.use("Agg")  # backend sem display

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch


# estados da cadeia principal: (rótulo, descrição curta)
CADEIA = [
    ("q0", "INÍCIO"),
    ("q1", "INFRA"),
    ("q2", "IMÓVEIS"),
    ("q3", "GEO"),
    ("q4", "GRAFO"),
    ("q5", "RANKING"),
]

# símbolos que rotulam as transições da cadeia
SIMBOLOS = ["c", "i", "g", "b", "r"]


def gerar(caminho="diagrama_automato.png"):

    fig, ax = plt.subplots(figsize=(12, 4.2))
    ax.set_xlim(-0.6, 11.6)
    ax.set_ylim(-2.2, 1.6)
    ax.axis("off")

    raio = 0.42
    xs = [i * 2.2 for i in range(len(CADEIA))]
    y = 0.0

    pos = {}

    # --- desenha estados da cadeia ---
    for (rotulo, desc), x in zip(CADEIA, xs):
        pos[rotulo] = (x, y)
        ax.add_patch(Circle((x, y), raio, fill=True, facecolor="#eef3fb",
                            edgecolor="#1f4e79", linewidth=1.8, zorder=3))
        # estado de aceitação q5: círculo duplo
        if rotulo == "q5":
            ax.add_patch(Circle((x, y), raio - 0.08, fill=False,
                                edgecolor="#1f4e79", linewidth=1.4, zorder=4))
        ax.text(x, y, rotulo, ha="center", va="center", fontsize=12,
                fontweight="bold", color="#1f4e79", zorder=5)
        ax.text(x, y - raio - 0.22, desc, ha="center", va="top", fontsize=8,
                color="#333333")

    # --- seta de início (entrando em q0) ---
    ax.add_patch(FancyArrowPatch((xs[0] - 1.0, y), (xs[0] - raio, y),
                                 arrowstyle="-|>", mutation_scale=16,
                                 color="black", linewidth=1.4))
    ax.text(xs[0] - 1.05, y + 0.18, "início", ha="center", fontsize=9)

    # --- transições da cadeia ---
    for i in range(len(CADEIA) - 1):
        x0, x1 = xs[i] + raio, xs[i + 1] - raio
        ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>",
                                     mutation_scale=16, color="#1f4e79",
                                     linewidth=1.6))
        ax.text((x0 + x1) / 2, y + 0.2, SIMBOLOS[i], ha="center",
                fontsize=12, fontweight="bold", color="#b00020")

    # --- estado de erro (armadilha) ---
    xe, ye = xs[2], -1.6
    pos["qE"] = (xe, ye)
    ax.add_patch(Circle((xe, ye), raio, fill=True, facecolor="#fdeaea",
                        edgecolor="#b00020", linewidth=1.8, zorder=3))
    ax.text(xe, ye, "qE", ha="center", va="center", fontsize=12,
            fontweight="bold", color="#b00020", zorder=5)
    ax.text(xe, ye - raio - 0.22, "ERRO (armadilha)", ha="center", va="top",
            fontsize=8, color="#333333")

    # transições representativas para qE (símbolo inesperado / x)
    for rotulo in ["q0", "q1", "q3", "q5"]:
        x0, y0 = pos[rotulo]
        ax.add_patch(FancyArrowPatch((x0, y0 - raio), (xe, ye + raio),
                                     arrowstyle="-|>", mutation_scale=12,
                                     color="#b00020", linewidth=0.9,
                                     linestyle=(0, (4, 3)),
                                     connectionstyle="arc3,rad=0.12"))
    ax.text(xe + 1.4, ye + 0.35, "x / símbolo inesperado",
            ha="left", va="center", fontsize=8, color="#b00020", style="italic")

    # auto-laço em qE
    ax.add_patch(FancyArrowPatch((xe - 0.18, ye + raio), (xe + 0.18, ye + raio),
                                 arrowstyle="-|>", mutation_scale=10,
                                 color="#b00020", linewidth=0.9,
                                 connectionstyle="arc3,rad=-2.2"))

    ax.set_title("Autômato Finito Determinístico do pipeline de recomendação\n"
                 "L(M) = { c i g b r }   —   estado de aceitação: q5",
                 fontsize=11)

    fig.tight_layout()
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)

    return caminho


if __name__ == "__main__":
    print("Diagrama salvo em:", gerar())
