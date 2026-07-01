(function () {
  function parseJsonScript(id, fallback) {
    var el = document.getElementById(id);
    if (!el) {
      return fallback;
    }
    try {
      return JSON.parse(el.textContent);
    } catch (err) {
      return fallback;
    }
  }

  var weeklyLabels = parseJsonScript("weekly-labels-data", []);
  var weeklyValues = parseJsonScript("weekly-values-data", []);
  var trendLabels = parseJsonScript("trend-labels-data", []);
  var donationTrend = parseJsonScript("donation-trend-data", []);
  var mealTrend = parseJsonScript("meal-trend-data", []);

  var weeklyCanvas = document.getElementById("weeklyContributionChart");
  if (weeklyCanvas && window.Chart) {
    new Chart(weeklyCanvas, {
      type: "bar",
      data: {
        labels: weeklyLabels,
        datasets: [
          {
            label: "Donations",
            data: weeklyValues,
            backgroundColor: "#c7d4cc",
            borderColor: "#97a19b",
            borderWidth: 1,
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              color: "#5d5d5d",
              callback: function (value) { return "Ksh " + value; },
            },
            grid: { color: "rgba(63,48,41,0.12)" },
          },
          x: {
            ticks: { color: "#5d5d5d" },
            grid: { display: false },
          },
        },
        plugins: {
          legend: { display: false },
        },
      },
    });
  }

  var trendCanvas = document.getElementById("contributionTrendChart");
  if (trendCanvas && window.Chart) {
    new Chart(trendCanvas, {
      type: "line",
      data: {
        labels: trendLabels,
        datasets: [
          {
            label: "Donations",
            data: donationTrend,
            borderColor: "#97a19b",
            backgroundColor: "rgba(151, 161, 155, 0.12)",
            tension: 0.4,
            fill: false,
            pointRadius: 3,
          },
          {
            label: "Meal Amount",
            data: mealTrend,
            borderColor: "#ddbea8",
            backgroundColor: "rgba(221, 190, 168, 0.12)",
            tension: 0.4,
            fill: false,
            pointRadius: 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              color: "#5d5d5d",
              callback: function (value) { return "Ksh " + value; },
            },
            grid: { color: "rgba(63,48,41,0.12)" },
          },
          x: {
            ticks: { color: "#5d5d5d" },
            grid: { display: false },
          },
        },
        plugins: {
          legend: {
            labels: {
              color: "#5d5d5d",
              boxWidth: 16,
            },
          },
        },
      },
    });
  }

  var journeyFill = document.getElementById("journeyFill");
  var journeyBoat = document.getElementById("journeyBoat");
  var journeyTrack = document.getElementById("journeyTrack");
  var journeyPercentBadge = document.getElementById("journeyPercentBadge");
  var config = window.impactConfig || {};

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function updateJourney() {
    if (!journeyFill || !journeyBoat || !journeyTrack) {
      return;
    }
    var percent = clamp(Number(config.progressPercent) || 0, 0, 100);
    journeyFill.style.width = percent + "%";
    if (journeyPercentBadge) {
      journeyPercentBadge.textContent = percent + "%";
    }

    var trackWidth = journeyTrack.clientWidth;
    var boatWidth = journeyBoat.clientWidth || 78;
    var edgeX = (percent / 100) * trackWidth;
    var leftShift = trackWidth * 0.05;
    var minX = boatWidth * 0.45;
    var maxX = trackWidth - boatWidth * 0.1;
    var boatLeft = clamp(edgeX - leftShift, minX, maxX);
    journeyBoat.style.left = boatLeft + "px";
  }

  window.addEventListener("resize", updateJourney);
  updateJourney();
})();
