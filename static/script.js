const form = document.getElementById('question-form');
const questionInput = form.querySelector('textarea');
const sendButton = form.querySelector('button[type="submit"]');
const messages = document.getElementById('messages');
const welcome = document.getElementById('welcome');
const statusElement = document.getElementById('status');
const newChatButton = document.getElementById('new-chat');
let sessionId = null;

newChatButton.addEventListener('click', () => {
  sessionId = null;
  messages.replaceChildren();
  messages.hidden = true;
  welcome.hidden = false;
  questionInput.value = '';
  statusElement.textContent = 'Ask a question about the patch notes.';
  questionInput.focus();
});

function addMessage(text, type) {
  const message = document.createElement('div');
  message.className = `message message--${type}`;
  message.textContent = text;
  messages.appendChild(message);
  messages.scrollTop = messages.scrollHeight;
  return message;
}

form.addEventListener('submit', async function (event) {
  event.preventDefault();
  const question = questionInput.value.trim();

  if (!question || sendButton.disabled) return;

  welcome.hidden = true;
  messages.hidden = false;
  addMessage(question, 'user');
  questionInput.value = '';
  sendButton.disabled = true;
  newChatButton.disabled = true;
  statusElement.textContent = 'Preparing an answer…';

  try {
    const response = await fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, session_id: sessionId }),
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(typeof error.detail === 'string' ? error.detail : `Request failed (${response.status})`);
    }

    const data = await response.json();
    if (typeof data.answer !== 'string' || !Array.isArray(data.sources) || typeof data.session_id !== 'string') {
      throw new Error('Unexpected response from the server');
    }
    sessionId = data.session_id;
    const answer = data.answer.replace(/`([^`]+)`/g, '$1');
    const sources = [...new Set(data.sources.map(source => source.filename).filter(Boolean))];
    const missingSources = sources.filter(source => !answer.includes(source));
    addMessage(answer + (missingSources.length ? `\n\nSources: ${missingSources.join(', ')}` : ''), 'assistant');
    statusElement.textContent = 'Ask a question about the patch notes.';
  } catch (error) {
    addMessage(`Could not get an answer: ${error.message}`, 'error');
    statusElement.textContent = 'Please check the API and try again.';
  } finally {
    sendButton.disabled = false;
    newChatButton.disabled = false;
    questionInput.focus();
  }
});
