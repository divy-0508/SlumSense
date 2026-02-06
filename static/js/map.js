let map;
let marker;
let heatLayer;

function initMap() {
    map = L.map('map').setView([23.8103, 90.4125], 12);

    const geoapifyUrl = `https://maps.geoapify.com/v1/tile/osm-bright/{z}/{x}/{y}.png?apiKey=${GEOAPIFY_API_KEY}`;
    
    L.tileLayer(geoapifyUrl, {
        attribution: 'Powered by <a href="https://www.geoapify.com/" target="_blank">Geoapify</a> | <a href="https://openmaptiles.org/" target="_blank">© OpenMapTiles</a> <a href="https://www.openstreetmap.org/copyright" target="_blank">© OpenStreetMap</a> contributors',
        maxZoom: 20, 
        id: 'osm-bright',
    }).addTo(map);

    map.on('click', onMapClick);

    document.getElementById("search-input").addEventListener("keypress", function(event) {
        if (event.key === "Enter") {
            performSearch();
        }
    });

    // Initialize Heatmap
    loadHeatmap();

    // Add Legend
    addLegend();

    console.log("Map initialized successfully");
}

async function loadHeatmap() {
    try {
        const response = await fetch('/get_heatmap_data');
        const points = await response.json();

        if (heatLayer) {
            map.removeLayer(heatLayer);
        }

        if (points && points.length > 0) {
            // Configuration for color gradient: Blue/Green (low) -> Yellow -> Red (high)
            heatLayer = L.heatLayer(points, {
                radius: 25,
                blur: 15,
                maxZoom: 14,
                gradient: {0.2: 'green', 0.5: 'yellow', 1.0: 'red'}
            }).addTo(map);
        }
    } catch (err) {
        console.error("Failed to load heatmap:", err);
    }
}

function addLegend() {
    const legend = L.control({position: 'bottomright'});
    legend.onAdd = function (map) {
        const div = L.DomUtil.create('div', 'legend');
        div.innerHTML += "<strong>Complaint Density</strong><br>";
        div.innerHTML += '<i style="background: green"></i> Low<br>';
        div.innerHTML += '<i style="background: yellow"></i> Moderate<br>';
        div.innerHTML += '<i style="background: red"></i> High<br>';
        return div;
    };
    legend.addTo(map);
}

async function onMapClick(e) {
    const { lat, lng } = e.latlng;
    updateMarkerAndPopup(lat, lng);
}

async function updateMarkerAndPopup(lat, lng) {
    if (marker) {
        marker.setLatLng([lat, lng]);
    } else {
        marker = L.marker([lat, lng]).addTo(map);
    }

    marker.bindPopup(`
        <div style="text-align:center;">
            <strong>Loading...</strong><br>
            Fetching environment & reports...
        </div>
    `).openPopup();

    try {
        const response = await fetch(`/get_env_data?lat=${lat}&lon=${lng}`);
        const data = await response.json();

        if (data.error) throw new Error(data.error);

        let aqiColor = "#cccccc";
        if (data.aqi <= 50) aqiColor = "#00e400";
        else if (data.aqi <= 100) aqiColor = "#ffff00";
        else if (data.aqi <= 150) aqiColor = "#ff7e00";
        else if (data.aqi <= 200) aqiColor = "#ff0000";
        else aqiColor = "#7e0023";

        let complaintsHtml = '';
        if (data.complaints && data.complaints.length > 0) {
            complaintsHtml = '<ul style="padding-left: 20px; margin: 5px 0; max-height: 100px; overflow-y: auto;">';
            data.complaints.forEach(c => {
                complaintsHtml += `<li><strong>${c.category}:</strong> ${c.description} <em style="font-size:0.8em">(${c.date})</em></li>`;
            });
            complaintsHtml += '</ul>';
        } else {
            complaintsHtml = '<p style="font-style:italic; margin: 5px 0;">No active complaints nearby.</p>';
        }

        const popupContent = `
            <div style="min-width: 250px; font-family: Arial, sans-serif;">
                <h4 style="margin: 0 0 10px 0; border-bottom: 2px solid #007bff; padding-bottom: 5px;">📍 Location Data</h4>
                
                <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                    <div><strong>Temp:</strong> ${data.temperature} ${data.temperature_unit}</div>
                    <div><strong>AQI:</strong> <span style="background-color: ${aqiColor}; padding: 2px 6px; border-radius: 4px; color: black; font-weight: bold;">${data.aqi}</span></div>
                </div>

                <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <h5 style="margin: 0 0 5px 0;">📢 Citizen Complaints</h5>
                    ${complaintsHtml}
                    <button onclick="toggleComplaintForm()" style="width: 100%; margin-top: 5px; padding: 5px; background: #007bff; color: white; border: none; border-radius: 3px; cursor: pointer;">+ Report Issue</button>
                </div>

                <div id="complaint-form" style="display: none; border-top: 1px solid #ddd; padding-top: 10px;">
                    <select id="comp-category" style="width: 100%; margin-bottom: 5px; padding: 5px;">
                        <option value="Garbage">Garbage / Waste</option>
                        <option value="Water">Water Supply</option>
                        <option value="Roads">Road / Pothole</option>
                        <option value="Electricity">Electricity</option>
                        <option value="Sewage">Sewage / Drainage</option>
                        <option value="Other">Other</option>
                    </select>
                    <textarea id="comp-desc" rows="2" placeholder="Describe the issue..." style="width: 100%; margin-bottom: 5px;"></textarea>
                    <button onclick="submitComplaint(${lat}, ${lng})" style="width: 100%; padding: 5px; background: #28a745; color: white; border: none; border-radius: 3px; cursor: pointer;">Submit Report</button>
                </div>
            </div>
        `;

        marker.bindPopup(popupContent).openPopup();

    } catch (error) {
        console.error("Error:", error);
        marker.bindPopup(`<div style="color:red">Error loading data.</div>`).openPopup();
    }
}

window.toggleComplaintForm = function() {
    const form = document.getElementById('complaint-form');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

window.submitComplaint = async function(lat, lng) {
    const category = document.getElementById('comp-category').value;
    const description = document.getElementById('comp-desc').value;

    if (!description) {
        alert("Please provide a description.");
        return;
    }

    try {
        const response = await fetch('/add_complaint', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ lat, lon: lng, category, description })
        });

        const result = await response.json();
        if (result.status === 'success') {
            alert("Complaint submitted successfully!");
            updateMarkerAndPopup(lat, lng); // Refresh popup
            loadHeatmap(); // Refresh heatmap
        } else {
            alert("Failed to submit.");
        }
    } catch (err) {
        alert("Error submitting complaint.");
    }
}

async function performSearch() {
    const query = document.getElementById('search-input').value;
    const resultsDiv = document.getElementById('search-results');
    
    if (!query) return;

    resultsDiv.innerHTML = '<div class="result-item">Searching...</div>';
    resultsDiv.style.display = 'block';

    try {
        const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        resultsDiv.innerHTML = '';

        if (data.features && data.features.length > 0) {
            data.features.forEach(feature => {
                const props = feature.properties;
                const coords = feature.geometry.coordinates; 
                
                const div = document.createElement('div');
                div.className = 'result-item';
                div.textContent = props.formatted;
                div.onclick = () => {
                    selectLocation(coords[1], coords[0]);
                };
                resultsDiv.appendChild(div);
            });
        } else {
            resultsDiv.innerHTML = '<div class="result-item">No results found</div>';
        }

    } catch (error) {
        console.error("Search error:", error);
        resultsDiv.innerHTML = '<div class="result-item" style="color:red">Error fetching results</div>';
    }
}

function selectLocation(lat, lng) {
    document.getElementById('search-results').style.display = 'none';
    map.setView([lat, lng], 14);
    updateMarkerAndPopup(lat, lng);
}

initMap();


