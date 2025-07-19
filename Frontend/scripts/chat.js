 // Typed.js intro
    var typed = new Typed('.element', {
      strings: [
        'Get instant insights on company data',
        'Personalized answers for each department',
        'Your smart AI assistant for decision-making',
      ],
      typeSpeed: 20,
      backSpeed: 20,
      loop: true
    });

    const messagesDiv = document.getElementById("messages");
    const input = document.getElementById("query");
    const sendBtn = document.getElementById("send-btn");
    const introDiv = document.getElementById("aiintro");
    const userInfo = document.getElementById("user-info");

    // Fetch user from localStorage
    const user = JSON.parse(localStorage.getItem("user") || "{}");

    if (!user.name || !user.role) {
      window.location.href = "/";
      throw new Error("User not logged in");
    }

    // Display user info
    userInfo.innerHTML = `
      <div><strong>${user.name}</strong></div>
      <div style="text-transform:capitalize">${user.role}</div>
    `;

    function appendMessage(text, sender) {
      const wrapper = document.createElement("div");
      wrapper.classList.add("message-wrapper");

      const msgDiv = document.createElement("div");
      msgDiv.classList.add("message", sender);

      if (sender === "bot") {
        msgDiv.innerHTML = marked.parse(text);
      } else {
        msgDiv.textContent = text;
      }

      if (sender === "bot") {
        wrapper.appendChild(msgDiv);
      } else {
        wrapper.style.justifyContent = "flex-end";
        msgDiv.style.alignSelf = "flex-end";
        wrapper.appendChild(msgDiv);
      }

      messagesDiv.appendChild(wrapper);
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    sendBtn.addEventListener("click", async () => {
      const question = input.value.trim();
      if (question === "") return;

      introDiv.style.display = "none";
      appendMessage(question, "user");
      input.value = "";
      input.disabled = true;
      sendBtn.disabled = true;

      let session_id = localStorage.getItem("session_id");
      if (!session_id) {
        session_id = crypto.randomUUID();
        localStorage.setItem("session_id", session_id);
      }

      try {
        const res = await fetch("/chat_Interface", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: question, role: user.role ,session_id})
        });

        if (!res.ok || !res.body) {
          throw new Error("Server error");
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let fullResponse = "";

        // Show empty message container first
        const wrapper = document.createElement("div");
        wrapper.classList.add("message-wrapper");

        const msgDiv = document.createElement("div");
        msgDiv.classList.add("message", "bot");
        msgDiv.innerHTML = "🧬..."; // typing placeholder
        
        wrapper.appendChild(msgDiv);
        messagesDiv.appendChild(wrapper);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          fullResponse += chunk;
          msgDiv.innerHTML = marked.parse(fullResponse);

          input.disabled = false;
          sendBtn.disabled = false;
        }

      } catch (err) {
        appendMessage("⚠️ Error: Could not get response from AI.", "bot");
      }

    });

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") sendBtn.click();
    });