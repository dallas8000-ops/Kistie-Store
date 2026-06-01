(function () {
  const stack = document.getElementById('kistieSupportStack');
  const fabToggle = document.getElementById('kistieFabToggle');
  const fabMenu = document.getElementById('kistieFabMenu');
  const openChatBtn = document.getElementById('kistieFabOpenChat');
  const chatWin = document.getElementById('kistie-chat-window');
  const closeBtn = document.getElementById('kistie-chat-close');
  const form = document.getElementById('kistie-chat-form');
  const input = document.getElementById('kistie-chat-input');
  const msgs = document.getElementById('kistie-chat-messages');

  if (!stack || !fabToggle || !fabMenu) return;

  let history = [];
  let chatOpened = false;

  function closeFabMenu() {
    fabMenu.hidden = true;
    fabToggle.setAttribute('aria-expanded', 'false');
    stack.classList.remove('kistie-support-stack--menu-open');
  }

  function toggleFabMenu() {
    const open = fabMenu.hidden;
    fabMenu.hidden = !open;
    fabToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    stack.classList.toggle('kistie-support-stack--menu-open', open);
    if (!open) closeChat();
  }

  function addMsg(text, role) {
    if (!msgs) return null;
    const div = document.createElement('div');
    div.className = 'kc-msg ' + role;
    div.textContent = text;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  function openChat() {
    if (!chatWin || !input) return;
    closeFabMenu();
    chatWin.classList.add('open');
    chatWin.setAttribute('aria-hidden', 'false');
    stack.classList.add('kistie-support-stack--chat-open');
    if (!chatOpened) {
      addMsg(
        'Hi! I\'m Kistie, your AI shopping assistant. Ask me about sizes, prices, stock or payment methods — in English or Luganda!',
        'bot'
      );
      chatOpened = true;
    }
    input.focus();
  }

  function closeChat() {
    if (!chatWin) return;
    chatWin.classList.remove('open');
    chatWin.setAttribute('aria-hidden', 'true');
    stack.classList.remove('kistie-support-stack--chat-open');
    history = [];
    chatOpened = false;
    if (msgs) msgs.innerHTML = '';
    if (input) input.value = '';
  }

  fabToggle.addEventListener('click', function () {
    if (chatWin && chatWin.classList.contains('open')) {
      closeChat();
      return;
    }
    toggleFabMenu();
  });

  if (openChatBtn) openChatBtn.addEventListener('click', openChat);
  if (closeBtn) closeBtn.addEventListener('click', closeChat);

  document.addEventListener('click', function (e) {
    if (!stack.contains(e.target)) {
      closeFabMenu();
    }
  });

  if (form && input) {
    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      addMsg(text, 'user');
      history.push({ role: 'user', content: text });
      const typing = addMsg('…', 'bot typing');
      try {
        const res = await fetch('/api/chat/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, history: history.slice(-6) }),
        });
        let data = null;
        try {
          data = await res.json();
        } catch (parseErr) {
          data = null;
        }
        const reply = data && data.reply
          ? data.reply
          : !res.ok
            ? 'Sorry, chat is temporarily busy. Please try again in a moment.'
            : 'Sorry, I could not get a response right now.';
        typing.textContent = reply;
        typing.className = 'kc-msg bot';
        history.push({ role: 'assistant', content: reply });
        if (history.length > 20) history = history.slice(-20);
      } catch (err) {
        typing.textContent = 'Connection issue. Please check internet and try again.';
        typing.className = 'kc-msg bot';
      }
      msgs.scrollTop = msgs.scrollHeight;
    });
  }
})();
