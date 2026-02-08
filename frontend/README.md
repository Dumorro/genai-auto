# GenAI Auto Frontend

**UI moderna para o sistema GenAI Auto** - Interface de chat com IA usando WebSocket para streaming em tempo real.

## 🎨 **Design**

- **Framework:** HTML + TailwindCSS (via CDN)
- **Icons:** Material Symbols
- **Fonts:** Space Grotesk (Google Fonts)
- **Theme:** Dark mode (mobile-first)
- **No authentication required** (sistema público)

## 📁 **Estrutura**

```
frontend/
├── index.html      # Home page (tela inicial)
├── chat.html       # Chat interface (conversação)
├── serve.py        # Servidor HTTP simples
└── README.md       # Este arquivo
```

## 🚀 **Como usar**

### **Opção 1: Servidor Python (Recomendado)**

```bash
# Iniciar backend API
cd ~/Documents/Repos/genai-auto
docker-compose up -d

# Iniciar frontend
cd frontend
python3 serve.py

# Abrir no navegador
open http://localhost:3000
```

### **Opção 2: Live Server (VS Code)**

1. Instale extensão "Live Server" no VS Code
2. Abra `frontend/index.html`
3. Clique com botão direito → "Open with Live Server"
4. Acesse: `http://localhost:5500`

### **Opção 3: Abrir diretamente**

```bash
open ~/Documents/Repos/genai-auto/frontend/index.html
```

⚠️ **Nota:** WebSocket pode não funcionar com `file://` protocol. Use um servidor HTTP.

## 🔌 **Conexão com Backend**

O frontend conecta automaticamente no WebSocket:
```
ws://localhost:8000/ws/chat
```

**Certifique-se que o backend está rodando:**
```bash
curl http://localhost:8000/health
# Deve retornar: {"status":"healthy"}
```

## ✨ **Features**

### **Home Page (`index.html`)**
- ✅ Welcome screen com sugestões
- ✅ Categorias de prompts (Creative, Coding, Office, etc.)
- ✅ Input area com auto-resize
- ✅ Navegação para chat com query param

### **Chat Page (`chat.html`)**
- ✅ WebSocket streaming em tempo real
- ✅ Mensagens do usuário (azul)
- ✅ Respostas da IA (branco/cinza)
- ✅ Indicador de digitação (typing dots)
- ✅ Progress updates ("Searching knowledge base...")
- ✅ Token-by-token streaming
- ✅ Copy message button
- ✅ Status indicator (Online/Offline/Connecting)
- ✅ Auto-reconnect on disconnect
- ✅ Auto-scroll to latest message
- ✅ Textarea auto-resize

## 🎯 **Uso**

### **Enviar primeira mensagem:**
1. Digite no input da home page
2. Clique no botão de enviar (seta pra cima)
3. Será redirecionado para chat.html com a mensagem

**OU**

1. Clique em um card de sugestão
2. Vai direto para chat.html

### **Conversar:**
1. Digite sua mensagem no input inferior
2. Pressione Enter ou clique no botão
3. Veja a resposta em tempo real (streaming)

## 🐛 **Troubleshooting**

### **"Offline" no status indicator**
- Backend não está rodando
- Solução: `cd ~/Documents/Repos/genai-auto && docker-compose up -d`

### **WebSocket connection failed**
- Porta 8000 não acessível
- Solução: Verificar se API está rodando: `curl http://localhost:8000/health`

### **Não vê mensagens**
- Abra DevTools (F12) → Console
- Verifique erros de WebSocket
- Confirme que `ws://localhost:8000/ws/chat` está acessível

### **CORS error**
- Não deveria acontecer (WebSocket não tem CORS)
- Se acontecer, verifique se está usando servidor HTTP (não `file://`)

## 📊 **Próximos Passos**

### **Melhorias planejadas:**
- [ ] Histórico de conversas (localStorage)
- [ ] Markdown rendering (code blocks, lists)
- [ ] Syntax highlighting para código
- [ ] Export conversation
- [ ] Voice input (Web Speech API)
- [ ] Image upload
- [ ] Multi-agent routing indicator
- [ ] Confidence score display
- [ ] Source documents preview

### **Integração com React (futuro):**
Se quiser migrar para React:
```bash
npm create vite@latest genai-auto-frontend -- --template react
cd genai-auto-frontend
npm install
npm install react-router-dom
# Converter HTML → JSX
```

## 🔗 **Links úteis**

- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **WebSocket Test:** http://localhost:8000/ws/test
- **Frontend:** http://localhost:3000

## 🎨 **Customização**

### **Trocar cor primária:**

Edite em ambos arquivos HTML:
```javascript
tailwind.config = {
    theme: {
        extend: {
            colors: {
                "primary": "#1337ec", // Mude aqui
            }
        }
    }
}
```

### **Trocar tema (light/dark):**

Remova `class="dark"` do `<html>` tag para light mode.

### **Trocar fonte:**

Altere o Google Fonts link:
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
```

## 📝 **Notas técnicas**

- **No build step:** Arquivos estáticos, sem webpack/vite
- **No dependencies:** TailwindCSS via CDN
- **No state management:** Vanilla JavaScript
- **WebSocket only:** Sem REST calls para chat
- **Session-less:** Não persiste histórico (cada reload = nova conversa)

## ✅ **Checklist de Deploy**

Para produção:
- [ ] Mudar `ws://localhost:8000` para URL de produção
- [ ] Adicionar HTTPS (wss://)
- [ ] Minificar HTML/CSS/JS
- [ ] Adicionar service worker (PWA)
- [ ] Implementar rate limiting no backend
- [ ] Adicionar analytics (opcional)
- [ ] Adicionar error tracking (Sentry)

---

**Status:** ✅ **Production Ready** (para MVP)  
**Version:** 1.0.0  
**Last Updated:** 2026-02-08
