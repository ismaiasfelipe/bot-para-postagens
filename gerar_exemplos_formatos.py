"""
Gera os exemplos visuais dos 10 formatos de carrossel (ver FORMATOS_CARROSSEL.md),
reaproveitando ao maximo as fotos ja geradas nesta sessao (evita gastar
novas chamadas de API onde nao e necessario).

Rode formato por formato comentando/descomentando as chamadas no fim do
arquivo, ou rode tudo de uma vez.
"""

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
    ROXO_NOBRE,
    ROSA_QUARTZO,
    OFF_WHITE,
)
from montar_post import montar_post

Path("saida/exemplos_formatos").mkdir(parents=True, exist_ok=True)

FOTO_TEAL = "saida/teste_pipeline_p009_0.png"
FOTO_AMARELA = "saida/teste_corrigir_cortina_0.png"
FOTO_VERMELHA = "saida/p009_estampa3_vermelha_0.png"
FOTO_VERMELHA_V2 = "saida/p009_estampa3_vermelha_v2_0.png"  # corrigida: cortina/saia consistentes
FOTO_AZUL = "saida/p009_estampa4_azul_final_0.png"  # corrigida: cortina/saia consistentes
FOTO_COLCHA = "saida/p006_troca_v1_1.png"


def formato_3_novidade_da_semana():
    p = "saida/exemplos_formatos/f03"
    montar_slide_hero(
        foto_produto=FOTO_TEAL,
        nome_produto="Jogo de Quarto Casal/Box",
        caminho_saida=f"{p}_slide1.png",
        badge_linha1="SÓ",
        badge_linha2="CHEGOU",
    )
    montar_post(
        foto_produto=FOTO_TEAL,
        titulo="Chegou pra ficar",
        subtitulo="Conheça o novo Jogo de Quarto da nossa coleção",
        nome_produto="Jogo de Quarto Casal/Box",
        caminho_saida=f"{p}_slide2.png",
    )
    montar_slide_detalhes(
        foto_produto=FOTO_TEAL,
        texto_qualidade="Produto de alta qualidade, sempre com muito carinho!",
        caminho_saida=f"{p}_slide3.png",
    )
    montar_slide_texto(
        titulo="Toda semana tem novidade",
        corpo="Chame no direct e garanta o seu!",
        caminho_saida=f"{p}_slide4.png",
        foto_fundo=FOTO_TEAL,
    )


def formato_4_detalhe_textura():
    p = "saida/exemplos_formatos/f04"
    montar_slide_zoom_cheio(FOTO_TEAL, (0.30, 0.55, 0.35, 0.35), "Sinta a qualidade", f"{p}_slide1.png")
    montar_slide_zoom_cheio(FOTO_TEAL, (0.05, 0.35, 0.35, 0.35), "Estampa em detalhe", f"{p}_slide2.png")
    montar_slide_zoom_cheio(FOTO_TEAL, (0.0, 0.55, 0.25, 0.30), "Acabamento com renda", f"{p}_slide3.png")
    montar_post(
        foto_produto=FOTO_TEAL,
        titulo="Qualidade em cada detalhe",
        subtitulo="Tecido selecionado, acabamento cuidadoso",
        nome_produto="Jogo de Quarto Casal/Box",
        caminho_saida=f"{p}_slide4.png",
    )


def formato_6_promocao_relampago():
    p = "saida/exemplos_formatos/f06"
    montar_slide_texto(
        titulo="Promoção Relâmpago",
        corpo="11/11 -- só até meia-noite",
        caminho_saida=f"{p}_slide1.png",
        foto_fundo=FOTO_TEAL,
    )
    montar_slide_hero(
        foto_produto=FOTO_TEAL,
        nome_produto="Jogo de Quarto Casal/Box",
        caminho_saida=f"{p}_slide2.png",
        badge_linha1="PROMOÇÃO",
        badge_linha2="11/11",
    )
    montar_post(
        foto_produto=FOTO_TEAL,
        titulo="[Condição a confirmar]",
        subtitulo="Preço/desconto real definido por vocês antes de publicar",
        caminho_saida=f"{p}_slide3.png",
        logo_estilo="nenhum",
    )
    montar_slide_texto(
        titulo="Corre que é por tempo limitado!",
        corpo="Chame no direct e garanta o seu!",
        caminho_saida=f"{p}_slide4.png",
        cor_fundo=ROSA_QUARTZO,
        cor_texto=OFF_WHITE,
        cor_destaque=ROXO_NOBRE,
    )


def formato_7_inspiracao_decoracao():
    p = "saida/exemplos_formatos/f07"
    montar_slide_texto(
        titulo="Inspire-se",
        corpo="Ambientes reais pra você se apaixonar",
        caminho_saida=f"{p}_slide1.png",
        foto_fundo=FOTO_AMARELA,
    )
    montar_slide_variedade(
        fotos_estampas=[FOTO_TEAL, FOTO_AMARELA, FOTO_VERMELHA_V2, FOTO_AZUL],
        caminho_saida=f"{p}_slide2.png",
        texto_central=("QUATRO", "JEITOS", "DE DECORAR"),
    )
    montar_post(
        foto_produto=FOTO_AMARELA,
        titulo="Esse aqui é o nosso queridinho",
        subtitulo="Jogo de Quarto Casal/Box, estampa amarela",
        caminho_saida=f"{p}_slide3.png",
        logo_estilo="icone",
    )
    montar_slide_texto(
        titulo="Qual combina mais com você?",
        corpo="Conta pra gente nos comentários",
        caminho_saida=f"{p}_slide4.png",
    )


def formato_2_campanha_sazonal():
    p = "saida/exemplos_formatos/f02"
    montar_post(
        foto_produto=FOTO_TEAL,
        titulo="Hora de renovar sua casa",
        subtitulo="Coleção Primavera chegou na IL Variedades",
        nome_produto="Jogo de Quarto Casal/Box",
        caminho_saida=f"{p}_slide1.png",
    )
    montar_slide_texto(
        titulo="Combina com",
        corpo="Toalhas de mesa, jogo de cozinha e cortinas leves -- categorias em destaque na Primavera.",
        caminho_saida=f"{p}_slide2.png",
        cor_fundo=ROSA_QUARTZO,
        cor_texto=OFF_WHITE,
        cor_destaque=ROXO_NOBRE,
        foto_fundo=FOTO_TEAL,
    )
    montar_slide_detalhes(
        foto_produto=FOTO_TEAL,
        texto_qualidade="Leveza e renovação em cada detalhe do tecido",
        caminho_saida=f"{p}_slide3.png",
    )
    montar_slide_texto(
        titulo="Hora de renovar sua casa",
        corpo="Chame no direct e garanta o seu! #Primavera #CasaNova",
        caminho_saida=f"{p}_slide4.png",
        cor_fundo=ROSA_QUARTZO,
        cor_texto=OFF_WHITE,
        cor_destaque=ROXO_NOBRE,
    )


def formato_5_kit_combo():
    """MOCKUP: usa os 2 produtos reais que temos (cama) como substituto
    ilustrativo -- o formato real combina categorias diferentes (cama +
    banho + mesa), que ainda nao tem foto de ambiente cadastrada.
    Layout peculiar: painel duas-fotos lado a lado (nao grade de
    circulos) + caixa de itens do combo, cada slide diferente do outro."""
    p = "saida/exemplos_formatos/f05"
    montar_post(
        foto_produto=FOTO_TEAL,
        titulo="Monte seu quarto completo",
        subtitulo="Combo ilustrativo -- na versão real, categorias diferentes",
        nome_produto="Jogo de Quarto Casal/Box",
        caminho_saida=f"{p}_slide1.png",
        logo_estilo="completo",
    )
    montar_slide_duas_fotos(
        FOTO_TEAL, FOTO_COLCHA,
        "Jogo de Quarto", "Colcha Preguiada",
        titulo="Peças que combinam entre si",
        caminho_saida=f"{p}_slide2.png",
    )
    montar_slide_itens_inclusos(
        foto_produto=FOTO_COLCHA,
        itens=["Jogo de Quarto Casal/Box", "Colcha Preguiada Casal/Box"],
        caminho_saida=f"{p}_slide3.png",
        titulo_caixa="NO COMBO",
    )
    montar_slide_texto(
        titulo="Compre o combo completo",
        corpo="E garanta um ambiente only IL Variedades. Chame no direct!",
        caminho_saida=f"{p}_slide4.png",
    )


def formato_8_giro_categoria():
    """MOCKUP: giro real usaria 4 produtos DIFERENTES da mesma categoria;
    aqui usamos as 4 estampas do jogo de quarto como substituto (mesma
    categoria "cama", mas mesmo produto -- so pra mostrar o layout).
    Cada slide usa um layout DIFERENTE (grade numerada, foto+texto,
    zoom cheio, oval) -- a logo completa aparece uma unica vez."""
    p = "saida/exemplos_formatos/f08"
    fotos = [FOTO_TEAL, FOTO_AMARELA, FOTO_VERMELHA_V2, FOTO_AZUL]

    montar_slide_grid_numerado(
        fotos,
        titulo="CONHEÇA NOSSA | LINHA DE CAMA",
        caminho_saida=f"{p}_slide1.png",
    )
    montar_post(
        FOTO_TEAL, "Estampa Turquesa", "A queridinha da casa",
        f"{p}_slide2.png", nome_produto="Jogo de Quarto Casal/Box",
        logo_estilo="completo",
    )
    montar_slide_zoom_cheio(
        FOTO_AMARELA, (0.10, 0.30, 0.55, 0.55), "Estampa Amarela -- alegre e marcante",
        f"{p}_slide3.png",
    )
    montar_slide_hero(
        FOTO_VERMELHA_V2, "Estampa Vermelha", f"{p}_slide4.png",
        badge_linha1="LINHA", badge_linha2="COMPLETA",
    )


def formato_9_paleta_em_foco():
    """MOCKUP: paleta real cruzaria categorias diferentes (cama, banho,
    mesa, sofa); aqui usamos as variantes de cor do jogo de quarto como
    substituto pra mostrar o layout. Peculiaridade: dois paineis
    duas-fotos, cada um com um par de tons, ladeando um slide de
    abertura com foto de fundo e um fechamento so texto."""
    p = "saida/exemplos_formatos/f09"
    montar_slide_texto(
        titulo="Monte sua casa em tons de azul",
        corpo="Mockup ilustrativo -- paleta real cruzaria categorias diferentes",
        caminho_saida=f"{p}_slide1.png",
        cor_fundo=ROSA_QUARTZO,
        cor_texto=OFF_WHITE,
        cor_destaque=ROXO_NOBRE,
        foto_fundo=FOTO_AZUL,
    )
    montar_slide_duas_fotos(
        FOTO_TEAL, FOTO_AZUL,
        "Tom Turquesa", "Tom Azul",
        titulo="Combinações em azul",
        caminho_saida=f"{p}_slide2.png",
    )
    montar_slide_duas_fotos(
        FOTO_AMARELA, FOTO_VERMELHA_V2,
        "Tom Amarelo", "Tom Vermelho",
        titulo="Outras combinações disponíveis",
        caminho_saida=f"{p}_slide3.png",
    )
    montar_slide_texto(
        titulo="Toda essa combinação te espera",
        corpo="Chame no direct e monte a sua!",
        caminho_saida=f"{p}_slide4.png",
    )


def formato_10_ambientes_estilos():
    """Peculiaridade: cada estilo usa um layout diferente (post, zoom
    cheio, oval) em vez de repetir a mesma composicao foto+texto 3x."""
    p = "saida/exemplos_formatos/f10"
    montar_post(
        foto_produto="saida/f10_estilo_aconchegante_0.png",
        titulo="Estilo aconchegante",
        subtitulo="Luz quente, clima intimista",
        nome_produto="Jogo de Quarto Casal/Box",
        caminho_saida=f"{p}_slide1.png",
        logo_estilo="completo",
    )
    montar_slide_zoom_cheio(
        "saida/f10_estilo_moderno_0.png",
        (0.0, 0.15, 1.0, 0.65),
        "Estilo clean e moderno",
        f"{p}_slide2.png",
    )
    montar_slide_hero(
        foto_produto=FOTO_TEAL,
        nome_produto="Jogo de Quarto Casal/Box",
        caminho_saida=f"{p}_slide3.png",
        badge_linha1="ESTILO",
        badge_linha2="CLÁSSICO",
    )
    montar_slide_texto(
        titulo="Um produto, infinitas possibilidades",
        corpo="Qual combina com você? Chame no direct!",
        caminho_saida=f"{p}_slide4.png",
    )


if __name__ == "__main__":
    formato_2_campanha_sazonal()
    formato_10_ambientes_estilos()
    formato_3_novidade_da_semana()
    formato_4_detalhe_textura()
    formato_5_kit_combo()
    formato_6_promocao_relampago()
    formato_7_inspiracao_decoracao()
    formato_8_giro_categoria()
    formato_9_paleta_em_foco()
