# Monitor de Promoções no Telegram — Notebook Gamer

Automação em Python que monitora grupos e canais de ofertas no Telegram em tempo real e envia alertas instantâneos via Bot sempre que surge uma promoção de **Notebook Gamer** ou modelos com placa de vídeo dedicada (`RTX` / `GTX`).

O projeto foi desenhado para permitir que você mantenha todos os grupos de anúncio silenciados no Telegram e receba notificações no celular apenas quando aparecer uma oferta do seu interesse, rodando 24h por dia gratuitamente na nuvem.

## Arquitetura e Funcionamento

Como usuários comuns não têm permissão de administrador para adicionar bots dentro de canais de ofertas de terceiros, este projeto combina duas frentes oficiais do Telegram:

1. **Leitura via Cliente ([Telethon](https://docs.telethon.dev/)):** Conecta à conta do usuário através da [API oficial do Telegram](https://core.telegram.org/api/obtaining_api_id) utilizando autenticação em texto ([`StringSession`](https://docs.telethon.dev/en/stable/concepts/sessions.html)), permitindo funcionar em servidores de nuvem com disco efêmero sem perder o login a cada reinicialização.
2. **Filtro Inteligente por Expressões Regulares (`Regex`):** Analisa cada nova mensagem recebida nos grupos/canais e identifica menções diretas (`notebook gamer`, `note gamer`, `laptop gamer`), linhas gamers consagradas no Brasil (`Acer Nitro`, `Nitro V15`, `Nitro 5`, `Predator Helios`, `Dell G15`, `Alienware`, `Lenovo LOQ`, `Lenovo Legion`, `Asus TUF`, `ROG Strix`, `ROG Zephyrus`, `HP Victus`, `MSI Katana`, `MSI Cyborg`) e notebooks anunciados diretamente pela GPU (`Notebook ... RTX/GTX`).
3. **Disparo de Alerta ([Telegram Bot API](https://core.telegram.org/bots/tutorial)):** Envia a oferta formatada em HTML — com o nome do canal e o link direto para a mensagem original — através de um bot particular criado no `@BotFather`.
4. **Servidor HTTP Keep-Alive Embutido:** Inclui um servidor web leve (`http.server`) em segundo plano na porta definida pela variável `PORT` (padrão `8080`) para responder a verificações de integridade do [UptimeRobot](https://uptimerobot.com/), impedindo que o serviço gratuito no [Render](https://render.com/docs/free) entre em hibernação após 15 minutos de inatividade.

## Estrutura do Repositório

| Arquivo | Descrição |
| :--- | :--- |
| `monitor_promocoes_telegram.py` | Script principal contendo o gerador de `StringSession`, o motor de filtragem via Regex, o cliente Telethon e o servidor HTTP Keep-Alive |
| `requirements.txt` | Declaração da única dependência externa do projeto (`telethon`) |

## Variáveis de Ambiente

Para executar o projeto no [Render](https://render.com/docs/free) (ou em qualquer plataforma de nuvem), configure as seguintes variáveis em **Environment Variables**:

| Variável | Obrigatória | Descrição |
| :--- | :--- | :--- |
| `API_ID` | Sim | ID numérico da aplicação obtido em [my.telegram.org](https://core.telegram.org/api/obtaining_api_id) |
| `API_HASH` | Sim | Hash secreto de 32 caracteres obtido em [my.telegram.org](https://core.telegram.org/api/obtaining_api_id) |
| `STRING_SESSION` | Sim | Chave de sessão gerada localmente via `python monitor_promocoes_telegram.py --gerar-sessao` |
| `BOT_TOKEN` | Recomendado | Token HTTP do bot de alertas criado no `@BotFather` ([documentação oficial](https://core.telegram.org/bots/tutorial)) |
| `MEU_CHAT_ID` | Recomendado | ID numérico da sua conta do Telegram que receberá os alertas do bot |
| `CHATS_MONITORADOS` | Opcional | Lista de usernames ou IDs de grupos específicos separados por vírgula (se vazio, monitora todos os grupos e canais da conta) |

## Como Executar e Fazer Deploy

### 1. Gerar a sessão localmente (apenas na primeira vez)

No seu computador, instale a dependência e execute o modo interativo para autenticar sua conta e obter sua `STRING_SESSION` e seu `MEU_CHAT_ID`:

```bash
pip install telethon
python monitor_promocoes_telegram.py --gerar-sessao
```

### 2. Deploy no Render (Nuvem Gratuita)

1. Conecte este repositório privado a um novo **Web Service** no [Render](https://render.com/docs/free).
2. Configure os comandos de execução:
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `python monitor_promocoes_telegram.py`
3. Adicione as variáveis de ambiente listadas na tabela acima (`API_ID`, `API_HASH`, `STRING_SESSION`, `BOT_TOKEN` e `MEU_CHAT_ID`).
4. Cadastre a URL pública gerada pelo Render em um monitor HTTP(s) gratuito no [UptimeRobot](https://uptimerobot.com/) com intervalo de 5 minutos para manter a instância ativa 24/7.

## Personalização de Filtros

Para adicionar, editar ou remover categorias e palavras-chave monitoradas, basta editar o dicionário `PADROES_INTERESSE` dentro de `monitor_promocoes_telegram.py` e realizar o commit no GitHub — o [Render](https://render.com/docs/deploys) atualizará o serviço automaticamente.
