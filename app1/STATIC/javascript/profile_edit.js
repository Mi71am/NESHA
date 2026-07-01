(function () {
  var form = document.getElementById("profileUpdateForm");
  if (!form) {
    return;
  }

  var fullName = document.getElementById("fullName");
  var email = document.getElementById("email");
  var phoneNumber = document.getElementById("phoneNumber");
  var newPassword = document.getElementById("newPassword");
  var confirmPassword = document.getElementById("confirmPassword");
  var passwordMatchError = document.getElementById("passwordMatchError");

  var allowedPasswordSpecial = /[!@#$%^&*()_+\-=?. ,]/;

  function getDigitsOnly(value) {
    return String(value || "").replace(/\D+/g, "");
  }

  function validateFullName() {
    var raw = String(fullName.value || "").replace(/\s+/g, " ");
    if (raw.length > 100) {
      raw = raw.slice(0, 100);
      fullName.value = raw;
    }

    var value = raw.trim();
    if (!value) {
      return false;
    }
    return /^[A-Za-z'-]+(\s+[A-Za-z'-]+)+$/.test(value);
  }

  function validateEmail() {
    var value = String(email.value || "").toLowerCase().trim();
    email.value = value;
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  }

  function validatePhone() {
    phoneNumber.value = getDigitsOnly(phoneNumber.value).slice(0, 10);
    return /^0\d{9}$/.test(phoneNumber.value);
  }

  function validateNewPassword() {
    var value = String(newPassword.value || "");
    if (!value) {
      return true;
    }
    if (value.length < 8) {
      return false;
    }
    if (!/[A-Z]/.test(value)) {
      return false;
    }
    if (!/[a-z]/.test(value)) {
      return false;
    }
    if (!/\d/.test(value)) {
      return false;
    }
    if (!allowedPasswordSpecial.test(value)) {
      return false;
    }
    return true;
  }

  function validateConfirmPassword() {
    var pw = String(newPassword.value || "");
    var confirm = String(confirmPassword.value || "");

    if (!pw && !confirm) {
      passwordMatchError.hidden = true;
      return true;
    }

    var ok = pw && confirm && pw === confirm;
    if (passwordMatchError) {
      passwordMatchError.hidden = !!ok;
    }
    return !!ok;
  }

  function setRuleState(ruleName, ok) {
    var el = document.querySelector('[data-rule="' + ruleName + '"]');
    if (!el) {
      return;
    }

    var baseLabel = el.getAttribute("data-label");
    if (!baseLabel) {
      baseLabel = el.textContent.replace(/^\s*[✓✗]\s*/, "");
      el.setAttribute("data-label", baseLabel);
    }

    el.classList.toggle("good", ok);
    el.classList.toggle("bad", !ok);
    el.textContent = (ok ? "✓ " : "✗ ") + baseLabel;
  }

  function updatePasswordRules() {
    var value = String(newPassword.value || "");
    var active = value.length > 0;

    setRuleState("length", !active || value.length >= 8);
    setRuleState("upper", !active || /[A-Z]/.test(value));
    setRuleState("lower", !active || /[a-z]/.test(value));
    setRuleState("number", !active || /\d/.test(value));
    setRuleState("special", !active || allowedPasswordSpecial.test(value));
  }

  phoneNumber.addEventListener("input", function () {
    phoneNumber.value = getDigitsOnly(phoneNumber.value).slice(0, 10);
  });

  form.querySelectorAll(".toggle-password").forEach(function (button) {
    button.addEventListener("click", function () {
      var targetId = button.getAttribute("data-target");
      var target = document.getElementById(targetId);
      if (!target) {
        return;
      }
      var isPassword = target.getAttribute("type") === "password";
      target.setAttribute("type", isPassword ? "text" : "password");
      button.textContent = isPassword ? "Hide" : "Show";
    });
  });

  newPassword.addEventListener("input", function () {
    updatePasswordRules();
    validateConfirmPassword();
  });
  confirmPassword.addEventListener("input", validateConfirmPassword);

  form.addEventListener("submit", function (event) {
    var ok = validateFullName() && validateEmail() && validatePhone() && validateNewPassword() && validateConfirmPassword();
    if (!ok) {
      event.preventDefault();
    }
  });

  updatePasswordRules();
})();
