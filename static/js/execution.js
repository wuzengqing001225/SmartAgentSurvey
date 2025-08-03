let progressPollingInterval;
let currentExecutionNum = 1;
let totalExecutions = 1;
let completedExecutions = new Set();
let executionFinished = false;

document.addEventListener('DOMContentLoaded', function () {
    const estimatedCostElem = document.getElementById('estimatedCost');
    const startButton = document.getElementById('startExecution');
    const stopButton = document.getElementById('stopExecution');
    const stopModal = document.getElementById('stopModal');
    const progressIndicator = document.getElementById('progressIndicator');
    const resultsSection = document.getElementById('resultsSection');

    const prevButton = document.getElementById('prevExecution');
    const nextButton = document.getElementById('nextExecution');
    const executionTitle = document.getElementById('executionTitle');

    stopButton.disabled = true;

    fetch('/sample/settings')
        .then(response => response.json())
        .then(data => {
            totalExecutions = parseInt(data.executions) || 1;
            document.getElementById('totalExecutions').textContent = totalExecutions;
        })
        .catch(error => {
            console.error('Error loading settings:', error);
        });

    function updateExecutionDisplay() {
        executionTitle.textContent = `Execution Results ${currentExecutionNum}`;
        prevButton.disabled = currentExecutionNum <= 1;
        nextButton.disabled = (currentExecutionNum >= totalExecutions) || (currentExecutionNum >= completedExecutions.size);
    }

    function showResults() {
        if (completedExecutions.size > 0) {
            resultsSection.style.display = 'block';
            currentExecutionNum = Math.max(...Array.from(completedExecutions));
            updateExecutionDisplay();
        } else {
            resultsSection.style.display = 'none';
        }
        progressIndicator.style.display = 'none';
    }

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
                            function finishExecution(message) {
                                clearInterval(pollInterval);
                                stopMessage.textContent = message;

                                showResults();
                                startButton.disabled = false;

                                setTimeout(() => {
                                    stopModal.style.display = 'none';
                                }, 2000);
                            }

                            if (status.stopped) {
                                finishExecution('Execution stopped successfully.');
                            }
                            if (executionFinished) {
                                executionFinished = false;
                                /* progress polling completes the last execution. However, the polling is cleared when clicking the button.
                                   in this if statement we know that the last execution has been completed for sure. So we should add it to the set
                                   and reload the results display accordingly.
                                * */
                                if(!completedExecutions.has(currentExecutionNum)) {
                                    completedExecutions.add(currentExecutionNum)
                                    showResults()
                                }
                                finishExecution('Execution already finished, stopping failed.')

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


    prevButton.addEventListener('click', () => {
        if (currentExecutionNum > 1) {
            currentExecutionNum--;
            updateExecutionDisplay();
        }
    });

    nextButton.addEventListener('click', () => {
        if (currentExecutionNum < totalExecutions && completedExecutions.has(currentExecutionNum + 1)) {
            currentExecutionNum++;
            updateExecutionDisplay();
        }
    });

    // Start execution handler
    startButton.addEventListener('click', function () {
        const progressBar = document.querySelector('.progress-bar-fill');
        const progressText = document.querySelector('.progress-text');


        completedExecutions.clear()
        progressIndicator.style.display = 'block';
        resultsSection.style.display = 'none';
        startButton.disabled = true;
        stopButton.disabled = false;
        currentExecutionNum = 1;
        document.getElementById('currentExecution').textContent = '1'

        const requestBody = {
            multi_modal: true
        };

        fetch('/api/execution/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    throw new Error(data.error || 'Execution failed');
                }
                stopButton.disabled = true;
                if (data.hasOwnProperty("stopped") && data.stopped) {
                    return;
                } else {
                    executionFinished = true;
                }
                document.getElementById('resultsSection').style.display = 'block';
            })
            .catch(error => {
                document.getElementById('progressIndicator').style.display = 'none';
                startButton.disabled = false;
                showError(error.message || 'Error during execution');
            });

        progressPollingInterval = setInterval(() => {
            fetch(`/api/execution/progress/${currentExecutionNum}`)
                .then(response => response.json())
                .then(data => {
                    if (!data.success) {
                        if (data.error) {
                            clearInterval(progressPollingInterval);
                            showError(data.error);
                            startButton.disabled = false;
                        }
                        return;
                    }

                    const progress = data.progress;
                    const executionNum = data.current_execution || 1;
                    const totalExecs = data.total_executions || totalExecutions;

                    document.getElementById('currentExecution').textContent = executionNum;
                    document.getElementById('totalExecutions').textContent = totalExecs;

                    progressBar.style.width = `${progress}%`;
                    progressText.textContent = `${Math.round(progress)}%`;

                    if (progress >= 100) {
                        completedExecutions.add(executionNum);

                        if (currentExecutionNum < totalExecs) {
                            currentExecutionNum = executionNum + 1;
                            updateExecutionDisplay();
                        } else {
                            clearInterval(progressPollingInterval);
                            showResults();
                            progressIndicator.style.display = 'none';
                            startButton.disabled = false;
                            stopButton.disabled = true;
                        }

                    }
                })
                .catch(error => {
                    clearInterval(progressPollingInterval);
                    progressIndicator.style.display = 'none';
                    startButton.disabled = false;
                    showError('Error checking progress');
                });
        }, 1000);
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
            document.getElementById('executions').textContent = totalExecutions;
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


});

window.downloadResults = function (format) {
    window.location.href = `/api/execution/download/${format}/${currentExecutionNum}`;
};

window.downloadSampleSpace = function () {
    window.location.href = `/api/execution/download/samplespace`;
};


function showError(message) {
    const alert = document.createElement('div');
    alert.className = 'error-alert';
    alert.textContent = message;
    document.body.appendChild(alert);
    setTimeout(() => alert.remove(), 3000);
}
