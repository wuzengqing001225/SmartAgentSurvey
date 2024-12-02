document.addEventListener('DOMContentLoaded', function() {
    // Load metrics
    fetch('/api/execution/metrics')
        .then(response => response.json())
        .then(data => {
            console.log('Metrics response:', data);  // Debug log
            if (data.error) {
                showError(data.error);
                return;
            }
            document.getElementById('surveyLength').textContent = data.survey_length || '-';
            document.getElementById('agentCount').textContent = data.agent_count || '-';
            document.getElementById('estimatedCost').textContent = 
                data.estimated_cost ? parseFloat(data.estimated_cost).toFixed(5) : '-';
        })
        .catch(error => {
            console.error('Metrics error:', error);  // Debug log
            showError('Error loading metrics');
        });
    
    // Keep processing status for current file
    const currentFile = localStorage.getItem('currentFile');
    if (currentFile) {
        document.querySelectorAll('.history-item').forEach(item => {
            if (item.dataset.filename === currentFile) {
                item.classList.add('active-processing');
                const statusBadge = item.querySelector('.status-badge');
                statusBadge.textContent = 'Processed';
                statusBadge.className = 'status-badge processed';
            } else {
                item.classList.add('processing');
            }
        });
    }
    
    // Start execution handler
    document.getElementById('startExecution').addEventListener('click', function() {
        const progressBar = document.querySelector('.progress-bar-fill');
        const progressText = document.querySelector('.progress-text');
        
        document.getElementById('progressIndicator').style.display = 'block';
        this.disabled = true;

        // Start execution
        fetch('/api/execution/start', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                throw new Error(data.error || 'Execution failed');
            }
            document.getElementById('resultsSection').style.display = 'block';
        })
        .catch(error => {
            document.getElementById('progressIndicator').style.display = 'none';
            this.disabled = false;
            showError(error.message || 'Error during execution');
        });

        // Poll progress
        const checkProgress = setInterval(() => {
            fetch('/api/execution/progress')
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    if (data.error) {
                        clearInterval(checkProgress);
                        document.getElementById('progressIndicator').style.display = 'none';
                        showError(data.error);
                        this.disabled = false;
                    }
                    return;
                }

                const progress = data.progress;
                progressBar.style.width = `${progress}%`;
                progressText.textContent = `${Math.round(progress)}%`;

                if (progress >= 100) {
                    clearInterval(checkProgress);
                    setTimeout(() => {
                        document.getElementById('progressIndicator').style.display = 'none';
                    }, 500);
                }
            })
            .catch(error => {
                clearInterval(checkProgress);
                document.getElementById('progressIndicator').style.display = 'none';
                this.disabled = false;
                showError('Error checking progress');
            });
        }, 1000);
    });
});

window.downloadResults = function(format) {
    window.location.href = `/api/execution/download/${format}`;
};

window.downloadSampleSpace = function() {
    window.location.href = '/api/execution/download/samplespace';
};

function showError(message) {
    const alert = document.createElement('div');
    alert.className = 'error-alert';
    alert.textContent = message;
    document.body.appendChild(alert);
    setTimeout(() => alert.remove(), 3000);
}