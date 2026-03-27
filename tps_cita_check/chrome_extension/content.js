// Content script for Cita Previa form automation.
// Runs in an isolated world — uses <script> tag injection to call
// page-world functions like envia() and enviar().

function injectAndRun(code) {
  const script = document.createElement("script");
  script.textContent = code;
  document.head.appendChild(script);
  script.remove();
}

window.addEventListener("message", (event) => {
  if (event.source !== window || !event.data || event.data.type !== "cita_auto") {
    return;
  }

  const { action, nie, name } = event.data;

  if (action === "fill_and_submit") {
    // Fill NIE and name into the first two visible text inputs.
    const inputs = document.querySelectorAll("input[type='text']");
    if (inputs.length >= 2) {
      inputs[0].value = nie;
      inputs[0].dispatchEvent(new Event("input", { bubbles: true }));
      inputs[0].dispatchEvent(new Event("change", { bubbles: true }));

      inputs[1].value = name;
      inputs[1].dispatchEvent(new Event("input", { bubbles: true }));
      inputs[1].dispatchEvent(new Event("change", { bubbles: true }));
    }
    // Call page-world function envia() to submit the form.
    injectAndRun("envia()");
  }

  if (action === "solicitar_cita") {
    // Call page-world function enviar('solicitud') to request the appointment.
    injectAndRun("enviar('solicitud')");
  }
});
