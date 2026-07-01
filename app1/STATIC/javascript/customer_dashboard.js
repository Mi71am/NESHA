(function () {
  var mealInput = document.getElementById("mealAmountInput");
  var addDonationCheck = document.getElementById("addDonationCheck");
  var donationControls = document.getElementById("donationControls");
  var donationButtons = Array.prototype.slice.call(document.querySelectorAll(".donation-chip"));

  var donationAmountBox = document.getElementById("donationAmountBox");
  var mealAmountBox = document.getElementById("mealAmountBox");
  var totalAmountBox = document.getElementById("totalAmountBox");
  var proceedBtn = document.getElementById("proceedDashboardBtn");

  if (!mealInput || !addDonationCheck || !donationControls || !donationAmountBox || !mealAmountBox || !totalAmountBox) {
    return;
  }

  var donationAmount = 0;
  var MAX_PAYMENT_AMOUNT = 1000000;
  var currentMealAmount = 0;
  var currentTotalAmount = 0;

  function getDigitsOnly(value) {
    return String(value || "").replace(/\D+/g, "");
  }

  function formatAmount(value) {
    if (!value || value <= 0) {
      return "-";
    }
    return "Ksh " + Number(value).toLocaleString();
  }

  function updateSummary() {
    var mealValue = Number(mealInput.value);
    if (Number.isNaN(mealValue) || mealValue < 0) {
      mealValue = 0;
    }
    if (mealValue > MAX_PAYMENT_AMOUNT) {
      mealValue = MAX_PAYMENT_AMOUNT;
      mealInput.value = String(MAX_PAYMENT_AMOUNT);
    }

    var total = mealValue + donationAmount;
    if (total > MAX_PAYMENT_AMOUNT) {
      mealValue = Math.max(0, MAX_PAYMENT_AMOUNT - donationAmount);
      mealInput.value = String(mealValue);
      total = mealValue + donationAmount;
    }
    currentMealAmount = mealValue;
    currentTotalAmount = total;

    donationAmountBox.textContent = formatAmount(donationAmount);
    mealAmountBox.textContent = formatAmount(mealValue);
    totalAmountBox.textContent = formatAmount(total);
  }

  function updateDonationState() {
    var enabled = addDonationCheck.checked;
    donationControls.hidden = !enabled;

    if (!enabled) {
      donationAmount = 0;
      donationButtons.forEach(function (button) {
        button.classList.remove("is-selected");
        button.disabled = true;
      });
    } else {
      donationButtons.forEach(function (button) {
        button.disabled = false;
      });
    }

    updateSummary();
  }

  donationButtons.forEach(function (button) {
    button.disabled = true;
    button.addEventListener("click", function () {
      var value = Number(button.getAttribute("data-donation"));
      if (Number.isNaN(value)) {
        return;
      }

      if (donationAmount === value) {
        donationAmount = 0;
        button.classList.remove("is-selected");
      } else {
        donationAmount = value;
        donationButtons.forEach(function (btn) {
          btn.classList.remove("is-selected");
        });
        button.classList.add("is-selected");
      }

      updateSummary();
    });
  });

  mealInput.addEventListener("input", function () {
    mealInput.value = getDigitsOnly(mealInput.value);
    updateSummary();
  });

  addDonationCheck.addEventListener("change", updateDonationState);

  if (proceedBtn) {
    proceedBtn.addEventListener("click", function () {
      if (currentTotalAmount <= 0) {
        return;
      }

      if (currentTotalAmount > MAX_PAYMENT_AMOUNT) {
        window.alert("Maximum allowed payment is Ksh 1,000,000.");
        return;
      }

      var config = window.dashboardPaymentConfig || {};
      var paymentsUrl = config.paymentsUrl || "/payments/";
      var query =
        "?source=dashboard" +
        "&amount=" + encodeURIComponent(String(currentTotalAmount)) +
        "&meal_amount=" + encodeURIComponent(String(currentMealAmount)) +
        "&donation_amount=" + encodeURIComponent(String(donationAmount));

      window.location.href = paymentsUrl + query;
    });
  }

  updateDonationState();
})();
