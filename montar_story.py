"""
Composicao de Stories (1 imagem, formato retrato) - IL Variedades Enxovais

O QUE ESTE SCRIPT FAZ
----------------------
Monta a imagem final de um Story (1080x1920, 9:16 -- Instagram nao aceita
story fora dessa proporcao) a partir dos mesmos ingredientes usados no
carrossel: foto do produto/ambiente, paleta e fontes da marca.

Reaproveita os helpers de desenho ja validados em
montar_carrossel_campanha.py (cores, fontes, corte de imagem, quebra de
linha) -- so os blocos de composicao aqui sao novos, adaptados pro
canvas mais alto e mais estreito do story.

8 blocos cobrem os 20 padroes documentados em
"copy's para stories/20 Padroes de Stories" (cada padrao e so uma
combinacao de texto/foto diferente num desses blocos, igual o carrossel
reaproveita 4 blocos pra 10 formatos):

  montar_story_foto           -> vitrine, novidade, ambiente_inspiracao,
                                  produto_dobrado, preco_destaque,
                                  contagem_prazo, campanha_tema
  montar_story_zoom            -> detalhe_textura, detalhe_emocional
  montar_story_itens           -> itens_inclusos
  montar_story_estampas        -> estampas_disponiveis
  montar_story_texto           -> pergunta_engajamento, promocao_relampago
  montar_story_duas_fotos      -> combo_sugerido, paleta_em_foco,
                                  qual_estilo, enquete_produto (ver nota)
  montar_story_grid_numerado   -> giro_categoria
  montar_story_destaque_secundario -> complete_o_look, combina_com_campanha

NOTA SOBRE ENQUETE/CAIXINHA DE PERGUNTA
----------------------------------------
A API do Instagram nao permite inserir sticker nativo (enquete, caixinha
de pergunta) numa publicacao automatizada -- isso so da pra fazer
manualmente, direto no app, depois de publicado. As funcoes abaixo pra
enquete_produto_story e pergunta_engajamento_story geram só a imagem de
fundo; o sticker em si tem que ser adicionado a mao.

NOTA SOBRE TEXTO
----------------
Igual no carrossel, nenhum texto fica por conta do Gemini -- tudo que
aparece escrito e desenhado aqui via Pillow, com a fonte real da marca,
calculando quebra de linha pra nunca vazar da caixa.

COMO RODAR
----------
pip install Pillow --break-system-packages
python montar_story.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from montar_carrossel_campanha import (
    FONTE_SCRIPT,
    FONTE_TEXTO,
    FONTE_TITULO,
    LOGO_PADRAO,
    OFF_WHITE,
    ROSA_QUARTZO,
    ROXO_NOBRE,
    _carregar_fonte,
    _cobrir_quadrado,
    _cobrir_retangulo,
    _forma_um_canto_arredondado,
    _hex_para_rgb,
    _quebrar_linhas,
    _texto_centralizado,
)

LARGURA, ALTURA = 1080, 1920


def montar_story_foto(
    foto_produto: str,
    caminho_saida: str,
    badge_linha1: str | None = None,
    badge_linha2: str | None = None,
    frase: str | None = None,
    logo: bool = False,
) -> None:
    """
    Foto full-bleed ocupando o story todo -- bloco mais usado, cobre a
    maioria dos padroes de "1 produto em foco".

    badge_linha1/2: banner no canto superior esquerdo (igual o hero do
    carrossel) -- usar pra "NOVIDADE", "SO CHEGOU", tema de campanha etc.
    frase: texto curto numa faixa semitransparente na base -- usar pra
    CTA, preco, prazo ou frase de tom de voz. Nunca inventar preco/prazo:
    só preencher quando o dado vier confirmado de fora.
    logo: se True, cola o badge da marca (assets/logo_badge.png) num
    canto inferior, discreto -- usado no padrao produto_dobrado.
    """
    tela = _cobrir_retangulo(Image.open(foto_produto), LARGURA, ALTURA)
    tela = tela.convert("RGB")
    draw = ImageDraw.Draw(tela)

    if badge_linha1:
        largura_banner, altura_banner = 420, 150
        draw.rectangle((0, 0, largura_banner, altura_banner), fill=_hex_para_rgb(OFF_WHITE))
        draw.rectangle((0, altura_banner - 5, largura_banner, altura_banner), fill=_hex_para_rgb(ROSA_QUARTZO))
        fonte_b1 = _carregar_fonte(FONTE_TITULO, 36, "Bold")
        draw.text((32, 28), badge_linha1, font=fonte_b1, fill=_hex_para_rgb(ROXO_NOBRE))
        if badge_linha2:
            fonte_b2 = _carregar_fonte(FONTE_TITULO, 46, "Bold")
            draw.text((32, 76), badge_linha2, font=fonte_b2, fill=_hex_para_rgb(ROSA_QUARTZO))

    if frase:
        fonte_frase = _carregar_fonte(FONTE_TITULO, 38, "Bold")
        largura_max = LARGURA - 140
        linhas = _quebrar_linhas(frase.upper(), fonte_frase, largura_max, draw)
        altura_faixa = 90 + len(linhas) * 50

        faixa = Image.new("RGBA", (LARGURA, altura_faixa), _hex_para_rgb(ROXO_NOBRE) + (210,))
        tela_rgba = tela.convert("RGBA")
        y_faixa = ALTURA - altura_faixa - (260 if logo else 0)
        tela_rgba.paste(faixa, (0, y_faixa), faixa)
        tela = tela_rgba.convert("RGB")
        draw = ImageDraw.Draw(tela)

        y = y_faixa + 45
        for linha in linhas:
            _texto_centralizado(draw, LARGURA // 2, y, linha, fonte_frase, _hex_para_rgb(OFF_WHITE))
            y += 50

    if logo:
        caminho_logo = Path(LOGO_PADRAO)
        if caminho_logo.exists():
            logo_img = Image.open(caminho_logo).convert("RGBA")
            lado_logo = 170
            escala = lado_logo / max(logo_img.size)
            logo_img = logo_img.resize((int(logo_img.width * escala), int(logo_img.height * escala)))
            x_logo = (LARGURA - logo_img.width) // 2
            y_logo = ALTURA - logo_img.height - 70
            tela.paste(logo_img, (x_logo, y_logo), logo_img)

    tela.save(caminho_saida)
    print(f"story (foto) salvo em {caminho_saida}")


def montar_story_zoom(
    foto_produto: str,
    caixa_zoom_relativa: tuple[float, float, float, float],
    frase: str,
    caminho_saida: str,
) -> None:
    """
    Full-bleed com um recorte AMPLIADO (zoom) da foto -- pra closes de
    tecido/acabamento, sem mostrar o produto inteiro.
    caixa_zoom_relativa: (x, y, w, h) em fracao de 0-1 da foto cover-fit.
    """
    foto = _cobrir_retangulo(Image.open(foto_produto), LARGURA, ALTURA)

    fx, fy, fw, fh = caixa_zoom_relativa
    x0, y0 = int(fx * LARGURA), int(fy * ALTURA)
    x1, y1 = int((fx + fw) * LARGURA), int((fy + fh) * ALTURA)
    recorte = foto.crop((x0, y0, x1, y1)).resize((LARGURA, ALTURA))
    tela = recorte.convert("RGBA")

    altura_faixa = 220
    faixa = Image.new("RGBA", (LARGURA, altura_faixa), _hex_para_rgb(OFF_WHITE) + (235,))
    tela.paste(faixa, (0, ALTURA - altura_faixa), faixa)
    tela = tela.convert("RGB")
    draw = ImageDraw.Draw(tela)

    fonte_frase = _carregar_fonte(FONTE_TITULO, 42, "Bold")
    linhas = _quebrar_linhas(frase.upper(), fonte_frase, LARGURA - 120, draw)
    y = ALTURA - altura_faixa + (altura_faixa - len(linhas) * 52) // 2
    for linha in linhas:
        _texto_centralizado(draw, LARGURA // 2, y, linha, fonte_frase, _hex_para_rgb(ROXO_NOBRE))
        y += 52

    tela.save(caminho_saida)
    print(f"story (zoom) salvo em {caminho_saida}")


def montar_story_itens(
    foto_produto: str,
    itens: list[str],
    caminho_saida: str,
    titulo_caixa: str = "ITENS INCLUSOS",
) -> None:
    """Foto full-bleed + caixa com lista curta (2-3 itens) ancorada na base."""
    tela = _cobrir_retangulo(Image.open(foto_produto), LARGURA, ALTURA).convert("RGB")

    largura_caixa, altura_caixa = LARGURA, 90 + len(itens) * 60 + 70
    caixa = Image.new("RGBA", (largura_caixa, altura_caixa), _hex_para_rgb(OFF_WHITE) + (255,))
    mascara = _forma_um_canto_arredondado(largura_caixa, altura_caixa, raio=90, canto="tl")
    caixa.putalpha(mascara)
    tela_rgba = tela.convert("RGBA")
    tela_rgba.paste(caixa, (0, ALTURA - altura_caixa), caixa)
    tela = tela_rgba.convert("RGB")
    draw = ImageDraw.Draw(tela)

    x_texto, y_texto = 60, ALTURA - altura_caixa + 50
    fonte_caixa_titulo = _carregar_fonte(FONTE_TITULO, 38, "Bold")
    draw.text((x_texto, y_texto), titulo_caixa, font=fonte_caixa_titulo, fill=_hex_para_rgb(ROSA_QUARTZO))
    draw.line((x_texto, y_texto + 50, x_texto + 220, y_texto + 50), fill=_hex_para_rgb(ROSA_QUARTZO), width=2)

    fonte_item = _carregar_fonte(FONTE_TITULO, 32, "Bold")
    y = y_texto + 80
    for item in itens:
        draw.ellipse((x_texto, y + 10, x_texto + 10, y + 20), fill=_hex_para_rgb(ROXO_NOBRE))
        draw.text((x_texto + 28, y), item, font=fonte_item, fill=_hex_para_rgb(ROXO_NOBRE))
        y += 60

    tela.save(caminho_saida)
    print(f"story (itens) salvo em {caminho_saida}")


def montar_story_estampas(
    fotos_estampas: list[str],
    caminho_saida: str,
    texto_central: tuple[str, str, str] = ("TEMOS", "{n} ESTAMPAS", "PRA VOCÊ!"),
) -> None:
    """Fundo off-white + coluna de circulos com as estampas + texto central."""
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    draw = ImageDraw.Draw(tela)

    raio = 155
    centro_x = LARGURA // 2
    n = len(fotos_estampas)
    y_inicio = 260
    espaco = 420
    for i, caminho_foto in enumerate(fotos_estampas[:4]):
        cy = y_inicio + i * espaco
        foto = _cobrir_quadrado(Image.open(caminho_foto), raio * 2)
        mascara_circulo = Image.new("L", (raio * 2, raio * 2), 0)
        ImageDraw.Draw(mascara_circulo).ellipse((0, 0, raio * 2, raio * 2), fill=255)
        tela.paste(foto, (centro_x - raio, cy - raio), mascara_circulo)
        draw.ellipse((centro_x - raio, cy - raio, centro_x + raio, cy + raio), outline=_hex_para_rgb(ROXO_NOBRE), width=5)

    fonte_central = _carregar_fonte(FONTE_TITULO, 40, "Bold")
    fonte_central_destaque = _carregar_fonte(FONTE_TITULO, 48, "Bold")
    linha1, linha2, linha3 = texto_central
    linha2 = linha2.format(n=n)

    y = y_inicio + (min(n, 4) - 1) * espaco + raio + 70
    _texto_centralizado(draw, centro_x, y, linha1, fonte_central, _hex_para_rgb(ROXO_NOBRE))
    y += 52
    _texto_centralizado(draw, centro_x, y, linha2, fonte_central_destaque, _hex_para_rgb(ROSA_QUARTZO))
    y += 58
    _texto_centralizado(draw, centro_x, y, linha3, fonte_central, _hex_para_rgb(ROXO_NOBRE))

    tela.save(caminho_saida)
    print(f"story (estampas) salvo em {caminho_saida}")


def montar_story_texto(
    titulo: str,
    corpo: str,
    caminho_saida: str,
    cor_fundo: str = ROXO_NOBRE,
    cor_texto: str = OFF_WHITE,
    cor_destaque: str = ROSA_QUARTZO,
    foto_pequena: str | None = None,
) -> None:
    """
    Fundo de cor solida + titulo/corpo centralizados -- pra anuncio de
    promocao, pergunta de engajamento, etc.
    foto_pequena: se informado, cola uma foto pequena do produto acima
    do texto (usado em promocao_relampago_story).
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(cor_fundo))
    draw = ImageDraw.Draw(tela)
    centro_x = LARGURA // 2

    y_topo = 220
    if foto_pequena:
        lado_foto = 560
        foto = _cobrir_quadrado(Image.open(foto_pequena), lado_foto)
        mascara = Image.new("L", (lado_foto, lado_foto), 0)
        ImageDraw.Draw(mascara).rounded_rectangle((0, 0, lado_foto, lado_foto), radius=32, fill=255)
        tela.paste(foto, (centro_x - lado_foto // 2, y_topo), mascara)
        y_topo += lado_foto + 70

    fonte_titulo = _carregar_fonte(FONTE_TITULO, 60, "Bold")
    largura_max = LARGURA - 140
    linhas_titulo = _quebrar_linhas(titulo.upper(), fonte_titulo, largura_max, draw)

    fonte_corpo = _carregar_fonte(FONTE_TEXTO, 34, "Regular")
    linhas_corpo = _quebrar_linhas(corpo, fonte_corpo, largura_max, draw)

    y = y_topo
    linha_y = y - 30
    draw.line((centro_x - 55, linha_y, centro_x + 55, linha_y), fill=_hex_para_rgb(cor_destaque), width=3)
    for linha in linhas_titulo:
        _texto_centralizado(draw, centro_x, y, linha, fonte_titulo, _hex_para_rgb(cor_destaque))
        y += 70
    y += 30
    for linha in linhas_corpo:
        _texto_centralizado(draw, centro_x, y, linha, fonte_corpo, _hex_para_rgb(cor_texto))
        y += 46

    tela.save(caminho_saida)
    print(f"story (texto) salvo em {caminho_saida}")


def montar_story_duas_fotos(
    foto_topo: str,
    foto_base: str,
    rotulo_topo: str,
    rotulo_base: str,
    titulo: str,
    caminho_saida: str,
) -> None:
    """
    Duas fotos empilhadas (metade de cima / metade de baixo -- faz mais
    sentido que lado a lado no formato retrato estreito) -- combo,
    paleta, comparacao de estilos, ou base pra enquete manual.
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    draw = ImageDraw.Draw(tela)

    fonte_titulo = _carregar_fonte(FONTE_TITULO, 46, "Bold")
    largura_t = draw.textlength(titulo.upper(), font=fonte_titulo)
    draw.text(((LARGURA - largura_t) / 2, 60), titulo.upper(), font=fonte_titulo, fill=_hex_para_rgb(ROXO_NOBRE))

    largura_painel, altura_painel = 940, 800
    x_painel = (LARGURA - largura_painel) // 2
    for y_painel, caminho_foto, rotulo in (
        (200, foto_topo, rotulo_topo),
        (1040, foto_base, rotulo_base),
    ):
        foto = _cobrir_retangulo(Image.open(caminho_foto), largura_painel, altura_painel)
        mascara = Image.new("L", (largura_painel, altura_painel), 0)
        ImageDraw.Draw(mascara).rounded_rectangle((0, 0, largura_painel, altura_painel), radius=28, fill=255)
        tela.paste(foto, (x_painel, y_painel), mascara)

        fonte_rotulo = _carregar_fonte(FONTE_TITULO, 30, "Bold")
        pad_x, pad_y = 22, 12
        largura_r = draw.textlength(rotulo, font=fonte_rotulo) + pad_x * 2
        x_r = x_painel + 22
        y_r = y_painel + altura_painel - 30 - pad_y * 2 - 20
        draw.rounded_rectangle((x_r, y_r, x_r + largura_r, y_r + 30 + pad_y * 2), radius=22, fill=_hex_para_rgb(OFF_WHITE))
        draw.text((x_r + pad_x, y_r + pad_y - 2), rotulo, font=fonte_rotulo, fill=_hex_para_rgb(ROXO_NOBRE))

    tela.save(caminho_saida)
    print(f"story (duas fotos) salvo em {caminho_saida}")


def montar_story_grid_numerado(
    fotos: list[str],
    titulo: str,
    caminho_saida: str,
) -> None:
    """Grade 2x2 numerada (1,2,3,4) -- giro por categoria/linha de produto."""
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    draw = ImageDraw.Draw(tela)

    fonte_titulo = _carregar_fonte(FONTE_TITULO, 50, "Bold")
    linhas = titulo.upper().split(" | ")
    y_titulo = 100
    for linha in linhas:
        largura = draw.textlength(linha, font=fonte_titulo)
        draw.text(((LARGURA - largura) / 2, y_titulo), linha, font=fonte_titulo, fill=_hex_para_rgb(ROXO_NOBRE))
        y_titulo += 62

    lado = 460
    espaco = 40
    x0 = (LARGURA - (lado * 2 + espaco)) // 2
    y0 = y_titulo + 80
    posicoes = [
        (x0, y0),
        (x0 + lado + espaco, y0),
        (x0, y0 + lado + espaco),
        (x0 + lado + espaco, y0 + lado + espaco),
    ]
    for numero, (pos, caminho_foto) in enumerate(zip(posicoes, fotos), start=1):
        foto = _cobrir_quadrado(Image.open(caminho_foto), lado)
        mascara = Image.new("L", (lado, lado), 0)
        ImageDraw.Draw(mascara).rounded_rectangle((0, 0, lado, lado), radius=28, fill=255)
        tela.paste(foto, pos, mascara)

        raio_bolha = 36
        cx, cy = pos[0] + raio_bolha + 12, pos[1] + raio_bolha + 12
        draw.ellipse((cx - raio_bolha, cy - raio_bolha, cx + raio_bolha, cy + raio_bolha), fill=_hex_para_rgb(ROXO_NOBRE))
        fonte_numero = _carregar_fonte(FONTE_TITULO, 34, "Bold")
        largura_n = draw.textlength(str(numero), font=fonte_numero)
        draw.text((cx - largura_n / 2, cy - 21), str(numero), font=fonte_numero, fill=_hex_para_rgb(OFF_WHITE))

    tela.save(caminho_saida)
    print(f"story (grid numerado) salvo em {caminho_saida}")


def montar_story_destaque_secundario(
    foto_principal: str,
    foto_secundaria: str,
    rotulo_principal: str,
    rotulo_secundario: str,
    caminho_saida: str,
) -> None:
    """
    Foto principal full-bleed + foto secundaria pequena num canto (com
    seta apontando) -- "complete o look" / "combina com".
    """
    tela = _cobrir_retangulo(Image.open(foto_principal), LARGURA, ALTURA).convert("RGBA")

    lado_secundaria = 360
    foto_sec = _cobrir_quadrado(Image.open(foto_secundaria), lado_secundaria)
    mascara = Image.new("L", (lado_secundaria, lado_secundaria), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, lado_secundaria, lado_secundaria), radius=28, fill=255)

    x_sec, y_sec = LARGURA - lado_secundaria - 50, ALTURA - lado_secundaria - 260
    sombra = Image.new("RGBA", tela.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle(
        (x_sec, y_sec + 8, x_sec + lado_secundaria, y_sec + lado_secundaria + 8), radius=28, fill=(0, 0, 0, 90)
    )
    sombra = sombra.filter(ImageFilter.GaussianBlur(12))
    tela = Image.alpha_composite(tela, sombra)

    foto_sec_rgba = foto_sec.convert("RGBA")
    foto_sec_rgba.putalpha(mascara)
    tela.paste(foto_sec_rgba, (x_sec, y_sec), foto_sec_rgba)
    tela = tela.convert("RGB")
    draw = ImageDraw.Draw(tela)
    draw.rounded_rectangle((x_sec, y_sec, x_sec + lado_secundaria, y_sec + lado_secundaria), radius=28, outline=_hex_para_rgb(OFF_WHITE), width=5)

    fonte_rotulo = _carregar_fonte(FONTE_TITULO, 26, "Bold")
    pad_x, pad_y = 18, 10
    for rotulo, pos in (
        (rotulo_principal, (40, ALTURA - 170)),
        (rotulo_secundario, (x_sec + 18, y_sec + lado_secundaria - 56)),
    ):
        largura_r = draw.textlength(rotulo, font=fonte_rotulo) + pad_x * 2
        draw.rounded_rectangle((pos[0], pos[1], pos[0] + largura_r, pos[1] + 36 + pad_y), radius=18, fill=_hex_para_rgb(OFF_WHITE))
        draw.text((pos[0] + pad_x, pos[1] + pad_y - 4), rotulo, font=fonte_rotulo, fill=_hex_para_rgb(ROXO_NOBRE))

    tela.save(caminho_saida)
    print(f"story (destaque secundario) salvo em {caminho_saida}")


if __name__ == "__main__":
    foto_principal = "saida/teste_pipeline_p009_0.png"

    montar_story_foto(
        foto_produto=foto_principal,
        caminho_saida="saida/story_vitrine.png",
        badge_linha1="SÓ CHEGOU",
        frase="Chame no direct e garanta o seu!",
    )

    montar_story_itens(
        foto_produto=foto_principal,
        itens=["01 Colcha com Babado", "01 Cortina", "02 Fronhas"],
        caminho_saida="saida/story_itens.png",
    )

    montar_story_texto(
        titulo="Promoção relâmpago",
        corpo="Só até hoje às 23h59 — chame no direct!",
        caminho_saida="saida/story_promocao.png",
        foto_pequena=foto_principal,
    )
