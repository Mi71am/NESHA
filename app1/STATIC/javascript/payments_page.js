(function () {
  var confirmBtn = document.getElementById("confirmPaymentBtn");
  var phoneInput = document.getElementById("phoneNumberInput");
  var processingToast = document.getElementById("processingToast");
  var successBanner = document.getElementById("paymentSuccessBanner");
  var receiptCard = document.getElementById("receiptCard");
  var receiptNumberValue = document.getElementById("receiptNumberValue");
  var receiptAmountValue = document.getElementById("receiptAmountValue");
  var receiptDonationValue = document.getElementById("receiptDonationValue");
  var receiptMealValue = document.getElementById("receiptMealValue");

  if (!confirmBtn || !phoneInput) {
    return;
  }

  var config = window.paymentConfig || {};

  function getDigitsOnly(value) {
    return String(value || "").replace(/\D+/g, "");
  }

  function isValidPhoneNumber(value) {
    return /^0\d{9}$/.test(String(value || ""));
  }

  function getCookie(name) {
    var cookies = document.cookie ? document.cookie.split(";") : [];
    for (var i = 0; i < cookies.length; i += 1) {
      var cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === name + "=") {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return "";
  }

  function showProcessingToast() {
    if (processingToast) {
      processingToast.hidden = false;
    }
  }

  function hideProcessingToast() {
    if (processingToast) {
      processingToast.hidden = true;
    }
  }

  function delay(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  phoneInput.addEventListener("input", function () {
    phoneInput.value = getDigitsOnly(phoneInput.value).slice(0, 10);
  });

  confirmBtn.addEventListener("click", function () {
    phoneInput.value = getDigitsOnly(phoneInput.value);

    if (!isValidPhoneNumber(phoneInput.value)) {
      window.alert("Enter a valid phone number in this format: 07XXXXXXXX");
      return;
    }

    confirmBtn.disabled = true;
    showProcessingToast();

    var payload = {
      source: config.source || "donation",
      amount: config.amount || "0",
      meal_amount: config.mealAmount || "0",
      donation_amount: config.donationAmount || "0",
      package_name: config.packageName || "",
      phone_number: phoneInput.value,
    };

    var requestPromise = fetch(config.confirmUrl || "/payments/confirm/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
      body: JSON.stringify(payload),
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok || !data.ok) {
          throw new Error((data && data.message) || "Payment failed.");
        }
        return data;
      });
    });

    Promise.all([requestPromise, delay(5000)])
      .then(function (results) {
        var data = results[0];
        hideProcessingToast();

        if (successBanner) {
          successBanner.hidden = false;
          successBanner.textContent = data.message || "Payment received.";
        }

        if (receiptCard && receiptNumberValue && receiptAmountValue && receiptDonationValue && receiptMealValue) {
          receiptCard.hidden = false;
          receiptNumberValue.textContent = String(data.receipt_number || "-");
          receiptAmountValue.textContent = "Ksh. " + String(data.amount || payload.amount || "0");
          receiptDonationValue.textContent = "Ksh. " + String(data.donation_amount || payload.donation_amount || "0");
          receiptMealValue.textContent = "Ksh. " + String(data.meal_amount || payload.meal_amount || "0");
        }
      })
      .catch(function (error) {
        hideProcessingToast();
        window.alert(error.message || "Unable to process payment.");
      })
      .finally(function () {
        confirmBtn.disabled = false;
      });
  });
})();
