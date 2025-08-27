async function sendMessage() {
  const inputEl = document.getElementById("user-input");
  const fileEl = document.getElementById("image-input");
  const message = inputEl.value.trim();
  const image = fileEl.files[0];

  if (!message && !image) return;

  appendMessage("user", message || "[Uploaded an image]");
  inputEl.value = "";
  fileEl.value = "";

  const chatBox = document.getElementById("chat-box");
  const botMessage = document.createElement("div");
  botMessage.className = "message bot";
  chatBox.appendChild(botMessage);

  const formData = new FormData();
  formData.append("input", message);
  if (image) {
    formData.append("image", image);
  }

  const response = await fetch("/process", {
    method: "POST",
    body: formData
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    botMessage.textContent += decoder.decode(value);
    chatBox.scrollTop = chatBox.scrollHeight;
  }
}

function appendMessage(sender, text) {
  const chatBox = document.getElementById("chat-box");
  const messageEl = document.createElement("div");
  messageEl.className = "message " + sender;
  messageEl.textContent = text;
  chatBox.appendChild(messageEl);
  chatBox.scrollTop = chatBox.scrollHeight;
}
