# Painel IL Variedades (PWA)

App de controle do bot, sem servidor próprio — fala direto com a API do
GitHub pra disparar os workflows que já existem (`definir_tema.yml`,
`pipeline_diario.yml`) e ler `historico_publicacoes.json` do repositório.

## Publicar (uma vez só)

1. No GitHub: **Settings → Pages → Source** → escolha **"GitHub Actions"**.
2. Dê um push em qualquer mudança dentro de `webapp/` (ou rode manualmente
   o workflow **"Publicar painel (PWA)"** em Actions) — ele publica
   automaticamente no GitHub Pages.
3. O link fica em **Settings → Pages** (algo como
   `https://ismaiasfelipe.github.io/bot-para-postagens/`).

## Usar no celular

1. Abra o link publicado no navegador do celular.
2. No primeiro acesso, o app pede um **token do GitHub**. Crie um
   (instruções dentro do próprio app, na tela inicial) com acesso **só a
   este repositório**, permissão de **Actions: Read and write** e
   **Contents: Read-only**.
3. Adicione à tela inicial ("Adicionar à tela de início" no menu do
   navegador) — ele abre como app, não como aba do navegador.

## O que cada aba faz

- **Postagens**: define o tema da semana (campanha/categoria/produto) —
  mesma coisa que rodar o workflow "Definir tema da semana" manualmente.
  Tem também um botão "Publicar agora" que dispara o pipeline diário
  fora do horário programado.
- **Chat**: só a interface por enquanto, sem IA conectada (fase 1).
- **Relatório**: lê `historico_publicacoes.json` direto do repositório e
  mostra os carrosséis/stories já publicados.

## Por que sem servidor

O bot inteiro já funciona assim: o "banco de dados" é o próprio repositório
git (`historico_publicacoes.json`, `tema_semana.json`), e quem dispara a
geração/publicação é o GitHub Actions. Um backend separado duplicaria onde
as credenciais (Gemini, Instagram, Google) precisam existir, sem necessidade.
