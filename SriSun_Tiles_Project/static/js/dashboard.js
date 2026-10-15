document.addEventListener('DOMContentLoaded', function () {
    const ctx = document.getElementById('stockChart');
    if (!ctx) return;

    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Godown 1', 'Godown 2', 'Godown 3'],
            datasets: [{
                label: 'Stock Quantity',
                data: [120, 96, 110],
                borderWidth: 1,
                backgroundColor: ['#0d6efd', '#198754', '#ffc107']
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
});
