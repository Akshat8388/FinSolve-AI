function toggleForm() {
      const loginForm = document.getElementById("loginForm");
      const signupForm = document.getElementById("signupForm");

      loginForm.classList.toggle("active");
      signupForm.classList.toggle("active");
    }

    window.onload = () => {
      document.getElementById("loginForm").classList.add("active");
    };

    document.querySelector('#loginForm form').addEventListener('submit', async (e) => {
      e.preventDefault();

      const name = e.target[0].value;
      const password = e.target[1].value;
      const role = e.target[2].value;

      try {
        const res = await fetch("/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, password, role }),
        });

        if (!res.ok) throw new Error("Please check your credentials or sign up.");

        const data = await res.json();
        localStorage.setItem("user", JSON.stringify({ name: data.user.name, role: data.user.role }));
        window.location.href = "/chat";
      } catch (err) {
        alert("Login failed: " + err.message);
      }
    });

    document.querySelector('#signupForm form').addEventListener('submit', async (e) => {
      e.preventDefault();

      const name = e.target[0].value;
      const email = e.target[1].value;
      const password = e.target[2].value;
      const role = e.target[3].value;

      try {
        const res = await fetch("/signup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, email, password, role }),
        });

        if (!res.ok) throw new Error("User existed ! Please Login");

        const data = await res.json();
        localStorage.setItem("user", JSON.stringify({ email: data.user.email, role: data.user.role , name: data.user.name,password:data.user.password }));
        window.location.href = "chat.html";
      } catch (err) {
        alert("Signup failed: " + err.message);
      }
    });