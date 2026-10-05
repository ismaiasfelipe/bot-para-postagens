// Service worker minimo: so cacheia o "shell" do app (HTML/CSS/JS/icones)
// pra instalar/abrir rapido. Chamadas pra api.github.com NUNCA passam
// pelo cache (precisam de dado fresco e vao com o token de autenticacao).

const CACHE = "il-painel-v1";
const ARQUIVOS_SHELL = [
  "./",
  "index.html",
  "manifest.webmanifest",
  "css/style.css",
  "js/campanhas.js",
  "js/github-api.js",
  "js/app.js",
  "icons/icon-192.png",
  "icons/icon-512.png",
];

self.addEventListener("install", (evento) => {
  evento.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(ARQUIVOS_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys().then((chaves) =>
      Promise.all(chaves.filter((c) => c !== CACHE).map((c) => caches.delete(c)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (evento) => {
  const url = new URL(evento.request.url);
  if (url.hostname === "api.github.com") return; // nunca cachear a API

  evento.respondWith(
    caches.match(evento.request).then((resposta) => resposta || fetch(evento.request))
  );
});
