// Modal functionality
function openSettingsModal() {
    document.getElementById('settingsModal').classList.add('show');
}

function closeSettingsModal() {
    document.getElementById('settingsModal').classList.remove('show');
}

function showMessage(message, alertClass) {
    const alert = document.createElement('div');
    alert.className = alertClass;
    alert.textContent = message;
    document.body.appendChild(alert);
    setTimeout(() => alert.remove(), 3000);
}

// Initialize settings functionality
document.addEventListener('DOMContentLoaded', function() {
    // Close modal when clicking outside
    document.getElementById('settingsModal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeSettingsModal();
        }
    });

    // Load current settings
    fetch('/api/settings')
        .then(response => response.json())
        .then(data => {
            document.getElementById('provider').value = data.llm_settings.provider;
            document.getElementById('api_key').value = data.llm_settings.api_key;
            document.getElementById('model').value = data.llm_settings.model;
            document.getElementById('max_tokens').value = data.llm_settings.max_tokens;
            document.getElementById('temperature').value = data.llm_settings.temperature;
            document.getElementById('temperatureValue').textContent = data.llm_settings.temperature;

            document.getElementById('sample_size').value = data.user_preference.sample.sample_size;
            document.getElementById('execution_order').value = data.user_preference.execution.order;
            document.getElementById('segmentation').checked = data.user_preference.execution.segmentation;
        });

    // Temperature slider value display
    document.getElementById('temperature').addEventListener('input', function(e) {
        document.getElementById('temperatureValue').textContent = e.target.value;
    });

    // Form submission
    document.getElementById('settingsForm').addEventListener('submit', function(e) {
        e.preventDefault();

        const formData = {
            llm_settings: {
                provider: document.getElementById('provider').value,
                api_key: document.getElementById('api_key').value,
                model: document.getElementById('model').value,
                max_tokens: parseInt(document.getElementById('max_tokens').value),
                temperature: parseFloat(document.getElementById('temperature').value)
            },
            user_preference: {
                sample: {
                    sample_size: parseInt(document.getElementById('sample_size').value)
                },
                execution: {
                    order: document.getElementById('execution_order').value,
                    segmentation: document.getElementById('segmentation').checked
                }
            }
        };

        fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMessage('Config saved successfully', 'success-alert');
                closeSettingsModal();
            } else {
                showMessage(data.error || 'Failed to save settings', 'error-alert');
            }
        })
        .catch(error => {
            showMessage('Error saving settings', 'error-alert');
        });
    });
});