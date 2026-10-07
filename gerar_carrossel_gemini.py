"""
Gerador de carrossel para Instagram com Gemini - IL Variedades Enxovais

O QUE ESTE SCRIPT FAZ
----------------------
1. Le o banco de produtos reais (produtos_reais.json, gerado por conectar_drive.py)
2. Para cada produto:
   - Se tiver "imagem_ambiente" (a foto real do produto no ambiente, com ou
     sem o diagrama de medidas/estampas sobreposto) E "imagem_estampa" (foto
     crua do tecido): usa EDICAO de imagem -- manda as duas fotos reais pro
     Gemini e pede pra recriar a cena limpa, fiel ao tecido real (evita a IA
     "inventar" um padrao novo baseado so em texto/cores da marca).
   - Se so tiver uma das duas, ou nenhuma: cai pra geracao por texto (menos
     fiel, usado como fallback).
   - Se tiver "fotos_variadas" (varias fotos do produto disperso/
     empilhado/dobrado, nao em cena de ambiente): opcionalmente gera uma
     composicao nesse estilo via gerar_composicao_dispersa_com_verificacao,
     reaproveitando o arranjo REAL dessas fotos como referencia (nao
     inventa a composicao do zero) -- usado quando o formato/post pede
     esse tipo de foto mais solta de produto, nao entra no rodizio
     automatico da foto hero pra nao duplicar custo de geracao.
3. Salva os arquivos gerados na pasta ./saida/

COMO RODAR
----------
1. pip install google-genai --break-system-packages
2. Rode conectar_drive.py primeiro para gerar produtos_reais.json
3. Defina sua chave de API:
   export GEMINI_API_KEY="sua_chave_aqui"
   (pegue a chave em https://aistudio.google.com/apikey)
4. python gerar_carrossel_gemini.py

CUSTO
-----
Cada chamada de geracao de imagem tem custo por imagem gerada.
Confira os precos atuais em https://ai.google.dev/pricing antes de rodar em lote.
"""

import json
import mimetypes
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from gerar_carrossel_completo import extrair_itens_inclusos

load_dotenv()

# --- Configuracao ---

PASTA_SAIDA = Path("saida")
PASTA_SAIDA.mkdir(exist_ok=True)

MODELO_IMAGEM = "gemini-2.5-flash-image"  # confira o nome de modelo mais recente na doc oficial
ARQUIVO_BANCO = "produtos_reais.json"

MARCA = {
    "nome": "IL Variedades - Enxovais & Lar",
    "cores": {
        "roxo_nobre": "#582C4D",
        "rosa_quartzo": "#C48B9F",
        "off_white": "#FAF9F6",
    },
    "tom_de_voz": "elegante, caloroso, acolhedor, em primeira pessoa do plural, com emojis discretos (🤍💜✨)",
    "call_to_action_padrao": "Chame no direct e garanta o seu!",
    "hashtags_fixas": ["#ilvariedades", "#Elegância", "#Sofisticação", "#Conforto"],
}


def carregar_banco(caminho: str = ARQUIVO_BANCO) -> dict:
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def limpar_descricao_tecnica(descricao_bruta: str) -> str:
    """
    A descricao vem do export de um Google Doc (tabela) para texto puro,
    entao chega com BOM e tabs/quebras de linha soltas. Aqui so colapsamos
    isso numa frase corrida pra caber no prompt de imagem.
    """
    texto = descricao_bruta.lstrip("﻿").strip()
    return " ".join(texto.split())


def extrair_dimensoes(descricao_tecnica: str) -> tuple[str, str]:
    """
    Extrai as medidas reais do produto a partir da ficha tecnica (mesmo
    parse tab-separated de extrair_itens_inclusos em gerar_carrossel_completo.py):
    CARACTERISTICAS tem as medidas do produto ABERTO/em uso (ex: "Lencol
    De Cima 2,10m x 2,40m"), DIMENSAO tem as medidas do produto DOBRADO/
    na embalagem (ex: "33cm x 38cm x 4cm"). Usadas no prompt de edicao de
    imagem pra reduzir a IA "inventando" a proporcao entre o produto
    dobrado (como normalmente aparece na foto crua de estampa) e o
    produto aberto (como deve aparecer na cena do ambiente).

    Mesma estrutura de 8 cabecalhos que extrair_itens_inclusos espera:
    PRODUTO, DESCRICAO, MODELO, CARACTERISTICAS, COMPOSICAO, INFORMACOES
    IMPORTANTES, PESO LIQ(kg), DIMENSAO. Devolve ("", "") se a estrutura
    nao bater com o padrao esperado (documento diferente do padrao).
    """
    if not descricao_tecnica:
        return "", ""
    texto = descricao_tecnica.lstrip("﻿").strip()
    celulas = [c.strip() for c in texto.split("\t")]

    cabecalhos_esperados = ["PRODUTO", "DESCRIÇÃO", "MODELO", "CARACTERÍSTICAS"]
    if len(celulas) < 8 or celulas[:4] != cabecalhos_esperados:
        return "", ""

    n_cabecalhos = 8
    indice_caracteristicas = n_cabecalhos + 3
    indice_dimensao = n_cabecalhos + 7
    medidas_aberto = celulas[indice_caracteristicas] if len(celulas) > indice_caracteristicas else ""
    medidas_dobrado = celulas[indice_dimensao] if len(celulas) > indice_dimensao else ""
    return medidas_aberto.replace("\n", "; "), medidas_dobrado


_CABECALHOS_CONHECIDOS_FICHA = {
    "PRODUTO", "DESCRIÇÃO", "MODELO", "CARACTERÍSTICAS", "COMPOSIÇÃO",
    "INFORMAÇÕES IMPORTANTES", "PESO LIQ(kg)", "DIMENSÃO",
    "PREÇO", "PREÇO (R$)", "PRECO", "VALOR",
}


def extrair_preco(descricao_tecnica: str) -> str:
    """
    Extrai o preco da ficha tecnica, se o campo existir. Em 06/10/2026 o
    modelo padrao de ficha tecnica AINDA NAO tem esse campo -- ao
    contrario de extrair_dimensoes (que usa indices fixos pros 8
    cabecalhos ja existentes), aqui a posicao do cabecalho "PRECO" e
    descoberta dinamicamente (varrendo celulas do inicio enquanto baterem
    com um nome de cabecalho conhecido), pra funcionar assim que o campo
    for adicionado ao modelo do Google Docs, em qualquer posicao.

    Devolve "" se o campo nao existir ou a ficha nao seguir a estrutura
    tab-separated esperada (mesmo parse de extrair_itens_inclusos).

    Limitacao conhecida: so encontra o campo se ele vier DEPOIS dos 4
    primeiros cabecalhos fixos (PRODUTO/DESCRIÇÃO/MODELO/CARACTERÍSTICAS)
    -- inserir "PREÇO" antes de CARACTERÍSTICAS quebraria essa checagem
    inicial (ela tambem e usada por extrair_itens_inclusos/
    extrair_dimensoes, entao nao da pra mudar so aqui). Na pratica, uma
    coluna nova tende a ser adicionada no fim da tabela, cenario ja
    coberto.
    """
    if not descricao_tecnica:
        return ""
    texto = descricao_tecnica.lstrip("﻿").strip()
    celulas = [c.strip() for c in texto.split("\t")]

    cabecalhos_esperados = ["PRODUTO", "DESCRIÇÃO", "MODELO", "CARACTERÍSTICAS"]
    if len(celulas) < 8 or celulas[:4] != cabecalhos_esperados:
        return ""

    n_cabecalhos = 0
    while n_cabecalhos < len(celulas) and celulas[n_cabecalhos] in _CABECALHOS_CONHECIDOS_FICHA:
        n_cabecalhos += 1

    for nome_variante in ("PREÇO", "PREÇO (R$)", "PRECO", "VALOR"):
        if nome_variante in celulas[:n_cabecalhos]:
            indice_cabecalho = celulas[:n_cabecalhos].index(nome_variante)
            indice_valor = n_cabecalhos + indice_cabecalho
            if indice_valor < len(celulas):
                return celulas[indice_valor]
    return ""


_INSTRUCOES_LINGUAGEM = {
    "neutra": "Tom neutro e informativo, direto ao ponto, sem exageros.",
    "acolhedora": "Tom caloroso, aconchegante e acolhedor, como se estivesse conversando com alguém querido.",
    "chamativa": "Tom animado e chamativo, com senso de novidade/urgência, mais pontos de exclamação, linguagem energética.",
    "agressiva": "Tom direto e imperativo, focado em ação imediata de compra, frases curtas e assertivas, sem rodeios.",
}


def montar_prompt_legenda(produto: dict, campanha: dict | None, linguagem: str) -> str:
    descricao = limpar_descricao_tecnica(produto.get("descricao_tecnica", ""))
    contexto_produto = f" Ficha técnica: {descricao[:300]}." if descricao else ""
    instrucao_tom = _INSTRUCOES_LINGUAGEM.get(linguagem, _INSTRUCOES_LINGUAGEM["neutra"])

    contexto_campanha = ""
    if campanha:
        contexto_campanha = (
            f"\nCampanha ativa: '{campanha['nome']}'. CTA sugerido: '{campanha['cta']}'."
        )

    return (
        f"Escreva uma legenda de Instagram para a loja de enxovais "
        f"{MARCA['nome']}, sobre o produto '{produto['nome']}' "
        f"({produto['categoria']}).{contexto_produto}{contexto_campanha}\n\n"
        f"TOM DE VOZ: {instrucao_tom}\n\n"
        "Regras:\n"
        "- Primeira pessoa do plural (nós, nosso/nossa).\n"
        "- No máximo 4-5 linhas curtas, sem contar hashtags.\n"
        "- Termine com uma chamada para ação clara (chamar no direct).\n"
        "- Pode usar emojis discretos (no máximo 2-3).\n"
        "- NÃO use markdown, asteriscos ou formatação -- só texto puro.\n"
        "- Responda APENAS com a legenda final, sem explicações."
    )


def gerar_legenda_ia(produto: dict, campanha: dict | None, linguagem: str = "neutra") -> str:
    """
    Gera a legenda do post via Gemini (texto), variando o tom de voz
    conforme 'linguagem' (ver tema_semana.LINGUAGENS_VALIDAS) -- usado no
    lugar de calendario_campanhas.montar_legenda quando o usuario escolhe
    um tom pelo painel PWA. Em caso de erro/resposta vazia da API, cai
    pro template fixo (montar_legenda) como fallback -- nunca deixa o
    post sem legenda por causa disso.
    """
    from calendario_campanhas import montar_legenda, HASHTAGS_FIXAS

    try:
        client = _obter_cliente()
        prompt = montar_prompt_legenda(produto, campanha, linguagem)
        resposta = client.models.generate_content(model=MODELO_IMAGEM, contents=prompt)
        texto = (resposta.text or "").strip()
        if not texto:
            raise ValueError("resposta vazia da API")
    except Exception as e:
        print(f"  aviso: geracao de legenda via IA falhou ({e!r}), usando template fixo")
        return montar_legenda(campanha, produto)

    hashtags = f"{campanha['hashtags_extras']} {HASHTAGS_FIXAS}".strip() if campanha else HASHTAGS_FIXAS
    return f"{texto}\n\n{hashtags}"


def montar_prompt_texto(produto: dict, marca: dict) -> str:
    """Prompt para o fallback de geracao pura por texto (sem fotos de referencia reais)."""
    cores = marca["cores"]

    descricao = limpar_descricao_tecnica(produto.get("descricao_tecnica", ""))
    contexto_produto = f"Detalhes do produto (ficha tecnica): {descricao[:400]}. " if descricao else ""

    cor = produto.get("cor_predominante", "").strip()
    cor_texto = f", cor {cor}" if cor else ""

    return (
        f"Fotografia de produto profissional para e-commerce de enxovais. "
        f"Produto: {produto['nome']} ({produto['categoria']}){cor_texto}. "
        f"{contexto_produto}"
        f"Ambientado em um quarto/casa aconchegante, luz natural suave, composicao minimalista. "
        f"Paleta de cores da cena deve harmonizar com roxo nobre ({cores['roxo_nobre']}) "
        f"e rosa quartzo ({cores['rosa_quartzo']}) como tons de apoio (moveis, texteis, paredes), "
        f"fundo em tom off-white ({cores['off_white']}). "
        f"Estilo elegante, sofisticado, acolhedor -- sem texto, sem logotipo, sem pessoas. "
        f"Proporcao quadrada, adequada para post de Instagram."
    )


def montar_prompt_edicao(produto: dict, trocar_estampa: bool = False) -> str:
    """
    Prompt para o modo de edicao (produto tem foto real do ambiente e/ou da
    estampa). Instrui o Gemini a recriar a cena fielmente, sem inventar
    padrao novo e sem manter marcacoes de diagrama (setas, textos, medidas)
    que possam estar sobrepostas na foto de ambiente.

    trocar_estampa=True: usado quando a foto de "estampa" passada e de uma
    variante DIFERENTE da que aparece na foto de ambiente (troca de cor/
    padrao mantendo a mesma cena) -- reforca que a substituicao deve ser
    total em todas as superficies de tecido, nao so nos detalhes/acabamento.
    """
    descricao = limpar_descricao_tecnica(produto.get("descricao_tecnica", ""))
    contexto_produto = f" Ficha tecnica do produto: {descricao[:400]}." if descricao else ""

    medidas_aberto, medidas_dobrado = extrair_dimensoes(produto.get("descricao_tecnica", ""))
    instrucao_medidas = ""
    if medidas_aberto:
        instrucao_medidas = (
            f"\n\nMEDIDAS REAIS DO PRODUTO ABERTO/EM USO (use pra manter a "
            f"escala e as proporcoes corretas em relacao aos moveis/comodo "
            f"da cena): {medidas_aberto}."
        )
        if medidas_dobrado:
            instrucao_medidas += (
                f" Medidas DOBRADO/na embalagem (so pra referencia de "
                f"escala -- NAO e como o produto deve aparecer na foto "
                f"final): {medidas_dobrado}."
            )
        instrucao_medidas += (
            " O produto DEVE aparecer ABERTO/ESTENDIDO/em uso na cena (ex: "
            "lencol/colcha estendido sobre a cama, cortina pendurada "
            "esticada, toalha aberta) -- mesmo que a foto de referencia da "
            "estampa mostre o tecido dobrado ou empilhado, a cena final "
            "nao deve mostrar o produto dobrado."
        )

    instrucao_estampa = (
        "A foto crua do tecido/estampa e de uma variante DIFERENTE da que "
        "aparece na foto do ambiente -- e uma troca de estampa proposital. "
        "Substitua COMPLETAMENTE o padrao em TODAS as superficies de tecido "
        "do produto (colcha/cobertura, fronhas, cortina, barras e "
        "acabamentos) pelo padrao da foto de referencia da estampa. Nao "
        "deixe nenhuma parte do produto com o padrao antigo da foto de "
        "ambiente -- so o comodo, moveis e enquadramento devem permanecer "
        "os mesmos."
        if trocar_estampa else
        "Se houver tambem uma foto crua do tecido/estampa: use-a como "
        "referencia fiel de padrao, cor e escala real do tecido."
    )

    return (
        f"Voce recebeu foto(s) real(is) de referencia do produto "
        f"'{produto['nome']}' ({produto['categoria']}) de uma loja de "
        f"enxovais.{contexto_produto}{instrucao_medidas}\n\n"
        "Se houver uma foto do produto montado num ambiente (cama/quarto/casa): "
        "ela pode ter anotacoes de diagrama sobrepostas (setas, caixas de "
        "texto como 'Estampa 1'/'Estampa 2', linhas e numeros de medida em "
        "cm) e/ou closes de amostra de tecido no topo da imagem. "
        f"{instrucao_estampa} "
        "\n\n"
        "Gere uma nova fotografia de produto, profissional, para e-commerce, "
        "recriando a MESMA cena do produto no ambiente (mesmo comodo, mesmos "
        "moveis, mesmo angulo de camera, mesmo enquadramento e proporcoes "
        "quando essa foto existir), porem: "
        "(a) remova completamente qualquer seta, caixa de texto, legenda ou "
        "linha/numero de medida -- a imagem final deve ser UMA UNICA "
        "fotografia limpa, de corpo inteiro da cena, SEM nenhum elemento de "
        "diagrama e SEM nenhum close/inset de amostra de tecido separado "
        "(nao monte um colgate ou grade com varias fotos -- so a foto do "
        "produto no ambiente); "
        "(b) garanta que o tecido siga fielmente o padrao, cores e escala "
        "reais mostrados nas fotos de referencia, sem inventar um padrao novo. "
        "ISSO E CRITICO: e um tecido estampado industrial, com um motivo que "
        "se REPETE em tamanho e espacamento CONSTANTES por toda a superficie "
        "(como um papel de parede) -- nao reinterprete, redesenhe ou varie o "
        "tamanho das flores/motivos entre a colcha e a fronha, e preserve os "
        "tracos finos (contorno, folhas, linhas) exatamente como aparecem na "
        "foto de referencia da estampa, na mesma escala relativa ao tecido; "
        "(c) iluminacao natural suave, estilo elegante e sofisticado, sem "
        "pessoas, sem logotipo, sem texto. "
        "Proporcao quadrada, adequada para post de Instagram."
    )


def montar_prompt_troca_estampa(produto: dict, correcao: str | None = None) -> str:
    """
    Prompt pra trocar a variante de cor/estampa COMPLETA de um produto
    (corpo do tecido + barra/acabamento), reaproveitando uma foto de
    ambiente ja existente. Ver PROJETO.md ("Tecnica de troca de estampa
    completa validada") pro raciocinio e exemplos por tras dessa tecnica.

    Se o resultado sair distorcido (motivo com tamanho inconsistente,
    elemento que nao trocou, etc.), ajuste o texto abaixo e rode de novo
    -- essa funcao e so o ponto de partida, nao uma solucao definitiva.

    correcao=None: modo 1a passada -- troca tudo a partir da foto de
    ambiente original (produto['imagem_ambiente']).
    correcao="texto livre": modo 2a passada -- a IMAGEM 1 usada como base
    ja esta parcialmente correta (normalmente o resultado bom da 1a
    passada); o texto de 'correcao' descreve o que ainda falta ajustar,
    ex: "a cortina ainda esta com o padrao antigo, corrija so ela".
    """
    descricao = limpar_descricao_tecnica(produto.get("descricao_tecnica", ""))
    contexto_produto = f" Ficha tecnica do produto: {descricao[:400]}." if descricao else ""

    if correcao:
        instrucao_cena = (
            f"IMAGEM 1: uma fotografia do produto que JA ESTA CORRETA na "
            f"maior parte -- mantenha tudo IDENTICO (pixel a pixel), "
            f"EXCETO o seguinte, que precisa ser corrigido: {correcao}"
        )
    else:
        instrucao_cena = (
            "IMAGEM 1: foto real do produto (numa variante de cor "
            "DIFERENTE da desejada) montado no ambiente. Pode ter closes "
            "de amostra de tecido e/ou anotacoes de diagrama sobrepostas "
            "(setas, texto, medidas em cm) -- ignore e remova tudo isso."
        )

    return (
        f"Voce recebeu 3 imagens de referencia de um produto de enxoval "
        f"('{produto['nome']}', {produto['categoria']}) de uma loja de "
        f"enxovais.{contexto_produto}\n"
        f"{instrucao_cena}\n"
        "IMAGEM 2: foto real, plana, do CORPO/PADRAO do tecido da NOVA "
        "variante (a estampa principal que cobre a maior parte do produto).\n"
        "IMAGEM 3: foto real da BARRA/ACABAMENTO liso (com ou sem renda) "
        "da NOVA variante (a cor solida de detalhe/borda/acabamento).\n\n"
        "Gere uma nova fotografia de produto, profissional, para "
        "e-commerce, recriando a MESMA cena (mesmo comodo, moveis, angulo "
        "de camera, enquadramento), com o produto na NOVA variante: "
        "(a) as superficies principais de tecido devem seguir fielmente o "
        "padrao da IMAGEM 2 -- e um tecido estampado industrial com "
        "motivo que se REPETE em tamanho e espacamento CONSTANTES por "
        "toda a superficie (como um papel de parede), sem reinterpretar "
        "ou variar o tamanho dos motivos entre as diferentes pecas do "
        "produto, preservando os tracos finos (contorno, folhas, linhas) "
        "na mesma escala da referencia; "
        "(b) as barras/acabamentos/detalhes devem usar a cor solida (e "
        "renda, se houver) da IMAGEM 3, substituindo COMPLETAMENTE a cor "
        "antiga -- nenhuma parte pode ficar com a cor antiga; "
        "(c) remova completamente qualquer seta, caixa de texto, legenda, "
        "linha/numero de medida ou close de amostra -- a imagem final "
        "deve ser UMA UNICA fotografia limpa, sem colagem/grade de varias "
        "fotos; "
        "(d) iluminacao natural suave, estilo elegante e sofisticado, sem "
        "pessoas, sem logotipo, sem texto, proporcao quadrada."
    )


def trocar_estampa_produto(
    produto: dict,
    estampa_corpo: str,
    estampa_barra: str,
    nome_arquivo: str,
    imagem_base: str | None = None,
    correcao: str | None = None,
) -> None:
    """
    Troca a estampa/variante completa de um produto que ja tem foto de
    ambiente, usando o fluxo de 2 passadas validado (ver PROJETO.md):

    1a passada (gera a variante nova a partir do ambiente original):
        trocar_estampa_produto(produto, estampa_corpo, estampa_barra, "p006_v1")

    2a passada (se algum elemento ficou com o padrao antigo, corrige sem
    perder o que ja saiu certo -- reusa o resultado bom como nova base):
        trocar_estampa_produto(
            produto, estampa_corpo, estampa_barra, "p006_v2",
            imagem_base="saida/p006_v1_0.png",
            correcao="a cortina ainda esta com o padrao antigo, corrija so ela",
        )

    Se sair distorcido, mexa em montar_prompt_troca_estampa() e rode de
    novo -- geracao de IA tem variacao aleatoria, e as vezes so rodar de
    novo com o mesmo prompt ja resolve.
    """
    base = imagem_base or produto.get("imagem_ambiente")
    if not base:
        raise ValueError(
            f"Produto {produto['id']} nao tem imagem_ambiente nem imagem_base informada"
        )

    prompt = montar_prompt_troca_estampa(produto, correcao=correcao)
    gerar_imagem_editada(prompt, [base, estampa_corpo, estampa_barra], nome_arquivo=nome_arquivo)


def montar_prompt_verificacao(produto: dict) -> str:
    """Prompt do 'juiz' que confere se a troca de estampa saiu consistente
    em TODA a peca, antes de mostrar o resultado pro usuario."""
    return (
        f"Voce e um revisor de qualidade de fotos de produto para "
        f"e-commerce de enxovais. Vai analisar 3 imagens sobre o produto "
        f"'{produto['nome']}'.\n"
        "IMAGEM 1: a foto FINAL gerada, que deveria mostrar o produto "
        "inteiro (colcha, fronhas, cortina, saia/rodape da cama, quando "
        "aplicavel) numa unica variante de cor/estampa nova e consistente.\n"
        "IMAGEM 2: referencia real do CORPO/PADRAO que deveria aparecer "
        "nas superficies principais (colcha, fronhas, cortina).\n"
        "IMAGEM 3: referencia real da BARRA/ACABAMENTO solido que deveria "
        "aparecer nas bordas/barras/saia da cama.\n\n"
        "Confira PEÇA POR PEÇA visível na IMAGEM 1 (colcha, cada fronha, "
        "cortina -- topo E corpo, saia/rodape da cama) se a cor/padrao "
        "bate com as referencias (IMAGEM 2 pro corpo, IMAGEM 3 pra "
        "barra/acabamento). Um erro comum e alguma peca (normalmente a "
        "cortina ou a saia da cama) ficar com a cor ANTIGA, diferente do "
        "resto -- preste atencao especial nisso.\n\n"
        "Responda EXATAMENTE nesse formato, sem mais nada:\n"
        "LINHA 1: 'SIM' se TODAS as pecas estao consistentes com as "
        "referencias, ou 'NAO' se alguma peca ainda esta com a cor/padrao "
        "errado.\n"
        "LINHA 2: se NAO, uma frase curta e especifica dizendo qual "
        "peca(s) estao erradas e com que cor ficaram (pra poder corrigir). "
        "Se SIM, deixe a linha 2 vazia."
    )


def verificar_troca_estampa(
    imagem_gerada: str, estampa_corpo: str, estampa_barra: str, produto: dict
) -> tuple[bool, str]:
    """
    Pede pro Gemini conferir (so texto, sem gerar imagem -- bem mais
    barato que uma geracao) se a troca de estampa ficou consistente em
    toda a peca. Retorna (passou, motivo_se_falhou).
    """
    client = _obter_cliente()
    partes = []
    for caminho in (imagem_gerada, estampa_corpo, estampa_barra):
        dados, mime_type = _carregar_bytes_imagem(caminho)
        partes.append(_part_de_bytes(dados, mime_type))
    partes.append(montar_prompt_verificacao(produto))

    resposta = client.models.generate_content(model=MODELO_IMAGEM, contents=partes)
    texto = (resposta.text or "").strip()
    linhas = texto.splitlines()
    passou = bool(linhas) and linhas[0].strip().upper().startswith("SIM")
    motivo = linhas[1].strip() if len(linhas) > 1 else ""
    return passou, motivo


def trocar_estampa_com_verificacao(
    produto: dict,
    estampa_corpo: str,
    estampa_barra: str,
    nome_arquivo: str,
    max_tentativas: int = 3,
) -> str:
    """
    Versao com filtro automatico de qualidade de trocar_estampa_produto():
    gera, pede pro Gemini conferir peca por peca contra as referencias, e
    se achar inconsistencia, tenta corrigir automaticamente (reusando o
    resultado anterior como base + o motivo da falha como instrucao de
    correcao) ate max_tentativas vezes. Imprime o progresso e retorna o
    caminho do melhor resultado (ultima tentativa, mesmo se nao passar).
    """
    imagem_base = None
    correcao = None
    caminho_atual = None

    for tentativa in range(1, max_tentativas + 1):
        nome = f"{nome_arquivo}_tentativa{tentativa}"
        print(f"  [tentativa {tentativa}/{max_tentativas}] gerando...")
        prompt = montar_prompt_troca_estampa(produto, correcao=correcao)
        base = imagem_base or produto.get("imagem_ambiente")
        resposta = _gerar_e_retornar_caminho(prompt, [base, estampa_corpo, estampa_barra], nome)
        if resposta is None:
            continue
        caminho_atual = resposta

        passou, motivo = verificar_troca_estampa(caminho_atual, estampa_corpo, estampa_barra, produto)
        if passou:
            print(f"  [tentativa {tentativa}] passou na verificacao.")
            return caminho_atual

        print(f"  [tentativa {tentativa}] reprovado: {motivo}")
        imagem_base = caminho_atual
        correcao = motivo or "algumas pecas ainda estao com a cor/padrao antigo, corrija"

    print(f"  aviso: nao passou na verificacao apos {max_tentativas} tentativas -- "
          f"revise visualmente {caminho_atual} antes de usar")
    return caminho_atual


def montar_prompt_verificacao_hero(produto: dict, n_referencias: int) -> str:
    """
    Prompt do 'juiz' geral pra foto principal do produto (nao especifico
    de troca de estampa). Criado em 03/09/2026 depois de detectar que
    produtos so com imagem_estampa (sem imagem_ambiente) as vezes saiam
    com cenas genericas de decoracao completamente desconectadas do
    produto real (ex: p002 "tapete medio" saiu com foto de quarto/cama).

    Criterio 3 (enquadramento/zoom) adicionado depois -- closes muito
    aproximados na intencao de mostrar a estampa estavam saindo
    distorcidos (ver filtro pedido pelo usuario).

    Criterios 4 (texto/legenda vazando da referencia) e 5 (quantidade de
    pecas) adicionados em 06/10/2026 depois de detectar, no processo de
    composicao em ambiente, uma foto final com a etiqueta "Estampa 2" da
    foto de referencia vazando pro resultado, e outra com 4 fronhas em
    vez do par (2) que a ficha tecnica real indica.
    """
    itens = extrair_itens_inclusos(produto.get("descricao_tecnica", ""))
    instrucao_itens = (
        f"5. A quantidade de cada peca na IMAGEM 1 bate com a ficha "
        f"tecnica real do produto ({'; '.join(itens)})? So REPROVE aqui "
        "se voce CONSEGUE CONTAR com clareza um numero errado de pecas "
        "(ex: 4 fronhas claramente separadas e visiveis, quando a ficha "
        "indica um par -- 2 fronhas). Na duvida, ou se as pecas estao "
        "parcialmente sobrepostas/dificeis de contar com certeza, "
        "considere que passou.\n\n"
        if itens else "\n"
    )
    n_criterios = "cinco" if itens else "quatro"
    return (
        f"Voce e um revisor de qualidade de fotos de produto para "
        f"e-commerce de enxovais. O produto e '{produto['nome']}' "
        f"(categoria: {produto['categoria']}).\n"
        f"IMAGEM 1: a foto FINAL gerada, que deveria mostrar esse produto.\n"
        f"IMAGENS 2 em diante: {n_referencias} foto(s) real(is) de "
        "referencia do produto (ambiente e/ou tecido cru).\n\n"
        "Confira:\n"
        "1. A IMAGEM 1 mostra claramente um produto da categoria "
        f"'{produto['categoria']}' reconhecivel como '{produto['nome']}'? "
        "Uma foto de cena generica de decoracao onde o produto nao "
        "aparece claramente, ou que mostra um item de categoria "
        "diferente, deve ser REPROVADA.\n"
        "2. O padrao/estampa e a cor do tecido na IMAGEM 1 batem com as "
        "referencias reais fornecidas? Um padrao/cor sem nenhuma relacao "
        "com o real deve ser REPROVADO.\n"
        "3. O enquadramento da IMAGEM 1 esta correto -- nem um zoom/corte "
        "tao aproximado na estampa que distorce o padrao do tecido ou "
        "deixa irreconhecivel o que e o produto, nem tao afastado que o "
        "produto fique pequeno demais na cena? Um corte exagerado demais "
        "deve ser REPROVADO.\n"
        "4. A IMAGEM 1 esta livre de texto/legenda/etiqueta/selo/marca "
        "d'agua CLARAMENTE LEGIVEL sobreposto a cena (ex: uma caixa de "
        "texto tipo 'Estampa 1'/'Estampa 2' vazada das referencias)? So "
        "REPROVE se houver letras ou numeros realmente legiveis "
        "sobrepostos a foto -- padrao decorativo do tecido, reflexo ou "
        "textura NAO conta como texto.\n"
        f"{instrucao_itens}"
        "Responda EXATAMENTE nesse formato, sem mais nada:\n"
        f"LINHA 1: 'SIM' se a imagem representa fielmente o produto, ou "
        f"'NAO' se reprovada por qualquer um dos {n_criterios} motivos "
        "acima.\n"
        "LINHA 2: se NAO, uma frase curta e especifica do motivo (pra "
        "poder corrigir). Se SIM, deixe a linha 2 vazia."
    )


def _verificar_com_prompt(prompt_texto: str, imagem_gerada: str, referencias: list[str]) -> tuple[bool, str]:
    """
    Nucleo generico do 'juiz': manda a imagem gerada + referencias + um
    prompt de verificacao pro Gemini e parseia a resposta SIM/NAO + motivo.
    Fatorado de verificar_foto_hero em 07/10/2026 pra poder ser
    reaproveitado por outros juizes dedicados no futuro.
    """
    client = _obter_cliente()
    partes = []
    for caminho in [imagem_gerada] + referencias:
        dados, mime_type = _carregar_bytes_imagem(caminho)
        partes.append(_part_de_bytes(dados, mime_type))
    partes.append(prompt_texto)

    resposta = client.models.generate_content(model=MODELO_IMAGEM, contents=partes)
    texto = (resposta.text or "").strip()
    linhas = texto.splitlines()
    passou = bool(linhas) and linhas[0].strip().upper().startswith("SIM")
    motivo = linhas[1].strip() if len(linhas) > 1 else ""
    return passou, motivo


def verificar_foto_hero(imagem_gerada: str, referencias: list[str], produto: dict) -> tuple[bool, str]:
    """
    Juiz geral (nao especifico de troca de estampa): confere se a foto
    gerada realmente retrata o produto certo, pra evitar cenas genericas
    desconectadas da referencia real. So texto de resposta, sem gerar
    imagem -- bem mais barato que uma geracao nova.
    """
    return _verificar_com_prompt(
        montar_prompt_verificacao_hero(produto, len(referencias)), imagem_gerada, referencias
    )


def montar_prompt_composicao_ambiente(produto: dict) -> str:
    """
    Prompt pra compor o produto DENTRO de uma foto de ambiente pronta (da
    biblioteca local ambientes_referencia/, escolhida por categoria -- ver
    executar_pipeline_semanal._escolher_foto_ambiente_principal), em vez de
    recriar a cena da foto de referencia original. Criado em 06/10/2026 a
    pedido do usuario: usar o processo completo (estampa real + referencia
    de escala/caimento real + ambiente pre-pronto) em vez de só editar a
    unica foto de ambiente que cada produto tem.

    3 imagens de referencia esperadas, NESSA ORDEM: (1) foto de estampa ou
    ambiente real (fidelidade de padrao/cor), (2) foto de ambiente real
    (escala/caimento -- pode repetir a (1) se so houver uma referencia),
    (3) foto limpa da biblioteca de ambientes (cena-base).
    """
    descricao = limpar_descricao_tecnica(produto.get("descricao_tecnica", ""))
    contexto_produto = f" Ficha tecnica do produto: {descricao[:400]}." if descricao else ""

    medidas_aberto, _ = extrair_dimensoes(produto.get("descricao_tecnica", ""))
    instrucao_medidas = (
        f" Use as medidas reais do produto aberto/em uso ({medidas_aberto}) "
        "pra manter escala e proporcoes corretas em relacao aos moveis/comodo."
        if medidas_aberto else ""
    )

    itens = extrair_itens_inclusos(produto.get("descricao_tecnica", ""))
    instrucao_itens = (
        f"\n\nITENS REAIS INCLUSOS NESSE PRODUTO, EXATAMENTE nessa "
        f"quantidade -- CONTE as pecas na imagem final antes de terminar "
        f"e confira que bate exatamente (NAO duplique nem invente pecas "
        f"extras -- ex: se o produto tem 02 Fronhas (= 1 PAR = 2 "
        f"travesseiros no total, nao 4), gere exatamente 2 travesseiros "
        f"na cama, nunca 4): "
        + "; ".join(itens) + "."
        if itens else ""
    )

    return (
        f"Voce recebeu 3 fotos de referencia do produto '{produto['nome']}' "
        f"({produto['categoria']}) de uma loja de enxovais.{contexto_produto}"
        f"{instrucao_medidas}{instrucao_itens}\n\n"
        "IMAGEM 1 e IMAGEM 2: fotos reais do produto (podem ter diagrama de "
        "medidas, setas, etiquetas tipo 'Estampa 1'/'Estampa 2', ou closes "
        "de amostra de tecido sobrepostos -- IGNORE completamente essas "
        "marcacoes, elas NAO podem aparecer, nem de forma alterada, na "
        "imagem final). Use-as SO como referencia fiel de padrao/cor/"
        "textura do tecido e de como o produto se comporta quando posto "
        "em uso (escala, caimento, formato) -- NAO use o comodo/cenario "
        "delas.\n"
        "IMAGEM 3: foto de um comodo real, limpo, SEM o produto -- essa E "
        "a cena-base que voce deve usar para a foto final.\n\n"
        "Gere uma nova fotografia realista mostrando ESSE PRODUTO (fiel ao "
        "padrao/estampa/cor real das imagens 1 e 2, na escala e caimento "
        "corretos) colocado/instalado dentro do comodo da IMAGEM 3 -- "
        "mantendo o comodo, os moveis, a iluminacao e o angulo de camera "
        "da IMAGEM 3 EXATAMENTE como estao, so adicionando o produto de "
        "forma realista (ex: a colcha estendida sobre a cama que ja "
        "aparece na imagem 3, a cortina pendurada na janela que ja aparece "
        "na cena, o jogo de toalha no suporte do banheiro).\n"
        "(a) ISSO E CRITICO: o tecido estampado tem um motivo que se "
        "REPETE em tamanho e espacamento CONSTANTES por toda a superficie "
        "-- nao reinterprete, redesenhe ou varie o tamanho do motivo, "
        "preserve os tracos finos (contorno, folhas, linhas) exatamente "
        "como aparecem nas imagens de referencia;\n"
        "(b) SE O PRODUTO TIVER MAIS DE UM TECIDO/ESTAMPA (ex: uma cor "
        "lisa na barra/babado/acabamento e um padrao floral/estampado no "
        "corpo principal, como costuma aparecer nas referencias): respeite "
        "EXATAMENTE qual parte de cada peca leva qual tecido, igual nas "
        "referencias -- nao deixe o padrao estampado 'vazar' ou se "
        "sobrepor a area do tecido liso (ou vice-versa). Se houver mais de "
        "uma peca igual (ex: um par de fronhas), TODAS as pecas do par "
        "devem usar a MESMA combinacao de tecidos, na MESMA posicao -- "
        "nao varie a composicao entre uma peca e outra;\n"
        "(c) NAO mude nada da cena da IMAGEM 3 alem de inserir o produto "
        "-- mesmos moveis, mesma parede, mesma iluminacao, mesmo angulo;\n"
        "(d) a imagem final deve ser UMA UNICA fotografia limpa, de corpo "
        "inteiro da cena, SEM nenhuma seta, caixa de texto, legenda, linha "
        "ou numero de medida, e SEM nenhum close/inset separado de "
        "amostra de tecido (nao monte colagem/grade de varias fotos);\n"
        "(e) sem pessoas, sem logotipo, sem NENHUM texto -- incluindo "
        "qualquer etiqueta/selo tipo 'Estampa 1' ou 'Estampa 2' que "
        "apareca nas imagens 1 ou 2, isso e so pra uso interno de "
        "referencia e nao pode vazar pra imagem final de jeito nenhum.\n"
        "Proporcao quadrada, adequada para post de Instagram."
    )


def gerar_foto_composta_ambiente_com_verificacao(
    produto: dict,
    caminho_ambiente_base: str,
    nome_arquivo: str | None = None,
    max_tentativas: int = 3,
    referencias_fidelidade_override: list[str] | None = None,
) -> str | None:
    """
    Gera o produto composto dentro de uma foto de ambiente pronta (ver
    montar_prompt_composicao_ambiente), com a mesma verificacao de
    fidelidade e retry das outras geracoes. Essa e a forma PRINCIPAL de
    gerar a foto do produto agora (ver executar_pipeline_semanal.
    obter_foto_hero) -- gerar_foto_hero_com_verificacao (edicao da cena
    original) vira fallback, usado so quando o produto nao tem categoria
    com pasta de ambiente correspondente ou nenhuma referencia real.

    referencias_fidelidade_override: quando passado, usa essa lista de
    fotos como referencia fiel de padrao/cor EM VEZ de imagem_estampa/
    imagem_ambiente -- usado pra gerar com uma estampa real DIFERENTE da
    usada no hero (ver executar_pipeline_semanal.obter_foto_ambiente_
    variacao, que passa uma foto de produto['fotos_estampas']). Criado em
    07/10/2026: o usuario corrigiu que a variedade de estampa deve vir da
    pasta "estampas" (fotos individuais e limpas de catalogo, uma por
    estampa real disponivel), nao de "fotos variadas" (que so mostra
    varias pecas juntas numa mesma foto de referencia).

    Retorna None se o produto nao tiver nenhuma referencia real (estampa/
    ambiente), ou se reprovar em todas as tentativas -- o chamador deve
    cair pro fallback nesse caso, nunca usar uma imagem reprovada.
    """
    referencias_fidelidade = referencias_fidelidade_override or [
        c for c in (produto.get("imagem_estampa"), produto.get("imagem_ambiente")) if c
    ]
    if not referencias_fidelidade:
        return None

    referencias_geracao = referencias_fidelidade + [caminho_ambiente_base]
    nome_arquivo = nome_arquivo or f"{produto['id']}_composto"
    correcao = None
    caminho_atual = None

    for tentativa in range(1, max_tentativas + 1):
        nome = f"{nome_arquivo}_v{tentativa}"
        print(f"  [tentativa {tentativa}/{max_tentativas}] compondo {produto['id']} no ambiente...")
        prompt = montar_prompt_composicao_ambiente(produto)
        if correcao:
            prompt += (
                f"\n\nATENCAO: uma tentativa anterior falhou por isso: "
                f"{correcao}. Corrija isso especificamente."
            )
        caminho_atual = _gerar_e_retornar_caminho(prompt, referencias_geracao, nome)
        if caminho_atual is None:
            print("  -> nenhuma imagem retornada, tentando de novo")
            continue

        # Verificacao so com as referencias de FIDELIDADE do produto --
        # a foto-base do ambiente nao mostra o produto, incluir ela aqui
        # so confundiria o juiz.
        passou, motivo = verificar_foto_hero(caminho_atual, referencias_fidelidade, produto)
        if passou:
            print(f"  [tentativa {tentativa}] aprovado na verificacao.")
            return caminho_atual

        print(f"  [tentativa {tentativa}] reprovado: {motivo}")
        correcao = motivo or "a imagem nao corresponde ao produto real"

    print(
        f"  aviso: composicao em ambiente de '{produto['id']}' nao passou "
        f"na verificacao apos {max_tentativas} tentativas -- caindo pro "
        f"fallback"
    )
    return None




def gerar_foto_hero_com_verificacao(
    produto: dict, nome_arquivo: str | None = None, max_tentativas: int = 3
) -> str | None:
    """
    Gera a foto principal do produto (edicao com foto(s) real(is), ou
    fallback por texto se nao houver nenhuma referencia) e confere
    automaticamente se o resultado retrata o produto certo
    (verificar_foto_hero), tentando de novo com o motivo da reprovacao
    ate max_tentativas vezes.

    Retorna o caminho da imagem aprovada, ou None se reprovar em todas as
    tentativas -- nesse caso o chamador deve pular esse produto, NAO
    publicar a imagem reprovada.

    Produtos sem nenhuma foto real de referencia (fallback por texto) nao
    tem como ter fidelidade verificada -- sao aceitos sem checagem (hoje
    nenhum produto do catalogo cai nesse caso). USADO COMO FALLBACK: a
    forma principal de gerar a foto agora e
    gerar_foto_composta_ambiente_com_verificacao (ver
    executar_pipeline_semanal.obter_foto_hero).
    """
    nome_arquivo = nome_arquivo or produto["id"]
    referencias = [
        c for c in (produto.get("imagem_ambiente"), produto.get("imagem_estampa")) if c
    ]

    correcao = None
    caminho_atual = None

    for tentativa in range(1, max_tentativas + 1):
        nome = f"{nome_arquivo}_v{tentativa}"
        print(f"  [tentativa {tentativa}/{max_tentativas}] gerando foto hero de {produto['id']}...")

        if referencias:
            prompt = montar_prompt_edicao(produto)
            if correcao:
                prompt += (
                    f"\n\nATENCAO: uma tentativa anterior falhou por isso: "
                    f"{correcao}. Corrija isso especificamente."
                )
            caminho_atual = _gerar_e_retornar_caminho(prompt, referencias, nome)
        else:
            prompt = montar_prompt_texto(produto, MARCA)
            client = _obter_cliente()
            resposta = client.models.generate_content(model=MODELO_IMAGEM, contents=prompt)
            caminho_atual = None
            candidato = resposta.candidates[0] if resposta.candidates else None
            if candidato is not None and candidato.content is not None:
                for i, parte in enumerate(candidato.content.parts):
                    if parte.inline_data is not None:
                        caminho_atual = str(PASTA_SAIDA / f"{nome}_{i}.png")
                        with open(caminho_atual, "wb") as f:
                            f.write(parte.inline_data.data)
                        break
            return caminho_atual  # sem referencia real, nao da pra verificar fidelidade

        if caminho_atual is None:
            print("  -> nenhuma imagem retornada, tentando de novo")
            continue

        passou, motivo = verificar_foto_hero(caminho_atual, referencias, produto)
        if passou:
            print(f"  [tentativa {tentativa}] aprovado na verificacao.")
            return caminho_atual

        print(f"  [tentativa {tentativa}] reprovado: {motivo}")
        correcao = motivo or "a imagem nao corresponde ao produto real"

    print(
        f"  aviso: '{produto['id']}' nao passou na verificacao apos "
        f"{max_tentativas} tentativas -- pulando este produto"
    )
    return None


def montar_prompt_estampa_close(produto: dict) -> str:
    """
    Prompt pra gerar um CLOSE-UP/macro do tecido real (so a textura/
    padrao, preenchendo o quadro) -- NAO o produto inteiro como na foto
    hero. Criado em 06/10/2026: as fotos cruas de referencia
    (imagem_estampa/imagem_ambiente) sempre vem com diagrama de medida e
    etiquetas tipo "Estampa 1" sobrepostos (confirmado visualmente em
    varios produtos), entao nao da pra mostrar elas direto num slide --
    essa funcao gera uma versao limpa e aproximada, do mesmo jeito que
    gerar_foto_hero_com_verificacao gera a cena inteira limpa.
    """
    descricao = limpar_descricao_tecnica(produto.get("descricao_tecnica", ""))
    contexto_produto = f" Ficha tecnica do produto: {descricao[:400]}." if descricao else ""

    return (
        f"Voce recebeu foto(s) real(is) do produto '{produto['nome']}' "
        f"({produto['categoria']}) de uma loja de enxovais.{contexto_produto}\n\n"
        "Gere uma nova fotografia PROFISSIONAL, estilo e-commerce, em "
        "CLOSE-UP/MACRO do TECIDO: um enquadramento bem aproximado "
        "mostrando so uma porcao do tecido (textura, padrao/estampa e "
        "cores reais em detalhe), preenchendo quase todo o quadro -- NAO "
        "a peca inteira, NAO o produto montado num ambiente.\n"
        "(a) siga fielmente o padrao, cor e textura reais do tecido "
        "mostrados nas referencias, sem inventar um padrao novo;\n"
        "(b) NAO inclua diagramas, setas, textos, numeros de medida, "
        "etiquetas ('Estampa 1', etc.) ou qualquer marcacao sobreposta "
        "das fotos de referencia -- a cena final deve ser limpa, sem "
        "nenhum elemento grafico alem do proprio tecido;\n"
        "(c) iluminacao natural suave, leve profundidade de campo, sem "
        "pessoas, sem logotipo, sem texto.\n"
        "Proporcao quadrada, adequada para post de Instagram."
    )


def gerar_foto_estampa_close_com_verificacao(
    produto: dict,
    nome_arquivo: str | None = None,
    max_tentativas: int = 3,
    referencias_override: list[str] | None = None,
) -> str | None:
    """
    Gera um close-up/macro limpo do tecido real do produto (ver
    montar_prompt_estampa_close), usando imagem_estampa (preferencia --
    ja e um close do tecido cru) ou imagem_ambiente como referencia, com
    o mesmo filtro automatico de qualidade da foto hero
    (verificar_foto_hero, com retry). Usado como 2a foto do slide de
    fechamento do formato "vitrine" (ver executar_pipeline_semanal.
    obter_foto_estampa_close), pra dar variedade de verdade sem usar a
    foto de referencia crua (que tem diagrama sobreposto) nem inventar
    uma foto de outro produto.

    referencias_override: mesma ideia de gerar_foto_composta_ambiente_
    com_verificacao -- quando passado, usa essa lista em vez de
    imagem_estampa/imagem_ambiente, pra gerar o close de uma estampa real
    DIFERENTE (ver produto['fotos_estampas']).

    Retorna None se o produto nao tiver nenhuma referencia real, ou se
    reprovar em todas as tentativas -- o chamador deve cair pra repetir
    a foto principal nesse caso, nunca usar a imagem crua ou uma
    reprovada.
    """
    referencias = referencias_override or [
        c for c in (produto.get("imagem_estampa"), produto.get("imagem_ambiente")) if c
    ]
    if not referencias:
        return None

    nome_arquivo = nome_arquivo or f"{produto['id']}_estampa_close"
    correcao = None
    caminho_atual = None

    for tentativa in range(1, max_tentativas + 1):
        nome = f"{nome_arquivo}_v{tentativa}"
        print(f"  [tentativa {tentativa}/{max_tentativas}] gerando close da estampa de {produto['id']}...")
        prompt = montar_prompt_estampa_close(produto)
        if correcao:
            prompt += (
                f"\n\nATENCAO: uma tentativa anterior falhou por isso: "
                f"{correcao}. Corrija isso especificamente."
            )
        caminho_atual = _gerar_e_retornar_caminho(prompt, referencias, nome)
        if caminho_atual is None:
            print("  -> nenhuma imagem retornada, tentando de novo")
            continue

        passou, motivo = verificar_foto_hero(caminho_atual, referencias, produto)
        if passou:
            print(f"  [tentativa {tentativa}] aprovado na verificacao.")
            return caminho_atual

        print(f"  [tentativa {tentativa}] reprovado: {motivo}")
        correcao = motivo or "a imagem nao corresponde ao produto real"

    print(
        f"  aviso: close da estampa de '{produto['id']}' nao passou na "
        f"verificacao apos {max_tentativas} tentativas -- caindo pra "
        f"repetir a foto principal no slide"
    )
    return None




def montar_prompt_composicao_dispersa(produto: dict, n_referencias: int) -> str:
    """
    Prompt pra gerar uma foto do produto reaproveitando a COMPOSICAO real
    das fotos em "fotos variadas" (produto disperso, empilhado ou dobrado
    sobre uma superficie) -- em vez da cena de "ambiente" inteiro (cama
    montada, quarto decorado) que montar_prompt_edicao gera. Criado em
    05/10/2026 a pedido do usuario: usar "fotos variadas" como referencia
    de composicao pra esse tipo de enquadramento mais solto/de produto.
    """
    descricao = limpar_descricao_tecnica(produto.get("descricao_tecnica", ""))
    contexto_produto = f" Ficha tecnica do produto: {descricao[:400]}." if descricao else ""

    return (
        f"Voce recebeu {n_referencias} foto(s) real(is) do produto "
        f"'{produto['nome']}' ({produto['categoria']}) de uma loja de "
        f"enxovais, mostrando o produto numa composicao solta -- disperso, "
        f"empilhado ou dobrado sobre uma superficie, NAO montado num "
        f"ambiente inteiro (sem cama feita, sem quarto decorado ao redor)."
        f"{contexto_produto}\n\n"
        "Gere uma nova fotografia de produto, profissional, para "
        "e-commerce, reaproveitando o MESMO TIPO de composicao das fotos "
        "de referencia (produto disperso/empilhado/dobrado, nao 'vestido' "
        "num ambiente completo): "
        "(a) siga fielmente o padrao, cor e escala real do tecido "
        "mostrados nas referencias, sem inventar um padrao novo; "
        "(b) mantenha o mesmo estilo de arranjo das referencias (pilha "
        "dobrada, peca solta sobre a superficie, etc.) -- nao troque por "
        "uma cena de ambiente com cama/sofa montado; "
        "(c) fundo neutro ou levemente texturizado (mesa de madeira clara, "
        "superficie off-white), iluminacao natural suave, estilo elegante "
        "e sofisticado, sem pessoas, sem logotipo, sem texto. "
        "Proporcao quadrada, adequada para post de Instagram."
    )


def gerar_composicao_dispersa_com_verificacao(
    produto: dict, nome_arquivo: str | None = None, max_tentativas: int = 3
) -> str | None:
    """
    Gera uma foto do produto em composicao dispersa/empilhada/dobrada,
    usando "fotos_variadas" do produto como referencia de arranjo (ver
    montar_prompt_composicao_dispersa), com o mesmo filtro automatico de
    qualidade da foto hero (verifica_foto_hero, com retry).

    Retorna None se o produto nao tiver "fotos_variadas" no banco, ou se
    reprovar em todas as tentativas -- o chamador deve pular esse
    produto/formato nesse caso, nunca publicar a imagem reprovada.
    """
    referencias = produto.get("fotos_variadas") or []
    if not referencias:
        return None

    nome_arquivo = nome_arquivo or f"{produto['id']}_disperso"
    correcao = None
    caminho_atual = None

    for tentativa in range(1, max_tentativas + 1):
        nome = f"{nome_arquivo}_v{tentativa}"
        print(f"  [tentativa {tentativa}/{max_tentativas}] gerando composicao dispersa de {produto['id']}...")
        prompt = montar_prompt_composicao_dispersa(produto, len(referencias))
        if correcao:
            prompt += (
                f"\n\nATENCAO: uma tentativa anterior falhou por isso: "
                f"{correcao}. Corrija isso especificamente."
            )
        caminho_atual = _gerar_e_retornar_caminho(prompt, referencias, nome)
        if caminho_atual is None:
            print("  -> nenhuma imagem retornada, tentando de novo")
            continue

        passou, motivo = verificar_foto_hero(caminho_atual, referencias, produto)
        if passou:
            print(f"  [tentativa {tentativa}] aprovado na verificacao.")
            return caminho_atual

        print(f"  [tentativa {tentativa}] reprovado: {motivo}")
        correcao = motivo or "a imagem nao corresponde ao produto real"

    print(
        f"  aviso: composicao dispersa de '{produto['id']}' nao passou na "
        f"verificacao apos {max_tentativas} tentativas -- revise visualmente "
        f"{caminho_atual} antes de usar"
    )
    return caminho_atual


def _part_de_bytes(dados: bytes, mime_type: str):
    from google.genai import types

    return types.Part.from_bytes(data=dados, mime_type=mime_type)


def _gerar_e_retornar_caminho(prompt: str, caminhos_referencia: list[str], nome_arquivo: str) -> str | None:
    """Como gerar_imagem_editada, mas retorna o caminho do arquivo salvo (ou None)."""
    client = _obter_cliente()
    partes = []
    for caminho in caminhos_referencia:
        dados, mime_type = _carregar_bytes_imagem(caminho)
        partes.append(_part_de_bytes(dados, mime_type))
    partes.append(prompt)

    resposta = client.models.generate_content(model=MODELO_IMAGEM, contents=partes)
    candidato = resposta.candidates[0] if resposta.candidates else None
    if candidato is None or candidato.content is None:
        # Gemini pode devolver content=None (ex: finish_reason
        # PROHIBITED_CONTENT, bloqueio de seguranca) em vez de so "sem
        # imagem" -- sem essa checagem o .content.parts explode com
        # AttributeError e derruba o pipeline inteiro em vez de so pular
        # pra proxima tentativa, como o retry ja espera.
        motivo = getattr(candidato, "finish_reason", "desconhecido") if candidato else "sem candidato"
        print(f"  -> nenhuma imagem retornada pela API (motivo: {motivo})")
        return None
    for i, parte in enumerate(candidato.content.parts):
        if parte.inline_data is not None:
            caminho = PASTA_SAIDA / f"{nome_arquivo}_{i}.png"
            with open(caminho, "wb") as f:
                f.write(parte.inline_data.data)
            print(f"  -> salvo em {caminho}")
            return str(caminho)
    print("  -> nenhuma imagem retornada pela API")
    return None


def _carregar_bytes_imagem(caminho: str):
    with open(caminho, "rb") as f:
        dados = f.read()
    mime_type = mimetypes.guess_type(caminho)[0] or "image/jpeg"
    return dados, mime_type


def _obter_cliente():
    try:
        from google import genai
    except ImportError:
        sys.exit(
            "Pacote 'google-genai' nao encontrado. "
            "Instale com: pip install google-genai --break-system-packages"
        )

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit(
            "Variavel de ambiente GEMINI_API_KEY nao definida.\n"
            "Rode: export GEMINI_API_KEY='sua_chave_aqui'"
        )

    return genai.Client(api_key=api_key)


def _salvar_resposta(resposta, nome_arquivo: str):
    salvou_alguma = False
    candidato = resposta.candidates[0] if resposta.candidates else None
    if candidato is None or candidato.content is None:
        motivo = getattr(candidato, "finish_reason", "desconhecido") if candidato else "sem candidato"
        print(f"  -> nenhuma imagem retornada pela API (motivo: {motivo})")
        return
    for i, parte in enumerate(candidato.content.parts):
        if parte.inline_data is not None:
            caminho = PASTA_SAIDA / f"{nome_arquivo}_{i}.png"
            with open(caminho, "wb") as f:
                f.write(parte.inline_data.data)
            print(f"  -> salvo em {caminho}")
            salvou_alguma = True
    if not salvou_alguma:
        print("  -> nenhuma imagem retornada pela API")


def gerar_imagem_texto(prompt: str, nome_arquivo: str):
    """Gera a imagem so a partir de texto (sem fotos reais de referencia)."""
    client = _obter_cliente()
    resposta = client.models.generate_content(model=MODELO_IMAGEM, contents=prompt)
    _salvar_resposta(resposta, nome_arquivo)


def gerar_imagem_editada(prompt: str, caminhos_referencia: list[str], nome_arquivo: str):
    """Gera a imagem usando 1+ fotos reais como referencia (edicao/composicao)."""
    from google.genai import types

    client = _obter_cliente()

    partes = []
    for caminho in caminhos_referencia:
        dados, mime_type = _carregar_bytes_imagem(caminho)
        partes.append(types.Part.from_bytes(data=dados, mime_type=mime_type))
    partes.append(prompt)

    resposta = client.models.generate_content(model=MODELO_IMAGEM, contents=partes)
    _salvar_resposta(resposta, nome_arquivo)


def gerar_carrossel():
    dados = carregar_banco()
    produtos = dados["produtos"]

    print(f"Gerando carrossel com {len(produtos)} slides para {MARCA['nome']}\n")

    for produto in produtos:
        print(f"[{produto['id']}] {produto['nome']}")

        referencias = [
            caminho for caminho in (produto.get("imagem_ambiente"), produto.get("imagem_estampa"))
            if caminho
        ]

        if referencias:
            prompt = montar_prompt_edicao(produto)
            print(f"  modo: edicao com {len(referencias)} foto(s) real(is)")
            gerar_imagem_editada(prompt, referencias, nome_arquivo=produto["id"])
        else:
            prompt = montar_prompt_texto(produto, MARCA)
            print("  modo: geracao por texto (sem fotos reais disponiveis)")
            gerar_imagem_texto(prompt, nome_arquivo=produto["id"])

        print()

    print("Concluido. Proximo passo: montar as legendas (tom de voz da marca)")
    print(f"CTA padrao sugerido: \"{MARCA['call_to_action_padrao']}\"")


if __name__ == "__main__":
    gerar_carrossel()
