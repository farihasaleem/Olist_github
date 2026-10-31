
const API = "/api/analytics";
let charts = {};

async function fetchData(endpoint, filters = {}) {
    const params = new URLSearchParams();

    Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value);
    });

    const url = `${API}/${endpoint}?${params.toString()}`;
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }

    return await response.json();
}

function getFilters() {
    return {
        start_date: document.getElementById("startDate").value,
        end_date: document.getElementById("endDate").value,
        state: document.getElementById("state").value
    };
}

function formatCurrency(value) {
    return "R$ " + Number(value).toLocaleString("en-US", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function createChart(id, type, labels, datasets) {
    if (charts[id]) charts[id].destroy();

    const ctx = document.getElementById(id);

    charts[id] = new Chart(ctx, {
        type: type,
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: type !== "bar" && type !== "line"
                }
            }
        }
    });
}

async function loadDashboard() {
    const status = document.getElementById("status");
    status.textContent = "Loading dashboard...";

    const filters = getFilters();

    try {
        const [
            summary,
            revenue,
            categories,
            states,
            payments,
            reviews
        ] = await Promise.all([
            fetchData("summary", filters),
            fetchData("revenue-by-month", filters),
            fetchData("top-categories", filters),
            fetchData("orders-by-state", filters),
            fetchData("payment-types", filters),
            fetchData("review-vs-delivery", filters)
        ]);

        // KPI cards
        document.getElementById("revenue").textContent =
            formatCurrency(summary.total_revenue);

        document.getElementById("orders").textContent =
            Number(summary.total_orders).toLocaleString();

        document.getElementById("aov").textContent =
            formatCurrency(summary.avg_order_value);

        document.getElementById("review").textContent =
            Number(summary.avg_review_score).toFixed(2) + " / 5";

        document.getElementById("late").textContent =
            Number(summary.pct_late_deliveries).toFixed(2) + "%";

        // Revenue chart
        createChart("revenueChart", "line", revenue.labels, [{
            label: "Revenue",
            data: revenue.values,
            borderWidth: 2,
            tension: 0.3
        }]);

        // Categories chart
        createChart("categoryChart", "bar", categories.labels, [{
            label: "Revenue",
            data: categories.values
        }]);

        // State chart
        createChart("stateChart", "bar", states.labels, [{
            label: "Orders",
            data: states.values
        }]);

        // Payment chart
        createChart("paymentChart", "doughnut", payments.labels, [{
            label: "Payments",
            data: payments.values
        }]);

        // Review chart
        createChart("reviewChart", "bar", reviews.labels, [
            {
                label: "On time",
                data: reviews.distribution.on_time
            },
            {
                label: "Late",
                data: reviews.distribution.late
            }
        ]);

        status.textContent = "Dashboard updated successfully.";

    } catch (error) {
        console.error(error);
        status.textContent = "Unable to load dashboard. Check the API connection.";
    }
}

// Populate state filter
async function loadStates() {
    try {
        const data = await fetchData("orders-by-state");
        const select = document.getElementById("state");

        data.labels.forEach(state => {
            const option = document.createElement("option");
            option.value = state;
            option.textContent = state;
            select.appendChild(option);
        });
    } catch (error) {
        console.error("Unable to load states:", error);
    }
}

document.getElementById("applyFilters").addEventListener(
    "click", loadDashboard
);

document.getElementById("resetFilters").addEventListener("click", () => {
    document.getElementById("startDate").value = "";
    document.getElementById("endDate").value = "";
    document.getElementById("state").value = "";
    loadDashboard();
});

async function initializeDashboard() {
    await loadStates();
    await loadDashboard();
}

initializeDashboard();
