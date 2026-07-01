(() => {
  const labelsEl = document.getElementById("cashier-weekly-labels");
  const valuesEl = document.getElementById("cashier-weekly-values");
  const canvas = document.getElementById("cashierWeeklyChart");

  if (!labelsEl || !valuesEl || !canvas || typeof Chart === "undefined") {
    return;
  }

  const labels = JSON.parse(labelsEl.textContent || "[]");
  const values = JSON.parse(valuesEl.textContent || "[]");

  new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Meal Payments (KES)",
          data: values,
          borderColor: "#6b8f72",
          backgroundColor: "rgba(107, 143, 114, 0.12)",
          fill: true,
          tension: 0.28,
          pointRadius: 3,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: true } },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback(value) {
              return `Ksh ${value}`;
            },
          },
        },
      },
    },
  });
})();
