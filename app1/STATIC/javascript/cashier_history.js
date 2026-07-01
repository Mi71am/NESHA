(() => {
  const wLabelsEl = document.getElementById("cashier-history-weekly-labels");
  const wValuesEl = document.getElementById("cashier-history-weekly-values");
  const mLabelsEl = document.getElementById("cashier-history-monthly-labels");
  const mValuesEl = document.getElementById("cashier-history-monthly-values");

  if (typeof Chart === "undefined") {
    return;
  }

  const weeklyCanvas = document.getElementById("cashierHistoryWeeklyChart");
  if (weeklyCanvas && wLabelsEl && wValuesEl) {
    const labels = JSON.parse(wLabelsEl.textContent || "[]");
    const values = JSON.parse(wValuesEl.textContent || "[]");
    new Chart(weeklyCanvas, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "7-Day Meal Payments (KES)",
          data: values,
          borderColor: "#6b8f72",
          backgroundColor: "rgba(107, 143, 114, 0.12)",
          fill: true,
          tension: 0.25,
          pointRadius: 3,
        }],
      },
      options: { responsive: true, scales: { y: { beginAtZero: true } } },
    });
  }

  const monthlyCanvas = document.getElementById("cashierHistoryMonthlyChart");
  if (monthlyCanvas && mLabelsEl && mValuesEl) {
    const labels = JSON.parse(mLabelsEl.textContent || "[]");
    const values = JSON.parse(mValuesEl.textContent || "[]");
    new Chart(monthlyCanvas, {
      type: "bar",
      data: {
        labels,
        datasets: [{
          label: "6-Month Meal Totals (KES)",
          data: values,
          backgroundColor: "rgba(221, 190, 168, 0.7)",
          borderColor: "#8a6f5a",
          borderWidth: 1,
        }],
      },
      options: { responsive: true, scales: { y: { beginAtZero: true } } },
    });
  }
})();
