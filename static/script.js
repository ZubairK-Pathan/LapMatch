document.getElementById('search-btn').addEventListener('click', executeSearch);
document.getElementById('prompt-input').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        executeSearch();
    }
});

async function executeSearch() {
    const prompt = document.getElementById('prompt-input').value.trim();
    if (!prompt) return;


    document.getElementById('loader').classList.remove('hidden');
    document.getElementById('cards-grid').classList.add('hidden');
    document.getElementById('dev-data').classList.add('hidden');
    document.getElementById('cards-grid').innerHTML = ''; // Clear previous

    try {
        const response = await fetch('/api/recommend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt })
        });

        const data = await response.json();
        
        document.getElementById('loader').classList.add('hidden');
        
        if (data.error) {
            alert(data.error);
            return;
        }

        renderCards(data.results);
        renderDevData(data);
    } catch (error) {
        document.getElementById('loader').classList.add('hidden');
        alert("Server error. Ensure backend is running.");
        console.error(error);
    }
}

function renderCards(laptops) {
    const grid = document.getElementById('cards-grid');
    grid.classList.remove('hidden');

    laptops.forEach((laptop, index) => {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.animationDelay = `${index * 0.15}s`;

        const matchPct = (laptop.match_score * 100).toFixed(1);
        
        // Format price to Indian Rupee
        const priceFmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(laptop.price);

        card.innerHTML = `
            <div class="card-header">
                <span class="rank">#${index + 1} MATCH</span>
            </div>
            <img class="card-img" src="${laptop.image_url}" alt="${laptop.name}" onerror="this.src='https://via.placeholder.com/400x250/111827/3b82f6?text=Image+Unavailable'" />
            <h3>${laptop.name}</h3>
            <div class="metrics">
                <div class="metric">
                    <span class="metric-label">Price</span>
                    <span class="metric-value">${priceFmt}</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Suitability</span>
                    <span class="metric-value">${matchPct}%</span>
                </div>
            </div>
            <div class="pitch">
                ${laptop.pitch}
            </div>
        `;
        grid.appendChild(card);
    });
}

function renderDevData(data) {
    const devBox = document.getElementById('dev-data');
    const isDevMode = document.getElementById('dev-mode-cb').checked;
    
    if (isDevMode && data.calculations) {
        let statsStr = "";
        data.results.forEach((r, i) => {
            statsStr += `[#${i+1} Match: ${r.name}]\n↳ TOPSIS Distance Score: ${(r.match_score * 100).toFixed(2)}%\n↳ Raw Dimensions: [Weight Proxy: ${r.weight}, Battery Proxy: ${r.battery}]\n\n`;
        });
        
        devBox.innerHTML = `
            <h4> Edge AI Intent Extraction:</h4>
            <code>${JSON.stringify(data.calculations.extracted_intent, null, 2)}</code>
            <hr style="border:0; border-top:1px solid rgba(255,255,255,0.1); margin: 1rem 0;">
            <h4>🧮 Mathematical TOPSIS Vectors:</h4>
            <pre style="margin:0; font-family:inherit;">${statsStr}</pre>
        `;
        devBox.classList.remove('hidden');
    }
}
