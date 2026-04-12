
// Set date picker constraint to current moment preventing legacy UX confusions explicitly on load universally
document.getElementById('date_picker').valueAsDate = new Date();

// ----------------------------------------------------
// Chart.JS Integrations explicitly formatting Python Dictionary items payload via TO_JSON safe serialization templating explicitly bound to Window constraints universally
// ----------------------------------------------------
// Retrieve pure python dictionaries natively into Javascript arrays using safe JSON parsers universally mapped properly converting single quotes automatically utilizing |tojson universally
const categoryDataRaw = Object.entries({{ category_summary | tojson }});
const monthlyDataRaw = Object.entries({{ monthly_summary | tojson }});

// Initialize empty arrays explicitly to hold ChartJS consumable formatted labels mapping strictly
const catLabels = [];
const catValues = [];
categoryDataRaw.forEach(([cat, val]) => { catLabels.push(cat); catValues.push(val); });

const monthLabels = [];
const monthValues = [];
// Optional quick string split ordering temporal series alphabetically reliably universally ensuring proper sequence regardless of random dict hash ordering intrinsically utilizing Javascript sort mechanisms efficiently
monthlyDataRaw.sort().forEach(([month, val]) => { monthLabels.push(month); monthValues.push(val); });

// ChartJS global aesthetics ensuring matching dark modes implicitly rendering universally
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'DM Sans', sans-serif";

// Generate pie charting instances explicitly configuring options formatting datasets colors mapping nicely onto layout universally
const pieCtx = document.getElementById('pieChart').getContext('2d');
new Chart(pieCtx, {
    type: 'doughnut',
    data: {
        labels: catLabels,
        datasets: [{
            data: catValues,
            backgroundColor: [
                '#3b82f6', '#06b6d4', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444'
            ],
            borderWidth: 0,
            hoverOffset: 4
        }]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right' } } }
});

// Generate bar charting tracking month distributions strictly utilizing gradient simulated aesthetics mapped smoothly
const barCtx = document.getElementById('barChart').getContext('2d');
new Chart(barCtx, {
    type: 'bar',
    data: {
        // Slicing to get only up to last 6 months for a tight comparison chart
        labels: monthLabels.slice(-6),
        datasets: [{
            label: 'Spent (₹)',
            data: monthValues.slice(-6),
            backgroundColor: '#06b6d4',
            borderRadius: 4
        }]
    },
    options: { responsive: true, maintainAspectRatio: false }
});

// Generate line charting tracking daily spends in current month
const dailyDataRaw = Object.entries({{ daily_summary | tojson }});
// Sort by day properly representing timeline
dailyDataRaw.sort((a, b) => parseInt(a[0]) - parseInt(b[0]));
const dayLabels = [];
const dayValues = [];
dailyDataRaw.forEach(([day, val]) => { dayLabels.push(day); dayValues.push(val); });

const lineCtx = document.getElementById('lineChart').getContext('2d');
new Chart(lineCtx, {
    type: 'line',
    data: {
        labels: dayLabels,
        datasets: [{
            label: 'Daily Spend (₹)',
            data: dayValues,
            borderColor: '#8b5cf6', // Indigo-purple line accent
            backgroundColor: 'rgba(139, 92, 246, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4
        }]
    },
    options: { responsive: true, maintainAspectRatio: false }
});


// ----------------------------------------------------
// Category Progress Bars simulated logic
// ----------------------------------------------------
// Predefined budget targets per category to satisfy exact prompt requirement mapping effectively visualizing progress cleanly natively exclusively inside Javascript limits efficiently mapping loop dynamically 
// Predefined budget targets per category passed from backend
const categoryBudgets = {{ category_budgets | tojson }};
const progressContainer = document.getElementById('category-progress-container');

categoryDataRaw.forEach(([cat, spent]) => {
    // Retrieve predefined limit matching explicitly
    let limit = categoryBudgets[cat] || 1000;
    // Percentage capped explicitly failing over mapping 100 perfectly
    let rawPct = (spent / limit) * 100;
    let percent = Math.min(rawPct, 100).toFixed(1);

    // Bar coloring threshold mapping smoothly universally determining intensity intuitively
    // Green = under 50%, Yellow = 50% to 80%, Red = over 80% (Per the prompt requirement)
    let barColor = 'var(--success)';
    if (rawPct > 80) barColor = 'var(--danger)';
    else if (rawPct >= 50) barColor = 'var(--warning)';

    // DOM string injections building HTML mapping arrays directly creating div groups dynamically cleanly explicitly 
    let htmlStr = `
                <div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.9rem; margin-bottom: 0.25rem;">
                        <span>${cat}</span>
                        <span>₹${Math.floor(spent)} / ₹${limit} (${percent}%)</span>
                    </div>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: 0%; background-color: ${barColor};" data-target="${percent}"></div>
                    </div>
                </div>
            `;
    // Append mapped structures seamlessly iteratively
    progressContainer.innerHTML += htmlStr;
});

// Trigger animation strictly after initial layout rendering causing sliding visual cue explicitly using timeout micro-task queuing reliably
setTimeout(() => {
    document.querySelectorAll('.progress-bar').forEach(bar => {
        bar.style.width = bar.getAttribute('data-target') + '%';
    });
}, 300);

// ----------------------------------------------------
// Amount Color Coding execution parsing DOM arrays mapping threshold conditionally mapping dynamically universally looping rows effectively 
// ----------------------------------------------------
// Define intensity constraint maps utilizing classes injected immediately dynamically rendering mapping effectively inherently 
document.querySelectorAll('.amount-cell').forEach(cell => {
    let amount = parseFloat(cell.getAttribute('data-amount'));
    if (amount > 1000) cell.classList.add('val-high');
    else if (amount > 300) cell.classList.add('val-med');
    else cell.classList.add('val-low');
});

// ----------------------------------------------------
// Table Filtering & Search logic 
// ----------------------------------------------------
// Bound to HTML keyups and onChange directly mitigating mapping overhead cleanly explicitly isolating specific rows intuitively manipulating display constraints uniquely 
function filterTable() {
    let searchQ = document.getElementById('searchInput').value.toLowerCase();
    let catFilter = document.getElementById('categoryFilter').value;
    let rows = document.querySelectorAll('tbody tr:not(#emptyRow)');

    rows.forEach(row => {
        // Ignore empty-state row logic
        if (!row.cells[1]) return;

        let name = row.querySelector('.searchName').innerText.toLowerCase();
        let notes = row.querySelector('.searchNotes').innerText.toLowerCase();
        let category = row.cells[2].getAttribute('data-category');

        let matchesSearch = name.includes(searchQ) || notes.includes(searchQ);
        let matchesCat = (catFilter === "All" || category === catFilter);

        if (matchesSearch && matchesCat) {
            row.classList.remove('hidden-row');
        } else {
            row.classList.add('hidden-row');
        }
    });
}

// ----------------------------------------------------
// Table Sorting Logic isolating arrays sorting explicit elements appending dom trees strictly
// ----------------------------------------------------
function sortTable() {
    let sortType = document.getElementById('sortSelect').value;
    let tbody = document.querySelector('tbody');
    let rows = Array.from(tbody.querySelectorAll('tr:not(#emptyRow)'));

    // Map row parsing strings to datatypes reliably capturing mapped values explicitly
    rows.sort((a, b) => {
        if (sortType.includes('amount')) {
            let aVal = parseFloat(a.querySelector('.amount-cell').getAttribute('data-amount'));
            let bVal = parseFloat(b.querySelector('.amount-cell').getAttribute('data-amount'));
            return sortType === 'amount-asc' ? aVal - bVal : bVal - aVal;
        } else {
            let aVal = new Date(a.cells[0].innerText).getTime();
            let bVal = new Date(b.cells[0].innerText).getTime();
            return sortType === 'date-asc' ? aVal - bVal : bVal - aVal;
        }
    });

    // Re-append universally ensuring DOM updates correctly ordering elements completely mapping seamlessly 
    rows.forEach(row => tbody.appendChild(row));
}

// Execute default sort layout descending temporal series explicitly instantly organizing inputs natively universally generating seamless views initially explicitly 
sortTable();

// ----------------------------------------------------
// Theme Toggle utilizing native variable swapping maps directly affecting global roots cleanly mapping effectively generating persistence optionally mapping cookies optionally later explicitly explicitly 
// ----------------------------------------------------
function toggleTheme() {
    const body = document.body;
    const btn = document.getElementById('themeBtn');
    if (body.classList.contains('light-theme')) {
        body.classList.remove('light-theme');
        btn.innerText = "☀️ Light Mode";
        localStorage.setItem('theme', 'dark'); // Save user preference explicitly
    } else {
        body.classList.add('light-theme');
        btn.innerText = "🌙 Dark Mode";
        localStorage.setItem('theme', 'light'); // Save user preference explicitly
    }
}

// Apply saved theme sequence directly on pageload avoiding flashes
if (localStorage.getItem('theme') === 'light') {
    document.body.classList.add('light-theme');
    document.getElementById('themeBtn').innerText = "🌙 Dark Mode";
}

// Loader visual hook mitigating submit jitter universally ensuring seamless submit maps visibly providing feedback explicitly 
function showLoader() {
    document.getElementById('add_loader').style.display = 'block';
}
