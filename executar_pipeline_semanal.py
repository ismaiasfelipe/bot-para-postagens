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
    gerar_foto_composta_ambiente_com_verificacao,
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

# Biblioteca de fotos de ambiente PRONTAS (comodo real, limpo, sem nenhum
# produto) baixadas do Drive (pasta "ambientes" em referencias e exemplos)
# -- ver _escolher_pasta_ambiente/_fotos_ambiente_candidatas. Usada pra
# compor a foto do produto DENTRO de um desses comodos (gerar_carrossel_
# gemini.gerar_foto_composta_ambiente_com_verificacao), em vez de so
# recriar a cena da unica foto de referencia que cada produto tem -- da
# variedade de ambiente de verdade entre produtos/slides diferentes.
PASTA_AMBIENTES_REF = Path("ambientes_referencia")

# categoria do catalogo (ver produtos_reais.json) -> nome da subpasta em
# ambientes_referencia/. "cama (quarto)" e "infantil" sao tratados a parte
# em _escolher_pasta_ambiente (casal vs solteiro, por palavra no nome).
PASTA_AMBIENTE_POR_CATEGORIA = {
    "Banho": "banheiro",
    "Sofá": "sala_de_estar",
}

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


def _escolher_pasta_ambiente(produto: dict) -> str | None:
    """
    Decide qual subpasta de ambientes_referencia/ combina com a categoria
    do produto. "cama (quarto)" e "infantil" variam entre quarto_casal e
    quarto_solteiro pela PALAVRA no nome do produto (ex: "... casal/box"
    vs "... solteiro"); infantil cai em quarto_solteiro por padrao (decidido
    com o usuario em 06/10/2026 -- produtos infantis de cama costumam ser
    tamanho solteiro, e ainda nao existe uma pasta "quarto infantil"
    dedicada). "mesa (cozinha)" varia entre cozinha e sala_de_jantar pelo
    nome (toalha de mesa -> sala de jantar; o resto -> cozinha).

    Retorna None se a categoria nao bater com nenhuma pasta conhecida --
    o chamador cai pro fallback (gerar_foto_hero_com_verificacao).
    """
    categoria = produto["categoria"]
    nome = produto["nome"].lower()

    if _categoria_bate(categoria, "Cama") or _categoria_bate(categoria, "Infantil"):
        if _categoria_bate(categoria, "Infantil"):
            return "quarto_solteiro"
        return "quarto_solteiro" if "solteiro" in nome else "quarto_casal"

    if _categoria_bate(categoria, "Mesa"):
        return "sala_de_jantar" if "mesa" in nome else "cozinha"

    for categoria_campanha, pasta in PASTA_AMBIENTE_POR_CATEGORIA.items():
        if _categoria_bate(categoria, categoria_campanha):
            return pasta

    return None


def _fotos_ambiente_disponiveis(nome_pasta: str) -> list[str]:
    pasta = PASTA_AMBIENTES_REF / nome_pasta
    if not pasta.exists():
        return []
    return sorted(str(p) for p in pasta.iterdir() if p.is_file())


def _indice_estavel(texto: str, modulo: int) -> int:
    """
    Indice DETERMINISTICO (nao aleatorio) a partir de um texto -- o mesmo
    produto sempre escolhe a mesma foto de ambiente principal (cache
    estavel entre rodadas, sem gastar geracao nova a toa), mas produtos
    diferentes tendem a cair em indices diferentes da pasta.
    """
    return int(hashlib.sha1(texto.encode("utf-8")).hexdigest(), 16) % modulo


def _fotos_ambiente_candidatas(produto: dict) -> list[str]:
    """
    Todas as fotos de ambiente disponiveis pra categoria do produto,
    ORDENADAS a partir de um indice estavel por produto (mesmo produto
    sempre comeca pela mesma, produtos diferentes tendem a comecar em
    pontos diferentes da pasta), em vez de so UMA foto fixa. Usada tanto
    pra tentar VARIAS salas antes de desistir (ver obter_foto_hero --
    corrigido em 07/10/2026 depois do usuario reportar que o slide 1
    ainda caia na cena antiga/crua quando a 1a sala tentada falhava)
    quanto pra escolher salas diferentes pros varios slides do vitrine.
    """
    nome_pasta = _escolher_pasta_ambiente(produto)
    candidatos = _fotos_ambiente_disponiveis(nome_pasta) if nome_pasta else []
    if not candidatos:
        return []
    indice_inicial = _indice_estavel(produto["id"], len(candidatos))
    return [candidatos[(indice_inicial + i) % len(candidatos)] for i in range(len(candidatos))]


def _foto_estampa_indice(produto: dict, indice: int) -> str | None:
    """
    produto['fotos_estampas'][indice] -- fotos de catalogo limpas (fundo
    branco, sem embalagem), uma por estampa real diferente que esse
    modelo tem disponivel (pasta "estampas" do Drive).

    Indice FIXO por slide (0=hero, 1=variacao de ambiente, 2+=grid),
    nao mais um hash -- corrigido em 07/10/2026 depois do usuario
    reportar que o slide 2 saiu com a MESMA estampa do slide 1: dois
    hashes diferentes podiam cair no mesmo indice por coincidencia, e
    nao havia garantia nenhuma de que dois slides nao repetissem. Com
    indice fixo por posicao, cada slide usa uma estampa DIFERENTE da
    lista por construcao (contanto que a lista seja grande o bastante).

    Retorna None se o produto nao tiver fotos_estampas suficientes pra
    esse indice -- o chamador deve tratar como "sem variedade aqui".
    """
    fotos = produto.get("fotos_estampas") or []
    if indice >= len(fotos):
        return None
    return fotos[indice]


def _obter_foto_composta(
    produto: dict, caminho_ambiente: str, sufixo_cache: str, caminho_estampa_override: str | None = None
) -> str | None:
    """
    Reaproveita uma composicao ja verificada em cache_hero/ se existir
    pra essa mesma combinacao de produto+ambiente+estampa; senao gera
    via Gemini (gerar_foto_composta_ambiente_com_verificacao) e salva no
    cache so se aprovada.

    caminho_estampa_override: quando passado, usa essa foto individual
    de produto['fotos_estampas'] (ver _foto_estampa_indice) como
    referencia de padrao/cor, em vez de imagem_estampa/imagem_ambiente
    -- pra dar variedade de estampa de verdade entre os slides, nao so
    de ambiente.
    """
    pasta_cache = Path("cache_hero")
    pasta_cache.mkdir(exist_ok=True)
    assinatura_ambiente = hashlib.sha1(caminho_ambiente.encode("utf-8")).hexdigest()[:8]
    partes_nome = [_chave_cache_hero(produto), sufixo_cache, assinatura_ambiente]
    if caminho_estampa_override:
        partes_nome.append(hashlib.sha1(caminho_estampa_override.encode("utf-8")).hexdigest()[:8])
    caminho_cache = pasta_cache / (f"{'_'.join(partes_nome)}.png")
    if caminho_cache.exists():
        return str(caminho_cache)

    aprovado = gerar_foto_composta_ambiente_com_verificacao(
        produto,
        caminho_ambiente,
        nome_arquivo=f"{produto['id']}_{sufixo_cache}",
        referencias_fidelidade_override=[caminho_estampa_override] if caminho_estampa_override else None,
    )
    if aprovado is None:
        return None

    caminho_cache.write_bytes(Path(aprovado).read_bytes())
    return str(caminho_cache)


def obter_foto_hero(produto: dict) -> str | None:
    """
    Foto principal do produto. Forma PRINCIPAL (desde 06/10/2026): compoe
    o produto dentro de uma foto de ambiente PRONTA e limpa da biblioteca
    local (ver _fotos_ambiente_candidatas/ambientes_referencia/),
    escolhida pela categoria do produto. Usa fotos_estampas[0] (ver
    _foto_estampa_indice) como estampa de referencia quando disponivel,
    pra deixar explicito e controlavel qual estampa cada slide do
    vitrine usa (em vez de depender de qual estampa imagem_ambiente
    mostra, que podia coincidir com a escolhida pra outro slide).

    Tenta TODAS as salas disponiveis da categoria (nao so a 1a) antes de
    desistir -- corrigido em 07/10/2026: o usuario reportou que o slide
    1 ainda saia com a cena de referencia antiga/crua ("o quarto que não
    é para ser usado") sempre que a 1a sala falhava na verificacao;
    agora so cai nesse fallback depois de esgotar TODAS as salas da
    categoria.

    Fallback (gerar_foto_hero_com_verificacao, edita a cena da propria
    foto de referencia): usado so quando a categoria nao bate com
    nenhuma pasta de ambiente conhecida, ou quando NENHUMA sala da
    biblioteca funcionou.

    Retorna None se reprovar em todas as tentativas (dos dois metodos) --
    o chamador deve pular esse produto, nunca publicar uma foto reprovada.
    """
    estampa = _foto_estampa_indice(produto, 0)
    for foto_ambiente in _fotos_ambiente_candidatas(produto):
        composta = _obter_foto_composta(produto, foto_ambiente, "hero", estampa)
        if composta:
            return composta

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
    Close-up/macro do tecido do produto, pro slide de fechamento do
    formato "vitrine" (ver montar_dados_formato) -- combinado com a foto
    hero, mostrando a MESMA estampa (fotos_estampas[0], igual ao hero)
    de perto. Reaproveita cache_hero/ se ja existir; senao gera via
    Gemini (gerar_foto_estampa_close_com_verificacao).

    Retorna None se o produto nao tiver nenhuma referencia real ou tudo
    reprovar -- o chamador (_construir_vitrine) cai pra repetir a foto
    principal nesse caso.
    """
    pasta_cache = Path("cache_hero")
    pasta_cache.mkdir(exist_ok=True)

    estampa = _foto_estampa_indice(produto, 0)
    if estampa:
        assinatura = hashlib.sha1(estampa.encode("utf-8")).hexdigest()[:8]
        caminho_cache_estampa = pasta_cache / f"{_chave_cache_hero(produto)}_estampa_close_{assinatura}.png"
        if caminho_cache_estampa.exists():
            return str(caminho_cache_estampa)
        aprovado = gerar_foto_estampa_close_com_verificacao(produto, referencias_override=[estampa])
        if aprovado is not None:
            caminho_cache_estampa.write_bytes(Path(aprovado).read_bytes())
            return str(caminho_cache_estampa)

    caminho_cache = pasta_cache / f"{_chave_cache_hero(produto)}_estampa_close.png"
    if caminho_cache.exists():
        return str(caminho_cache)

    aprovado = gerar_foto_estampa_close_com_verificacao(produto)
    if aprovado is None:
        return None

    caminho_cache.write_bytes(Path(aprovado).read_bytes())
    return str(caminho_cache)


def obter_foto_ambiente_variacao(produto: dict) -> str | None:
    """
    2a foto do produto MONTADO (cama/jogo inteiro, nao close de tecido),
    pra variar os slides do formato "vitrine" em vez de repetir a foto
    principal em todos. Usa uma sala DIFERENTE da tentada primeiro pro
    hero (ver _fotos_ambiente_candidatas) E, quando disponivel, uma
    estampa DIFERENTE (fotos_estampas[1], ver _foto_estampa_indice) --
    corrigido em 07/10/2026: antes usava um indice escolhido por hash
    que podia coincidir com o do hero (usuario reportou slide 1 e 2 com
    a mesma estampa); agora e sempre indice 1, garantido diferente do
    indice 0 usado no hero.

    Retorna None se a categoria nao tiver pelo menos 2 salas (sem uma 2a
    opcao de verdade), ou se tudo reprovar na verificacao -- o chamador
    (_construir_vitrine) cai pra reaproveitar a foto principal.
    """
    salas = _fotos_ambiente_candidatas(produto)
    if len(salas) < 2:
        return None
    estampa = _foto_estampa_indice(produto, 1) or _foto_estampa_indice(produto, 0)

    # comeca pela 2a sala da lista (a 1a e a que obter_foto_hero tenta
    # primeiro) e gira a partir dai, nunca pela 1a -- minimiza (sem
    # garantir 100%, se a 2a sala tambem falhar) repetir a MESMA sala do
    # hero.
    for foto_ambiente in salas[1:] + salas[:1]:
        composta = _obter_foto_composta(produto, foto_ambiente, "ambiente_var", estampa)
        if composta:
            return composta
    return None


def obter_fotos_estampas_grid(produto: dict, quantidade: int = 3) -> list[str] | None:
    """
    Ate `quantidade` fotos do produto MONTADO (cama/jogo inteiro em
    ambiente, NAO close de tecido) pro grid de variedade do slide 3 do
    formato "vitrine", cada uma com uma estampa real DIFERENTE
    (fotos_estampas[2], [3], [4]... continuando depois dos indices 0/1
    ja usados pro hero/variacao -- ver _foto_estampa_indice) e, quando
    possivel, uma sala tambem diferente.

    Corrigido em 07/10/2026 a pedido do usuario -- duas correcoes na
    mesma tacada:
    (1) "não era pra colocar close nas estampas, era pra aparecer camas
    inteiras com estampas diferentes": a 1a tentativa gerava closes de
    tecido (gerar_foto_estampa_close_com_verificacao); agora reaproveita
    o MESMO gerador de composicao em ambiente do hero/variacao
    (_obter_foto_composta), so que com uma sala+estampa por item do
    grid.
    (2) "no slide 3 tem duas estampas iguais": a versao anterior pegava
    fotos_estampas[:quantidade] sempre a partir do indice 0 -- podia
    repetir a mesma estampa ja usada no hero (indice 0) ou colidir com
    indices escolhidos por hash noutros slides. Agora usa indices FIXOS
    e exclusivos (2, 3, 4...), nunca sobrepondo hero (0) ou variacao (1).

    Retorna None se o produto nao tiver pelo menos 2 estampas sobrando
    (alem das ja usadas em hero/variacao), ou se tudo reprovar -- o
    chamador (_construir_vitrine) cai pro grid antigo (fotos de
    ambiente/hero repetidas).
    """
    salas = _fotos_ambiente_candidatas(produto)
    if not salas:
        return None

    resultado = []
    for i in range(quantidade):
        estampa = _foto_estampa_indice(produto, i + 2)
        if not estampa:
            break
        foto_ambiente = salas[(i + 2) % len(salas)]
        composta = _obter_foto_composta(produto, foto_ambiente, f"grid{i}", estampa)
        if composta:
            resultado.append(composta)

    return resultado if len(resultado) >= 2 else None


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
        # Gera (com cache) uma 2a foto de ambiente (outro angulo/
        # composicao), um close-up do tecido, e ate 3 closes de estampas
        # REAIS diferentes pro grid (fotos_estampas_grid) -- None em
        # qualquer uma faz _construir_vitrine cair pro fallback
        # (reaproveita a principal).
        return {
            "foto_principal": foto_hero,
            "foto_ambiente_variacao": obter_foto_ambiente_variacao(produto),
            "foto_estampa_close": obter_foto_estampa_close(produto),
            "fotos_estampas": obter_fotos_estampas_grid(produto),
            "campanha": campanha,
        }
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
