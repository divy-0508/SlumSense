console.log("🔥 JS LOADED");

document.addEventListener("DOMContentLoaded", () => {
    console.log("🔥 DOM READY");

    const citySelect = document.getElementById("citySelect");
    const categorySelect = document.getElementById("categorySelect");
    const cardsDiv = document.getElementById("metricCards");

    const chartDiv1 = document.getElementById("mainChart"); // Dynamic metric chart
    const chartDiv2 = document.getElementById("chart2");    // Complaints trend
    const chartDiv3 = document.getElementById("chart3");    // Comparison chart

    if (!citySelect || !categorySelect || !cardsDiv || !chartDiv1 || !chartDiv2 || !chartDiv3) {
        console.warn("Analytics elements not found. Dashboard script skipped.");
        return;
    }

    const chart1 = echarts.init(chartDiv1);
    const chart2 = echarts.init(chartDiv2);
    const chart3 = echarts.init(chartDiv3);

    // Generic line chart draw function
    function drawChart(chart, metric, dates) {
        chart.setOption({
            title: {
                text: metric.title,
                left: 'center',
                textStyle: { color: '#333', fontSize: 16 }
            },
            tooltip: { trigger: 'axis' },
            grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
            xAxis: {
                type: 'category',
                data: dates,
                axisLabel: { color: '#666' },
                boundaryGap: false,
                axisLine: { lineStyle: { color: '#ccc' } }
            },
            yAxis: {
                type: 'value',
                axisLabel: { color: '#666' },
                splitLine: { lineStyle: { color: '#eee' } }
            },
            series: [{
                data: metric.values,
                type: 'line',
                smooth: true,
                lineStyle: { width: 3, color: '#2a7c6f' },
                areaStyle: { color: 'rgba(42, 124, 111, 0.1)' },
                symbol: 'circle',
                symbolSize: 6
            }],
            backgroundColor: 'transparent'
        });
    }

    // Comparison chart (Supply vs Demand / Efficiency)
    function drawComparisonChart(dates, metricA, metricB, title) {
        chart3.setOption({
            title: {
                text: title,
                left: 'center',
                textStyle: { color: '#333', fontSize: 16 }
            },
            tooltip: { trigger: 'axis' },
            legend: {
                data: [metricA.title, metricB.title],
                textStyle: { color: '#666' },
                top: 30
            },
            grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
            xAxis: {
                type: 'category',
                data: dates,
                axisLabel: { color: '#666' },
                boundaryGap: false,
                axisLine: { lineStyle: { color: '#ccc' } }
            },
            yAxis: {
                type: 'value',
                axisLabel: { color: '#666' },
                splitLine: { lineStyle: { color: '#eee' } }
            },
            series: [
                {
                    name: metricA.title,
                    type: 'line',
                    smooth: true,
                    data: metricA.values,
                    lineStyle: { color: '#3498db', width: 3 },
                    areaStyle: { color: 'rgba(52, 12, 219, 0.1)' }
                },
                {
                    name: metricB.title,
                    type: 'line',
                    smooth: true,
                    data: metricB.values,
                    lineStyle: { color: '#e74c3c', width: 3 },
                    areaStyle: { color: 'rgba(231, 76, 60, 0.1)' }
                }
            ],
            backgroundColor: 'transparent'
        });
    }

    function drawComplaintsComparison(dates, totalMetric, solvedMetric) {
        chart2.setOption({
            title: {
                text: 'Total vs Solved Complaints',
                left: 'center',
                textStyle: { color: '#333', fontSize: 16 }
            },
            tooltip: { trigger: 'axis' },
            legend: {
                data: [totalMetric.title, solvedMetric.title],
                textStyle: { color: '#666' },
                top: 30
            },
            grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
            xAxis: {
                type: 'category',
                data: dates,
                axisLabel: { color: '#666' },
                boundaryGap: false,
                axisLine: { lineStyle: { color: '#ccc' } }
            },
            yAxis: {
                type: 'value',
                axisLabel: { color: '#666' },
                splitLine: { lineStyle: { color: '#eee' } }
            },
            series: [
                {
                    name: totalMetric.title,
                    type: 'line',
                    smooth: true,
                    data: totalMetric.values,
                    lineStyle: { color: '#f39c12', width: 3 },
                    areaStyle: { color: 'rgba(243, 156, 18, 0.1)' }
                },
                {
                    name: solvedMetric.title,
                    type: 'line',
                    smooth: true,
                    data: solvedMetric.values,
                    lineStyle: { color: '#2ecc71', width: 3 },
                    areaStyle: { color: 'rgba(46, 204, 113, 0.1)' }
                }
            ],
            backgroundColor: 'transparent'
        });
    }


    // Load data for selected city and category
    function load(city) {
        const category = categorySelect.value;
        if (!city) {
            console.log("No city selected");
            return;
        }
        console.log(`➡️ Fetching: ${city} (${category})`);

        fetch(`/get_analytics_data?city=${encodeURIComponent(city)}&category=${encodeURIComponent(category)}`)
            .then(r => {
                if (!r.ok) throw new Error("Network response was not ok");
                return r.json();
            })
            .then(data => {
                console.log("✅ DATA:", data);

                // Clear previous cards
                cardsDiv.innerHTML = "";

                // Create cards for all metrics
                Object.entries(data.metrics).forEach(([key, m]) => {
                    const d = document.createElement("div");
                    d.className = "card analytics-card";

                    // Format latest value
                    const latest = typeof m.latest === "number" ? m.latest.toFixed(2) : m.latest;
                    d.innerHTML = `<strong>${m.title}</strong><br><span style="font-size: 1.2rem;">${latest}</span>`;

                    // Click card to update dynamic chart
                    d.onclick = () => drawChart(chart1, m, data.dates);
                    cardsDiv.appendChild(d);
                });

                // Chart1: Primary metric
                if (data.primary_metric && data.metrics[data.primary_metric]) {
                    drawChart(chart1, data.metrics[data.primary_metric], data.dates);
                } else if (data.metrics.index) {
                    drawChart(chart1, data.metrics.index, data.dates);
                }

                // Chart2: Complaints trend
                if (data.metrics.total_complaints && data.metrics.solved_complaints) {
                    drawComplaintsComparison(
                        data.dates,
                        data.metrics.total_complaints,
                        data.metrics.solved_complaints
                    );
                }

                // Chart3: Comparison (Supply vs Demand or similar)
                if (data.comparison) {
                    const metricA = data.metrics[data.comparison.metricA];
                    const metricB = data.metrics[data.comparison.metricB];
                    if (metricA && metricB) {
                        drawComparisonChart(data.dates, metricA, metricB, data.comparison.title);
                    }
                }
                
                // Resize charts
                setTimeout(() => {
                    chart1.resize();
                    chart2.resize();
                    chart3.resize();
                }, 100);
            })
            .catch(e => {
                console.error("❌ FETCH ERROR", e);
                cardsDiv.innerHTML = `<p style="color: red;">Error loading data: ${e.message}</p>`;
            });
    }

    // Initial load
    if(citySelect.value) load(citySelect.value);

    // Reload when city or category changes
    citySelect.onchange = () => load(citySelect.value);
    categorySelect.onchange = () => load(citySelect.value);
    
    // Resize charts on window resize
    window.addEventListener('resize', () => {
        chart1.resize();
        chart2.resize();
        chart3.resize();
    });
});
