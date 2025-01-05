let progressPollingInterval;

document.addEventListener('DOMContentLoaded', function () {
    const startButton = document.getElementById('startExecution');
    const stopButton = document.getElementById('stopExecution');
    const stopModal = document.getElementById('stopModal');
    stopButton.disabled = true;

    //stopping logic
    stopButton.addEventListener('click', function () {
        clearInterval(progressPollingInterval);
        stopModal.style.display = 'block';
        stopButton.disabled = true;
        const stopMessage = document.querySelector('#stopMessage');

        stopMessage.textContent = 'Stopping execution...';

        fetch('/api/execution/stop', {method: 'POST'})
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    throw new Error(data.error || 'Error stopping execution');
                }

                const pollInterval = setInterval(() => {
                    fetch('/api/execution/stop')
                        .then(response => response.json())
                        .then(status => {
                            if (status.stopped) {
                                clearInterval(pollInterval);
                                stopMessage.textContent = 'Execution stopped successfully.';
                                resetUI();

                                setTimeout(() => {
                                    stopModal.style.display = 'none';
                                    startButton.disabled = false;
                                }, 2000);
                            }
                        })
                        .catch(error => {
                            clearInterval(pollInterval);
                            stopMessage.textContent = 'Error occurred while stopping execution.';
                            console.error('Error polling stopping status:', error);
                        });
                }, 1000);
            })
            .catch(error => {
                stopMessage.textContent = error.message || 'An error occurred while sending the stop request.';
                console.error('Error stopping execution:', error);
            });
    });

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
    document.getElementById('startExecution').addEventListener('click', function () {
        const progressBar = document.querySelector('.progress-bar-fill');
        const progressText = document.querySelector('.progress-text');

        document.getElementById('progressIndicator').style.display = 'block';
        startButton.disabled = true;
        stopButton.disabled = false;

        // Start execution
        fetch('/api/execution/start', {
            method: 'POST'
        })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    throw new Error(data.error || 'Execution failed');
                }
                if (data.hasOwnProperty("stopped") && data.stopped) {
                    return;
                }
                document.getElementById('resultsSection').style.display = 'block';
            })
            .catch(error => {
                document.getElementById('progressIndicator').style.display = 'none';
                this.disabled = false;
                showError(error.message || 'Error during execution');
            })
            .finally(() => {
                startButton.disabled = false;
                stopButton.disabled = true;
            });

        // Poll progress
        progressPollingInterval = setInterval(() => {
            fetch('/api/execution/progress')
                .then(response => response.json())
                .then(data => {
                    if (!data.success) {
                        if (data.error) {
                            clearInterval(progressPollingInterval);
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
                        clearInterval(progressPollingInterval);
                        setTimeout(() => {
                            document.getElementById('progressIndicator').style.display = 'none';
                        }, 500);
                    }
                })
                .catch(error => {
                    clearInterval(progressPollingInterval);
                    document.getElementById('progressIndicator').style.display = 'none';
                    this.disabled = false;
                    showError('Error checking progress');
                });
        }, 1000);
    });
});

window.downloadResults = function (format) {
    window.location.href = `/api/execution/download/${format}`;
};

window.downloadSampleSpace = function () {
    window.location.href = '/api/execution/download/samplespace';
};

function showError(message) {
    const alert = document.createElement('div');
    alert.className = 'error-alert';
    alert.textContent = message;
    document.body.appendChild(alert);
    setTimeout(() => alert.remove(), 3000);
}

function resetUI() {
    document.getElementById('progressIndicator').style.display = 'none';

    const progressBar = document.querySelector('.progress-bar-fill');
    const progressText = document.querySelector('.progress-text');
    progressBar.style.width = '0%';
    progressText.textContent = '0%';

    document.getElementById('startExecution').disabled = false;
    //document.getElementById('resultsSection').style.display = 'none';
}