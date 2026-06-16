(function() {
    var savedCity = localStorage.getItem('jobflow_city');
    if (savedCity) {
        var cityLink = document.querySelector('.nav-right a[href="city.html"]');
        if (cityLink) {
            cityLink.innerHTML = '<i class="fas fa-map-marker-alt"></i> ' + savedCity;
        }
    }
})();
