// Main JavaScript file
console.log('DD3S Application Loaded');

// CSRF Token Helper
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// Auto-dismiss alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Search functionality
function performSearch(query) {
    if (query.length < 3) {
        console.log('Query too short');
        return;
    }
    
    fetch(`/api/search/?q=${encodeURIComponent(query)}`, {
        headers: {
            'X-CSRFToken': csrftoken
        },
        credentials: 'same-origin'
    })
        .then(response => response.json())
        .then(data => {
            console.log('Search results:', data);
            // Update UI with results
        })
        .catch(error => console.error('Search error:', error));
}

// Debounce function for search
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
