"""
Dispatcher dos 10 formatos de carrossel - IL Variedades Enxovais

O QUE ESTE SCRIPT FAZ
----------------------
Junta os blocos de montar_carrossel_campanha.py e montar_post.py numa
unica funcao de entrada: gerar_carrossel(formato, produto_id, **dados).
Recebe o ID do produto (de produtos_reais.json) + as fotos/dados
especificos de cada formato, e devolve os caminhos dos 4 slides prontos.

O QUE ESTE SCRIPT *NAO* FAZ
----------------------------
Nao gera fotos novas via Gemini -- isso e responsabilidade de
gerar_carrossel_gemini.py (trocar_estampa_com_verificacao, etc.). Este
dispatcher so faz a camada grafica (Pillow, sem custo de API) em cima de
fotos que voce ja tem em disco.

FORMATOS DISPONIVEIS (ver FORMATOS_CARROSSEL.md pra descricao completa)
-------------------------------------------------------------------------
  "vitrine"               - foto_principal, fotos_estampas=[...], itens_inclusos=[...] (opcional)
  "campanha_sazonal"      - foto_principal, campanha={...}
  "novidade_semana"       - foto_principal
  "detalhe_textura"       - foto_principal, recortes_zoom=[...] (opcional)
  "kit_combo"             - foto_principal, produto_extra={"nome":..., "foto":...}
  "promocao_relampago"    - foto_principal, data_promocao, condicao
  "inspiracao_decoracao"  - fotos_grid=[...], foto_destaque=... (opcional)
  "giro_categoria"        - variantes=[{"foto":..., "nome":...}, ...] (3-4)
  "paleta_em_foco"        - cor_paleta, pares=[(foto,rotulo), (foto,rotulo), (foto,rotulo), (foto,rotulo)]
  "ambientes_estilos"     - estilos=[{"foto":..., "titulo":..., "subtitulo":...}, ...] (3)

COMO RODAR
----------
python gerar_carrossel_completo.py   # roda o exemplo no fim do arquivo
ou: from gerar_carrossel_completo import gerar_carrossel
"""

import json
from pathlib import Path

from montar_carrossel_campanha import (
    montar_slide_hero,
    montar_slide_itens_inclusos,
    montar_slide_detalhes,
    montar_slide_variedade,
    montar_slide_texto,
    montar_slide_zoom_cheio,
    montar_slide_duas_fotos,
    montar_slide_grid_numerado,
    montar_slide_duas_fotos_sobrepostas,
    montar_slide_circulo_organico,
    ROXO_NOBRE,
    ROSA_QUARTZO,
    OFF_WHITE,
)
from montar_post import montar_post

ARQUIVO_BANCO = "produtos_reais.json"


def _buscar_produto(produto_id: str) -> dict:
    with open(ARQUIVO_BANCO, "r", encoding="utf-8") as f:
        banco = json.load(f)
    for produto in banco["produtos"]:
        if produto["id"] == produto_id:
            return produto
    raise ValueError(f"Produto '{produto_id}' nao encontrado em {ARQUIVO_BANCO}")


def extrair_itens_inclusos(descricao_tecnica: str) -> list[str]:
    """
    A ficha tecnica vem do Google Docs como um dump tab-separated de
    cabecalhos + valores na mesma ordem (PRODUTO, DESCRICAO, MODELO,
    CARACTERISTICAS, COMPOSICAO, ...). O campo CARACTERISTICAS costuma
    ter a lista "01 Colcha..., 01 Cortina..., 02 Fronhas..." separada por
    quebras de linha dentro da propria celula -- e isso que vira "itens
    inclusos". Se a estrutura nao bater (documento diferente do padrao),
    devolve lista vazia em vez de quebrar.
    """
    if not descricao_tecnica:
        return []
    texto = descricao_tecnica.lstrip("﻿").strip()
    celulas = [c.strip() for c in texto.split("\t")]

    cabecalhos_esperados = ["PRODUTO", "DESCRIÇÃO", "MODELO", "CARACTERÍSTICAS"]
    if len(celulas) < 8 or celulas[:4] != cabecalhos_esperados:
        return []

    n_cabecalhos = 8  # PRODUTO..DIMENSÃO, ver montar_prompt_edicao/ficha padrao
    indice_caracteristicas = 3
    indice_valor = n_cabecalhos + indice_caracteristicas
    if len(celulas) <= indice_valor:
        return []

    bruto = celulas[indice_valor]
    itens = [linha.strip() for linha in bruto.splitlines() if linha.strip()]
    return itens


def _slide_paths(pasta_saida: str, n: int = 4) -> list[str]:
    Path(pasta_saida).mkdir(parents=True, exist_ok=True)
    return [f"{pasta_saida}/slide{i}.png" for i in range(1, n + 1)]


# --- construtores de cada formato -----------------------------------------


def _construir_vitrine(
    produto, pasta_saida, foto_principal, fotos_estampas=None, itens_inclusos=None,
    foto_estampa_close=None, foto_ambiente_variacao=None, campanha=None,
):
    # Ordem/escolha de slides fiel ao wireframe real (exemplo de carrosseis -
    # ex1): hero (1), itens inclusos (2), grade de estampas (3 -- NAO 4,
    # como estava antes) e fechamento com 2 fotos sobrepostas (4). O antigo
    # slide 3 (montar_slide_detalhes, zoom com linha apontando) nao
    # corresponde a nenhum slide do ex1 -- foi substituido por
    # montar_slide_duas_fotos_sobrepostas, ja construida a partir desse
    # mesmo wireframe (ex1/slide4) mas que so estava sendo usada em
    # promocao_relampago.
    s = _slide_paths(pasta_saida)
    itens_inclusos = itens_inclusos or extrair_itens_inclusos(produto.get("descricao_tecnica", "")) or [produto["nome"]]

    # Selo do slide 1: montar_slide_hero tem "NOVA COLEÇÃO"/"PRIMAVERA"
    # como default (sobrou de um teste antigo, nao faz sentido como
    # padrao global -- um post de Black Friday nao pode sair com selo de
    # Primavera). Usa o nome da campanha ativa quando houver; sem
    # campanha, cai num selo neutro generico.
    if campanha:
        badge_linha1, badge_linha2 = "PROMOÇÃO", campanha["nome"].upper()
    else:
        badge_linha1, badge_linha2 = "", "NOVIDADE"

    # Variedade de FOTO entre os slides (nao so de texto): foto_ambiente_variacao
    # e foto_estampa_close sao geradas e verificadas via IA com angulo/
    # enquadramento DIFERENTE da hero (ver executar_pipeline_semanal.
    # obter_foto_ambiente_variacao/obter_foto_estampa_close) -- antes os 4
    # slides do vitrine repetiam a mesma foto_principal em tudo. Slide 2
    # (itens inclusos) usa a variacao de ambiente quando aprovada, senao
    # cai pra foto principal. A grade do slide 3 reaproveita as fotos REAIS
    # e distintas que tiver disponivel (nunca inventa uma 2a/3a foto so
    # pra encher a grade).
    foto_itens = foto_ambiente_variacao or foto_principal
    if fotos_estampas is None:
        fotos_estampas = list(dict.fromkeys(
            f for f in (foto_principal, foto_ambiente_variacao, foto_estampa_close) if f
        ))

    # Slide 4 combina a foto hero (gerada) com um close-up REAL do tecido
    # (foto_estampa_close). NUNCA usa imagem_ambiente/imagem_estampa cru
    # direto aqui: confirmado visualmente que essas fotos de referencia
    # sempre vem com diagrama de medida/etiquetas sobrepostos, nao sao
    # apresentaveis num slide. Sem close aprovado (produto sem referencia,
    # ou reprovado na verificacao), repete a foto principal com texto
    # neutro -- nunca alega variedade que nao existe.
    if foto_estampa_close:
        foto_secundaria = foto_estampa_close
        titulo_fechamento, legenda_fechamento = "NOSSA ESTAMPA", "Tecido real, de perto"
    else:
        foto_secundaria = foto_principal
        titulo_fechamento, legenda_fechamento = "IL VARIEDADES", "Chame no direct e garanta o seu!"

    montar_slide_hero(foto_principal, produto["nome"], s[0], badge_linha1=badge_linha1, badge_linha2=badge_linha2)
    montar_slide_itens_inclusos(foto_itens, itens_inclusos, s[1])
    # Texto generico "CONHEÇA CADA DETALHE" em vez do default "N ESTAMPAS
    # DISPONIVEIS" (montar_slide_variedade) -- fotos_estampas agora mistura
    # hero + variacao de ambiente + close de tecido (nao sao N padroes de
    # estampa diferentes), entao "estampas" seria enganoso.
    montar_slide_variedade(
        fotos_estampas, s[2], texto_central=("CONHEÇA", "CADA DETALHE", "DESSE PRODUTO")
    )
    montar_slide_duas_fotos_sobrepostas(foto_principal, foto_secundaria, titulo_fechamento, legenda_fechamento, s[3])
    return s


def _construir_campanha_sazonal(produto, pasta_saida, foto_principal, campanha):
    """
    campanha: {"nome": "Primavera", "cta": "...", "hashtags": "#Primavera #CasaNova",
               "combina_com": "Toalhas de mesa, jogo de cozinha...", "tom_detalhe": "..."}
    """
    s = _slide_paths(pasta_saida)

    montar_post(
        foto_principal, campanha["cta"], f"Coleção {campanha['nome']} chegou na IL Variedades",
        s[0], nome_produto=produto["nome"],
    )
    montar_slide_texto(
        "Combina com", campanha.get("combina_com", ""), s[1],
        cor_fundo=ROSA_QUARTZO, cor_texto=OFF_WHITE, cor_destaque=ROXO_NOBRE, foto_fundo=foto_principal,
    )
    montar_slide_detalhes(foto_principal, campanha.get("tom_detalhe", "Qualidade em cada detalhe"), s[2])
    montar_slide_texto(
        campanha["cta"], f"Chame no direct e garanta o seu! {campanha.get('hashtags', '')}".strip(), s[3],
        cor_fundo=ROSA_QUARTZO, cor_texto=OFF_WHITE, cor_destaque=ROXO_NOBRE,
    )
    return s


def _construir_novidade_semana(produto, pasta_saida, foto_principal):
    s = _slide_paths(pasta_saida)
    montar_slide_hero(foto_principal, produto["nome"], s[0], badge_linha1="SÓ", badge_linha2="CHEGOU")
    montar_post(foto_principal, "Chegou pra ficar", f"Conheça o novo {produto['nome']}", s[1], nome_produto=produto["nome"])
    montar_slide_detalhes(foto_principal, "Produto de alta qualidade, sempre com muito carinho!", s[2])
    montar_slide_texto("Toda semana tem novidade", "Chame no direct e garanta o seu!", s[3], foto_fundo=foto_principal)
    return s


def _construir_detalhe_textura(produto, pasta_saida, foto_principal, recortes_zoom=None):
    recortes_zoom = recortes_zoom or [
        (0.30, 0.55, 0.35, 0.35),
        (0.05, 0.35, 0.35, 0.35),
        (0.0, 0.55, 0.25, 0.30),
    ]
    s = _slide_paths(pasta_saida)
    montar_slide_zoom_cheio(foto_principal, recortes_zoom[0], "Sinta a qualidade", s[0])
    montar_slide_zoom_cheio(foto_principal, recortes_zoom[1], "Estampa em detalhe", s[1])
    montar_slide_zoom_cheio(foto_principal, recortes_zoom[2], "Acabamento cuidadoso", s[2])
    montar_post(foto_principal, "Qualidade em cada detalhe", "Tecido selecionado, acabamento cuidadoso", s[3], nome_produto=produto["nome"])
    return s


def _construir_kit_combo(produto, pasta_saida, foto_principal, produto_extra):
    """produto_extra: {"nome": "...", "foto": "..."}"""
    s = _slide_paths(pasta_saida)
    montar_post(foto_principal, "Monte seu ambiente completo", "Peças que combinam entre si", s[0], nome_produto=produto["nome"], logo_estilo="completo")
    montar_slide_duas_fotos(foto_principal, produto_extra["foto"], produto["nome"], produto_extra["nome"], "Peças que combinam entre si", s[1])
    montar_slide_itens_inclusos(produto_extra["foto"], [produto["nome"], produto_extra["nome"]], s[2], titulo_caixa="NO COMBO")
    montar_slide_texto("Compre o combo completo", "E garanta um ambiente only IL Variedades. Chame no direct!", s[3])
    return s


def _construir_promocao_relampago(produto, pasta_saida, foto_principal, data_promocao, condicao):
    s = _slide_paths(pasta_saida)
    foto_secundaria = produto.get("imagem_estampa") or foto_principal
    montar_slide_duas_fotos_sobrepostas(
        foto_principal, foto_secundaria,
        "Promoção Relâmpago", f"{data_promocao} -- corre que é por tempo limitado",
        s[0],
    )
    montar_slide_circulo_organico(foto_principal, produto["nome"], s[1])
    montar_post(foto_principal, condicao, "", s[2], logo_estilo="nenhum")
    montar_slide_texto("Corre que é por tempo limitado!", "Chame no direct e garanta o seu!", s[3], cor_fundo=ROSA_QUARTZO, cor_texto=OFF_WHITE, cor_destaque=ROXO_NOBRE)
    return s


def _construir_inspiracao_decoracao(produto, pasta_saida, fotos_grid, foto_destaque=None):
    foto_destaque = foto_destaque or fotos_grid[0]
    s = _slide_paths(pasta_saida)
    montar_slide_texto("Inspire-se", "Ambientes reais pra você se apaixonar", s[0], foto_fundo=foto_destaque)
    montar_slide_variedade(fotos_grid, s[1], texto_central=("VÁRIOS", "JEITOS", "DE DECORAR"))
    montar_post(foto_destaque, "Esse aqui é o nosso queridinho", produto["nome"], s[2], logo_estilo="icone")
    montar_slide_texto("Qual combina mais com você?", "Conta pra gente nos comentários", s[3])
    return s


def _construir_giro_categoria(produto, pasta_saida, variantes):
    """variantes: [{"foto":..., "nome":...}, ...] -- 3 a 4 produtos/variantes."""
    s = _slide_paths(pasta_saida)
    montar_slide_grid_numerado([v["foto"] for v in variantes], f"CONHEÇA NOSSA | LINHA DE {produto['categoria'].upper()}", s[0])
    montar_post(variantes[0]["foto"], variantes[0]["nome"], "A queridinha da casa", s[1], nome_produto=variantes[0]["nome"], logo_estilo="completo")
    montar_slide_zoom_cheio(variantes[1]["foto"], (0.10, 0.30, 0.55, 0.55), variantes[1]["nome"], s[2])
    montar_slide_hero(variantes[2]["foto"], variantes[2]["nome"], s[3], badge_linha1="LINHA", badge_linha2="COMPLETA")
    return s


def _construir_paleta_em_foco(produto, pasta_saida, cor_paleta, pares):
    """pares: 2 tuplas de (foto1, rotulo1, foto2, rotulo2) -- 4 fotos ao todo, 2 por slide."""
    s = _slide_paths(pasta_saida)
    montar_slide_texto(
        f"Monte sua casa em tons de {cor_paleta}", "Combinações que conversam entre si", s[0],
        cor_fundo=ROSA_QUARTZO, cor_texto=OFF_WHITE, cor_destaque=ROXO_NOBRE, foto_fundo=pares[0][0],
    )
    montar_slide_duas_fotos(pares[0][0], pares[0][2], pares[0][1], pares[0][3], f"Combinações em {cor_paleta}", s[1])
    montar_slide_duas_fotos(pares[1][0], pares[1][2], pares[1][1], pares[1][3], "Outras combinações disponíveis", s[2])
    montar_slide_texto("Toda essa combinação te espera", "Chame no direct e monte a sua!", s[3])
    return s


def _construir_ambientes_estilos(produto, pasta_saida, estilos):
    """estilos: [{"foto":..., "titulo":..., "subtitulo":...}, ...] -- 3 itens."""
    s = _slide_paths(pasta_saida)
    montar_post(estilos[0]["foto"], estilos[0]["titulo"], estilos[0]["subtitulo"], s[0], nome_produto=produto["nome"], logo_estilo="completo")
    montar_slide_zoom_cheio(estilos[1]["foto"], (0.0, 0.15, 1.0, 0.65), estilos[1]["titulo"], s[1])
    montar_slide_hero(estilos[2]["foto"], produto["nome"], s[2], badge_linha1="ESTILO", badge_linha2=estilos[2]["titulo"].upper())
    montar_slide_texto("Um produto, infinitas possibilidades", "Qual combina com você? Chame no direct!", s[3])
    return s


FORMATOS = {
    "vitrine": _construir_vitrine,
    "campanha_sazonal": _construir_campanha_sazonal,
    "novidade_semana": _construir_novidade_semana,
    "detalhe_textura": _construir_detalhe_textura,
    "kit_combo": _construir_kit_combo,
    "promocao_relampago": _construir_promocao_relampago,
    "inspiracao_decoracao": _construir_inspiracao_decoracao,
    "giro_categoria": _construir_giro_categoria,
    "paleta_em_foco": _construir_paleta_em_foco,
    "ambientes_estilos": _construir_ambientes_estilos,
}


def gerar_carrossel(formato: str, produto_id: str, pasta_saida: str | None = None, **dados) -> list[str]:
    """
    Monta o carrossel de 4 slides do formato pedido pro produto pedido.
    Ver o topo do arquivo pra saber quais chaves cada formato espera em
    **dados (fotos, campanha, etc. -- tudo que nao vem de produtos_reais.json).

    Retorna a lista dos 4 caminhos de slide gerados.
    """
    if formato not in FORMATOS:
        raise ValueError(f"Formato '{formato}' nao existe. Opcoes: {', '.join(FORMATOS)}")

    produto = _buscar_produto(produto_id)
    pasta_saida = pasta_saida or f"saida/carrossel_{produto_id}_{formato}"
    return FORMATOS[formato](produto, pasta_saida, **dados)


if __name__ == "__main__":
    # exemplo: reaproveita as fotos do jogo de quarto ja geradas nesta sessao
    slides = gerar_carrossel(
        "vitrine",
        "p009",
        foto_principal="saida/teste_pipeline_p009_0.png",
        fotos_estampas=[
            "saida/teste_pipeline_p009_0.png",
            "saida/teste_corrigir_cortina_0.png",
            "saida/p009_estampa3_vermelha_v2_0.png",
            "saida/p009_estampa4_azul_final_0.png",
        ],
    )
    print("\nCarrossel pronto:")
    for caminho in slides:
        print(" ", caminho)
