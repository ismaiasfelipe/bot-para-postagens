"""
Composicao de Stories (1 imagem, formato retrato) - IL Variedades Enxovais

O QUE ESTE SCRIPT FAZ
----------------------
Monta a imagem final de um Story (1080x1920, 9:16 -- Instagram nao aceita
story fora dessa proporcao) a partir dos mesmos ingredientes usados no
carrossel: foto do produto/ambiente, paleta e fontes da marca.

REESCRITO em 05/10/2026 depois de catalogar visualmente os 10 wireframes
reais da pasta do Drive "referencias e exemplos/exemplo de stories"
(story1 a story10) -- a versao anterior deste arquivo usava layouts
inventados (oval generico, grid numerado etc. copiados do carrossel) que
NAO correspondiam aos wireframes reais. Cada funcao abaixo agora reproduz
a ESTRUTURA EXATA (posicoes, proporcoes, geometria) de um wireframe
especifico, so trocando os placeholders "imagem"/"Texto" pelo conteudo
real -- exatamente a regra que o usuario pediu pro projeto inteiro.

10 blocos (um por wireframe) cobrem os 20 padroes documentados em
"copy's para stories/20 Padroes de Stories" (varios padroes reaproveitam
o mesmo bloco estrutural, so trocando texto/foto -- igual o carrossel
reaproveita poucos blocos pra 10 formatos nomeados):

  montar_story_cartao_app       (story1)  -> vitrine, novidade,
                                              ambiente_inspiracao
  montar_story_texto_puro       (story2)  -> promocao_relampago,
                                              pergunta_engajamento
  montar_story_oval_vertical    (story3)  -> detalhe_textura,
                                              detalhe_emocional
  montar_story_foto_minimal     (story4)  -> produto_dobrado,
                                              preco_destaque, contagem_prazo
  montar_story_duas_fotos_moldura (story5)-> combo_sugerido, paleta_em_foco,
                                              qual_estilo, enquete_produto
  montar_story_abas_onduladas   (story6)  -> campanha_tema,
                                              (fechamento/CTA generico)
  montar_story_circulo_fita     (story7)  -> complete_o_look,
                                              combina_com_campanha
  montar_story_trio_circulos    (story8)  -> estampas_disponiveis,
                                              itens_inclusos
  montar_story_banner_topo      (story9)  -> giro_categoria (legenda simples)
  montar_story_grade_2x2        (story10) -> giro_categoria, itens_inclusos

NOTA SOBRE ENQUETE/CAIXINHA DE PERGUNTA
----------------------------------------
A API do Instagram nao permite inserir sticker nativo (enquete, caixinha
de pergunta) numa publicacao automatizada -- isso so da pra fazer
manualmente, direto no app, depois de publicado. As funcoes abaixo pra
enquete_produto_story e pergunta_engajamento_story geram so a imagem de
fundo; o sticker em si tem que ser adicionado a mao.

NOTA SOBRE TEXTO
----------------
A API tambem nao renderiza "caption" em Stories -- todo texto tem que
estar desenhado na propria imagem (ja e o que todas as funcoes abaixo
fazem).

COMO RODAR
----------
pip install Pillow --break-system-packages
python montar_story.py
"""

import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from montar_carrossel_campanha import (
    FONTE_SCRIPT,
    FONTE_TEXTO,
    FONTE_TITULO,
    OFF_WHITE,
    ROSA_QUARTZO,
    ROXO_NOBRE,
    _carregar_fonte,
    _cobrir_quadrado,
    _cobrir_retangulo,
    _forma_blob,
    _hex_para_rgb,
    _quebrar_linhas,
    _rotacionar_com_sombra,
    _texto_centralizado,
)

LARGURA, ALTURA = 1080, 1920


def _mascara_onda(largura: int, altura: int, y_base: int, amplitude: int, lado: str = "baixo", fase: float = 0.0) -> Image.Image:
    """
    Mascara de uma faixa dividida por uma linha ondulada (1 senoide
    completa) -- motivo das 'abas' onduladas vistas no wireframe real
    (exemplo de stories - story6). lado='baixo' preenche tudo ABAIXO da
    onda; lado='cima' preenche tudo ACIMA.
    """
    mask = Image.new("L", (largura, altura), 0)
    draw = ImageDraw.Draw(mask)
    pontos = []
    for x in range(0, largura + 1, 10):
        y = y_base + amplitude * math.sin(2 * math.pi * x / largura + fase)
        pontos.append((x, y))
    if lado == "baixo":
        pontos = [(0, altura)] + pontos + [(largura, altura)]
    else:
        pontos = [(0, 0)] + pontos + [(largura, 0)]
    draw.polygon(pontos, fill=255)
    return mask


def _forma_fita(largura: int, altura: int, raio_canto: int = 18, profundidade_notch: float = 0.4) -> Image.Image:
    """
    Mascara de 'fita/marcador de pagina' (ribbon) -- retangulo com os 2
    cantos de cima arredondados e um entalhe triangular (V) cortado da
    base. Motivo visto nos wireframes reais (exemplo de carrosseis -
    ex9/slide2 e exemplo de stories - story7).
    """
    mask = Image.new("L", (largura, altura), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, largura, altura), radius=raio_canto, fill=255)
    largura_notch = largura * 0.5
    x0 = (largura - largura_notch) / 2
    profundidade = altura * profundidade_notch
    draw.polygon(
        [(x0, altura), (x0 + largura_notch / 2, altura - profundidade), (x0 + largura_notch, altura)],
        fill=0,
    )
    return mask


def _moldura_retrato(imagem: Image.Image, largura: int, altura: int, borda: int = 12) -> Image.Image:
    """
    Moldura tipo 'print de foto' -- borda off-white fina uniforme nos 4
    lados + contorno escuro fino por fora. Motivo das 2 fotos
    sobrepostas inclinadas do wireframe real (exemplo de stories -
    story5), diferente da moldura polaroid (que tem base grossa).
    """
    foto = _cobrir_retangulo(imagem, largura - borda * 2, altura - borda * 2)
    moldura = Image.new("RGB", (largura, altura), _hex_para_rgb(OFF_WHITE))
    moldura.paste(foto, (borda, borda))
    ImageDraw.Draw(moldura).rectangle((0, 0, largura - 1, altura - 1), outline=(40, 40, 40), width=3)
    return moldura


def montar_story_cartao_app(
    foto_produto: str,
    texto_banner: str,
    titulo_card: str,
    legenda: str,
    caminho_saida: str,
) -> None:
    """
    Banner solto no topo + 'cartao' branco (estilo print de app) com
    cabecalho proprio e a foto preenchendo o resto do cartao + legenda
    solta embaixo. Baseado no wireframe real (exemplo de stories - story1).
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    draw = ImageDraw.Draw(tela)

    bx0, by0 = 0, int(ALTURA * 0.14)
    bx1, by1 = int(LARGURA * 0.80), by0 + int(ALTURA * 0.05)
    draw.rectangle((bx0, by0, bx1, by1), fill=_hex_para_rgb(ROXO_NOBRE))
    fonte_banner = _carregar_fonte(FONTE_TITULO, 34, "Bold")
    _texto_centralizado(draw, (bx0 + bx1) // 2, by0 + 20, texto_banner, fonte_banner, _hex_para_rgb(OFF_WHITE))

    cx0, cy0 = int(LARGURA * 0.08), int(ALTURA * 0.27)
    cx1, cy1 = int(LARGURA * 0.92), int(ALTURA * 0.84)
    largura_card, altura_card = cx1 - cx0, cy1 - cy0

    sombra = Image.new("RGBA", tela.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle((cx0, cy0 + 14, cx1, cy1 + 14), radius=36, fill=(0, 0, 0, 70))
    sombra = sombra.filter(ImageFilter.GaussianBlur(18))
    tela = Image.alpha_composite(tela.convert("RGBA"), sombra).convert("RGB")

    card = Image.new("RGB", (largura_card, altura_card), _hex_para_rgb(OFF_WHITE))
    draw_card = ImageDraw.Draw(card)

    altura_cabecalho = int(altura_card * 0.08)
    fonte_titulo_card = _carregar_fonte(FONTE_TITULO, 32, "Bold")
    draw_card.text((34, (altura_cabecalho - 32) // 2), titulo_card, font=fonte_titulo_card, fill=_hex_para_rgb(ROXO_NOBRE))
    for i in range(3):
        cy = altura_cabecalho // 2 - 18 + i * 18
        draw_card.ellipse((largura_card - 42, cy - 4, largura_card - 34, cy + 4), fill=_hex_para_rgb(ROSA_QUARTZO))

    foto = _cobrir_retangulo(Image.open(foto_produto), largura_card, altura_card - altura_cabecalho)
    card.paste(foto, (0, altura_cabecalho))

    mascara_card = Image.new("L", (largura_card, altura_card), 0)
    ImageDraw.Draw(mascara_card).rounded_rectangle((0, 0, largura_card, altura_card), radius=36, fill=255)
    tela.paste(card, (cx0, cy0), mascara_card)

    draw = ImageDraw.Draw(tela)
    fonte_legenda = _carregar_fonte(FONTE_TITULO, 36, "Bold")
    _texto_centralizado(draw, LARGURA // 2, cy1 + int(ALTURA * 0.025), legenda, fonte_legenda, _hex_para_rgb(ROXO_NOBRE))

    tela.save(caminho_saida)
    print(f"story (cartao app) salvo em {caminho_saida}")


def montar_story_texto_puro(
    texto_topo: str,
    texto_centro: str,
    texto_rodape: str,
    caminho_saida: str,
) -> None:
    """
    So texto, sem foto -- banner solido flush no topo-esquerda, texto
    solto flutuando no centro e um paralelogramo solido flush na
    base-direita (sangrando pela borda). Baseado no wireframe real
    (exemplo de stories - story2) -- usado pra CTA/enquete/pergunta onde
    nao ha produto pra mostrar.
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    draw = ImageDraw.Draw(tela)

    bx1 = int(LARGURA * 0.78)
    by0, by1 = int(ALTURA * 0.08), int(ALTURA * 0.23)
    draw.rectangle((0, by0, bx1, by1), fill=_hex_para_rgb(ROXO_NOBRE))
    fonte_banner = _carregar_fonte(FONTE_TITULO, 40, "Bold")
    _texto_centralizado(draw, bx1 // 2, (by0 + by1) // 2 - 22, texto_topo, fonte_banner, _hex_para_rgb(OFF_WHITE))

    fonte_centro = _carregar_fonte(FONTE_TITULO, 44, "Bold")
    linhas = _quebrar_linhas(texto_centro, fonte_centro, int(LARGURA * 0.8), draw)
    y = int(ALTURA * 0.43) - len(linhas) * 26
    for linha in linhas:
        _texto_centralizado(draw, LARGURA // 2, y, linha, fonte_centro, _hex_para_rgb(ROXO_NOBRE))
        y += 56

    px0 = int(LARGURA * 0.40)
    py0 = int(ALTURA * 0.75)
    draw.polygon(
        [(px0, py0), (LARGURA, py0), (LARGURA, ALTURA), (px0 - int(LARGURA * 0.18), ALTURA)],
        fill=_hex_para_rgb(ROXO_NOBRE),
    )
    fonte_rodape = _carregar_fonte(FONTE_TITULO, 38, "Bold")
    _texto_centralizado(draw, int(LARGURA * 0.72), py0 + int(ALTURA * 0.12), texto_rodape, fonte_rodape, _hex_para_rgb(OFF_WHITE))

    tela.save(caminho_saida)
    print(f"story (texto puro) salvo em {caminho_saida}")


def montar_story_oval_vertical(
    foto_produto: str,
    texto_banner: str,
    texto_rodape: str,
    legenda_externa: str,
    caminho_saida: str,
) -> None:
    """
    Banner solto no topo + foto recortada num oval vertical + rodape
    solido escuro sobrepondo a base do oval + legenda solta embaixo de
    tudo. Baseado no wireframe real (exemplo de stories - story3).
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    draw = ImageDraw.Draw(tela)

    bx0, bx1 = int(LARGURA * 0.17), int(LARGURA * 0.83)
    by0, by1 = int(ALTURA * 0.06), int(ALTURA * 0.12)
    draw.rectangle((bx0, by0, bx1, by1), fill=_hex_para_rgb(ROXO_NOBRE))
    fonte_banner = _carregar_fonte(FONTE_TITULO, 32, "Bold")
    _texto_centralizado(draw, (bx0 + bx1) // 2, by0 + 12, texto_banner, fonte_banner, _hex_para_rgb(OFF_WHITE))

    ox0, ox1 = int(LARGURA * 0.17), int(LARGURA * 0.83)
    oy0, oy1 = int(ALTURA * 0.17), int(ALTURA * 0.63)
    largura_oval, altura_oval = ox1 - ox0, oy1 - oy0

    foto = _cobrir_retangulo(Image.open(foto_produto), largura_oval, altura_oval)
    mascara_oval = Image.new("L", (largura_oval, altura_oval), 0)
    ImageDraw.Draw(mascara_oval).ellipse((0, 0, largura_oval, altura_oval), fill=255)
    tela.paste(foto, (ox0, oy0), mascara_oval)
    draw.ellipse((ox0, oy0, ox1, oy1), outline=_hex_para_rgb(ROXO_NOBRE), width=4)

    fy0, fy1 = int(ALTURA * 0.67), int(ALTURA * 0.84)
    draw.rectangle((bx0, fy0, bx1, fy1), fill=_hex_para_rgb(ROXO_NOBRE))
    fonte_rodape = _carregar_fonte(FONTE_TITULO, 34, "Bold")
    _texto_centralizado(draw, (bx0 + bx1) // 2, int(ALTURA * 0.79), texto_rodape, fonte_rodape, _hex_para_rgb(OFF_WHITE))

    fonte_legenda = _carregar_fonte(FONTE_TITULO, 36, "Bold")
    _texto_centralizado(draw, LARGURA // 2, int(ALTURA * 0.88), legenda_externa, fonte_legenda, _hex_para_rgb(ROXO_NOBRE))

    tela.save(caminho_saida)
    print(f"story (oval vertical) salvo em {caminho_saida}")


def montar_story_foto_minimal(
    foto_produto: str,
    legenda: str,
    caminho_saida: str,
) -> None:
    """
    Foto full-bleed (ocupa o canvas inteiro) com uma caixa solida flush
    na borda direita, na parte inferior, contendo a legenda -- o layout
    mais simples dos wireframes. Baseado no wireframe real (exemplo de
    stories - story4).
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    foto = _cobrir_retangulo(Image.open(foto_produto), LARGURA, ALTURA)
    tela.paste(foto, (0, 0))

    bx0, by0 = int(LARGURA * 0.30), int(ALTURA * 0.74)
    by1 = int(ALTURA * 0.90)
    overlay = Image.new("RGBA", tela.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle((bx0, by0, LARGURA, by1), fill=_hex_para_rgb(ROXO_NOBRE) + (235,))
    tela = Image.alpha_composite(tela.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(tela)

    fonte_legenda = _carregar_fonte(FONTE_TITULO, 38, "Bold")
    linhas = _quebrar_linhas(legenda, fonte_legenda, LARGURA - bx0 - 60, draw)
    y = (by0 + by1) // 2 - len(linhas) * 24
    for linha in linhas:
        draw.text((bx0 + 40, y), linha, font=fonte_legenda, fill=_hex_para_rgb(OFF_WHITE))
        y += 48

    tela.save(caminho_saida)
    print(f"story (foto minimal) salvo em {caminho_saida}")


def montar_story_duas_fotos_moldura(
    foto_cima: str,
    foto_baixo: str,
    texto_meio: str,
    legenda: str,
    caminho_saida: str,
) -> None:
    """
    2 fotos com moldura tipo print, levemente inclinadas, em cascata
    diagonal, com um cartao branco de texto sobrepondo as duas no meio e
    uma legenda solta no canto superior direito. Baseado no wireframe
    real (exemplo de stories - story5).
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), (90, 90, 90))
    draw = ImageDraw.Draw(tela)

    largura_foto, altura_foto = 540, 760
    moldura1 = _moldura_retrato(Image.open(foto_cima), largura_foto, altura_foto)
    moldura2 = _moldura_retrato(Image.open(foto_baixo), largura_foto, altura_foto)
    girada1 = _rotacionar_com_sombra(moldura1, -6)
    girada2 = _rotacionar_com_sombra(moldura2, 5)
    tela.paste(girada1, (60, 180), girada1)
    tela.paste(girada2, (LARGURA - largura_foto - 60, 960), girada2)

    fonte_legenda = _carregar_fonte(FONTE_TITULO, 36, "Bold")
    draw.text((680, 400), legenda, font=fonte_legenda, fill=_hex_para_rgb(OFF_WHITE))

    largura_card, altura_card = 560, 340
    x_card, y_card = (LARGURA - largura_card) // 2, 760
    sombra = Image.new("RGBA", tela.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle(
        (x_card, y_card + 8, x_card + largura_card, y_card + altura_card + 8), radius=30, fill=(0, 0, 0, 90)
    )
    sombra = sombra.filter(ImageFilter.GaussianBlur(14))
    tela = Image.alpha_composite(tela.convert("RGBA"), sombra).convert("RGB")
    draw = ImageDraw.Draw(tela)
    draw.rounded_rectangle((x_card, y_card, x_card + largura_card, y_card + altura_card), radius=30, fill=_hex_para_rgb(OFF_WHITE))

    fonte_meio = _carregar_fonte(FONTE_TITULO, 40, "Bold")
    linhas = _quebrar_linhas(texto_meio, fonte_meio, largura_card - 80, draw)
    y = y_card + (altura_card - len(linhas) * 48) // 2
    for linha in linhas:
        _texto_centralizado(draw, LARGURA // 2, y, linha, fonte_meio, _hex_para_rgb(ROXO_NOBRE))
        y += 48

    tela.save(caminho_saida)
    print(f"story (duas fotos com moldura) salvo em {caminho_saida}")


def montar_story_abas_onduladas(
    foto_produto: str,
    texto_meio: str,
    texto_cta: str,
    caminho_saida: str,
) -> None:
    """
    Foto no topo ate uma linha ondulada, faixa media ondulada com texto,
    faixa inferior solida com um botao-pilula de CTA. Baseado no
    wireframe real (exemplo de stories - story6).
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    foto = _cobrir_retangulo(Image.open(foto_produto), LARGURA, ALTURA)
    tela.paste(foto, (0, 0))

    y_onda1, y_onda2 = int(ALTURA * 0.56), int(ALTURA * 0.87)
    overlay = Image.new("RGBA", tela.size, (0, 0, 0, 0))
    mascara_meio = _mascara_onda(LARGURA, ALTURA, y_onda1, 40, "baixo")
    faixa_meio = Image.new("RGBA", tela.size, (150, 150, 150, 235))
    overlay.paste(faixa_meio, (0, 0), mascara_meio)
    mascara_base = _mascara_onda(LARGURA, ALTURA, y_onda2, 30, "baixo")
    faixa_base = Image.new("RGBA", tela.size, _hex_para_rgb(ROXO_NOBRE) + (255,))
    overlay.paste(faixa_base, (0, 0), mascara_base)
    tela = Image.alpha_composite(tela.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(tela)

    fonte_meio = _carregar_fonte(FONTE_TITULO, 36, "Bold")
    _texto_centralizado(draw, LARGURA // 2, (y_onda1 + y_onda2) // 2 - 20, texto_meio, fonte_meio, _hex_para_rgb(OFF_WHITE))

    largura_pill, altura_pill = 760, 100
    x_pill = (LARGURA - largura_pill) // 2
    y_pill = int(ALTURA * 0.92)
    draw.rounded_rectangle((x_pill, y_pill, x_pill + largura_pill, y_pill + altura_pill), radius=50, fill=_hex_para_rgb(OFF_WHITE))
    fonte_cta = _carregar_fonte(FONTE_TITULO, 38, "Bold")
    _texto_centralizado(draw, LARGURA // 2, y_pill + 30, texto_cta, fonte_cta, _hex_para_rgb(ROXO_NOBRE))

    tela.save(caminho_saida)
    print(f"story (abas onduladas) salvo em {caminho_saida}")


def montar_story_circulo_fita(
    foto_produto: str,
    texto_fita: str,
    texto_circulo: str,
    legenda_topo: str,
    caminho_saida: str,
) -> None:
    """
    Circulo grande sangrando pelas bordas inferior-esquerda com a foto +
    uma fita/marcador sobrepondo o canto superior-direito do circulo +
    legenda solta no topo do canvas. Baseado no wireframe real (exemplo
    de stories - story7).
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    draw = ImageDraw.Draw(tela)

    fonte_legenda = _carregar_fonte(FONTE_TITULO, 40, "Bold")
    _texto_centralizado(draw, LARGURA // 2, int(ALTURA * 0.07), legenda_topo, fonte_legenda, _hex_para_rgb(ROXO_NOBRE))

    diametro = int(LARGURA * 0.95)
    cx, cy = int(LARGURA * 0.34), int(ALTURA * 0.80)
    raio = diametro // 2
    foto = _cobrir_quadrado(Image.open(foto_produto), diametro)
    mascara_circulo = Image.new("L", (diametro, diametro), 0)
    ImageDraw.Draw(mascara_circulo).ellipse((0, 0, diametro, diametro), fill=255)
    tela.paste(foto, (cx - raio, cy - raio), mascara_circulo)

    mascara_circulo_cheia = Image.new("L", tela.size, 0)
    ImageDraw.Draw(mascara_circulo_cheia).ellipse((cx - raio, cy - raio, cx + raio, cy + raio), fill=255)
    mascara_rodape = Image.new("L", tela.size, 0)
    ImageDraw.Draw(mascara_rodape).rectangle((0, int(ALTURA * 0.88), LARGURA, ALTURA), fill=255)
    mascara_faixa = ImageChops.multiply(mascara_circulo_cheia, mascara_rodape)

    overlay = Image.new("RGBA", tela.size, (0, 0, 0, 0))
    faixa = Image.new("RGBA", tela.size, _hex_para_rgb(ROXO_NOBRE) + (210,))
    overlay.paste(faixa, (0, 0), mascara_faixa)
    tela = Image.alpha_composite(tela.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(tela)

    fonte_circulo = _carregar_fonte(FONTE_TITULO, 38, "Bold")
    _texto_centralizado(draw, cx, int(ALTURA * 0.90), texto_circulo, fonte_circulo, _hex_para_rgb(OFF_WHITE))

    largura_fita, altura_fita = 260, 220
    x_fita, y_fita = cx + int(raio * 0.35), cy - raio - int(altura_fita * 0.25)
    mascara_fita = _forma_fita(largura_fita, altura_fita, raio_canto=18, profundidade_notch=0.35)
    fita = Image.new("RGBA", (largura_fita, altura_fita), _hex_para_rgb(ROSA_QUARTZO) + (255,))
    fita.putalpha(mascara_fita)
    tela.paste(fita, (x_fita, y_fita), fita)
    draw = ImageDraw.Draw(tela)
    fonte_fita = _carregar_fonte(FONTE_TITULO, 32, "Bold")
    _texto_centralizado(draw, x_fita + largura_fita // 2, y_fita + 60, texto_fita, fonte_fita, _hex_para_rgb(OFF_WHITE))

    tela.save(caminho_saida)
    print(f"story (circulo com fita) salvo em {caminho_saida}")


def montar_story_trio_circulos(
    fotos: list[str],
    texto_centro: str,
    caminho_saida: str,
) -> None:
    """
    3 circulos grandes se sobrepondo, cada um sangrando por pelo menos
    uma borda do canvas, com texto solto no espaco negativo entre eles.
    Baseado no wireframe real (exemplo de stories - story8).
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), (150, 150, 150))

    circulos = [
        (int(LARGURA * 0.30), int(ALTURA * 0.02), int(LARGURA * 0.78)),
        (int(LARGURA * 0.78), int(ALTURA * 0.47), int(LARGURA * 0.58)),
        (int(LARGURA * 0.30), int(ALTURA * 0.83), int(LARGURA * 0.76)),
    ]
    for (cx, cy, diametro), caminho_foto in zip(circulos, fotos[:3]):
        raio = diametro // 2
        foto = _cobrir_quadrado(Image.open(caminho_foto), diametro)
        mascara_circulo = Image.new("L", (diametro, diametro), 0)
        ImageDraw.Draw(mascara_circulo).ellipse((0, 0, diametro, diametro), fill=255)
        base = Image.new("RGBA", tela.size, (0, 0, 0, 0))
        base.paste(foto, (cx - raio, cy - raio), mascara_circulo)
        tela = Image.alpha_composite(tela.convert("RGBA"), base).convert("RGB")
        draw = ImageDraw.Draw(tela)
        draw.ellipse((cx - raio, cy - raio, cx + raio, cy + raio), outline=(90, 90, 90), width=4)

    draw = ImageDraw.Draw(tela)
    fonte_centro = _carregar_fonte(FONTE_TITULO, 40, "Bold")
    linhas = _quebrar_linhas(texto_centro, fonte_centro, int(LARGURA * 0.3), draw)
    y = int(ALTURA * 0.47) - len(linhas) * 24
    for linha in linhas:
        draw.text((int(LARGURA * 0.08), y), linha, font=fonte_centro, fill=(20, 20, 20))
        y += 48

    tela.save(caminho_saida)
    print(f"story (trio de circulos) salvo em {caminho_saida}")


def montar_story_banner_topo(
    foto_produto: str,
    texto_banner: str,
    legenda_centro: str,
    caminho_saida: str,
) -> None:
    """
    Foto full-bleed com um banner solido perto do topo + legenda solta
    flutuando mais abaixo -- o layout mais direto, pra textos curtos de
    efeito. Baseado no wireframe real (exemplo de stories - story9).
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    foto = _cobrir_retangulo(Image.open(foto_produto), LARGURA, ALTURA)
    tela.paste(foto, (0, 0))
    draw = ImageDraw.Draw(tela)

    bx0, bx1 = int(LARGURA * 0.17), int(LARGURA * 0.82)
    by0, by1 = int(ALTURA * 0.15), int(ALTURA * 0.23)
    draw.rectangle((bx0, by0, bx1, by1), fill=(70, 70, 70))
    fonte_banner = _carregar_fonte(FONTE_TITULO, 34, "Bold")
    linhas = _quebrar_linhas(texto_banner, fonte_banner, bx1 - bx0 - 40, draw)
    y = (by0 + by1) // 2 - len(linhas) * 22
    for linha in linhas:
        _texto_centralizado(draw, (bx0 + bx1) // 2, y, linha, fonte_banner, _hex_para_rgb(OFF_WHITE))
        y += 44

    fonte_legenda = _carregar_fonte(FONTE_TITULO, 40, "Bold")
    _texto_centralizado(draw, LARGURA // 2, int(ALTURA * 0.46), legenda_centro, fonte_legenda, (20, 20, 20))

    tela.save(caminho_saida)
    print(f"story (banner no topo) salvo em {caminho_saida}")


def montar_story_grade_2x2(
    fotos: list[str],
    celula_texto: int,
    texto: str,
    caminho_saida: str,
) -> None:
    """
    Grade 2x2 flush preenchendo o canvas inteiro, com 3 fotos e 1 celula
    de texto solido. celula_texto: indice 0-3 (0=sup-esq, 1=sup-dir,
    2=inf-esq, 3=inf-dir). Baseado no wireframe real (exemplo de stories
    - story10).
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(ROXO_NOBRE))
    draw = ImageDraw.Draw(tela)

    largura_cel, altura_cel = LARGURA // 2, ALTURA // 2
    fonte_celula = _carregar_fonte(FONTE_TITULO, 40, "Bold")

    indice_foto = 0
    for indice in range(4):
        linha, coluna = divmod(indice, 2)
        x, y = coluna * largura_cel, linha * altura_cel
        if indice == celula_texto:
            draw.rectangle((x, y, x + largura_cel, y + altura_cel), fill=_hex_para_rgb(ROXO_NOBRE))
            _texto_centralizado(draw, x + largura_cel // 2, y + altura_cel // 2 - 20, texto, fonte_celula, _hex_para_rgb(OFF_WHITE))
        else:
            foto = _cobrir_retangulo(Image.open(fotos[indice_foto]), largura_cel, altura_cel)
            tela.paste(foto, (x, y))
            indice_foto += 1

    tela.save(caminho_saida)
    print(f"story (grade 2x2) salvo em {caminho_saida}")


if __name__ == "__main__":
    foto_principal = "saida/p001_1.png"
    fotos_exemplo = [
        "saida/p001_1.png", "saida/p001_v1_1.png", "saida/p002_1.png",
        "saida/p002_v1_0.png", "saida/p003_1.png",
    ]

    montar_story_cartao_app(foto_principal, "NOVA COLEÇÃO", "Jogo de Quarto", "Confira os detalhes", "saida/teste_story1.png")
    montar_story_texto_puro("OFERTA ESPECIAL", "O que você achou dessa estampa?", "Responda", "saida/teste_story2.png")
    montar_story_oval_vertical(foto_principal, "DESTAQUE", "Toque de elegância", "Confira mais", "saida/teste_story3.png")
    montar_story_foto_minimal(foto_principal, "Conforto em cada detalhe", "saida/teste_story4.png")
    montar_story_duas_fotos_moldura(foto_principal, fotos_exemplo[1], "Combine e renove", "Veja como", "saida/teste_story5.png")
    montar_story_abas_onduladas(foto_principal, "Qualidade em cada fio", "Saiba mais", "saida/teste_story6.png")
    montar_story_circulo_fita(foto_principal, "Novo", "Peça completa", "Inspiração do dia", "saida/teste_story7.png")
    montar_story_trio_circulos(fotos_exemplo[:3], "Estampas disponíveis", "saida/teste_story8.png")
    montar_story_banner_topo(foto_principal, "PROMOÇÃO RELÂMPAGO", "Só até domingo!", "saida/teste_story9.png")
    montar_story_grade_2x2(fotos_exemplo[:3], 3, "Saiba mais", "saida/teste_story10.png")
