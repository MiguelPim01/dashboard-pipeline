(function () {
  "use strict";

  const CHART_SELECTOR = ".chart-canvas";

  function parseJSONAttribute(element, attributeName, fallback) {
    const raw = element.getAttribute(attributeName);
    if (!raw) return fallback;
    try {
      return JSON.parse(raw);
    } catch (error) {
      console.warn(`Failed to parse ${attributeName}`, error);
      return fallback;
    }
  }

  function readBooleanAttribute(element, attributeName, fallback) {
    const value = element.getAttribute(attributeName);
    if (value === null) return fallback;
    return String(value).toLowerCase() === "true";
  }

  function buildDataset(dataset, index, chartType, labels) {
    const palette = [
      "#2563eb",
      "#7c3aed",
      "#0891b2",
      "#16a34a",
      "#ea580c",
      "#dc2626",
      "#ca8a04",
      "#4f46e5",
      "#0f766e",
      "#9333ea",
      "#be123c",
      "#0369a1"
    ];

    const values = Array.isArray(dataset.data) ? dataset.data : [];

    // One color per bar
    if (chartType === "bar") {
      return {
        label: dataset.label,
        data: values,
        backgroundColor: values.map((_, i) => palette[i % palette.length] + "99"),
        borderColor: values.map((_, i) => palette[i % palette.length]),
        borderWidth: 1
      };
    }

    const color = palette[index % palette.length];

    return {
      label: dataset.label,
      data: values,
      borderColor: color,
      backgroundColor: color + "22",
      borderWidth: 2,
      pointRadius: 2,
      pointHoverRadius: 4,
      tension: 0.25,
      fill: false
    };
  }

  function getChartOptions(chartType, stacked) {
    const cartesian = !["pie", "doughnut"].includes(chartType);

    if (!cartesian) {
      return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false
        },
        plugins: {
          legend: {
            position: "top"
          },
          tooltip: {
            enabled: true
          }
        }
      };
    }

    return {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false
      },
      plugins: {
        legend: {
          position: "top"
        },
        tooltip: {
          enabled: true
        }
      },
      scales: {
        x: {
          stacked: stacked,
          grid: {
            display: false
          }
        },
        y: {
          stacked: stacked,
          beginAtZero: true,
          ticks: {
            precision: 0
          }
        }
      }
    };
  }

  function renderFallback(element, message) {
    const wrapper = element.parentElement;
    if (!wrapper) return;

    const fallback = document.createElement("div");
    fallback.className = "chart-empty-state";
    fallback.textContent = message;

    wrapper.innerHTML = "";
    wrapper.appendChild(fallback);
  }

  function initChart(canvas) {
    const chartType = canvas.getAttribute("data-chart-type") || "bar";
    const labels = parseJSONAttribute(canvas, "data-chart-labels", []);
    const datasets = parseJSONAttribute(canvas, "data-chart-datasets", []);
    const stacked = readBooleanAttribute(canvas, "data-chart-stacked", false);

    if (!Array.isArray(labels) || !Array.isArray(datasets) || datasets.length === 0) {
      renderFallback(canvas, "No chart data available for this widget.");
      return;
    }

    if (typeof window.Chart === "undefined") {
      renderFallback(
        canvas,
        "Chart.js was not loaded, so this chart could not be rendered."
      );
      return;
    }

    const normalizedType = chartType === "area" ? "line" : chartType;
    const normalizedDatasets = datasets.map((dataset, index) => {
      const built = buildDataset(dataset, index, normalizedType, labels);

      if (chartType === "area") {
        built.fill = true;
      }

      if (["pie", "doughnut"].includes(normalizedType)) {
        const palette = [
          "#2563eb",
          "#7c3aed",
          "#0891b2",
          "#16a34a",
          "#ea580c",
          "#dc2626",
          "#ca8a04",
          "#4f46e5",
          "#0f766e",
          "#9333ea",
          "#be123c",
          "#0369a1"
        ];
        built.backgroundColor = labels.map((_, i) => palette[i % palette.length]);
        built.borderColor = "#ffffff";
        built.borderWidth = 1;
      }

      return built;
    });

    const config = {
      type: normalizedType,
      data: {
        labels,
        datasets: normalizedDatasets
      },
      options: getChartOptions(normalizedType, stacked)
    };

    // eslint-disable-next-line no-new
    new window.Chart(canvas.getContext("2d"), config);
  }

  function initAllCharts() {
    const canvases = document.querySelectorAll(CHART_SELECTOR);
    canvases.forEach(initChart);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAllCharts);
  } else {
    initAllCharts();
  }
})();
