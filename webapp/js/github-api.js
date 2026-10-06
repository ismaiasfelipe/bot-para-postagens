// Camada fina sobre a API REST do GitHub -- todo o "backend" desse app e
// isso: disparar os workflows que ja existem (.github/workflows/) e ler
// arquivos do repo direto. Nenhum servidor proprio, nenhuma credencial
// alem do token do GitHub guardado so no localStorage deste navegador.

const CONFIG_KEY = "il_bot_config";

function carregarConfig() {
  const bruto = localStorage.getItem(CONFIG_KEY);
  if (!bruto) return null;
  try {
    return JSON.parse(bruto);
  } catch {
    return null;
  }
}

function salvarConfig({ token, owner, repo, branch }) {
  localStorage.setItem(
    CONFIG_KEY,
    JSON.stringify({ token, owner, repo, branch: branch || "main" })
  );
}

function limparConfig() {
  localStorage.removeItem(CONFIG_KEY);
}

function estaConfigurado() {
  const c = carregarConfig();
  return !!(c && c.token && c.owner && c.repo);
}

async function _chamarGitHub(caminho, opcoes = {}) {
  const config = carregarConfig();
  if (!config) throw new Error("App nao configurado -- defina o token do GitHub primeiro.");

  const resposta = await fetch(`https://api.github.com${caminho}`, {
    ...opcoes,
    headers: {
      Authorization: `Bearer ${config.token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      ...(opcoes.headers || {}),
    },
  });

  if (!resposta.ok) {
    const corpo = await resposta.text().catch(() => "");
    throw new Error(`GitHub API ${resposta.status}: ${corpo || resposta.statusText}`);
  }
  return resposta;
}

/**
 * Dispara um workflow (equivalente a clicar "Run workflow" no site do
 * GitHub). arquivoWorkflow: nome do arquivo em .github/workflows/
 * (ex: "definir_tema.yml"). inputs: mesmo shape dos "inputs" do
 * workflow_dispatch no YAML.
 */
async function dispararWorkflow(arquivoWorkflow, inputs = {}) {
  const config = carregarConfig();
  await _chamarGitHub(
    `/repos/${config.owner}/${config.repo}/actions/workflows/${arquivoWorkflow}/dispatches`,
    {
      method: "POST",
      body: JSON.stringify({ ref: config.branch || "main", inputs }),
    }
  );
}

/** Le o conteudo de um arquivo de texto do repo (decodifica base64 -> string). */
async function lerArquivoRepo(caminhoArquivo) {
  const config = carregarConfig();
  const resposta = await _chamarGitHub(
    `/repos/${config.owner}/${config.repo}/contents/${encodeURIComponent(caminhoArquivo)}?ref=${config.branch || "main"}`
  );
  const dados = await resposta.json();
  const binario = atob(dados.content.replace(/\n/g, ""));
  const bytes = Uint8Array.from(binario, (c) => c.charCodeAt(0));
  return new TextDecoder("utf-8").decode(bytes);
}

/** Lista as ultimas execucoes de um workflow (pra mostrar status: rodando/concluido/erro). */
async function listarExecucoes(arquivoWorkflow, porPagina = 5) {
  const config = carregarConfig();
  const resposta = await _chamarGitHub(
    `/repos/${config.owner}/${config.repo}/actions/workflows/${arquivoWorkflow}/runs?per_page=${porPagina}`
  );
  const dados = await resposta.json();
  return dados.workflow_runs || [];
}

/** Confirma que o token funciona e tem acesso ao repo (pra validar na tela de config). */
async function testarAcesso() {
  const config = carregarConfig();
  const resposta = await _chamarGitHub(`/repos/${config.owner}/${config.repo}`);
  return resposta.json();
}
