"""
Carrossel estilo campanha (4 slides) - IL Variedades Enxovais

O QUE ESTE SCRIPT FAZ
----------------------
Monta um carrossel de 4 slides inspirado na ESTRUTURA de um carrossel de
referencia de outra loja (Perollar) que o usuario mandou como exemplo --
mas com nossa identidade visual (logo, cores, tom de voz) e paleta da
campanha ativa (por padrao, Primavera: off-white predominante + rosa
quartzo como acento leve, ver campanhas/primavera/orientacoes-campanha
no Drive).

Slides:
  1. Hero: foto de corpo inteiro + badge de campanha (canto sup. esq.) +
     oval com nome do produto + marca (base)
  2. Itens inclusos: foto + caixa de lista do que vem no produto
  3. Detalhes: foto + 2 closes com linha apontando pra detalhes do tecido
     + texto de qualidade
  4. Variedade: grade de fotos circulares das estampas disponiveis

Isso e so ESTRUTURA/COMPOSICAO -- os dados reais (nome, itens inclusos,
fotos de cada estampa) sao passados por fora, ver o exemplo no fim do
arquivo.

COMO RODAR
----------
pip install Pillow --break-system-packages
python montar_carrossel_campanha.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

LARGURA, ALTURA = 1080, 1080

ROXO_NOBRE = "#582C4D"
ROSA_QUARTZO = "#C48B9F"
OFF_WHITE = "#FAF9F6"

PASTA_ASSETS = Path("assets")
LOGO_PADRAO = PASTA_ASSETS / "logo_badge.png"

PASTA_FONTES = PASTA_ASSETS / "fonts"
FONTE_TITULO = PASTA_FONTES / "OpenSans.ttf"  # variable, eixo wght -> Bold
FONTE_TEXTO = PASTA_FONTES / "OpenSans.ttf"  # variable, eixo wght -> Regular
FONTE_SCRIPT = PASTA_FONTES / "DancingScript.ttf"  # variable, eixo wght -> Bold


def _carregar_fonte(caminho: Path, tamanho: int, peso: str = "Bold") -> ImageFont.FreeTypeFont:
    """
    Carrega uma fonte variavel (Open Sans / Dancing Script, licenca OFL,
    embutidas em assets/fonts/) e ajusta o peso via eixo wght -- troca a
    antiga dependencia de Segoe UI / Lucida Handwriting do Windows, que
    nao existem no Linux (onde o GitHub Actions roda). Fontes fixas
    (nao-variaveis) ignoram 'peso'.
    """
    fonte = ImageFont.truetype(str(caminho), tamanho)
    try:
        nomes = {n.decode() if isinstance(n, bytes) else n for n in fonte.get_variation_names()}
        if peso in nomes:
            fonte.set_variation_by_name(peso)
    except OSError:
        pass  # fonte nao e variavel, usa como esta
    return fonte


def _hex_para_rgb(cor_hex: str) -> tuple[int, int, int]:
    cor_hex = cor_hex.lstrip("#")
    return tuple(int(cor_hex[i : i + 2], 16) for i in (0, 2, 4))


def _cobrir_quadrado(imagem: Image.Image, lado: int) -> Image.Image:
    """Redimensiona + recorta centralizado pra preencher um quadrado (cover-fit)."""
    imagem = imagem.convert("RGB")
    largura, altura = imagem.size
    escala = lado / min(largura, altura)
    imagem = imagem.resize((int(largura * escala) + 1, int(altura * escala) + 1))
    largura, altura = imagem.size
    x = (largura - lado) // 2
    y = (altura - lado) // 2
    return imagem.crop((x, y, x + lado, y + lado))


def _quebrar_linhas(texto: str, fonte: ImageFont.FreeTypeFont, largura_max: int, draw: ImageDraw.ImageDraw) -> list[str]:
    palavras = texto.split()
    linhas, linha_atual = [], ""
    for palavra in palavras:
        candidata = f"{linha_atual} {palavra}".strip()
        if draw.textlength(candidata, font=fonte) <= largura_max:
            linha_atual = candidata
        else:
            if linha_atual:
                linhas.append(linha_atual)
            linha_atual = palavra
    if linha_atual:
        linhas.append(linha_atual)
    return linhas


def _texto_centralizado(draw, centro_x, y, texto, fonte, cor):
    largura = draw.textlength(texto, font=fonte)
    draw.text((centro_x - largura / 2, y), texto, font=fonte, fill=cor)
    return largura


def _forma_um_canto_arredondado(largura, altura, raio, canto):
    """
    Mascara retangular flush nas bordas do canvas, com apenas UM canto
    arredondado num raio grande (o 'quarto de circulo' que da o efeito de
    cartao/blob ancorado num canto). canto: 'tl' | 'tr' | 'bl' | 'br'.
    """
    mask = Image.new("L", (largura, altura), 255)
    draw = ImageDraw.Draw(mask)
    if canto == "tl":
        draw.rectangle((0, 0, raio, raio), fill=0)
        draw.pieslice((0, 0, raio * 2, raio * 2), 180, 270, fill=255)
    elif canto == "tr":
        draw.rectangle((largura - raio, 0, largura, raio), fill=0)
        draw.pieslice((largura - raio * 2, 0, largura, raio * 2), 270, 360, fill=255)
    elif canto == "bl":
        draw.rectangle((0, altura - raio, raio, altura), fill=0)
        draw.pieslice((0, altura - raio * 2, raio * 2, altura), 90, 180, fill=255)
    elif canto == "br":
        draw.rectangle((largura - raio, altura - raio, largura, altura), fill=0)
        draw.pieslice((largura - raio * 2, altura - raio * 2, largura, altura), 0, 90, fill=255)
    return mask


def montar_slide_itens_inclusos(
    foto_produto: str,
    itens: list[str],
    caminho_saida: str,
    titulo_caixa: str = "ITENS INCLUSOS",
) -> None:
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    foto = _cobrir_quadrado(Image.open(foto_produto), LARGURA)
    tela.paste(foto, (0, 0))
    draw = ImageDraw.Draw(tela)

    largura_caixa, altura_caixa = 620, 340
    caixa = Image.new("RGBA", (largura_caixa, altura_caixa), _hex_para_rgb(OFF_WHITE) + (255,))
    mascara = _forma_um_canto_arredondado(largura_caixa, altura_caixa, raio=160, canto="tr")
    caixa.putalpha(mascara)
    tela.paste(caixa, (0, ALTURA - altura_caixa), caixa)

    draw = ImageDraw.Draw(tela)
    x_texto, y_texto = 50, ALTURA - altura_caixa + 55

    fonte_caixa_titulo = _carregar_fonte(FONTE_TITULO, 34, "Bold")
    draw.text((x_texto, y_texto), titulo_caixa, font=fonte_caixa_titulo, fill=_hex_para_rgb(ROSA_QUARTZO))
    draw.line((x_texto, y_texto + 46, x_texto + 200, y_texto + 46), fill=_hex_para_rgb(ROSA_QUARTZO), width=2)

    fonte_item = _carregar_fonte(FONTE_TITULO, 28, "Bold")
    y = y_texto + 72
    for item in itens:
        draw.ellipse((x_texto, y + 10, x_texto + 8, y + 18), fill=_hex_para_rgb(ROXO_NOBRE))
        draw.text((x_texto + 24, y), item, font=fonte_item, fill=_hex_para_rgb(ROXO_NOBRE))
        y += 46

    tela.save(caminho_saida)
    print(f"slide 2 (itens inclusos) salvo em {caminho_saida}")


def montar_slide_detalhes(
    foto_produto: str,
    texto_qualidade: str,
    caminho_saida: str,
    recortes_zoom: list[tuple[int, int, int, int]] | None = None,
) -> None:
    """
    recortes_zoom: lista de ate 2 caixas (x, y, w, h) em pixels da foto
    ORIGINAL pra usar como close -- se nao informado, usa 2 posicoes
    padrao (uma no tecido principal, outra numa barra/acabamento).
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    foto_original = Image.open(foto_produto).convert("RGB")
    foto = _cobrir_quadrado(foto_original, LARGURA)
    tela.paste(foto, (0, 0))
    draw = ImageDraw.Draw(tela)

    if recortes_zoom is None:
        w, h = foto.size
        recortes_zoom = [
            (int(w * 0.30), int(h * 0.55), 90, 90),
            (int(w * 0.24), int(h * 0.47), 90, 90),
        ]

    posicoes_circulo = [(700, 260), (330, 460)]
    raio_circulo = 110

    for (cx, cy), caixa_zoom in zip(posicoes_circulo, recortes_zoom):
        x0, y0, w0, h0 = caixa_zoom
        recorte = foto.crop((x0, y0, x0 + w0, y0 + h0)).resize((raio_circulo * 2, raio_circulo * 2))

        mascara_circulo = Image.new("L", (raio_circulo * 2, raio_circulo * 2), 0)
        ImageDraw.Draw(mascara_circulo).ellipse((0, 0, raio_circulo * 2, raio_circulo * 2), fill=255)

        draw.line((x0 + w0 // 2, y0 + h0 // 2, cx, cy), fill=_hex_para_rgb(ROXO_NOBRE), width=2)
        tela.paste(recorte, (cx - raio_circulo, cy - raio_circulo), mascara_circulo)
        draw.ellipse(
            (cx - raio_circulo, cy - raio_circulo, cx + raio_circulo, cy + raio_circulo),
            outline=_hex_para_rgb(ROXO_NOBRE),
            width=4,
        )

    largura_caixa, altura_caixa = 620, 260
    caixa = Image.new("RGBA", (largura_caixa, altura_caixa), _hex_para_rgb(OFF_WHITE) + (255,))
    mascara = _forma_um_canto_arredondado(largura_caixa, altura_caixa, raio=160, canto="tl")
    caixa.putalpha(mascara)
    tela.paste(caixa, (LARGURA - largura_caixa, ALTURA - altura_caixa), caixa)

    draw = ImageDraw.Draw(tela)
    x_texto = LARGURA - largura_caixa + 150
    y_texto = ALTURA - altura_caixa + 55

    fonte_texto = _carregar_fonte(FONTE_TITULO, 30, "Bold")
    linhas = _quebrar_linhas(texto_qualidade.upper(), fonte_texto, largura_caixa - 170, draw)
    y = y_texto + 30
    for linha in linhas:
        draw.text((x_texto, y), linha, font=fonte_texto, fill=_hex_para_rgb(ROXO_NOBRE))
        y += 40

    tela.save(caminho_saida)
    print(f"slide 3 (detalhes) salvo em {caminho_saida}")


def montar_slide_variedade(
    fotos_estampas: list[str],
    caminho_saida: str,
    texto_central: tuple[str, str, str] = ("TEMOS", "{n} ESTAMPAS", "DISPONÍVEIS PARA VOCÊ!"),
) -> None:
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    draw = ImageDraw.Draw(tela)

    raio = 165
    posicoes_por_quantidade = {
        4: [(215, 250), (LARGURA - 215, 250), (215, ALTURA - 250), (LARGURA - 215, ALTURA - 250)],
        5: [(LARGURA // 2, 200), (215, 460), (LARGURA - 215, 460), (215, 830), (LARGURA - 215, 830)],
    }
    posicoes = posicoes_por_quantidade.get(
        len(fotos_estampas), posicoes_por_quantidade[5][: len(fotos_estampas)]
    )
    for (cx, cy), caminho_foto in zip(posicoes, fotos_estampas):
        foto = _cobrir_quadrado(Image.open(caminho_foto), raio * 2)
        mascara_circulo = Image.new("L", (raio * 2, raio * 2), 0)
        ImageDraw.Draw(mascara_circulo).ellipse((0, 0, raio * 2, raio * 2), fill=255)
        tela.paste(foto, (cx - raio, cy - raio), mascara_circulo)
        draw.ellipse((cx - raio, cy - raio, cx + raio, cy + raio), outline=_hex_para_rgb(ROXO_NOBRE), width=4)

    fonte_central = _carregar_fonte(FONTE_TITULO, 34, "Bold")
    fonte_central_destaque = _carregar_fonte(FONTE_TITULO, 40, "Bold")
    centro_x = LARGURA // 2
    linha1, linha2, linha3 = texto_central
    linha2 = linha2.format(n=len(fotos_estampas))

    y = ALTURA // 2 - 60
    _texto_centralizado(draw, centro_x, y, linha1, fonte_central, _hex_para_rgb(ROXO_NOBRE))
    y += 44
    _texto_centralizado(draw, centro_x, y, linha2, fonte_central_destaque, _hex_para_rgb(ROSA_QUARTZO))
    y += 50
    _texto_centralizado(draw, centro_x, y, linha3, fonte_central, _hex_para_rgb(ROXO_NOBRE))

    tela.save(caminho_saida)
    print(f"slide 4 (variedade) salvo em {caminho_saida}")


def _cobrir_retangulo(imagem: Image.Image, largura: int, altura: int) -> Image.Image:
    imagem = imagem.convert("RGB")
    w, h = imagem.size
    escala = max(largura / w, altura / h)
    imagem = imagem.resize((int(w * escala) + 1, int(h * escala) + 1))
    w, h = imagem.size
    x, y = (w - largura) // 2, (h - altura) // 2
    return imagem.crop((x, y, x + largura, y + altura))


def montar_slide_duas_fotos(
    foto_esq: str,
    foto_dir: str,
    rotulo_esq: str,
    rotulo_dir: str,
    titulo: str,
    caminho_saida: str,
) -> None:
    """
    Duas fotos lado a lado, cada uma com etiqueta -- usado pra comparar/
    combinar 2 produtos ou 2 variantes (formatos Kit/Combo e Paleta em
    Foco), sem repetir o visual de grade de circulos.
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    draw = ImageDraw.Draw(tela)

    fonte_titulo = _carregar_fonte(FONTE_TITULO, 40, "Bold")
    largura_t = draw.textlength(titulo.upper(), font=fonte_titulo)
    draw.text(((LARGURA - largura_t) / 2, 45), titulo.upper(), font=fonte_titulo, fill=_hex_para_rgb(ROXO_NOBRE))

    largura_painel, altura_painel = 500, 760
    y_painel = 150
    for x_painel, caminho_foto, rotulo in (
        (30, foto_esq, rotulo_esq),
        (LARGURA - largura_painel - 30, foto_dir, rotulo_dir),
    ):
        foto = _cobrir_retangulo(Image.open(caminho_foto), largura_painel, altura_painel)
        mascara = Image.new("L", (largura_painel, altura_painel), 0)
        ImageDraw.Draw(mascara).rounded_rectangle((0, 0, largura_painel, altura_painel), radius=24, fill=255)
        tela.paste(foto, (x_painel, y_painel), mascara)

        fonte_rotulo = _carregar_fonte(FONTE_TITULO, 26, "Bold")
        pad_x, pad_y = 20, 10
        largura_r = draw.textlength(rotulo, font=fonte_rotulo) + pad_x * 2
        x_r = x_painel + 18
        y_r = y_painel + altura_painel - 26 - pad_y * 2 - 18
        draw.rounded_rectangle((x_r, y_r, x_r + largura_r, y_r + 26 + pad_y * 2), radius=20, fill=_hex_para_rgb(OFF_WHITE))
        draw.text((x_r + pad_x, y_r + pad_y - 2), rotulo, font=fonte_rotulo, fill=_hex_para_rgb(ROXO_NOBRE))

    tela.save(caminho_saida)
    print(f"slide duas fotos salvo em {caminho_saida}")


def montar_slide_grid_numerado(
    fotos: list[str],
    titulo: str,
    caminho_saida: str,
) -> None:
    """
    Grade 2x2 com um numero (1, 2, 3...) em cada foto -- tipo indice de
    um "tour" pelo catalogo. titulo pode ter " | " pra quebrar em 2 linhas.
    Usado no formato Giro pela Categoria.
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    draw = ImageDraw.Draw(tela)

    fonte_titulo = _carregar_fonte(FONTE_TITULO, 46, "Bold")
    linhas = titulo.upper().split(" | ")
    y_titulo = 50
    for linha in linhas:
        largura = draw.textlength(linha, font=fonte_titulo)
        draw.text(((LARGURA - largura) / 2, y_titulo), linha, font=fonte_titulo, fill=_hex_para_rgb(ROXO_NOBRE))
        y_titulo += 56

    lado = 460
    posicoes = [(20, 210), (LARGURA - lado - 20, 210), (20, ALTURA - lado - 20), (LARGURA - lado - 20, ALTURA - lado - 20)]
    for numero, (pos, caminho_foto) in enumerate(zip(posicoes, fotos), start=1):
        foto = _cobrir_quadrado(Image.open(caminho_foto), lado)
        mascara = Image.new("L", (lado, lado), 0)
        ImageDraw.Draw(mascara).rounded_rectangle((0, 0, lado, lado), radius=28, fill=255)
        tela.paste(foto, pos, mascara)

        raio_bolha = 34
        cx, cy = pos[0] + raio_bolha + 10, pos[1] + raio_bolha + 10
        draw.ellipse((cx - raio_bolha, cy - raio_bolha, cx + raio_bolha, cy + raio_bolha), fill=_hex_para_rgb(ROXO_NOBRE))
        fonte_numero = _carregar_fonte(FONTE_TITULO, 32, "Bold")
        largura_n = draw.textlength(str(numero), font=fonte_numero)
        draw.text((cx - largura_n / 2, cy - 20), str(numero), font=fonte_numero, fill=_hex_para_rgb(OFF_WHITE))

    tela.save(caminho_saida)
    print(f"slide grade numerada salvo em {caminho_saida}")


def montar_slide_texto(
    titulo: str,
    corpo: str,
    caminho_saida: str,
    cor_fundo: str = ROXO_NOBRE,
    cor_texto: str = OFF_WHITE,
    cor_destaque: str = ROSA_QUARTZO,
    foto_fundo: str | None = None,
) -> None:
    """
    Slide predominantemente de texto -- pra anuncios, CTA de fechamento, etc.

    foto_fundo: opcional, caminho de uma foto pra usar como fundo
    desfocado + escurecido (em vez de cor solida) -- deixa o slide mais
    preenchido e ainda garante contraste pro texto por cima (overlay
    escuro), em vez de jogar o texto direto sobre a foto nitida.
    """
    if foto_fundo:
        foto = _cobrir_quadrado(Image.open(foto_fundo), LARGURA)
        foto = foto.filter(ImageFilter.GaussianBlur(14))
        overlay = Image.new("RGBA", foto.size, _hex_para_rgb(cor_fundo) + (185,))
        tela = Image.alpha_composite(foto.convert("RGBA"), overlay).convert("RGB")
    else:
        tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(cor_fundo))
    draw = ImageDraw.Draw(tela)

    centro_x = LARGURA // 2
    fonte_titulo = _carregar_fonte(FONTE_TITULO, 64, "Bold")
    largura_max = LARGURA - 160

    linhas_titulo = _quebrar_linhas(titulo.upper(), fonte_titulo, largura_max, draw)
    altura_titulo = len(linhas_titulo) * 76

    fonte_corpo = _carregar_fonte(FONTE_TEXTO, 32, "Regular")
    linhas_corpo = _quebrar_linhas(corpo, fonte_corpo, largura_max, draw)
    altura_corpo = len(linhas_corpo) * 44

    y = (ALTURA - altura_titulo - altura_corpo - 40) // 2
    linha_y = y - 30
    draw.line((centro_x - 50, linha_y, centro_x + 50, linha_y), fill=_hex_para_rgb(cor_destaque), width=3)

    for linha in linhas_titulo:
        _texto_centralizado(draw, centro_x, y, linha, fonte_titulo, _hex_para_rgb(cor_destaque))
        y += 76

    y += 30
    for linha in linhas_corpo:
        _texto_centralizado(draw, centro_x, y, linha, fonte_corpo, _hex_para_rgb(cor_texto))
        y += 44

    tela.save(caminho_saida)
    print(f"slide de texto salvo em {caminho_saida}")


def montar_slide_zoom_cheio(
    foto_produto: str,
    caixa_zoom_relativa: tuple[float, float, float, float],
    titulo: str,
    caminho_saida: str,
) -> None:
    """
    Slide full-bleed com um recorte AMPLIADO (zoom) da foto, sem 'foto
    hero' inteira -- usado no formato Detalhe & Textura em Foco.
    caixa_zoom_relativa: (x, y, w, h) em fracao de 0-1 da foto cover-fit.
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    foto = _cobrir_quadrado(Image.open(foto_produto), LARGURA)

    fx, fy, fw, fh = caixa_zoom_relativa
    x0, y0 = int(fx * LARGURA), int(fy * ALTURA)
    x1, y1 = int((fx + fw) * LARGURA), int((fy + fh) * ALTURA)
    recorte = foto.crop((x0, y0, x1, y1)).resize((LARGURA, ALTURA))
    tela.paste(recorte, (0, 0))

    faixa = Image.new("RGBA", (LARGURA, 130), _hex_para_rgb(OFF_WHITE) + (235,))
    tela_rgba = tela.convert("RGBA")
    tela_rgba.paste(faixa, (0, ALTURA - 130), faixa)
    tela = tela_rgba.convert("RGB")
    draw = ImageDraw.Draw(tela)

    fonte_titulo = _carregar_fonte(FONTE_TITULO, 40, "Bold")
    _texto_centralizado(draw, LARGURA // 2, ALTURA - 90, titulo.upper(), fonte_titulo, _hex_para_rgb(ROXO_NOBRE))

    tela.save(caminho_saida)
    print(f"slide de zoom salvo em {caminho_saida}")


def montar_slide_hero(
    foto_produto: str,
    nome_produto: str,
    caminho_saida: str,
    nome_marca: str = "IL Variedades",
    badge_linha1: str = "NOVA COLEÇÃO",
    badge_linha2: str = "PRIMAVERA",
) -> None:
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    foto = _cobrir_quadrado(Image.open(foto_produto), LARGURA)
    tela.paste(foto, (0, 0))
    draw = ImageDraw.Draw(tela)

    # --- banner de campanha (canto superior esquerdo) ---
    largura_banner, altura_banner = 340, 120
    draw.rectangle((0, 0, largura_banner, altura_banner), fill=_hex_para_rgb(OFF_WHITE))
    draw.rectangle((0, altura_banner - 4, largura_banner, altura_banner), fill=_hex_para_rgb(ROSA_QUARTZO))

    fonte_badge1 = _carregar_fonte(FONTE_TITULO, 30, "Bold")
    fonte_badge2 = _carregar_fonte(FONTE_TITULO, 38, "Bold")
    draw.text((28, 24), badge_linha1, font=fonte_badge1, fill=_hex_para_rgb(ROXO_NOBRE))
    draw.text((28, 62), badge_linha2, font=fonte_badge2, fill=_hex_para_rgb(ROSA_QUARTZO))

    # --- oval inferior com nome do produto + marca ---
    largura_oval, altura_oval = 760, 260
    x_oval = (LARGURA - largura_oval) // 2
    y_oval = ALTURA - altura_oval - 40

    sombra = Image.new("RGBA", tela.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).ellipse(
        (x_oval, y_oval + 10, x_oval + largura_oval, y_oval + altura_oval + 10),
        fill=(0, 0, 0, 70),
    )
    sombra = sombra.filter(ImageFilter.GaussianBlur(16))
    tela.paste(Image.alpha_composite(tela.convert("RGBA"), sombra).convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(tela)

    draw.ellipse(
        (x_oval, y_oval, x_oval + largura_oval, y_oval + altura_oval),
        fill=_hex_para_rgb(OFF_WHITE),
        outline=_hex_para_rgb(ROXO_NOBRE),
        width=3,
    )

    centro_x = LARGURA // 2

    fonte_produto = _carregar_fonte(FONTE_SCRIPT, 44, "Bold")
    linhas_produto = _quebrar_linhas(nome_produto, fonte_produto, largura_oval - 80, draw)
    y = y_oval + 55
    for linha in linhas_produto:
        _texto_centralizado(draw, centro_x, y, linha, fonte_produto, _hex_para_rgb(ROXO_NOBRE))
        y += 52

    y += 8
    draw.line((centro_x - 60, y, centro_x + 60, y), fill=_hex_para_rgb(ROSA_QUARTZO), width=2)
    y += 16

    fonte_marca = _carregar_fonte(FONTE_TITULO, 30, "Bold")
    _texto_centralizado(draw, centro_x, y, nome_marca.upper(), fonte_marca, _hex_para_rgb(ROSA_QUARTZO))

    tela.save(caminho_saida)
    print(f"slide 1 (hero) salvo em {caminho_saida}")


if __name__ == "__main__":
    foto_principal = "saida/teste_pipeline_p009_0.png"

    montar_slide_hero(
        foto_produto=foto_principal,
        nome_produto="Jogo de Quarto Casal/Box",
        caminho_saida="saida/campanha_slide1.png",
    )

    montar_slide_itens_inclusos(
        foto_produto=foto_principal,
        itens=["01 Colcha com Babado", "01 Cortina", "02 Fronhas"],
        caminho_saida="saida/campanha_slide2.png",
    )

    montar_slide_detalhes(
        foto_produto=foto_principal,
        texto_qualidade="Produto de alta qualidade feito com carinho e dedicação!",
        caminho_saida="saida/campanha_slide3.png",
    )

    montar_slide_variedade(
        fotos_estampas=[
            foto_principal,
            "saida/teste_corrigir_cortina_0.png",
            "saida/p009_estampa3_vermelha_0.png",
            "saida/p009_estampa4_azul_0.png",
        ],
        caminho_saida="saida/campanha_slide4.png",
    )
