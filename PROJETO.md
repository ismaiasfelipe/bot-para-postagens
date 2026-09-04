# Projeto: Bot de conteúdo Instagram — IL Variedades Enxovais

## Objetivo geral
Criar um pipeline automatizado que:
1. Usa um banco de dados real de produtos (fotos/vídeos da loja)
2. Gera imagens/vídeos novos com a API do Gemini, baseados nesse banco
3. Monta o conteúdo final (carrossel ou reel, já formatado pro Instagram)
4. Publica automaticamente no Instagram, numa programação semanal fixa

## Sobre a marca
- Nome: IL Variedades — Enxovais & Lar
- Negócio familiar de enxovais desde 1999, na cidade de Elói Mendes, MG
- Público-alvo: 25+ anos, maior concentração no público feminino
- Diferenciais: relação com o cliente, atendimento personalizado, produtos de alta qualidade
- Categorias de produto: Cama, Mesa, Banho, Sofá, Infantil

## Identidade visual (seguir sempre)
- Roxo Nobre: #582C4D
- Rosa Quartzo: #C48B9F
- Off-White: #FAF9F6
- Conceito: monograma "il" + coração, traço fluido/caligráfico
- Tipografia: sans-serif moderna (peso forte no nome, peso leve no subtítulo)

## Tom de voz
- Elegante, caloroso, acolhedor, em primeira pessoa do plural ("nossos produtos")
- Emojis discretos: 🤍 💜 ✨
- CTA padrão: "Chame no direct e garanta o seu!"
- Hashtags fixas: #ilvariedades #Elegância #Sofisticação #Conforto

## Onde está o banco de dados de produtos
**JÁ EXISTE UM CATÁLOGO REAL E ESTRUTURADO NO DRIVE** (construído em sessão
anterior a 22-31/07/2026, mais completo do que se pensava inicialmente).

Estrutura confirmada (pasta raiz "produtos", ID: 14HEzU31Lu4ieHCLGgKrDFkHI3Q3lOcOk):
```
produtos/
  cama (quarto)/          -> lençol casal 4pçs, colcha preguiada, jogo de
                              quarto, cobertor/manta, colcha pique queen,
                              coberdrom, capas de colchão (4 tamanhos)
  banho (banheiro)/
  mesa (cozinha)/
  sofá (cortinas, tapetes e adereços)/
  infantil/
```
Cada pasta de produto contém até 4 subpastas: `estampas` (fotos cruas do
tecido), `produto no ambiente` (fotos em cena/decoração), `fotos variadas`,
e `descrição` (Google Doc com ficha técnica: descrição, modelo,
características, composição, peso, dimensão).

**Cobertura real**: nem todo produto tem todas as subpastas preenchidas
ainda (ex: "lençol casal 4 pçs" tem 10 fotos em estampas + 1 em produto no
ambiente + ficha técnica completa, mas "fotos variadas" está vazia). O
script `conectar_drive.py` já lida com isso automaticamente.

- `conectar_drive.py` — já configurado com o ID real da pasta "produtos".
  Ao rodar, varre todas as categorias e produtos, pega a melhor foto
  disponível de cada um (prioridade: produto no ambiente > estampas >
  fotos variadas), baixa localmente e gera `produtos_reais.json` incluindo
  a ficha técnica de cada produto (quando existir).
- `produtos_exemplo.json` — arquivo de teste com dados fictícios, não é
  mais necessário usar, pode ser descartado depois que produtos_reais.json
  funcionar.
- **Pendente**: só falta criar a conta de serviço no Google Cloud e
  compartilhar a pasta "produtos" com ela (passo a passo dentro do próprio
  conectar_drive.py).

## Mapa completo da pasta-mãe no Drive (confirmado em 04/08/2026)
Pasta raiz: "Enxovais Conteúdo Bot" (ID: 1Wg7o1JBo6MQPsZVGLH8m2yQ2Qsu7RNyo)

```
Enxovais Conteúdo Bot/
├── marca/                          [PREENCHIDA]
│   ├── identidade visual/
│   ├── tom de voz/
│   ├── sobre a loja/
│   └── dados de contato e redes/
│
├── produtos/                       [PARCIALMENTE PREENCHIDA -- catálogo real]
│   ├── cama (quarto)/  banho (banheiro)/  mesa (cozinha)/
│   ├── sofá (cortinas, tapetes e adereços)/  infantil/
│   (cada produto: estampas/ · produto no ambiente/ · fotos variadas/ · descrição/)
│
├── campanhas/                      [PREENCHIDA -- 23 campanhas com orientações]
│   ├── dia do consumidor/ (produtos-alvo/ · copy/ · referências visuais/)
│   ├── dia das mulheres/  dia das mães/  dia das crianças/  dia dos namorados/
│   ├── primavera/  verão/  outono/  inverno/
│   ├── black friday/  natal/
│   ├── dia 1 do 1/  dia 2 do 2/  dia 3 do 3/  dia 4 do 4/  dia 5 do 5/
│   │   dia 6 do 6/  dia 7 do 7/  dia 8 do 8/  dia 9 do 9/  dia 10 do 10/
│   │   dia 11 do 11/  dia 12 do 12/  (promoções relâmpago mensais)
│   (cada pasta de campanha tem um doc "orientações-campanha": período,
│   cores, temática, categorias/produtos prioritários, tom de voz
│   específico, CTA, hashtags extras e referência visual)
│
└── referências e exemplos/         [SÓ ESTRUTURA, VAZIA]
    ├── exemplo de carrosséis/
    ├── copy's para vídeos/
    └── ambientes/
```

**Implicação para a programação semanal do bot:** existem 23 campanhas ao
todo -- 11 sazonais/datas comemorativas (Dia das Mulheres, Dia das Mães,
Dia do Consumidor, Outono, Dia dos Namorados, Inverno, Primavera, Dia das
Crianças, Black Friday, Verão, Natal) e 12 promoções relâmpago mensais
recorrentes ("Dia X do X", uma por mês, ex: 9/9, 10/10, 11/11, 12/12).
Cada uma tem um documento "orientações-campanha" com período, cores,
temática, categorias/produtos prioritários, tom de voz específico, CTA e
referência visual. O agendador semanal deve verificar se alguma campanha
está no período ativo (as mensais são sempre no dia N do mês N; as outras
têm janelas maiores) e priorizar as orientações daquela pasta em vez do
fluxo genérico. Quando cai numa mesma semana mais de uma campanha (ex:
Dia 5 do 5 no mesmo mês do Dia das Mães), as orientações já foram escritas
cruzando as duas intencionalmente. As subpastas "produtos-alvo", "copy" e
"referências visuais" de cada campanha ainda estão vazias -- servem para
quando o usuário quiser deixar algo pronto com antecedência, mas não são
obrigatórias: na ausência delas, o bot usa as orientações gerais do doc
principal.

## Importância de cada pasta (para o pipeline entender o que usar e quando)

**marca/** — fonte de verdade para tudo que é fixo e não muda por post:
cores, tipografia, conceito do logo, tom de voz, dados de contato. Todo
prompt de geração de imagem e toda legenda devem respeitar o que está aqui.

**produtos/** — o banco de mídia real. É daqui que o pipeline pega a foto
de referência e a ficha técnica de cada produto pra gerar o conteúdo.
Sem essa pasta não há o que postar.

**campanhas/** — a camada de contexto temporal. Diz o "quando" e o "por
quê" de cada post: se a semana cai dentro de alguma campanha (sazonal ou
promoção relâmpago mensal), o pipeline deve buscar aqui as orientações
específicas (cores, categorias prioritárias, tom, CTA) em vez de usar o
fluxo genérico. Sem essa pasta, todo post fica genérico o ano inteiro.

**referências e exemplos/** — pasta de estilo/qualidade, ainda vazia mas
com propósito definido: é onde entram exemplos prontos que servem de
"régua" visual e de escrita para o pipeline imitar.
- `exemplo de carrosséis/` — carrosséis (de qualquer marca, inclusive
  concorrentes ou referências externas) cujo layout/composição a loja
  gostaria de replicar. Serve de referência visual para a etapa de
  montagem do carrossel (que ainda não foi construída).
- `copy's para vídeos/` — exemplos de roteiro/legenda de vídeo que
  funcionam bem no nicho, para inspirar a geração de texto de reels.
- `ambientes/` — fotos de ambientes decorados (quartos, salas, mesas
  postas) que sirvam de referência de cenário para as imagens geradas
  via Gemini, complementando (não substituindo) as fotos reais de
  produto que já existem em produtos/*/produto no ambiente/.
Enquanto essa pasta estiver vazia, o pipeline funciona só com o que está
em marca/ e campanhas/ para orientação de estilo -- ela não é bloqueante,
mas populá-la deve melhorar a qualidade das gerações com o tempo.

## Status atual do projeto (o que já foi feito)
- [x] Identidade visual documentada (cores, tipografia, conceito)
- [x] Tom de voz documentado com exemplos reais de legendas antigas
- [x] Dados de contato e endereço confirmados
- [x] Catálogo real de produtos já existe e mapeado no Drive (fotos +
      ficha técnica), estrutura confirmada em 04/08/2026
- [x] Conta de serviço do Google Cloud configurada e pasta "produtos"
      compartilhada -- conectar_drive.py funcionando (corrigido bug de
      dict invertido que fazia todo produto ser pulado)
- [x] produtos_reais.json gerado com sucesso: 10/50 produtos têm foto
      (5 com imagem_ambiente + imagem_estampa, 5 só com imagem_estampa)
- [x] Pipeline de geração de imagem redesenhado (05/08/2026): descobrimos
      que gerar por texto puro (descrevendo cor/estampa) faz a IA
      **inventar** um padrão novo influenciado pelas cores da marca,
      distorcendo o produto real -- inaceitável.
      Nova abordagem validada: usar EDIÇÃO de imagem multi-input do Gemini,
      passando a foto real "produto no ambiente" (mesmo com o diagrama de
      medidas/setas/"Estampa 1-2" sobreposto -- o prompt já instrui a
      ignorar e remover essas marcações) + a foto real da "estampa" como
      referência, pedindo pra recriar a MESMA cena limpa e fiel ao tecido
      real. Testado 2x no produto "jogo de quarto", resultado muito
      próximo da foto real. gerar_carrossel_gemini.py agora escolhe
      automaticamente: modo edição (quando há imagem_ambiente e/ou
      imagem_estampa) ou fallback por texto (quando não há nenhuma foto
      real, hoje nenhum produto cai nesse caso).
- [ ] Continuar subindo o PNG de "produto no ambiente" (foto real + specs
      de medida) pra cada produto no Drive -- combinado com o usuário,
      ele vai preencher aos poucos; hoje só a categoria "cama (quarto)"
      tem alguns preenchidos
- [x] Camada gráfica (montar_post.py, 05/08/2026): compõe a foto gerada +
      badge do logo real (baixado do Drive, marca/identidade
      visual/logo - aplicações/png/, salvo em assets/logo_badge.png) +
      título/subtítulo + etiqueta com nome do produto, no estilo
      "CONHEÇA O MELHOR PARA A SUA CASA!". Camada 100% determinística
      (Pillow, sem custo de API) por cima da foto já gerada -- inclui
      recorte automático de bordas quase-brancas via `_recortar_bordas_brancas()`.
- [x] 10 formatos de carrossel definidos e exemplificados (05/08/2026) --
      ver FORMATOS_CARROSSEL.md pra descrição slide-a-slide de cada um.
      Blocos de construção reutilizáveis em montar_carrossel_campanha.py
      (montar_slide_hero, montar_slide_itens_inclusos, montar_slide_detalhes,
      montar_slide_variedade, montar_slide_texto, montar_slide_zoom_cheio)
      + montar_post.py (montar_post). Exemplos gerados em
      gerar_exemplos_formatos.py (reaproveita fotos já geradas, só usa
      API nova quando o formato exige ambiente genuinamente diferente).
      Regras aprendidas e aplicadas: sem floreios decorativos, texto nunca
      solto sobre foto sem caixa/sombra, logo completa no máximo 1-2x por
      carrossel (resto usa ícone ou nada -- assets/logo_icone.png), layouts
      diferentes entre slides do mesmo carrossel, cada formato com uma
      peculiaridade visual própria.
      **Ainda não integrado**: não existe uma função "gerar_carrossel(formato,
      produto, campanha)" que escolhe formato+produto+dados automaticamente --
      hoje cada formato é montado chamando as funções manualmente com dados
      passados na mão.
- [x] Filtro automático de qualidade (05/08/2026) -- verificar_troca_estampa()
      e trocar_estampa_com_verificacao() em gerar_carrossel_gemini.py, ver
      seção própria abaixo.
- [x] Conexão com a Instagram Graph API (03/09/2026) -- App "IL Variedades
      Bot" criado no Meta for Developers, vinculado ao BM 04 (IL Variedades
      Enxovais & Lar), usando o fluxo novo "Instagram API with Instagram
      Login" (graph.instagram.com, sem depender de token de Página do
      Facebook). Permissões ativas: instagram_business_basic,
      instagram_business_content_publish, instagram_business_manage_messages.
      Conta @ilvariedadesenxovais autorizada como testadora. Credenciais em
      `.env` (IG_APP_ID, IG_APP_SECRET, IG_USER_ID, IG_ACCESS_TOKEN).
      `publicar_instagram.py` criado com testar_conexao(),
      trocar_por_token_longa_duracao() (grant ig_exchange_token),
      renovar_token() via refresh_access_token (grant ig_refresh_token --
      o token gerado pelo botao "Gerar token" do painel ja vem de longa
      duracao/60 dias, exchange normal da "Session key invalid" nele;
      refresh funciona), publicar_carrossel() e publicar_imagem_unica().
      **Testado e validado em produção**: carrossel real
      (carrossel_p009_vitrine, jogo de quarto) publicado no feed de
      @ilvariedadesenxovais via upload_storage.enviar_carrossel() +
      publicar_instagram.publicar_carrossel() -- media_count da conta subiu
      de 26 para 27, confirmando publicação real.
      **Atenção**: o token de longa duração dura ~60 dias e precisa ser
      renovado antes de expirar (chamar refresh_access_token de novo e
      atualizar IG_ACCESS_TOKEN no .env) -- ainda não está automatizado.
- [x] Upload das imagens geradas para um storage público (validado
      05/08/2026, reconfirmado em produção real 03/09/2026)
- [ ] Agendador (cron) rodando o pipeline inteiro uma vez por semana --
      próximo item do roadmap agora que a publicação está validada
- [x] Orientações das 23 campanhas definidas e documentadas dentro de
      cada pasta no Drive (11 sazonais/datas comemorativas + 12
      promoções relâmpago mensais "Dia X do X")

## Aprendizado: troca de estampa num ambiente existente (05/08/2026)
Testamos usar a MESMA foto de ambiente com uma estampa DIFERENTE da
original (ex: trocar o floral azul do "jogo de quarto" pelo floral
amarelo de outra variante), pra visualizar produtos sem foto própria
reaproveitando um ambiente já fotografado.
- Passar a foto de estampa "como está" (foto dobrada, mostrando ao mesmo
  tempo a barra/acabamento E o corpo do tecido) faz o modelo confundir as
  duas regiões: ele só troca a barra/acabamento e mantém o padrão antigo
  no corpo principal, mesmo com o prompt pedindo troca total.
- **Solução que funcionou**: recortar (crop) só a parte PLANA/corpo do
  tecido na foto de estampa, sem a dobra, e usar só esse recorte como
  referência. Com isso a colcha e a fronha passaram a seguir fielmente a
  estampa nova. A cortina ainda ficou mista (não é crítico).
- Ainda não automatizado no código -- foi um recorte manual (Pillow) feito
  fora do pipeline. Se for usar troca de estampa de verdade no futuro,
  vale automatizar esse recorte (achar a metade "plana" da foto de
  estampa) dentro de conectar_drive.py ou gerar_carrossel_gemini.py.
- **Distorção de escala do motivo (resolvido 05/08/2026)**: mesmo com o
  recorte isolado, as flores saíam em tamanhos bem diferentes entre a
  colcha e a fronha (a IA "reinterpreta" a estampa em vez de repetir
  igual um tecido industrial). Reforçamos o prompt em
  `montar_prompt_edicao()` (gerar_carrossel_gemini.py) explicando que é
  um tecido com repetição de tamanho/espaçamento CONSTANTE (tipo papel de
  parede) e pra preservar os traços finos -- resolveu, padrão ficou
  consistente entre colcha/fronha/cortina. Efeito colateral observado: às
  vezes a IA devolve uma "ficha" com closes de amostra extras no topo em
  vez de só a foto limpa -- prompt reforçado de novo pra proibir isso
  explicitamente, mas ainda vale conferir visualmente cada geração.

## Técnica de troca de estampa completa validada (05/08/2026)
Fluxo que funcionou bem pra trocar TODA a variante de cor de um produto
(corpo floral + barra/acabamento liso), reaproveitando um ambiente já
fotografado:
1. Recortar da foto de estampa (pasta `estampas/`) duas referências
   isoladas e limpas: o **corpo** (parte plana do tecido, sem dobra) e a
   **barra/acabamento** (o triângulo liso com renda que aparece na dobra).
2. 1ª passada: gerar a partir da foto de ambiente original + as duas
   referências (corpo + barra), com prompt explicando os 3 papéis
   (ambiente/corpo/barra) e reforçando repetição industrial constante
   (ver `montar_prompt_edicao`). Às vezes acerta tudo, às vezes deixa
   algum elemento secundário (ex: cortina) com o padrão antigo -- rodar
   2-3x e escolher o melhor resultado costuma resolver a cama/produto
   principal.
3. 2ª passada (se algum elemento ainda ficou errado): usar o resultado
   BOM da 1ª passada como nova "imagem de ambiente" de entrada (em vez da
   foto original), + as mesmas referências de corpo/barra, com prompt
   dizendo explicitamente "essa imagem já está correta em X, mantenha
   IDÊNTICO, só corrija Y". Isso preserva o que já ficou bom sem arriscar
   perder ao regenerar do zero. Funcionou perfeitamente pra corrigir só a
   cortina sem alterar a cama já validada.
4. Resultados validados salvos em `referencias_validadas/` (fora de
   `saida/`, que é pra posts finais) -- ex:
   `jogo_de_quarto_estampa_amarela_completo_ok.png`.
Ainda é um processo manual/script avulso, não integrado como função
padrão em gerar_carrossel_gemini.py. Se a troca de estampa virar
recorrente, vale transformar esses passos numa função tipo
`trocar_estampa_produto(produto, nova_estampa_corpo, nova_estampa_barra)`.

## Filtro automático de qualidade (05/08/2026)
Depois de perceber que resultados com defeito (peça com a cor antiga)
às vezes passavam sem ninguém notar, adicionamos um "juiz" automático em
`gerar_carrossel_gemini.py`:
- `verificar_troca_estampa(imagem_gerada, estampa_corpo, estampa_barra, produto)`
  -- manda a imagem gerada + as 2 referências pro Gemini e pede pra
  conferir peça por peça (colcha, cada fronha, cortina topo/corpo, saia
  da cama) se bate com a referência. Só texto de resposta, sem gerar
  imagem -- bem mais barato que uma geração nova. Retorna (passou, motivo).
- `trocar_estampa_com_verificacao(produto, corpo, barra, nome_arquivo, max_tentativas=3)`
  -- gera, verifica, e se reprovar tenta corrigir automaticamente
  (reusando o resultado + o motivo da reprovação como instrução),
  até max_tentativas vezes. Retorna o caminho do melhor resultado mesmo
  se nunca passar (com aviso pra revisão manual).

**Validado**: pego a estampa azul do jogo de quarto (que tinha saído com
a cortina errada) e confirmei que o verificador identifica corretamente
o defeito toda vez, com descrição específica de qual peça e cor está
errada. A correção automática nem sempre converge em poucas tentativas
(no caso da azul, precisou de um ajuste manual pontual depois de 3
tentativas automáticas) -- mas o ponto principal funciona: erros não
passam mais silenciosamente, o sistema avisa qual imagem precisa de
atenção.

## Formato do produtos_reais.json (atualizado 05/08/2026)
Cada produto tem `imagem_ambiente` (foto real no ambiente, pode ter
diagrama de medidas sobreposto, ou null) e `imagem_estampa` (foto real
crua do tecido, ou null) em vez do antigo campo único `imagem_referencia`.
gerar_carrossel_gemini.py usa o(s) que existir(em) como entrada de edição
de imagem no Gemini; só cai pro modo texto puro se nenhum dos dois existir.

## Dispatcher dos 10 formatos (gerar_carrossel_completo.py, 05/08/2026)
`gerar_carrossel(formato, produto_id, pasta_saida=None, **dados)` -- ponto
de entrada único. Busca o produto em produtos_reais.json pelo ID, monta
os 4 slides do formato pedido (funções `_construir_*` mapeadas em
`FORMATOS`), salva em `saida/carrossel_<produto_id>_<formato>/slideN.png`.

Cada formato ainda espera fotos/dados específicos por fora (o dispatcher
NÃO gera fotos novas via Gemini -- isso é gerar_carrossel_gemini.py). Ver
o docstring do arquivo pra lista completa do que cada formato espera.

`extrair_itens_inclusos(descricao_tecnica)` -- parser da ficha técnica
(formato tab-separated do Google Docs, cabeçalhos+valores na mesma ordem)
que puxa a lista real de itens (ex: "01 Colcha casal 2,55m x 2,65m,
(Babado 50cm)") do campo CARACTERÍSTICAS, em vez de precisar digitar a
lista na mão. Cuidado ao debugar esse formato: as células vêm com `\r\n`
no final (não só `\n`), então qualquer comparação de cabeçalho precisa
dar `.strip()` em cada célula antes de comparar.

Testado e validado no formato "vitrine" com o produto p009 (jogo de
quarto) usando dados 100% reais (nome + itens inclusos da ficha técnica
real, sem nada digitado na mão pro slide 2).

**Blocos reutilizáveis relocados** pra montar_carrossel_campanha.py como
funções de primeira classe (antes viviam soltas em gerar_exemplos_formatos.py):
`montar_slide_duas_fotos()` e `montar_slide_grid_numerado()`.

## Upload pra storage público (upload_storage.py, 05/08/2026)
Bucket `il-variedades-carrossel` criado manualmente no Google Cloud
Console (mesmo projeto `project-4d4a1426-15ef-4d81-8a8` do service
account do Drive), com acesso público de leitura (`allUsers` = Storage
Object Viewer) e a conta de serviço `bot-il-variedades@...` com permissão
de escrita (Storage Object Admin).

`enviar_para_storage(caminho_local)` -- sobe um arquivo pra
`carrossel/<nome>` dentro do bucket e devolve a URL pública
(`https://storage.googleapis.com/il-variedades-carrossel/carrossel/...`).
`enviar_carrossel(lista_de_slides)` -- versão em lote pra um carrossel
inteiro (4 URLs na ordem certa).

Reaproveita a mesma `credenciais_drive.json` do Drive, só pedindo escopo
diferente (`devstorage.read_write` em vez de `drive.readonly`) -- não
precisou criar credencial nova.

**Testado e validado**: upload de um slide real + confirmação via `curl`
externo de que a URL responde 200 com o conteúdo certo.

## Próximo passo imediato (atualizado 03/09/2026)
Falta, em ordem de dependência:
1. Usuário fazer `git push` dos arquivos novos desta sessão (eu não
   consigo -- bloqueado pelo classificador do Claude Code): `tema_semana.py`,
   `_definir_tema.py`, `.github/workflows/*.yml`, `assets/fonts/*`,
   `cache_hero/*`, mudanças em `montar_post.py`/`montar_carrossel_campanha.py`/
   `executar_pipeline_semanal.py`/`gerar_carrossel_gemini.py`.
2. Testar os dois workflows manualmente no GitHub (aba Actions → "Run
   workflow") antes de confiar no agendamento automático: primeiro
   "Definir tema da semana", depois "Pipeline diario Instagram".
3. A partir de 11/09/2026 o pipeline diário passa a publicar de verdade
   sozinho (seg-sáb, 7h) -- usar essa semana pra definir o tema inicial
   e conferir os primeiros posts de perto.
4. Renovação do token de acesso do Instagram antes de expirar (~60 dias
   a partir de 03/09/2026, ou seja, por volta de 02/11/2026) -- rodar de
   novo o refresh via `publicar_instagram.py` e atualizar IG_ACCESS_TOKEN
   no `.env` (local) + fazer push. Vale automatizar isso no futuro.
5. Conforme o usuário for subindo mais PNGs de "produto no ambiente" no
   Drive, rodar conectar_drive.py de novo pra ampliar a cobertura além
   dos 10 produtos atuais (hoje só "cama (quarto)" tem fotos completas)
   -- também melhora a taxa de aprovação do verificador de foto hero.

## Calendário de campanhas + orquestrador semanal (03/09/2026)
`calendario_campanhas.py` -- copia local das orientações reais das 23
campanhas (puxadas do Drive), com cálculo automático de data (dia fixo,
segundo domingo, última sexta, ou intervalo cruzando o ano). Função
`campanhas_ativas_na_semana()` decide a campanha da semana (prioriza data
fixa sobre intervalo sazonal).

`executar_pipeline_semanal.py` -- orquestrador que junta tudo: escolhe
campanha → escolhe produto (por categoria + histórico, evita repetir os
últimos 8 posts) → gera/reaproveita a foto → monta o carrossel → escreve
a legenda → (com `--publicar`) sobe pro storage e publica de verdade.
Testado em preview com a campanha "Dia 9 do 9" + tapete médio, funcionou
ponta a ponta. **Escopo atual: só os 5 formatos que usam 1 foto hero**
(vitrine, campanha_sazonal, promocao_relampago, novidade_semana,
detalhe_textura) -- os outros 5 formatos exigem múltiplas fotos/produtos
e ainda pedem curadoria manual.

## Verificação automática de foto hero (03/09/2026) -- bug real encontrado
Descoberto que produtos SEM `imagem_ambiente` (só `imagem_estampa`) às
vezes geravam cenas completamente genéricas e desconectadas do produto
real (ex: p002 "tapete médio" saiu com foto de quarto/cama; confirmado
também em p001, p003, p004 -- todos os arquivos antigos em `saida/`
gerados na sessão de 04-05/08, antes desse fix). Causa: sem uma foto de
ambiente pra ancorar a cena, o Gemini "inventa" uma composição de
decoração genérica em vez de respeitar a referência de tecido.

Corrigido com `verificar_foto_hero()` + `gerar_foto_hero_com_verificacao()`
em `gerar_carrossel_gemini.py` (mesmo padrão do "juiz" já usado em
`verificar_troca_estampa`, generalizado pra foto principal): gera, pede
pro Gemini conferir se a foto bate com a categoria/padrão real, e se
reprovar, tenta de novo com o motivo (até 3x). Se reprovar em todas as
tentativas, retorna `None` -- o chamador (`executar_pipeline_semanal.py`)
pula esse produto e tenta o próximo candidato, NUNCA publica uma foto
reprovada.

Fotos aprovadas ficam em cache separado `cache_hero/{produto_id}.png`
(não reaproveita os arquivos antigos de `saida/`, que não passaram por
verificação). p001, p002, p003, p004 já foram regeradas e aprovadas
nesse cache -- confirmado visualmente por comparação com a foto real de
referência, bateram fielmente (mesma toalha/tapete, mesmo padrão/cor).

## Automação online via GitHub Actions (03/09/2026) -- substitui Task Scheduler
Decisão: em vez de Windows Task Scheduler (exigiria o PC ligado/logado
todo dia às 7h), o pipeline roda 100% na nuvem via GitHub Actions, no
próprio repositório (que já tem `.env`/`credenciais_drive.json`
commitados, então não precisou nem configurar GitHub Secrets).

Modelo de uso: o usuário define o "tema da semana" 1x por semana (de
qualquer lugar, pelo site/app do GitHub) e o pipeline publica sozinho de
segunda a sábado às 7h (10:00 UTC) seguindo esse tema, até a próxima
atualização.

- `tema_semana.py` -- le/escreve `tema_semana.json` (campanha_chave,
  categoria_foco, produto_id -- todos opcionais). `executar_pipeline_semanal.py`
  agora prioriza esse tema sobre a campanha automática do calendário.
- `.github/workflows/definir_tema.yml` -- workflow com `workflow_dispatch`
  e inputs (dropdown de campanha, categoria, produto). Acionar em
  github.com/ismaiasfelipe/bot-para-postagens → aba "Actions" → "Definir
  tema da semana" → "Run workflow" (funciona pelo navegador do celular
  também, sem precisar do PC).
- `.github/workflows/pipeline_diario.yml` -- roda via `cron: "0 10 * * 1-6"`
  (seg-sáb, 7h BRT). Só publica de verdade a partir de **11/09/2026**
  (guard de data no primeiro step) -- dá tempo do usuário atualizar o
  catálogo de produtos antes. Reinstala dependências, roda
  `executar_pipeline_semanal.py --publicar`, e commita de volta
  `historico_publicacoes.json` + `cache_hero/` + `saida/` pra manter
  continuidade entre execuções (cada run começa com checkout limpo do
  repo).

**Pendente do lado do usuário**: fazer push desses arquivos pro GitHub
(eu não consigo rodar `git push` diretamente -- bloqueado pelo
classificador de permissão do Claude Code), e testar 1x cada workflow
manualmente (via "Run workflow") antes do agendamento automático
começar valer.

## Fontes portáveis (03/09/2026) -- bug real encontrado
`montar_post.py` e `montar_carrossel_campanha.py` usavam fontes do
Windows (`C:\Windows\Fonts\segoeuib.ttf`, `LHANDW.TTF` -- Lucida
Handwriting), que não existem no Linux (onde o GitHub Actions roda) --
o pipeline quebraria completamente ao rodar na nuvem. Corrigido:
- Baixadas fontes open-source (licença OFL) pra `assets/fonts/`: **Open
  Sans** (variable, substitui Segoe UI Bold/Regular/Italic) e **Dancing
  Script** (variable, substitui Lucida Handwriting -- aliás combina
  melhor com o conceito "traço fluido/caligráfico" da marca).
- `_carregar_fonte()` (nova, duplicada nos dois arquivos) carrega a
  fonte variável e ajusta o peso certo via eixo `wght`
  (`set_variation_by_name`), substituindo toda chamada direta de
  `ImageFont.truetype`.
- Testado ponta a ponta: pipeline gerando carrossel com as fontes novas
  funciona igual, visualmente conferido.
- **Bug secundário encontrado e corrigido nesse teste**: o formato
  `promocao_relampago` estava recebendo a frase inteira do CTA da
  campanha como "condição" (título grande do slide 3), estourando o
  slide com texto demais. Agora usa um texto curto fixo ("Condição
  especial, só hoje!") -- o CTA completo já aparece por inteiro no
  slide 4.

## Repositório GitHub (criado 03/09/2026)
Projeto agora também vive em `github.com/ismaiasfelipe/bot-para-postagens`
(privado), sincronizado localmente porque a pasta `Documents\Enxovais`
já é compartilhada entre os dois PCs do usuário via OneDrive -- o clone
git nem precisou ser feito manualmente no segundo PC, o `.git` sincronizou
junto. Repositório inclui tudo, inclusive `credenciais_drive.json` e
`.env` (decisão explícita do usuário, mesma conta em ambos os PCs).
