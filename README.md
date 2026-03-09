# Imóveis e Infraestrutura Urbana para Qualidade de Vida — Águas Claras (DF)

Projeto em Python para análise de **qualidade de vida urbana aplicada ao mercado imobiliário**, utilizando dados de infraestrutura urbana do OpenStreetMap e um modelo de acessibilidade espacial.

O sistema calcula índices de **atratividade residencial** para imóveis na região de Águas Claras (Brasília – DF) com base na proximidade a serviços urbanos essenciais.

O resultado final é um **mapa interativo** que permite visualizar imóveis e infraestrutura urbana simultaneamente.

---

# Objetivo

Avaliar **a qualidade de vida associada a imóveis urbanos** considerando a proximidade a serviços essenciais, como:

* hospitais
* escolas
* parques
* farmácias

A hipótese central é que **quanto maior a acessibilidade a serviços urbanos, maior a qualidade de vida associada ao imóvel**.

---

# Modelo de Análise

O projeto utiliza dois modelos principais.

## Modelo de Acessibilidade Gravitacional

A acessibilidade é calculada com base na distância entre imóveis e serviços urbanos.

[
A = \frac{1}{(d + \epsilon)^\beta}
]

Onde:

* **d** = distância entre imóvel e serviço
* **β** = coeficiente de decaimento espacial (1.5 no projeto)
* **ε** = constante pequena para evitar divisão por zero

Esse modelo assume que **serviços mais próximos têm maior influência na qualidade urbana**.

---

## Índice de Qualidade de Vida (Cobb-Douglas)

Após calcular a acessibilidade por categoria de serviço, o sistema gera o índice final de qualidade de vida:

[
QV =
hospital^{0.4}
\cdot
school^{0.3}
\cdot
park^{0.2}
\cdot
pharmacy^{0.1}
]

Os pesos representam a importância relativa de cada serviço urbano.

Também é calculado um segundo indicador:

**IAR — Índice de Atratividade Residencial**

[
IAR =
0.4 \cdot hospital +
0.3 \cdot school +
0.2 \cdot park +
0.1 \cdot pharmacy
]

---

# Estrutura do Projeto

```
AguasClarasAlugueis/
│
├── main.py
├── extracao_infra.py
├── scraper_imoveis.py
├── geocodificacao.py
├── modelagem.py
├── mapa.py
└── mapa_qualidade_vida_ac.html
```

---

# Descrição dos Arquivos

## `main.py`

Arquivo principal que executa todo o pipeline do projeto.

Fluxo de execução:

1. Coleta infraestrutura urbana do OpenStreetMap
2. Geração de dataset de imóveis
3. Cálculo de distâncias entre imóveis e serviços
4. Cálculo de acessibilidade urbana
5. Cálculo dos índices IAR e QV
6. Geração do mapa interativo

---

## `extracao_infra.py`

Responsável por extrair infraestrutura urbana utilizando a biblioteca **OSMnx**.

Serviços coletados:

* hospitais
* escolas
* universidades
* farmácias
* parques
* áreas de recreação

Os dados são convertidos para **centroides geográficos**, garantindo consistência na análise espacial.

---

## `scraper_imoveis.py`

Gera um **dataset simulado de imóveis** na região de Águas Claras.

Cada imóvel possui:

* preço
* área
* coordenadas geográficas

Os imóveis são distribuídos aleatoriamente em torno do centro da região.

Essa abordagem permite demonstrar o funcionamento do modelo sem depender de scraping externo.

---

## `geocodificacao.py`

Calcula a **matriz de distâncias** entre:

* imóveis
* serviços urbanos

Utiliza a função `cdist` da biblioteca **SciPy**.

Também gera um **score inicial de acessibilidade** baseado na proximidade ao serviço mais próximo.

---

## `modelagem.py`

Contém a classe **MotorUrbano**, responsável por toda a modelagem urbana.

Principais funções:

* cálculo de acessibilidade por categoria
* normalização das variáveis
* cálculo dos índices finais

Indicadores produzidos:

* **IAR** — Índice de Atratividade Residencial
* **QV** — Índice de Qualidade de Vida

---

## `mapa.py`

Gera um **mapa interativo** utilizando a biblioteca **Folium**.

Elementos exibidos no mapa:

* marcadores para infraestrutura urbana
* círculos representando imóveis
* coloração baseada no índice de qualidade de vida
* popups com informações do imóvel

O mapa é salvo automaticamente como:

```
mapa_qualidade_vida_ac.html
```

---

# Interpretação do Mapa

No mapa interativo:

### Infraestrutura urbana

Marcadores coloridos representam serviços:

| Cor         | Serviço  |
| ----------- | -------- |
| 🔴 vermelho | hospital |
| 🔵 azul     | escola   |
| 🟢 verde    | parque   |
| 🟠 laranja  | farmácia |

---

### Imóveis

Círculos representam imóveis.

Ao clicar em um imóvel são exibidos:

* preço
* área
* índice de qualidade de vida (QV)

---

### Escala de cores

A cor do círculo indica a qualidade de vida:

| Cor         | Interpretação           |
| ----------- | ----------------------- |
| 🟡 amarelo  | menor acessibilidade    |
| 🟠 laranja  | média                   |
| 🔴 vermelho | maior qualidade de vida |

---

# ⚙️ Instalação

Criar ambiente virtual:

```
python -m venv venv
source venv/bin/activate
```

Instalar dependências:

```
pip install osmnx geopandas folium branca numpy scipy pandas
```

---

# Execução

Execute o projeto com:

```
python main.py
```

O sistema irá:

1. coletar infraestrutura urbana
2. gerar imóveis simulados
3. calcular acessibilidade
4. gerar o mapa interativo

Ao final será aberto automaticamente:

```
mapa_qualidade_vida_ac.html
```

---

# Possíveis Extensões

O projeto pode ser expandido com:

* dados reais de imóveis
* cálculo de **tempo de deslocamento** em vez de distância
* integração com transporte público
* análise de **preço por m²**
* modelos de machine learning para valorização imobiliária
* dashboards interativos

---

# Tecnologias Utilizadas

* Python
* OSMnx
* GeoPandas
* Folium
* NumPy
* SciPy
* Pandas

---

# Área de Estudo

Região de **Águas Claras — Brasília (DF)**.

A escolha da região se deve à alta densidade urbana e forte presença de infraestrutura urbana, tornando-a ideal para análise de acessibilidade.

---

# Autoria

Projeto desenvolvido para estudo de:

* análise urbana
* geoprocessamento
* modelagem espacial
* ciência de dados aplicada a cidades

---
