(function () {
  var packageButtons = Array.prototype.slice.call(document.querySelectorAll('.package-btn'));
  var customInput = document.getElementById('customAmountInput');
  var proceedBtn = document.getElementById('proceedDonationBtn');
  var packageSelectedMsg = document.getElementById('packageSelectedMsg');

  if (!customInput || !proceedBtn) {
    return;
  }

  var selectedAmount = 0;
  var MAX_PAYMENT_AMOUNT = 1000000;
  var selectedPackage = '';
  var config = window.donationConfig || {};
  var paymentsUrl = config.paymentsUrl || '/payments/';

  function getDigitsOnly(value) {
    return String(value || '').replace(/\D+/g, '');
  }

  function updatePackageMessage(label) {
    if (!packageSelectedMsg) {
      return;
    }
    var normalized = String(label || '').trim().toUpperCase();
    if (!normalized || normalized === 'CUSTOM CONTRIBUTION') {
      packageSelectedMsg.hidden = true;
      packageSelectedMsg.textContent = '';
      return;
    }
    packageSelectedMsg.hidden = false;
    packageSelectedMsg.textContent = 'PACKAGE ' + normalized + ' SELECTED';
  }

  function selectPackage(button) {
    packageButtons.forEach(function (btn) {
      btn.classList.remove('is-selected');
    });
    button.classList.add('is-selected');
    selectedAmount = Number(button.getAttribute('data-amount')) || 0;
    selectedPackage = String(button.getAttribute('data-package') || '').trim().toUpperCase();
    customInput.value = '';
    updatePackageMessage(selectedPackage);
  }

  packageButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      selectPackage(button);
    });
  });

  customInput.addEventListener('input', function () {
    var digits = getDigitsOnly(customInput.value);
    if (digits) {
      var numeric = Math.min(Number(digits), MAX_PAYMENT_AMOUNT);
      customInput.value = String(numeric);
      digits = customInput.value;
    } else {
      customInput.value = '';
    }

    if (digits) {
      packageButtons.forEach(function (btn) {
        btn.classList.remove('is-selected');
      });
      selectedAmount = Number(digits) || 0;
      selectedPackage = 'CUSTOM CONTRIBUTION';
      updatePackageMessage(selectedPackage);
    } else {
      selectedAmount = 0;
      selectedPackage = '';
      updatePackageMessage(selectedPackage);
    }
  });

  proceedBtn.addEventListener('click', function () {
    var amount = selectedAmount;
    if (!amount || amount <= 0) {
      customInput.value = getDigitsOnly(customInput.value);
      amount = Number(customInput.value) || 0;
    }
    if (!amount || amount <= 0) {
      return;
    }

    if (amount > MAX_PAYMENT_AMOUNT) {
      window.alert('Maximum allowed payment is Ksh 1,000,000.');
      return;
    }

    if (!selectedPackage) {
      selectedPackage = 'CUSTOM CONTRIBUTION';
    }

    var query =
      '?source=donation' +
      '&amount=' + encodeURIComponent(String(amount)) +
      '&package=' + encodeURIComponent(selectedPackage);

    window.location.href = paymentsUrl + query;
  });

})();
