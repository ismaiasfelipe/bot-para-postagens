"""
Tema da semana - IL Variedades Enxovais

Guarda a escolha manual do usuario pra semana atual, definida atraves do
workflow "Definir tema da semana" no GitHub Actions (acionavel pelo site
ou app do GitHub, de qualquer lugar, sem precisar do PC ligado).
executar_pipeline_semanal.py le esse arquivo antes de decidir
campanha/produto automaticamente pelo calendario -- se houver um tema
definido, ele tem prioridade sobre a campanha do calendario.

FORMATO DE tema_semana.json
------------------------------
{
  "definido_em": "2026-09-11",
  "campanha_chave": "dia_das_maes" | null,
  "categoria_foco": "Cama" | null,
  "produto_id": "p009" | null
}

campanha_chave: usa as orientacoes (cores/tom/cta/hashtags) dessa
  campanha de calendario_campanhas.CAMPANHAS, independente da data real
  -- pra quando o usuario quer "adiantar" uma campanha fora da janela
  automatica, ou reforcar a que ja esta ativa.
categoria_foco: sem campanha especifica, so restringe a categoria de
  produto (Cama, Banho, Mesa, Sofá, Infantil) pro rodizio da semana --
  pra quando o usuario so quer "essa semana, foco em toalhas" sem ligar
  a nenhuma campanha do calendario.
produto_id: forca um produto especifico a semana toda (ignora o
  rodizio/historico) -- pra quando o usuario quer repetir o mesmo
  produto em todos os posts da semana.

Todos os campos sao opcionais -- tema_semana.json ausente, ou com tudo
None, volta pro fluxo automatico normal (calendario decide sozinho).
"""

import json
from pathlib import Path

ARQUIVO_TEMA = "tema_semana.json"


def carregar_tema() -> dict | None:
    if not Path(ARQUIVO_TEMA).exists():
        return None
    with open(ARQUIVO_TEMA, encoding="utf-8") as f:
        return json.load(f)


def salvar_tema(
    campanha_chave: str | None,
    categoria_foco: str | None,
    produto_id: str | None,
    definido_em: str,
) -> None:
    tema = {
        "definido_em": definido_em,
        "campanha_chave": campanha_chave or None,
        "categoria_foco": categoria_foco or None,
        "produto_id": produto_id or None,
    }
    with open(ARQUIVO_TEMA, "w", encoding="utf-8") as f:
        json.dump(tema, f, ensure_ascii=False, indent=2)
