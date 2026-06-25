(function() {
    var KEY = 'jobflow_city';

    function applyCity(city) {
        if (!city) return;
        var cityLink = document.querySelector('.nav-right a[href="city.html"]');
        if (cityLink) {
            cityLink.innerHTML = '<i class="fas fa-map-marker-alt"></i> ' + city;
        }
        var cityInput = document.getElementById('cityInput');
        if (cityInput && !cityInput.value.trim()) {
            cityInput.value = city;
        }
    }

    var savedCity = localStorage.getItem(KEY);
    if (savedCity) {
        applyCity(savedCity);
    }

    window.addEventListener('storage', function(e) {
        if (e.key === KEY && e.newValue) {
            var cityLink = document.querySelector('.nav-right a[href="city.html"]');
            if (cityLink) {
                cityLink.innerHTML = '<i class="fas fa-map-marker-alt"></i> ' + e.newValue;
            }
            var cityInput = document.getElementById('cityInput');
            if (cityInput) {
                cityInput.value = e.newValue;
            }
        }
    });
})();
