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

  function buildDataset(dataset, index, chartType) {
    const palette = [
      "#4f7df3",
      "#3fa9dc",
      "#8b6be8",
      "#47c19a",
      "#f0ad3d",
      "#ec6b64",
      "#6d7ae0",
      "#d962a0",
      "#57c26f",
      "#9a6be8",
      "#4d7fe6",
      "#36a8d9"
    ];

    const values = Array.isArray(dataset.data) ? dataset.data : [];

    if (chartType === "bar") {
      return {
        label: dataset.label,
        data: values,
        backgroundColor: values.map((_, i) => palette[i % palette.length] + "cc"),
        borderColor: values.map((_, i) => palette[i % palette.length]),
        borderWidth: 1,
        borderRadius: {
          topLeft: 10,
          topRight: 10,
          bottomLeft: 0,
          bottomRight: 0
        },
        borderSkipped: false,
        categoryPercentage: 0.72,
        barPercentage: 0.9,
        maxBarThickness: 42
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

  function getChartOptions(chartType, stacked, datasetCount, labelCount) {
    const cartesian = !["pie", "doughnut"].includes(chartType);

    if (chartType === "bar") {
      return {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 650,
          easing: "easeOutQuart"
        },
        plugins: {
          legend: {
            display: datasetCount > 1,
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
            },
            ticks: {
              autoSkip: labelCount > 10,
              maxRotation: 35,
              minRotation: 35,
              color: "#64748b"
            }
          },
          y: {
            stacked: stacked,
            beginAtZero: true,
            grid: {
              color: "rgba(148, 163, 184, 0.22)"
            },
            ticks: {
              precision: 0,
              color: "#64748b"
            }
          }
        }
      };
    }

    if (!cartesian) {
      return {
        responsive: true,
        maintainAspectRatio: false,
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
          },
          ticks: {
            color: "#64748b"
          }
        },
        y: {
          stacked: stacked,
          beginAtZero: true,
          grid: {
            color: "rgba(148, 163, 184, 0.18)"
          },
          ticks: {
            precision: 0,
            color: "#64748b"
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
      const built = buildDataset(dataset, index, normalizedType);

      if (chartType === "area") {
        built.fill = true;
      }

      if (["pie", "doughnut"].includes(normalizedType)) {
        const palette = [
          "#4f7df3",
          "#3fa9dc",
          "#8b6be8",
          "#47c19a",
          "#f0ad3d",
          "#ec6b64",
          "#6d7ae0",
          "#d962a0",
          "#57c26f",
          "#9a6be8",
          "#4d7fe6",
          "#36a8d9"
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
      options: getChartOptions(
        normalizedType,
        stacked,
        normalizedDatasets.length,
        labels.length
      )
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
