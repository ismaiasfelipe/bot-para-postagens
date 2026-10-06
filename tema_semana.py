"""
Tema da semana - IL Variedades Enxovais

Guarda a escolha manual do usuario pra semana atual, definida pelo painel
PWA (webapp/), que escreve tema_semana.json direto pela API do GitHub
(ver webapp/js/github-api.js escreverArquivoRepo) -- sem passar mais pelo
workflow_dispatch de definir_tema.yml, que so aceitava 1 valor por campo.
executar_pipeline_semanal.py le esse arquivo antes de decidir
campanha/produto/formato automaticamente pelo calendario -- se houver um
tema definido, ele tem prioridade.

FORMATO DE tema_semana.json
------------------------------
{
  "definido_em": "2026-10-06",
  "campanhas_chaves": ["dia_das_maes", "__padrao_marca__"] | null,
  "categorias_foco": ["Cama", "Banho"] | null,
  "produtos_ids": ["p009", "p003"] | null,
  "linguagem": "neutra" | "acolhedora" | "chamativa" | "agressiva",
  "padroes": ["apresentacao_produto", "promocao"] | null,
  "preco_dia": "segunda" | ... | "sabado" | "todos" | null
}

Todo campo de lista (campanhas_chaves/categorias_foco/produtos_ids/
padroes): quando tem mais de 1 valor marcado, o bot sorteia um
aleatoriamente A CADA publicacao do dia (nao fixa a semana toda) -- ver
escolher_campanha/escolher_produtos_candidatos/escolher_formato em
executar_pipeline_semanal.py.

campanhas_chaves: usa as orientacoes (cores/tom/cta/hashtags) dessa
  campanha de calendario_campanhas.CAMPANHAS, independente da data real.
  O valor especial "__padrao_marca__" representa "sem campanha do
  calendario" (fluxo generico de marca) e pode ser combinado com
  campanhas reais na mesma lista.
categoria_foco: sem campanha especifica, so restringe a categoria de
  produto (Cama, Banho, Mesa, Sofá, Infantil) pro rodizio -- so e usado
  se campanhas_chaves estiver vazio/None.
produtos_ids: restringe o rodizio a esses produtos especificos (em vez
  de qualquer produto da categoria da campanha).
linguagem: tom de voz da legenda gerada por IA (ver
  gerar_carrossel_gemini.gerar_legenda_ia). Default "neutra" se ausente.
padroes: categorias de formato de negocio (ver
  calendario_campanhas.MAPEAMENTO_PADRAO_FORMATOS) -- "cross_sell" e
  "estilo_vida" mapeiam pra formatos que normalmente pedem curadoria
  manual de varias fotos; o pipeline tenta montar automaticamente
  reaproveitando candidatos/fotos_variadas, com qualidade variavel.
preco_dia: dia da semana (ou "todos") em que o carrossel/story deve
  mostrar o preco do produto (extraido da ficha tecnica, ver
  gerar_carrossel_gemini.extrair_preco). None = nunca mostra preco.

Todos os campos sao opcionais -- tema_semana.json ausente, ou com tudo
None, volta pro fluxo automatico normal (calendario decide sozinho).
"""

import json
from pathlib import Path

ARQUIVO_TEMA = "tema_semana.json"

CAMPANHA_PADRAO_MARCA = "__padrao_marca__"
LINGUAGENS_VALIDAS = ("neutra", "acolhedora", "chamativa", "agressiva")
PADROES_VALIDOS = ("apresentacao_produto", "promocao", "cross_sell", "estilo_vida")
DIAS_SEMANA_VALIDOS = ("segunda", "terca", "quarta", "quinta", "sexta", "sabado", "todos")


def carregar_tema() -> dict | None:
    if not Path(ARQUIVO_TEMA).exists():
        return None
    with open(ARQUIVO_TEMA, encoding="utf-8") as f:
        return json.load(f)


def salvar_tema(
    campanhas_chaves: list[str] | None = None,
    categorias_foco: list[str] | None = None,
    produtos_ids: list[str] | None = None,
    linguagem: str = "neutra",
    padroes: list[str] | None = None,
    preco_dia: str | None = None,
    definido_em: str = "",
) -> dict:
    tema = {
        "definido_em": definido_em,
        "campanhas_chaves": campanhas_chaves or None,
        "categorias_foco": categorias_foco or None,
        "produtos_ids": produtos_ids or None,
        "linguagem": linguagem if linguagem in LINGUAGENS_VALIDAS else "neutra",
        "padroes": [p for p in (padroes or []) if p in PADROES_VALIDOS] or None,
        "preco_dia": preco_dia if preco_dia in DIAS_SEMANA_VALIDOS else None,
    }
    with open(ARQUIVO_TEMA, "w", encoding="utf-8") as f:
        json.dump(tema, f, ensure_ascii=False, indent=2)
    return tema
