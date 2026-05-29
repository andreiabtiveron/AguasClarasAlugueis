# PropTech Águas Claras — Recomendação Imobiliária Orientada à Qualidade de Vida

Modelo computacional de apoio à decisão imobiliária para **Águas Claras/DF**, que
recomenda imóveis com base em critérios objetivos de **qualidade de vida**. O
projeto articula três pilares:

1. **Teoria da Computação** — o pipeline de recomendação é formalizado como um
   **autômato finito determinístico (AFD)**;
2. **Modelo relacional** — imóveis e *facilities* urbanas estruturados em tabelas
   (CSV + banco SQLite) com integridade referencial;
3. **Teoria dos grafos** — imóveis e serviços modelados como um grafo bipartido,
   analisado por **escore multicritério por perfil** e **PageRank**.

O resultado é um **ranking de imóveis por perfil de morador** e um **mapa
interativo** das facilities.

> **Nota sobre os dados:** as facilities são coletadas do OpenStreetMap; os
> imóveis ainda são **simulados** (`scraper_imoveis.py`). A substituição por
> coleta real (web scraping) é o próximo passo previsto.

---

## Arquitetura e fluxo

```
extracao_infra.py   ──┐  (facilities do OpenStreetMap)
scraper_imoveis.py  ──┤  (imóveis — simulados por ora)
                      ▼
geocodificacao.py     │  distâncias imóvel × serviço
modelagem_grafo.py    │  grafo + pesos w(i,f)=1/(1+d) + perfis + PageRank
persistencia.py       │  tabelas relacionais (CSV + SQLite) + dicionário + limpeza
automato.py           │  AFD que valida a ordem das etapas do pipeline
mapa.py               │  mapa interativo (Folium)
                      ▼
main.py               =  orquestra todo o pipeline
gerar_artigo.py       =  gera o artigo acadêmico (.docx) com resultados reais
diagrama_automato.py  =  gera o diagrama de estados do AFD (figura do artigo)
```

O **autômato** (`automato.py`) reconhece a linguagem `L(M) = { c i g b r }`:
coletar infra → coletar imóveis → geocodificar → construir grafo → gerar ranking.
Qualquer ordem inválida cai no estado-armadilha `qE`, garantindo que o sistema
nunca entregue um ranking sem cumprir todas as etapas.

---

## Modelos formais

### Peso da aresta (função inversa da distância)

```
w(i, f) = 1 / (1 + d(i, f))
```

onde `d(i, f)` é a distância (Haversine) entre o imóvel `i` e a facility `f`.
Uma aresta só é criada quando `d < limiar` (padrão: 1500 m).

### Escore multicritério por perfil

```
score(i) = α·E(i) + β·S(i) + γ·H(i) + δ·L(i) − λ·C(i)
```

`E, S, H, L` são as acessibilidades a educação, saúde, comércio/serviços e lazer;
`C` é o custo de moradia (penalização). Os pesos dependem do **perfil-alvo**
(família, idoso, estudante, jovem profissional), definidos em `modelagem_grafo.PERFIS`.

---

## Modelo relacional

Quatro tabelas, exportadas em **CSV** e em banco **SQLite** (`aguas_claras.db`)
com chaves primárias e estrangeiras:

| Tabela | Chave | Conteúdo |
| --- | --- | --- |
| `imovel` | `id_imovel` | tipo, finalidade, preço, área, quartos, banheiros, vagas, condomínio, geolocalização, fonte |
| `facility` | `id_facility` | nome, categoria (FK), endereço, geolocalização |
| `categoria_facility` | `id_categoria` | nome da categoria |
| `proximidade` | (`id_imovel`, `id_facility`) | distância, tempo estimado, peso relacional |

A limpeza aplica 7 regras (chave nula, duplicatas, tipos, domínio, coordenadas,
texto, integridade referencial). O **dicionário de dados** é gerado em
`dicionario_dados.csv` / `.md`.

---

## Instalação

```bash
python -m venv venv
source venv/bin/activate          # bash/zsh
# fish: source venv/bin/activate.fish
pip install -r requirements.txt
```

---

## Execução

### Pipeline completo (coleta real de facilities + mapa)

```bash
python main.py
```

Gera os CSVs, o banco `aguas_claras.db`, os rankings por perfil
(`ranking_<perfil>.csv`), as centralidades e o mapa `mapa_qualidade_vida_ac.html`.

### Componentes isolados (sem dependências pesadas)

```bash
python automato.py          # demonstra o AFD e a tabela de transição
python modelagem_grafo.py   # grafo, ranking por perfil e PageRank (dados sintéticos)
python persistencia.py      # tabelas relacionais + SQLite (dados sintéticos)
python diagrama_automato.py # diagrama de estados do autômato (PNG)
python gerar_artigo.py      # gera o artigo .docx com resultados reais
```

---

## Artigo

`gerar_artigo.py` produz **`Artigo_QualidadeVida_AguasClaras.docx`** com as nove
seções exigidas (Introdução, Fundamentação teórica, Modelagem formal, Metodologia,
Resultados, Discussão, Conclusão, Referências, Bibliografia), fórmulas, o diagrama
do autômato e a seção de **Resultados alimentada por números reais** da execução
do pipeline — garantindo reprodutibilidade e consistência entre artigo e código.

---

## Tecnologias

Python · OSMnx · GeoPandas · NetworkX · SciPy · Folium · NumPy · Pandas ·
SQLite · python-docx · Matplotlib

---

## Área de estudo

Região administrativa de **Águas Claras — Brasília (DF)**, escolhida por sua alta
densidade urbana, verticalização recente e forte presença de infraestrutura e
mobilidade (metrô), o que a torna ideal para análise de acessibilidade.
