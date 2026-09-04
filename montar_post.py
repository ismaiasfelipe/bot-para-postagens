"""
Camada grafica do carrossel - IL Variedades Enxovais

O QUE ESTE SCRIPT FAZ
----------------------
Pega uma foto de produto ja gerada (gerar_carrossel_gemini.py) e monta o
layout final do post: fundo off-white, foto do produto com cantos
arredondados e sombra, badge do logo real da marca no canto, titulo em
roxo forte e subtitulo em italico -- no estilo do exemplo "CONHEÇA O
MELHOR PARA A SUA CASA!" que a loja ja usava.

Isso e uma camada DETERMINISTICA (Pillow, sem IA) por cima da foto ja
gerada -- roda rapido, sem custo de API, e da pra ajustar texto/posicao
livremente sem gerar imagem de novo.

COMO RODAR
----------
1. pip install Pillow --break-system-packages
2. python montar_post.py  (roda o exemplo no fim do arquivo)
   ou importe montar_post() em outro script.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --- Configuracao / identidade visual ---

LARGURA, ALTURA = 1080, 1080

ROXO_NOBRE = "#582C4D"
ROSA_QUARTZO = "#C48B9F"
OFF_WHITE = "#FAF9F6"

PASTA_ASSETS = Path("assets")
LOGO_PADRAO = PASTA_ASSETS / "logo_badge.png"
LOGO_ICONE = PASTA_ASSETS / "logo_icone.png"

PASTA_FONTES = PASTA_ASSETS / "fonts"
FONTE_TITULO = PASTA_FONTES / "OpenSans.ttf"  # variable, eixo wght -> Bold
FONTE_SUBTITULO = PASTA_FONTES / "OpenSans-Italic.ttf"  # variable, eixo wght -> Regular


def _carregar_fonte(caminho: Path, tamanho: int, peso: str = "Bold") -> ImageFont.FreeTypeFont:
    """
    Carrega uma fonte variavel (Open Sans, licenca OFL, embutida em
    assets/fonts/) e ajusta o peso via eixo wght -- troca a antiga
    dependencia de Segoe UI do Windows, que nao existe no Linux (onde o
    GitHub Actions roda). Fontes fixas (nao-variaveis) ignoram 'peso'.
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


def _arredondar_com_sombra(
    imagem: Image.Image, raio: int, cor_sombra=(0, 0, 0, 90), desloc_sombra=(0, 14)
) -> Image.Image:
    """Aplica cantos arredondados numa imagem e devolve com uma sombra suave por baixo."""
    imagem = imagem.convert("RGBA")
    mascara = Image.new("L", imagem.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle(
        (0, 0, imagem.size[0], imagem.size[1]), radius=raio, fill=255
    )
    imagem.putalpha(mascara)

    margem = 40
    tela = Image.new(
        "RGBA",
        (imagem.size[0] + margem * 2, imagem.size[1] + margem * 2),
        (0, 0, 0, 0),
    )
    sombra = Image.new("RGBA", tela.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle(
        (
            margem + desloc_sombra[0],
            margem + desloc_sombra[1],
            margem + imagem.size[0] + desloc_sombra[0],
            margem + imagem.size[1] + desloc_sombra[1],
        ),
        radius=raio,
        fill=cor_sombra,
    )
    sombra = sombra.filter(ImageFilter.GaussianBlur(18))

    tela.alpha_composite(sombra)
    tela.alpha_composite(imagem, (margem, margem))
    return tela


def _cobrir_quadrado(imagem: Image.Image, lado: int) -> Image.Image:
    """Redimensiona + recorta centralizado pra preencher um quadrado sem distorcer (cover-fit)."""
    imagem = imagem.convert("RGB")
    largura, altura = imagem.size
    escala = lado / min(largura, altura)
    imagem = imagem.resize((int(largura * escala) + 1, int(altura * escala) + 1))
    largura, altura = imagem.size
    x = (largura - lado) // 2
    y = (altura - lado) // 2
    return imagem.crop((x, y, x + lado, y + lado))


def _recortar_bordas_brancas(
    imagem: Image.Image, limiar: int = 240, tolerancia_fracao: float = 0.02
) -> Image.Image:
    """
    Remove faixas quase-brancas (letterboxing) que a geracao de imagem as
    vezes deixa nas bordas. Ao contrario de um bbox simples (que um unico
    pixel ruidoso ja falsifica), aqui uma linha/coluna so conta como borda
    se quase 100% dos seus pixels forem quase-brancos -- assim nao corta
    dentro da foto real por causa de ruido de compressao.
    """
    import numpy as np

    array = np.array(imagem.convert("L"))
    altura, largura = array.shape
    quase_branco = array >= limiar

    def linha_e_borda(i):
        return quase_branco[i].mean() >= (1 - tolerancia_fracao)

    def coluna_e_borda(i):
        return quase_branco[:, i].mean() >= (1 - tolerancia_fracao)

    topo = 0
    while topo < altura and linha_e_borda(topo):
        topo += 1
    baixo = altura - 1
    while baixo > topo and linha_e_borda(baixo):
        baixo -= 1
    esquerda = 0
    while esquerda < largura and coluna_e_borda(esquerda):
        esquerda += 1
    direita = largura - 1
    while direita > esquerda and coluna_e_borda(direita):
        direita -= 1

    if (topo, baixo, esquerda, direita) == (0, altura - 1, 0, largura - 1):
        return imagem
    return imagem.crop((esquerda, topo, direita + 1, baixo + 1))


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


def montar_post(
    foto_produto: str,
    titulo: str,
    subtitulo: str,
    caminho_saida: str,
    nome_produto: str | None = None,
    logo_estilo: str = "completo",
) -> None:
    """
    Monta o post final (1080x1080) no estilo "CONHECA O MELHOR": fundo
    off-white, foto do produto a esquerda (cantos arredondados + sombra),
    titulo em roxo forte e subtitulo em italico a direita.

    nome_produto: se informado, mostra uma etiqueta com o nome do produto
    sobre o canto inferior esquerdo da foto (ex: "Colcha Preguiada").

    logo_estilo: "completo" (badge com nome da marca -- usar em so 1-2
    slides do carrossel), "icone" (so o simbolo, mais discreto, pode
    repetir mais), ou "nenhum" (sem marca nesse slide).
    """
    tela = Image.new("RGB", (LARGURA, ALTURA), _hex_para_rgb(OFF_WHITE))
    draw = ImageDraw.Draw(tela)

    # --- foto do produto (lado esquerdo, maior, sem bordas brancas, sem distorcer) ---
    foto = Image.open(foto_produto).convert("RGB")
    foto = _recortar_bordas_brancas(foto)
    lado_foto = 660
    foto = _cobrir_quadrado(foto, lado_foto)
    foto_com_sombra = _arredondar_com_sombra(foto, raio=28)
    x_foto, y_foto = 40, 230
    tela.paste(foto_com_sombra, (x_foto - 40, y_foto - 40), foto_com_sombra)

    # --- marca (canto superior direito, estilo configuravel) ---
    if logo_estilo != "nenhum":
        caminho_logo = str(LOGO_PADRAO) if logo_estilo == "completo" else str(LOGO_ICONE)
        largura_badge = 220 if logo_estilo == "completo" else 110
        badge = Image.open(caminho_logo).convert("RGBA")
        proporcao = badge.size[1] / badge.size[0]
        badge = badge.resize((largura_badge, int(largura_badge * proporcao)))
        raio_badge = 20 if logo_estilo == "completo" else largura_badge
        badge = _arredondar_com_sombra(badge, raio=raio_badge, desloc_sombra=(0, 8))
        tela.paste(badge, (LARGURA - badge.size[0] - 20, 20), badge)

    # --- etiqueta com o nome do produto (sobre o canto da foto) ---
    if nome_produto:
        fonte_etiqueta = _carregar_fonte(FONTE_TITULO, 26, "Bold")
        texto_etiqueta = nome_produto.strip()
        pad_x, pad_y = 22, 12
        largura_etiqueta = draw.textlength(texto_etiqueta, font=fonte_etiqueta) + pad_x * 2
        altura_etiqueta = 26 + pad_y * 2
        x_etiqueta = x_foto + 24
        y_etiqueta = y_foto + lado_foto - altura_etiqueta - 24
        draw.rounded_rectangle(
            (x_etiqueta, y_etiqueta, x_etiqueta + largura_etiqueta, y_etiqueta + altura_etiqueta),
            radius=altura_etiqueta / 2,
            fill=_hex_para_rgb(OFF_WHITE),
        )
        draw.text(
            (x_etiqueta + pad_x, y_etiqueta + pad_y - 2),
            texto_etiqueta,
            font=fonte_etiqueta,
            fill=_hex_para_rgb(ROXO_NOBRE),
        )

    # --- titulo (roxo forte, negrito, lado direito) ---
    x_texto = x_foto + lado_foto + 40  # margem de sobra, nunca encosta na foto
    largura_texto = LARGURA - x_texto - 50

    fonte_titulo = _carregar_fonte(FONTE_TITULO, 62, "Bold")
    linhas_titulo = _quebrar_linhas(titulo.upper(), fonte_titulo, largura_texto, draw)

    y = 300  # comeca logo abaixo do badge do logo
    for linha in linhas_titulo:
        draw.text((x_texto, y), linha, font=fonte_titulo, fill=_hex_para_rgb(ROXO_NOBRE))
        y += 72

    # --- subtitulo (italico, tom mais claro) ---
    y += 20
    fonte_subtitulo = _carregar_fonte(FONTE_SUBTITULO, 28, "Italic")
    linhas_subtitulo = _quebrar_linhas(subtitulo.upper(), fonte_subtitulo, largura_texto, draw)
    for linha in linhas_subtitulo:
        draw.text((x_texto, y), linha, font=fonte_subtitulo, fill=_hex_para_rgb(ROSA_QUARTZO))
        y += 40

    tela.save(caminho_saida)
    print(f"post montado em {caminho_saida}")


if __name__ == "__main__":
    montar_post(
        foto_produto="saida/p006_troca_v1_1.png",
        titulo="Conheça o melhor para a sua casa!",
        subtitulo="Tudo o que você precisa para deixar sua casa elegante e confortável...",
        nome_produto="Colcha Preguiada Casal/Box",
        caminho_saida="saida/post_exemplo.png",
    )
