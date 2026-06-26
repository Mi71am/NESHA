(function () {
  var form = document.getElementById('signupForm');
  if (!form) {
    return;
  }

  var fullName = document.getElementById('fullName');
  var email = document.getElementById('email');
  var phoneNumber = document.getElementById('phoneNumber');
  var roleSelect = document.getElementById('roleSelect');
  var password = document.getElementById('password');
  var confirmPassword = document.getElementById('confirmPassword');
  var submit = document.getElementById('signupSubmit');
  var passwordMatchError = document.getElementById('passwordMatchError');

  if (passwordMatchError) {
    passwordMatchError.hidden = true;
  }

  var cashierFields = document.getElementById('cashierFields');
  var schoolFields = document.getElementById('schoolFields');

  var cashierNationalId = document.getElementById('cashierNationalId');
  var cashierEmployeeNumber = document.getElementById('cashierEmployeeNumber');
  var cashierWorkstationNumber = document.getElementById('cashierWorkstationNumber');
  var cashierInstitutionName = document.getElementById('cashierInstitutionName');
  var cashierYearsOfService = document.getElementById('cashierYearsOfService');

  var schoolNationalId = document.getElementById('schoolNationalId');
  var schoolName = document.getElementById('schoolName');
  var schoolCode = document.getElementById('schoolCode');
  var tscNumber = document.getElementById('tscNumber');
  var schoolPosition = document.getElementById('schoolPosition');
  var schoolYearsOfService = document.getElementById('schoolYearsOfService');

  var schoolRoleOptions = [
    { value: '', label: 'Select role at school' },
    { value: 'Head Teacher', label: 'Head Teacher' },
    { value: 'Deputy Head Teacher', label: 'Deputy Head Teacher' },
    { value: 'Teacher', label: 'Teacher' },
    { value: 'Bursar', label: 'Bursar' }
  ];

  schoolPosition = ensureSchoolRoleDropdown();

  var allowedPasswordSpecial = /[!@#$%^&*()_+\-=?. ,]/;
  var invalidPasswordChars = /[^A-Za-z0-9!@#$%^&*()_+\-=?. ,]/;
  var passwordRules = {
    length: function (v) { return v.length >= 8; },
    upper: function (v) { return /[A-Z]/.test(v); },
    lower: function (v) { return /[a-z]/.test(v); },
    number: function (v) { return /\d/.test(v); },
    special: function (v) { return allowedPasswordSpecial.test(v); }
  };

  var baseFields = [fullName, email, phoneNumber, roleSelect, password, confirmPassword].filter(Boolean);
  var cashierRoleFields = [
    cashierNationalId,
    cashierEmployeeNumber,
    cashierWorkstationNumber,
    cashierInstitutionName,
    cashierYearsOfService
  ].filter(Boolean);
  var schoolRoleFields = [
    schoolNationalId,
    schoolName,
    schoolCode,
    tscNumber,
    schoolPosition,
    schoolYearsOfService
  ].filter(Boolean);

  function normalizeSpaces(value) {
    return (value || '').replace(/\s+/g, ' ').trim();
  }

  function capitalizeWords(value) {
    return normalizeSpaces(value)
      .split(' ')
      .filter(Boolean)
      .map(function (word) {
        return word
          .split(/([-'])/)
          .map(function (piece) {
            if (piece === '-' || piece === "'") {
              return piece;
            }
            return piece.charAt(0).toUpperCase() + piece.slice(1).toLowerCase();
          })
          .join('');
      })
      .join(' ');
  }

  function getErrorAnchor(field) {
    if (!field) {
      return null;
    }
    var parent = field.parentElement;
    if (parent && parent.classList && parent.classList.contains('input-wrap')) {
      return parent;
    }
    return field;
  }

  function ensureErrorElement(field) {
    if (!field) {
      return null;
    }
    if (field._clientErrorEl) {
      return field._clientErrorEl;
    }

    var el = document.createElement('p');
    el.className = 'field-error js-error';
    el.style.display = 'none';
    el.style.opacity = '0';
    el.style.transition = 'opacity 180ms ease';

    var anchor = getErrorAnchor(field);
    if (anchor) {
      anchor.insertAdjacentElement('afterend', el);
    }

    field._clientErrorEl = el;
    return el;
  }

  function showError(field, message) {
    if (!field) {
      return;
    }
    var el = ensureErrorElement(field);
    if (el) {
      el.textContent = message;
      el.style.display = 'block';
      requestAnimationFrame(function () {
        el.style.opacity = '1';
      });
    }
    field.style.border = '2px solid #ff7070';
  }

  function clearError(field) {
    if (!field) {
      return;
    }
    var el = ensureErrorElement(field);
    if (el) {
      el.style.opacity = '0';
      el.style.display = 'none';
      el.textContent = '';
    }
    field.style.border = '2px solid #8ad18a';
  }

  function resetFieldState(field) {
    if (!field) {
      return;
    }
    var el = ensureErrorElement(field);
    if (el) {
      el.style.opacity = '0';
      el.style.display = 'none';
      el.textContent = '';
    }
    field.style.border = '';
  }

  function setSectionVisible(section, isVisible) {
    if (!section) {
      return;
    }
    section.classList.toggle('is-visible', isVisible);
  }

  function clearHiddenGroup(fields) {
    fields.forEach(function (field) {
      if (!field) {
        return;
      }
      field.value = '';
      resetFieldState(field);
    });
  }

  function setRuleState(ruleName, ok) {
    var el = document.querySelector('[data-rule="' + ruleName + '"]');
    if (!el) {
      return;
    }

    var baseLabel = el.getAttribute('data-label');
    if (!baseLabel) {
      baseLabel = el.textContent.replace(/^\s*[✓✗]\s*/, '');
      el.setAttribute('data-label', baseLabel);
    }

    el.classList.toggle('good', ok);
    el.classList.toggle('bad', !ok);
    el.textContent = (ok ? '✓ ' : '✗ ') + baseLabel;
  }

  function validatePasswordChecklist(value) {
    var allOk = true;
    Object.keys(passwordRules).forEach(function (ruleName) {
      var ok = passwordRules[ruleName](value);
      setRuleState(ruleName, ok);
      if (!ok) {
        allOk = false;
      }
    });
    return allOk;
  }

  function attachNumericGuard(field) {
    if (!field) {
      return;
    }

    field.addEventListener('beforeinput', function (event) {
      if (!event.data) {
        return;
      }
      if (!/^\d+$/.test(event.data)) {
        event.preventDefault();
      }
    });

    field.addEventListener('paste', function (event) {
      var text = (event.clipboardData || window.clipboardData).getData('text') || '';
      if (!/^\d+$/.test(text.trim())) {
        event.preventDefault();
      }
    });
  }

  function attachPhoneGuard() {
    if (!phoneNumber) {
      return;
    }

    phoneNumber.addEventListener('beforeinput', function (event) {
      if (!event.data) {
        return;
      }
      if (!/^[\d+\s]+$/.test(event.data)) {
        event.preventDefault();
      }
    });

    phoneNumber.addEventListener('paste', function (event) {
      var text = (event.clipboardData || window.clipboardData).getData('text') || '';
      if (!/^[\d+\s]+$/.test(text)) {
        event.preventDefault();
      }
    });
  }

  function validateFullName() {
    var value = capitalizeWords(fullName.value).slice(0, 100);
    fullName.value = value;

    if (!value) {
      showError(fullName, 'Full name is required.');
      return false;
    }
    if (value.length < 5) {
      showError(fullName, 'Name is too short.');
      return false;
    }

    var words = value.split(' ').filter(Boolean);
    if (words.length < 2) {
      showError(fullName, 'Please enter your first and last name.');
      return false;
    }

    if (!/^[A-Za-z'-]+(\s+[A-Za-z'-]+)+$/.test(value)) {
      showError(fullName, 'Name can only contain letters.');
      return false;
    }

    clearError(fullName);
    return true;
  }

  function validateEmail() {
    var raw = email.value || '';

    if (!raw.trim()) {
      showError(email, 'Email address is required.');
      return false;
    }
    if (/\s/.test(raw)) {
      showError(email, 'Email cannot contain spaces.');
      return false;
    }

    var value = raw.toLowerCase().trim();
    email.value = value;

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      showError(email, 'Enter a valid email address.');
      return false;
    }

    clearError(email);
    return true;
  }

  function validatePhone() {
    var raw = phoneNumber.value || '';

    if (!raw.trim()) {
      showError(phoneNumber, 'Phone number is required.');
      return false;
    }
    if (/[A-Za-z]/.test(raw)) {
      showError(phoneNumber, 'Phone number cannot contain letters.');
      return false;
    }

    var value = raw.replace(/\s+/g, '');
    phoneNumber.value = value;

    if (!/^\+?\d+$/.test(value)) {
      showError(phoneNumber, 'Enter a valid Kenyan phone number.');
      return false;
    }

    var normalized = value.charAt(0) === '+' ? value.slice(1) : value;
    if (!/^07\d{8}$/.test(normalized) && !/^2547\d{8}$/.test(normalized)) {
      showError(phoneNumber, 'Enter a valid Kenyan phone number.');
      return false;
    }

    clearError(phoneNumber);
    return true;
  }

  function validatePassword() {
    var value = password.value || '';

    if (!value) {
      showError(password, 'Password is required.');
      validatePasswordChecklist('');
      return false;
    }
    if (value.length < 8 || value.length > 32) {
      showError(password, 'Password must be between 8 and 32 characters.');
      validatePasswordChecklist(value);
      return false;
    }
    if (invalidPasswordChars.test(value)) {
      showError(password, 'Password contains unsupported characters.');
      validatePasswordChecklist(value);
      return false;
    }

    var rulesOk = validatePasswordChecklist(value);
    if (!rulesOk) {
      showError(password, 'Password does not meet the required format.');
      return false;
    }

    clearError(password);
    return true;
  }

  function validateConfirmPassword() {
    var value = confirmPassword.value || '';

    if (!value) {
      showError(confirmPassword, 'Confirm password is required.');
      return false;
    }

    if (value !== password.value) {
      showError(confirmPassword, 'Passwords do not match.');
      return false;
    }

    clearError(confirmPassword);
    return true;
  }

  function validateNationalId(field) {
    if (!field) {
      return true;
    }

    var value = (field.value || '').replace(/\s+/g, '');
    field.value = value;

    if (!value) {
      showError(field, 'National ID is required.');
      return false;
    }
    if (!/^\d{8}$/.test(value)) {
      showError(field, 'National ID must contain exactly 8 digits.');
      return false;
    }

    clearError(field);
    return true;
  }

  function validateTscNumber() {
    if (!tscNumber) {
      return true;
    }

    var value = (tscNumber.value || '').replace(/\s+/g, '').toUpperCase();
    tscNumber.value = value;

    if (!value) {
      showError(tscNumber, 'TSC number is required.');
      return false;
    }
    if (!/^TSC\d{7}$/.test(value)) {
      showError(tscNumber, 'Invalid TSC number format.');
      return false;
    }

    clearError(tscNumber);
    return true;
  }

  function validateSchoolCode() {
    if (!schoolCode) {
      return true;
    }

    var value = (schoolCode.value || '').replace(/\s+/g, '');
    schoolCode.value = value;

    if (!value) {
      showError(schoolCode, 'School code is required.');
      return false;
    }
    if (!/^\d{8}$/.test(value)) {
      showError(schoolCode, 'School code must contain exactly 8 digits.');
      return false;
    }

    clearError(schoolCode);
    return true;
  }

  function validateSchoolName() {
    if (!schoolName) {
      return true;
    }

    var value = capitalizeWords(schoolName.value).slice(0, 100);
    schoolName.value = value;

    if (!value) {
      showError(schoolName, 'School name is required.');
      return false;
    }
    if (value.length < 3) {
      showError(schoolName, 'School name is required.');
      return false;
    }

    clearError(schoolName);
    return true;
  }

  function ensureSchoolRoleDropdown() {
    if (!schoolPosition || schoolPosition.tagName === 'SELECT') {
      return schoolPosition;
    }

    var select = document.createElement('select');
    select.id = schoolPosition.id;
    select.name = schoolPosition.name;
    select.className = 'field-select';

    schoolRoleOptions.forEach(function (item) {
      var option = document.createElement('option');
      option.value = item.value;
      option.textContent = item.label;
      option.selected = (schoolPosition.value || '') === item.value;
      select.appendChild(option);
    });

    schoolPosition.replaceWith(select);
    schoolPosition = select;
    return schoolPosition;
  }

  function validateSchoolRole() {
    var field = ensureSchoolRoleDropdown();
    if (!field) {
      return true;
    }

    if (!field.value) {
      showError(field, 'Please select your role at the school.');
      return false;
    }

    clearError(field);
    return true;
  }

  function validateYearsOfService(field) {
    if (!field) {
      return true;
    }

    var value = (field.value || '').replace(/\s+/g, '');
    field.value = value;

    if (!value) {
      showError(field, 'Enter years of service.');
      return false;
    }
    if (!/^\d+$/.test(value)) {
      showError(field, 'Years of service must be between 0 and 50.');
      return false;
    }

    var years = Number(value);
    if (years < 0 || years > 50) {
      showError(field, 'Years of service must be between 0 and 50.');
      return false;
    }

    clearError(field);
    return true;
  }

  function validateInstitution() {
    if (!cashierInstitutionName) {
      return true;
    }

    var value = capitalizeWords(cashierInstitutionName.value);
    cashierInstitutionName.value = value;

    if (!value || value.length < 3) {
      showError(cashierInstitutionName, 'Institution name is required.');
      return false;
    }

    clearError(cashierInstitutionName);
    return true;
  }

  function validateWorkstationNumber() {
    if (!cashierWorkstationNumber) {
      return true;
    }

    var value = (cashierWorkstationNumber.value || '').replace(/\s+/g, '').toUpperCase();
    cashierWorkstationNumber.value = value;

    if (!value) {
      showError(cashierWorkstationNumber, 'Workstation number is required.');
      return false;
    }
    if (!/^WS-\d{5}$/.test(value)) {
      showError(cashierWorkstationNumber, 'Format must be WS-00001.');
      return false;
    }

    clearError(cashierWorkstationNumber);
    return true;
  }

  function validateEmployeeNumber() {
    if (!cashierEmployeeNumber) {
      return true;
    }

    var value = (cashierEmployeeNumber.value || '').replace(/\s+/g, '').toUpperCase();
    cashierEmployeeNumber.value = value;

    if (!value) {
      showError(cashierEmployeeNumber, 'Employee number is required.');
      return false;
    }
    if (!/^EMP\d{5}$/.test(value)) {
      showError(cashierEmployeeNumber, 'Format must be EMP00001.');
      return false;
    }

    clearError(cashierEmployeeNumber);
    return true;
  }

  function updateRoleSections() {
    var role = roleSelect.value || 'customer_donor';
    var showCashier = role === 'cashier';
    var showSchool = role === 'school_representative';

    setSectionVisible(cashierFields, showCashier);
    setSectionVisible(schoolFields, showSchool);

    if (!showCashier) {
      clearHiddenGroup(cashierRoleFields);
    }
    if (!showSchool) {
      clearHiddenGroup(schoolRoleFields);
    }
  }

  function validateRoleSpecificFields() {
    var role = roleSelect.value || 'customer_donor';

    if (role === 'cashier') {
      var cashierOk = true;
      cashierOk = validateNationalId(cashierNationalId) && cashierOk;
      cashierOk = validateInstitution() && cashierOk;
      cashierOk = validateWorkstationNumber() && cashierOk;
      cashierOk = validateEmployeeNumber() && cashierOk;
      cashierOk = validateYearsOfService(cashierYearsOfService) && cashierOk;
      return cashierOk;
    }

    if (role === 'school_representative') {
      var schoolOk = true;
      schoolOk = validateNationalId(schoolNationalId) && schoolOk;
      schoolOk = validateTscNumber() && schoolOk;
      schoolOk = validateSchoolCode() && schoolOk;
      schoolOk = validateSchoolName() && schoolOk;
      schoolOk = validateSchoolRole() && schoolOk;
      schoolOk = validateYearsOfService(schoolYearsOfService) && schoolOk;
      return schoolOk;
    }

    return true;
  }

  function validateAll() {
    updateRoleSections();

    var ok = true;
    ok = validateFullName() && ok;
    ok = validateEmail() && ok;
    ok = validatePhone() && ok;
    ok = validatePassword() && ok;
    ok = validateConfirmPassword() && ok;
    ok = validateRoleSpecificFields() && ok;

    submit.disabled = !ok;
    return ok;
  }

  baseFields.concat(cashierRoleFields).concat(schoolRoleFields).forEach(function (field) {
    ensureErrorElement(field);
    field.addEventListener('input', validateAll);
    field.addEventListener('change', validateAll);
  });

  [cashierNationalId, schoolNationalId, schoolCode, schoolYearsOfService, cashierYearsOfService]
    .filter(Boolean)
    .forEach(attachNumericGuard);

  attachPhoneGuard();

  form.querySelectorAll('.toggle-password').forEach(function (button) {
    button.addEventListener('click', function () {
      var targetId = button.getAttribute('data-target');
      var target = document.getElementById(targetId);
      if (!target) {
        return;
      }
      var isPassword = target.getAttribute('type') === 'password';
      target.setAttribute('type', isPassword ? 'text' : 'password');
      button.textContent = isPassword ? 'Hide' : 'Show';
    });
  });

  form.setAttribute('novalidate', 'novalidate');
  form.addEventListener('submit', function (event) {
    if (!validateAll()) {
      event.preventDefault();
    }
  });

  validateAll();
})();
