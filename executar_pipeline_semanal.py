"""
Orquestrador semanal - IL Variedades Enxovais

O QUE ESTE SCRIPT FAZ
----------------------
Roda o pipeline inteiro uma vez:
1. Descobre a campanha ativa na semana (calendario_campanhas.py) ou usa
   o fluxo generico se nenhuma estiver ativa
2. Escolhe um produto que combine com a campanha (categoria) e que nao
   tenha sido usado nos ultimos 8 posts (historico_publicacoes.json)
3. Escolhe o formato de carrossel (o sugerido pela campanha, ou um dos
   genericos em rodizio)
4. Gera a foto "hero" do produto via Gemini -- REAPROVEITA se ja existir
   saida/{produto_id}_0.png (evita custo/gasto repetido)
5. Monta os 4 slides do carrossel (gerar_carrossel_completo.py)
6. Monta 2 Stories (montar_story.py) reaproveitando a MESMA foto hero --
   regra "2 stories por carrossel" do planejamento original. Gira entre
   os 6 blocos de story que precisam so de 1 foto (ver BLOCOS_STORY);
   os outros 4 blocos (texto puro, duas fotos, trio de circulos, grade)
   exigem curadoria manual de fotos extras e nao entram no rodizio
   automatico -- mesma logica dos 5 formatos de carrossel manuais.
7. Escreve a legenda no tom de voz da campanha (ou generico)
8. Se publicar=True: sobe pro storage e publica de verdade no Instagram
   (carrossel + os 2 stories), e registra tudo no historico

ESCOPO ATUAL -- IMPORTANTE
----------------------------
So usa os 5 formatos que precisam de 1 unica foto hero: vitrine,
campanha_sazonal, promocao_relampago, novidade_semana, detalhe_textura.
Os outros 5 formatos (kit_combo, inspiracao_decoracao, giro_categoria,
paleta_em_foco, ambientes_estilos) exigem multiplas fotos/produtos por
slide e ainda pedem curadoria manual -- nao estao no rodizio automatico.

CUSTO E EFEITOS
------------------
- Gerar uma foto nova (quando o produto ainda nao tem saida/{id}_0.png)
  chama a API do Gemini -- tem custo. Mesmo com publicar=False isso pode
  acontecer, porque a foto e necessaria pra montar o preview do carrossel.
- publicar=True sobe imagens pro Google Cloud Storage e publica um post
  DE VERDADE no Instagram real da loja. So rode assim com confirmacao.

COMO RODAR
----------
python executar_pipeline_semanal.py            # so mostra o que faria (nao publica)
python executar_pipeline_semanal.py --publicar  # publica de verdade
"""

import argparse
import hashlib
import json
import random
from datetime import date
from pathlib import Path

from calendario_campanhas import (
    CAMPANHAS, campanhas_ativas_na_semana, montar_legenda, HASHTAGS_FIXAS,
    MAPEAMENTO_PADRAO_FORMATOS,
)
from tema_semana import carregar_tema, CAMPANHA_PADRAO_MARCA
from gerar_carrossel_gemini import (
    gerar_foto_hero_com_verificacao,
    gerar_foto_estampa_close_com_verificacao,
    gerar_legenda_ia,
    extrair_preco,
)
from gerar_carrossel_completo import gerar_carrossel
from montar_story import (
    montar_story_abas_onduladas,
    montar_story_banner_topo,
    montar_story_cartao_app,
    montar_story_circulo_fita,
    montar_story_foto_minimal,
    montar_story_oval_vertical,
)
from upload_storage import enviar_carrossel, enviar_para_storage
from publicar_instagram import publicar_carrossel, publicar_story

ARQUIVO_PRODUTOS = "produtos_reais.json"
ARQUIVO_HISTORICO = "historico_publicacoes.json"
FORMATOS_SIMPLES_GENERICOS = ["vitrine", "novidade_semana", "detalhe_textura"]

# quantos produtos extras (alem do principal) cada formato multi-foto
# precisa, pra saber quantos tentar reunir em _obter_produtos_extras
QUANTIDADE_EXTRAS_POR_FORMATO = {
    "kit_combo": 1,
    "giro_categoria": 2,
    "inspiracao_decoracao": 2,
    "paleta_em_foco": 3,
    "ambientes_estilos": 2,
}

DIAS_SEMANA_PT = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]


def _construir_story_banner_topo(foto_hero, produto, campanha, caminho):
    texto = campanha["nome"].upper() if campanha else "NOVIDADE"
    montar_story_banner_topo(foto_hero, texto, produto["nome"], caminho)


def _construir_story_foto_minimal(foto_hero, produto, campanha, caminho):
    montar_story_foto_minimal(foto_hero, produto["nome"], caminho)


def _construir_story_oval_vertical(foto_hero, produto, campanha, caminho):
    texto = campanha["nome"].upper() if campanha else "DESTAQUE"
    montar_story_oval_vertical(foto_hero, texto, "Toque de elegância", "Confira mais", caminho)


def _construir_story_circulo_fita(foto_hero, produto, campanha, caminho):
    etiqueta = campanha["nome"][:10] if campanha else "Novo"
    montar_story_circulo_fita(foto_hero, etiqueta, produto["nome"], "Inspiração do dia", caminho)


def _construir_story_abas_onduladas(foto_hero, produto, campanha, caminho):
    cta = campanha["cta"] if campanha else "Chame no direct"
    montar_story_abas_onduladas(foto_hero, produto["nome"], cta, caminho)


def _construir_story_cartao_app(foto_hero, produto, campanha, caminho):
    texto = campanha["nome"].upper() if campanha else "NOVA COLEÇÃO"
    montar_story_cartao_app(foto_hero, texto, produto["nome"], "Confira os detalhes", caminho)


# So os blocos que precisam de 1 unica foto (a propria foto hero do
# carrossel) entram no rodizio automatico -- ver nota no docstring do
# modulo.
BLOCOS_STORY = [
    _construir_story_banner_topo,
    _construir_story_foto_minimal,
    _construir_story_oval_vertical,
    _construir_story_circulo_fita,
    _construir_story_abas_onduladas,
    _construir_story_cartao_app,
]


def _carregar_produtos() -> list[dict]:
    with open(ARQUIVO_PRODUTOS, encoding="utf-8") as f:
        return json.load(f)["produtos"]


def _carregar_historico() -> list[dict]:
    if not Path(ARQUIVO_HISTORICO).exists():
        return []
    with open(ARQUIVO_HISTORICO, encoding="utf-8") as f:
        return json.load(f)


def _salvar_historico(historico: list[dict]) -> None:
    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)


def _categoria_bate(categoria_produto: str, categoria_campanha: str) -> bool:
    if categoria_campanha == "Todas":
        return True
    return categoria_produto.lower().startswith(categoria_campanha.lower())


def _campanha_sintetica_categoria(categoria: str) -> dict:
    """Tema da semana com so categoria (sem campanha do calendario) -- ver tema_semana.py."""
    return {
        "chave": f"foco_{categoria.lower()}",
        "nome": f"Semana de {categoria}",
        "categorias": [categoria],
        "cta": "Chame no direct e garanta o seu!",
        "hashtags_extras": "",
        "tom_detalhe": "",
        "combina_com": "",
        "formato_sugerido": "vitrine",
    }


def escolher_campanha() -> dict | None:
    """
    Prioridade: tema da semana definido manualmente (painel PWA) >
    campanha ativa pelo calendario > nenhuma (fluxo generico).

    Se o tema tiver mais de 1 campanha marcada, sorteia uma a cada
    publicacao do dia (nao fixa a semana toda) -- CAMPANHA_PADRAO_MARCA
    sorteada equivale a "nenhuma campanha" (fluxo generico de marca).
    """
    tema = carregar_tema()
    if tema:
        chaves = tema.get("campanhas_chaves")
        if chaves:
            escolhida = random.choice(chaves)
            if escolhida != CAMPANHA_PADRAO_MARCA:
                encontrada = next((c for c in CAMPANHAS if c["chave"] == escolhida), None)
                if encontrada:
                    return encontrada
            return None
        if tema.get("categorias_foco"):
            return _campanha_sintetica_categoria(random.choice(tema["categorias_foco"]))

    ativas = campanhas_ativas_na_semana()
    return ativas[0] if ativas else None


def escolher_produtos_candidatos(campanha: dict | None, historico: list[dict]) -> list[dict]:
    """
    Devolve os produtos candidatos em ordem de preferencia (nao usados
    recentemente primeiro). Devolve uma LISTA -- se o primeiro candidato
    reprovar na verificacao de foto (obter_foto_hero), o chamador tenta o
    proximo em vez de travar ou publicar algo errado; formatos multi-foto
    tambem puxam os proximos da lista como "extras" (ver
    _obter_produtos_extras).

    Secao "Produtos" do painel PWA: categorias_foco marca quais
    categorias entram (cada uma com um sub-seletor "Aleatorio" OU
    produtos especificos, ver webapp/js/app.js
    _renderizarProdutosPorCategoria); produtos_ids tem os IDs marcados a
    mao em QUALQUER uma dessas categorias. Categoria marcada mas SEM
    nenhum produto seu em produtos_ids == "Aleatorio" pra ela (qualquer
    produto daquela categoria entra); categoria com pelo menos 1 produto
    marcado fica restrita so a esses. Se nada foi marcado em nenhuma das
    duas listas, cai pro fluxo pela campanha (como antes).
    """
    tema = carregar_tema()
    produtos = _carregar_produtos()
    usados_recentes = {h["produto_id"] for h in historico[-8:]}

    categorias_foco = (tema or {}).get("categorias_foco")
    produtos_ids = (tema or {}).get("produtos_ids")

    if categorias_foco or produtos_ids:
        pool = produtos
        if categorias_foco:
            pool = [p for p in produtos if any(_categoria_bate(p["categoria"], c) for c in categorias_foco)]
        if produtos_ids:
            categorias_com_pin = {p["categoria"] for p in pool if p["id"] in produtos_ids}
            pool = [p for p in pool if p["categoria"] not in categorias_com_pin or p["id"] in produtos_ids]
        if pool:
            nao_usados = [p for p in pool if p["id"] not in usados_recentes]
            usados = [p for p in pool if p["id"] in usados_recentes]
            random.shuffle(nao_usados)
            return nao_usados + usados

    candidatos = produtos
    if campanha:
        filtrados = [
            p for p in produtos
            if any(_categoria_bate(p["categoria"], c) for c in campanha["categorias"])
        ]
        if filtrados:
            candidatos = filtrados

    nao_usados = [p for p in candidatos if p["id"] not in usados_recentes]
    usados = [p for p in candidatos if p["id"] in usados_recentes]
    return nao_usados + usados  # nao usados primeiro, usados como ultimo recurso


def escolher_formato(campanha: dict | None, historico: list[dict]) -> str:
    """
    Prioridade: "padroes" marcados no tema da semana (sorteia 1 padrao,
    depois 1 formato tecnico dentro dele) > formato sugerido pela
    campanha > rodizio generico.
    """
    tema = carregar_tema()
    if tema and tema.get("padroes"):
        padrao = random.choice(tema["padroes"])
        formatos = MAPEAMENTO_PADRAO_FORMATOS.get(padrao) or FORMATOS_SIMPLES_GENERICOS
        return random.choice(formatos)
    if campanha:
        return campanha.get("formato_sugerido", "vitrine")
    n = len(historico)
    return FORMATOS_SIMPLES_GENERICOS[n % len(FORMATOS_SIMPLES_GENERICOS)]


def _obter_produtos_extras(
    candidatos: list[dict], excluir_id: str, quantidade: int
) -> list[tuple[dict, str]]:
    """
    Reune ate `quantidade` produtos extras (alem do principal, ja em
    `excluir_id`) com foto hero aprovada, pros formatos multi-foto
    (kit_combo, giro_categoria, inspiracao_decoracao, paleta_em_foco,
    ambientes_estilos -- ver QUANTIDADE_EXTRAS_POR_FORMATO). Percorre os
    MESMOS candidatos ja filtrados por categoria da campanha, pulando o
    produto principal e qualquer um que reprove na verificacao de foto.

    Pode devolver MENOS que `quantidade` se nao houver candidatos
    suficientes (o chamador deve tratar esse caso -- ver rodar()).
    """
    extras = []
    for candidato in candidatos:
        if candidato["id"] == excluir_id:
            continue
        if len(extras) >= quantidade:
            break
        foto = obter_foto_hero(candidato)
        if foto is not None:
            extras.append((candidato, foto))
    return extras


def _obter_produtos_extras_mesma_cor(
    candidatos: list[dict], produto_principal: dict, quantidade: int
) -> list[tuple[dict, str]]:
    """
    Como _obter_produtos_extras, mas so aceita candidatos com a MESMA
    cor_predominante do produto principal -- usado por 'paleta_em_foco',
    que precisa de produtos que combinem de verdade em cor (ver
    enriquecer_cores.py), nao so "o proximo da lista com foto aprovada".
    Sem cor_predominante classificada no produto principal, devolve []
    direto -- o chamador trata igual a nao achar extras suficientes
    (cai pro formato generico, ver rodar()).
    """
    cor = produto_principal.get("cor_predominante")
    if not cor:
        return []
    mesma_cor = [c for c in candidatos if c.get("cor_predominante") == cor]
    return _obter_produtos_extras(mesma_cor, produto_principal["id"], quantidade)


def _chave_cache_hero(produto: dict) -> str:
    """
    ID do produto + hash curto das fotos de referencia reais (imagem_ambiente
    + imagem_estampa) -- NAO so o ID sozinho. Descoberto em 06/10/2026: o
    catalogo foi regenerado (10 -> 53 produtos) e os IDs antigos (p001,
    p002...) passaram a apontar pra produtos DIFERENTES, mas cache_hero/
    continuava servindo a foto antiga pra quem pedisse "p001" -- 2 posts
    reais foram publicados no Instagram com foto trocada antes disso ser
    percebido. Com o hash, se as referencias do produto mudam (catalogo
    regenerado de novo, fotos trocadas no Drive, etc.), a chave muda
    sozinha e uma foto nova e gerada -- nunca mais reaproveita as costas
    de um ID que mudou de produto.
    """
    referencias = "|".join(filter(None, (produto.get("imagem_ambiente"), produto.get("imagem_estampa"))))
    assinatura = hashlib.sha1(referencias.encode("utf-8")).hexdigest()[:10]
    return f"{produto['id']}_{assinatura}"


def obter_foto_hero(produto: dict) -> str | None:
    """
    Reaproveita uma foto ja verificada em cache_hero/ se existir pra essa
    MESMA combinacao de produto+referencias (ver _chave_cache_hero);
    senao gera uma nova via Gemini COM verificacao automatica de
    fidelidade (gerar_foto_hero_com_verificacao, com retry) e salva no
    cache so se aprovada.

    Retorna None se reprovar em todas as tentativas -- o chamador deve
    pular esse produto, nunca publicar uma foto reprovada.

    Cache separado de saida/ de proposito: os arquivos soltos em saida/
    (de sessoes anteriores a 03/09/2026) nao passaram por verificacao e
    alguns saem com cenas genericas sem relacao com o produto real (ver
    PROJETO.md, "Verificacao de foto hero") -- so o cache novo, com
    aprovacao confirmada, e reaproveitado automaticamente.
    """
    pasta_cache = Path("cache_hero")
    pasta_cache.mkdir(exist_ok=True)
    caminho_cache = pasta_cache / f"{_chave_cache_hero(produto)}.png"
    if caminho_cache.exists():
        return str(caminho_cache)

    aprovado = gerar_foto_hero_com_verificacao(produto)
    if aprovado is None:
        return None

    caminho_cache.write_bytes(Path(aprovado).read_bytes())
    return str(caminho_cache)


def obter_foto_estampa_close(produto: dict) -> str | None:
    """
    Reaproveita um close-up verificado do tecido em cache_hero/ se
    existir pra essa mesma combinacao de produto+referencias (mesma
    chave de obter_foto_hero, so com sufixo); senao gera via Gemini
    (gerar_foto_estampa_close_com_verificacao). So usado pelo formato
    "vitrine" hoje, pro slide de fechamento (ver montar_dados_formato).

    Retorna None se o produto nao tiver referencia real ou reprovar --
    o chamador (_construir_vitrine) cai pra repetir a foto principal
    nesse caso.
    """
    pasta_cache = Path("cache_hero")
    pasta_cache.mkdir(exist_ok=True)
    caminho_cache = pasta_cache / f"{_chave_cache_hero(produto)}_estampa_close.png"
    if caminho_cache.exists():
        return str(caminho_cache)

    aprovado = gerar_foto_estampa_close_com_verificacao(produto)
    if aprovado is None:
        return None

    caminho_cache.write_bytes(Path(aprovado).read_bytes())
    return str(caminho_cache)


def escolher_blocos_stories(historico: list[dict]) -> list:
    """Gira pelos 6 blocos de story de 1-foto-so, 2 diferentes por post (ver BLOCOS_STORY)."""
    n = len(historico)
    indice1 = n % len(BLOCOS_STORY)
    indice2 = (n + 1) % len(BLOCOS_STORY)
    return [BLOCOS_STORY[indice1], BLOCOS_STORY[indice2]]


def montar_stories_do_post(
    pasta_saida: str,
    foto_hero: str,
    produto: dict,
    campanha: dict | None,
    historico: list[dict],
    preco: str = "",
) -> list[str]:
    """
    Gira pelos 2 blocos de story do rodizio normal -- EXCETO quando ha
    preco do dia (tema_semana.preco_dia, ver _deve_mostrar_preco): nesse
    caso o 2o slot vira um story dedicado de preco
    (_construir_story_preco), substituindo o bloco do rodizio normal
    nesse dia (regra "2 stories por carrossel" se mantem, so muda o
    conteudo de 1 deles).
    """
    pasta_stories = Path(pasta_saida) / "stories"
    pasta_stories.mkdir(parents=True, exist_ok=True)
    blocos = escolher_blocos_stories(historico)
    caminhos = []
    for i, construtor in enumerate(blocos, start=1):
        caminho = str(pasta_stories / f"story{i}.png")
        if i == len(blocos) and preco:
            _construir_story_preco(foto_hero, produto, campanha, caminho, preco)
        else:
            construtor(foto_hero, produto, campanha, caminho)
        caminhos.append(caminho)
    return caminhos


def montar_dados_formato(
    formato: str,
    campanha: dict | None,
    foto_hero: str,
    produto: dict | None = None,
    extras: list[tuple[dict, str]] | None = None,
    preco: str = "",
) -> dict:
    extras = extras or []

    if formato == "campanha_sazonal":
        return {
            "foto_principal": foto_hero,
            "campanha": {
                "nome": campanha["nome"],
                "cta": campanha["cta"],
                "hashtags": f"{campanha['hashtags_extras']} {HASHTAGS_FIXAS}",
                "combina_com": campanha.get("combina_com", ""),
                "tom_detalhe": campanha.get("tom_detalhe", ""),
            },
        }
    if formato == "promocao_relampago":
        # "condicao" vira o titulo grande do slide 3 (montar_post) -- tem
        # que ser curto, NUNCA a frase inteira do CTA (que ja aparece,
        # por completo, no slide 4), senao o texto estoura o slide. O
        # nome/data da campanha ja aparecem nos slides 1 e 2, nao repete.
        # Se tiver preco do dia (tema_semana.preco_dia), substitui a
        # condicao generica pelo valor real.
        return {
            "foto_principal": foto_hero,
            "data_promocao": date.today().strftime("%d/%m"),
            "condicao": f"Por apenas {preco}, só hoje!" if preco else "Condição especial, só hoje!",
        }
    if formato == "kit_combo":
        # precisa de 1 produto extra -- ver QUANTIDADE_EXTRAS_POR_FORMATO
        # e _obter_produtos_extras. Chamador garante len(extras) >= 1
        # antes de chegar aqui (ver rodar()).
        extra_produto, extra_foto = extras[0]
        return {
            "foto_principal": foto_hero,
            "produto_extra": {"nome": extra_produto["nome"], "foto": extra_foto},
        }
    if formato == "giro_categoria":
        # variantes[0] e o produto principal, [1] e [2] sao os extras --
        # chamador garante len(extras) >= 2 antes de chegar aqui.
        variantes = [{"foto": foto_hero, "nome": produto["nome"]}]
        variantes += [{"foto": foto, "nome": p["nome"]} for p, foto in extras[:2]]
        return {"variantes": variantes}
    if formato == "inspiracao_decoracao":
        # fotos_grid: produto principal + ate 2 extras (chamador garante
        # pelo menos 2 extras antes de chegar aqui).
        fotos_grid = [foto_hero] + [foto for _, foto in extras[:2]]
        return {"fotos_grid": fotos_grid, "foto_destaque": foto_hero}
    if formato == "paleta_em_foco":
        # pares: 2 tuplas de (foto1,rotulo1,foto2,rotulo2) -- 4 fotos ao
        # todo (produto principal + ate 3 extras, chamador garante isso).
        todos = [(produto, foto_hero)] + extras[:3]
        rotulos = [p["nome"][:18] for p, _ in todos]
        fotos = [foto for _, foto in todos]
        # extras ja vem filtrados pela mesma cor de produto (ver
        # _obter_produtos_extras_mesma_cor) -- so cai no generico se
        # produto nao tiver sido classificado ainda (enriquecer_cores.py).
        cor_paleta = produto.get("cor_predominante") or "nossa seleção"
        pares = [
            (fotos[0], rotulos[0], fotos[1], rotulos[1]),
            (fotos[2], rotulos[2], fotos[3], rotulos[3]),
        ]
        return {"cor_paleta": cor_paleta, "pares": pares}
    if formato == "ambientes_estilos":
        # estilos: produto principal + ate 2 extras (chamador garante
        # pelo menos 2 extras antes de chegar aqui).
        todos = [(produto, foto_hero)] + extras[:2]
        return {
            "estilos": [
                {"foto": foto, "titulo": p["nome"], "subtitulo": "Qualidade IL Variedades"}
                for p, foto in todos
            ]
        }
    if formato == "vitrine":
        # Slide de fechamento (duas fotos sobrepostas) usa um close-up
        # real do tecido como 2a foto quando disponivel (ver
        # obter_foto_estampa_close/_construir_vitrine) -- None aqui faz
        # _construir_vitrine cair pra repetir a foto principal.
        return {"foto_principal": foto_hero, "foto_estampa_close": obter_foto_estampa_close(produto)}
    return {"foto_principal": foto_hero}  # novidade_semana, detalhe_textura


def _dia_semana_hoje() -> str:
    return DIAS_SEMANA_PT[date.today().weekday()]


def _deve_mostrar_preco(tema: dict | None) -> bool:
    if not tema or not tema.get("preco_dia"):
        return False
    preco_dia = tema["preco_dia"]
    return preco_dia == "todos" or preco_dia == _dia_semana_hoje()


def _construir_story_preco(foto_hero, produto, campanha, caminho, preco):
    etiqueta = campanha["nome"][:10] if campanha else "Promoção"
    montar_story_circulo_fita(foto_hero, etiqueta, produto["nome"], f"Por {preco}", caminho)


def rodar(publicar: bool = False) -> None:
    tema = carregar_tema()
    campanha = escolher_campanha()
    historico = _carregar_historico()
    candidatos = escolher_produtos_candidatos(campanha, historico)
    formato = escolher_formato(campanha, historico)

    print(f"Campanha ativa: {campanha['nome'] if campanha else 'nenhuma (fluxo generico)'}")
    print(f"Formato: {formato}")

    produto = None
    foto_hero = None
    for candidato in candidatos:
        print(f"\nTentando produto: {candidato['id']} - {candidato['nome']}")
        foto_hero = obter_foto_hero(candidato)
        if foto_hero is not None:
            produto = candidato
            break
        print(f"  '{candidato['id']}' reprovado na verificacao, tentando o proximo candidato...")

    if produto is None:
        print("\nNenhum produto candidato passou na verificacao de foto. Nada foi publicado.")
        return

    print(f"\nProduto escolhido: {produto['id']} - {produto['nome']}")
    print(f"Foto hero: {foto_hero}")

    # formatos multi-foto (kit_combo, giro_categoria, inspiracao_decoracao,
    # paleta_em_foco, ambientes_estilos) precisam de produtos extras com
    # foto aprovada -- se nao achar o suficiente entre os candidatos
    # restantes, cai pra um formato generico de 1 foto em vez de travar
    # ou publicar com dados incompletos.
    extras = []
    quantidade_extra = QUANTIDADE_EXTRAS_POR_FORMATO.get(formato, 0)
    if quantidade_extra:
        if formato == "paleta_em_foco":
            extras = _obter_produtos_extras_mesma_cor(candidatos, produto, quantidade_extra)
        else:
            extras = _obter_produtos_extras(candidatos, produto["id"], quantidade_extra)
        if len(extras) < quantidade_extra:
            print(
                f"  aviso: so achou {len(extras)}/{quantidade_extra} produtos extras pro "
                f"formato '{formato}' -- caindo pra um formato generico de 1 foto"
            )
            formato = FORMATOS_SIMPLES_GENERICOS[len(historico) % len(FORMATOS_SIMPLES_GENERICOS)]
            extras = []

    preco = ""
    if _deve_mostrar_preco(tema):
        preco = extrair_preco(produto.get("descricao_tecnica", ""))
        if preco:
            print(f"Preço do dia ({tema['preco_dia']}): {preco}")
        else:
            print(f"  aviso: tema pede preco hoje, mas '{produto['id']}' nao tem preco na ficha tecnica")

    pasta_saida = f"saida/carrossel_{produto['id']}_{formato}"
    dados_formato = montar_dados_formato(
        formato, campanha, foto_hero, produto=produto, extras=extras, preco=preco
    )
    slides = gerar_carrossel(formato, produto["id"], pasta_saida=pasta_saida, **dados_formato)
    print(f"Slides montados: {slides}")

    stories = montar_stories_do_post(pasta_saida, foto_hero, produto, campanha, historico, preco=preco)
    print(f"Stories montados: {stories}")

    linguagem = (tema or {}).get("linguagem")
    legenda = gerar_legenda_ia(produto, campanha, linguagem) if linguagem else montar_legenda(campanha, produto)
    if preco and preco not in legenda:
        legenda = f"{legenda}\n\n💰 Por {preco}"
    print(f"\nLegenda:\n{legenda}\n")

    if not publicar:
        print("Modo preview (sem --publicar) -- nada foi enviado pro storage nem publicado.")
        return

    urls = enviar_carrossel(slides)
    post_id = publicar_carrossel(urls, legenda)
    print(f"Publicado com sucesso! ID do post: {post_id}")

    urls_stories = [enviar_para_storage(caminho) for caminho in stories]
    story_ids = [publicar_story(url) for url in urls_stories]
    print(f"Stories publicados com sucesso! IDs: {story_ids}")

    historico.append({
        "data": date.today().isoformat(),
        "produto_id": produto["id"],
        "campanha": campanha["chave"] if campanha else None,
        "formato": formato,
        "post_id": post_id,
        "story_ids": story_ids,
    })
    _salvar_historico(historico)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--publicar", action="store_true", help="Publica de verdade no Instagram")
    args = parser.parse_args()
    rodar(publicar=args.publicar)
