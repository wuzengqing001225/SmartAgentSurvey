document.addEventListener('DOMContentLoaded', function () {
    let currentFile = localStorage.getItem('currentFile');
    let currentDimensions = null;
    let currentProfiles = [];
    let currentProfileIndex = 0;

    let sampleSizeInput = document.getElementById('sampleSizeInput');
    let settingsModalInput = document.getElementById('sample_size');
    let generateCard = document.getElementById('generateCardIdThing');
    generateCard.classList.remove('active');

    fetch('/api/settings')
        .then(response => response.json())
        .then(data => {
            const sampleSize = data.user_preference.sample.sample_size;
            sampleSizeInput.value = sampleSize;
            if (settingsModalInput) {
                settingsModalInput.value = sampleSize;
            }
        })
        .catch(error => console.error('Error loading sample size:', error));

    sampleSizeInput.addEventListener('change', function () {
        const newSize = parseInt(this.value);
        if (isNaN(newSize) || newSize < 1 || newSize > 1000) {
            showError('Sample size must be between 1 and 1000');
            return;
        }

        fetch('/api/settings')
            .then(response => response.json())
            .then(data => {
                const updatedConfig = {
                    llm_settings: data.llm_settings,
                    user_preference: {
                        ...data.user_preference,
                        sample: {
                            ...data.user_preference.sample,
                            sample_size: newSize
                        }
                    }
                };

                return fetch('/api/settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(updatedConfig)
                });
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showSuccess('Sample size updated successfully');
                    if (settingsModalInput) {
                        settingsModalInput.value = newSize;
                    }
                } else {
                    showError(data.error || 'Failed to update sample size');
                }
            })
            .catch(error => showError('Error updating sample size'));
    });

    sampleSizeInput.addEventListener('input', function () {
        if (settingsModalInput) {
            settingsModalInput.value = sampleSizeInput.value;
        }
    });

    // Keep processing status
    if (currentFile) {
        document.querySelectorAll('.history-item').forEach(item => {
            // Remove any existing active classes first
            item.classList.remove('active', 'active-processing');

            if (item.dataset.filename === currentFile) {
                item.classList.add('active-processing');
                // Update status badge if needed
                const statusBadge = item.querySelector('.status-badge');
                if (statusBadge && !statusBadge.classList.contains('calibration')) {
                    statusBadge.textContent = 'Attention Check';
                    statusBadge.className = 'status-badge calibration';
                }
            } else {
                // Disable other items
                item.classList.add('processing');
            }
        });
    }

    // Method Selection
    window.selectMethod = function (method) {
        if (method === 'upload') {
            document.getElementById('methodSelectionView').classList.remove('active');
            document.getElementById('uploadView').classList.add('active');
        } else {

            const originalContent = generateCard.innerHTML;
            generateCard.innerHTML = `
                            <h3 id="header3text">
                            <span class="spinner-card"></span>
                            Generating...</h3>
                            <p>Create and customize sample dimensions</p>
                            <div class="method-icon">⚙️</div>`;

            // Disable the card click
            generateCard.style.pointerEvents = 'none';
            // Generate dimensions
            fetch('/sample/generate_dimensions', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({filename: currentFile})
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        currentDimensions = data.dimensions;
                        renderDimensionsGrid(data.dimensions);
                        document.getElementById('methodSelectionView').classList.remove('active');
                        document.getElementById('dimensionsView').classList.add('active');
                    } else {
                        showError(data.error || 'Failed to generate dimensions');
                        generateCard.innerHTML = originalContent;
                        generateCard.style.pointerEvents = 'auto';
                        generateCard.style.opacity = '1';
                    }
                })
                .catch(error => {
                    showError('Error generating dimensions')
                    generateCard.innerHTML = originalContent;
                    generateCard.style.pointerEvents = 'auto';
                    generateCard.style.opacity = '1';
                });

        }
    };

    // Dimensions Management
    function renderDimensionsGrid(dimensions) {
        const grid = document.getElementById('dimensionsGrid');
        grid.innerHTML = '';

        Object.entries(dimensions).forEach(([name, config]) => {
            const card = document.createElement('div');
            card.className = 'dimension-card';
            card.innerHTML = `
                <div class="dimension-header">
                    <div class="dimension-name">
                        <input type="text" value="${name}" class="dimension-name-input" readonly>
                    </div>
                    <button class="btn-icon" onclick="removeDimension('${name}')">×</button>
                </div>
                ${renderDimensionContent(config)}
            `;
            grid.appendChild(card);
        });
    }

    function renderDimensionContent(config) {
        if (config.scale) {
            return `
                <div class="dimension-values">
                    <label>Range:</label>
                    <div class="scale-inputs">
                        <input type="number" value="${config.scale[0]}" placeholder="Min">
                        <input type="number" value="${config.scale[1]}" placeholder="Max">
                        <input type="number" value="${config.scale[2]}" placeholder="Step">
                    </div>
                </div>
            `;
        } else {
            return `
                <div class="dimension-values">
                    <label>Options:</label>
                    <div class="options-container">
                        ${config.options.map((opt, idx) => `
                            <div class="option-row">
                                <input type="text" value="${opt}" class="option-input">
                                <div class="distribution-input-group">
                                    <input type="number" value="${config.distribution[idx]}" min="0" max="100" class="distribution-input">
                                    <span>&ensp;%</span>
                                </div>
                                <button class="btn-icon delete-option" onclick="removeOption(this)">×</button>
                            </div>
                        `).join('')}
                        <button class="btn secondary add-option" onclick="addOption(this)">+ Add Option</button>
                    </div>
                </div>
            `;
        }
    }

    window.addNewDimension = function () {
        let dimensionNumber = 1;
        const baseName = 'New Dimension';
        let dimensionName = baseName;

        while (dimensionName in currentDimensions) {
            dimensionNumber++;
            dimensionName = `${baseName} ${dimensionNumber}`;
        }

        const newDimension = {
            options: ['Option 1', 'Option 2'],
            distribution: [50, 50],
            format: 'You are X.'
        };
        currentDimensions[dimensionName] = newDimension;
        renderDimensionsGrid(currentDimensions);
    };

    window.addOption = function (button) {
        const optionsContainer = button.closest('.options-container');
        const newRow = document.createElement('div');
        newRow.className = 'option-row';
        newRow.innerHTML = `
            <input type="text" value="New Option" class="option-input">
            <div class="distribution-input-group">
                <input type="number" value="0" min="0" max="100" class="distribution-input">
                <span>%</span>
            </div>
            <button class="btn-icon delete-option" onclick="removeOption(this)">×</button>
        `;
        optionsContainer.insertBefore(newRow, button);
    };

    window.removeOption = function (button) {
        const row = button.closest('.option-row');
        const container = row.closest('.options-container');
        if (container.querySelectorAll('.option-row').length > 1) {
            row.remove();
        }
    };

    window.removeDimension = function (name) {
        delete currentDimensions[name];
        renderDimensionsGrid(currentDimensions);
    };

    // Save and Generate functions
    function collectDimensionData() {
        const dimensions = {};
        document.querySelectorAll('.dimension-card').forEach(card => {
            const name = card.querySelector('.dimension-name input').value;

            if (card.querySelector('.scale-inputs')) {
                const inputs = card.querySelectorAll('.scale-inputs input');
                dimensions[name] = {
                    scale: [
                        parseInt(inputs[0].value),
                        parseInt(inputs[1].value),
                        parseInt(inputs[2].value)
                    ],
                    format: 'Your age is X years old.'
                };
            } else {
                const options = [];
                const distribution = [];
                card.querySelectorAll('.option-row').forEach(row => {
                    options.push(row.querySelector('.option-input').value);
                    distribution.push(parseInt(row.querySelector('.distribution-input').value) || 0);
                });
                dimensions[name] = {
                    options: options,
                    distribution: distribution,
                    format: 'You are X.'
                };
            }
        });
        return dimensions;
    }

    window.saveDimensions = function () {
        const updatedDimensions = collectDimensionData();
        currentDimensions = updatedDimensions;

        fetch('/sample/save_dimensions', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({dimensions: updatedDimensions})
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showSuccess('Dimensions saved successfully');
                } else {
                    showError(data.error || 'Failed to save dimensions');
                }
            })
            .catch(error => showError('Error saving dimensions'));
    };

    window.generateSamples = function () {
        const updatedDimensions = collectDimensionData();
        const sampleSize = parseInt(sampleSizeInput.value) || 10;

        fetch('/sample/update_dimensions', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                dimensions: updatedDimensions,
                sample_size: sampleSize
            })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showResults(data);
                } else {
                    showError(data.error || 'Failed to generate samples');
                }
            })
            .catch(error => showError('Error generating samples'));
    };

    // File Upload Handling
    if (document.getElementById('sampleDropZone')) {
        const dropZone = document.getElementById('sampleDropZone');
        const fileInput = document.getElementById('sampleFileInput');

        dropZone.addEventListener('drop', handleDrop);
        dropZone.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', handleFileSelect);

        function handleDrop(e) {
            e.preventDefault();
            const file = e.dataTransfer.files[0];
            if (file) uploadSampleFile(file);
        }

        function handleFileSelect(e) {
            const file = e.target.files[0];
            if (file) uploadSampleFile(file);
        }

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
    }

    function uploadSampleFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        fetch('/sample/upload', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showResults(data, true);
                } else {
                    showError(data.error || 'Upload failed');
                }
            })
            .catch(error => showError('Error uploading file'));
    }

    // Record how the user entered the total samples page
    let lastEntryMethod = null; // 'generate' or 'upload'

    // Results Display
    function showResults(data, isUpload = false) {
        document.getElementById('uploadView').classList.remove('active');
        document.getElementById('dimensionsView').classList.remove('active');
        document.getElementById('resultsView').classList.add('active');
        lastEntryMethod = isUpload ? 'upload' : 'generate';
        fetch('/sample/results')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    renderResults(data);
                } else {
                    showError(data.error || 'Failed to load results');
                }
            })
            .catch(error => showError('Error loading results'));
    }

    // Add navigation function for going back to Sample Dimensions
    window.goBackToDimensions = function() {
        // Hide all views
        document.getElementById('resultsView').classList.remove('active');
        document.getElementById('resultsView').style.display = '';
        document.getElementById('dimensionsView').classList.remove('active');
        document.getElementById('dimensionsView').style.display = '';
        document.getElementById('methodSelectionView').classList.remove('active');
        document.getElementById('uploadView').classList.remove('active');
        document.getElementById('profileView').classList.remove('active');
        // Only show dimensionsView
        document.getElementById('dimensionsView').classList.add('active');
    };

    function renderResults(data) {
        document.querySelectorAll('.history-item').forEach(item => {
            item.classList.remove('active', 'active-processing');
            if (item.dataset.filename === currentFile) {
                item.classList.add('active-processing');
                const statusBadge = item.querySelector('.status-badge');
                statusBadge.textContent = 'Sampled';
                statusBadge.className = 'status-badge sampled';
            } else {
                item.classList.add('processing');
            }
        });

        if (data.is_upload) {
            const resultsContainer = document.getElementById('resultsView');
            resultsContainer.style.display = 'flex';
            resultsContainer.style.padding = 0;
            resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="sample-count">
                        <h2>Total Samples</h2>
                        <div class="count-number">${data.total_samples}</div>
                    </div>
                </div>
                <div class="execution-controls">
                    <div class="execution-button">
                        <button class="btn secondary" onclick="${lastEntryMethod === 'upload' ? 'goBackToMethodSelection()' : 'goBackToDimensions()'}">Previous Step</button>
                    </div>
                    <div class="execution-button">
                        <button class="btn primary" onclick="downloadSampleSpace()">Download Profiles</button>
                    </div>
                    <div class="sample-size-control">
                        <label for="executionCountInput">Number of Executions:</label>
                        <input type="number" id="executionCountInput" min="1" value="1" class="number-input">
                    </div>
                    <div class="execution-button">
                        <button class="btn primary" onclick="proceedToExecution()">Proceed to Execution</button>
                    </div>
                </div>
                <div class="container-upload" id="profilesContainerUpload"></div>
            `;
            const profilesContainer = document.getElementById('profilesContainerUpload');
            profilesContainer.innerHTML = data.samples.map((sample, index) => `
                <div class="text-profile-upload">
                    <span><strong>Profile ${index + 1}:</strong> ${sample}</span>
                </div>
            `).join('');
        } else {
            const resultsContainer = document.getElementById('resultsView');
            resultsContainer.style.display = 'block';
            resultsContainer.style.padding = 0;
            resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="sample-count">
                        <h2>Total Samples</h2>
                        <div class="count-number">${data.total_samples}</div>
                    </div>
                </div>
                <div class="execution-controls">
                    <div class="execution-button">
                        <button class="btn secondary" onclick="${lastEntryMethod === 'upload' ? 'goBackToMethodSelection()' : 'goBackToDimensions()'}">Previous Step</button>
                    </div>
                    <div class="execution-button">
                        <button class="btn primary" onclick="downloadSampleSpace()">Download Profiles</button>
                    </div>
                    <div class="sample-size-control">
                        <label for="executionCountInput">Number of Executions:</label>
                        <input type="number" id="executionCountInput" min="1" value="1" class="number-input">
                    </div>
                    <div class="execution-button">
                        <button class="btn primary" onclick="proceedToExecutionAndSendProfiles()">Proceed to Execution</button>
                    </div>
                </div>
                <div class="profiles-container" id="profilesContainer"></div>
            `;
            const profilesContainer = document.getElementById('profilesContainer');
            profilesContainer.innerHTML = data.samples.map((sample, index) => `
            <div class="profile-card" data-index="${index}">
                <div class="profile-header">Profile ${index + 1}</div>
                <div class="profile-attributes">
                    ${Object.entries(sample).map(([key, value]) => {
                const dimensionConfig = data.dimensions[key];
                return `
                    <div class="attribute-row">
                        <div class="attribute-name">${key}</div>
                        <div class="attribute-value">
                            ${renderEditableAttribute(value, dimensionConfig, key, index)}
                        </div>
                    </div>
                    `;
            }).join('')}
                </div>
            </div>
            `).join('');
        }
    }

    function renderEditableAttribute(value, dimensionConfig, key, index) {
        if (!dimensionConfig) {
            // Non-configurable attributes as plain text input
            return `<input type="text" class="editable-input" data-key="${key}" data-index="${index}" value="${value}" />`;
        }

        if (dimensionConfig.scale) {
            // Numeric value with constrained input
            const [min, max] = dimensionConfig.scale;
            return `
            <input type="number" class="editable-input"
                data-key="${key}" data-index="${index}"
                value="${value}" min="${min}" max="${max}" />
        `;
        } else if (dimensionConfig.options) {
            // Dropdown for predefined options
            return `
            <select class="editable-select" data-key="${key}" data-index="${index}">
                ${dimensionConfig.options.map(opt => `
                    <option value="${opt}" ${opt === value ? 'selected' : ''}>${opt}</option>
                `).join('')}
            </select>
        `;
        }

        return `<input type="text" class="editable-input" data-key="${key}" data-index="${index}" value="${value}" />`;
    }

    window.downloadSampleSpace = function () {
        collectAndSendEditedProfiles();
        window.location.href = `/api/execution/download/samplespace`;
    }

    function collectAndSendEditedProfiles() {
        const editedProfiles = [];
        document.querySelectorAll('.profile-card').forEach(card => {
            const profile = {};
            card.querySelectorAll('.editable-input, .editable-select').forEach(input => {
                const key = input.getAttribute('data-key');
                const value = input.value;
                profile[key] = value;
            });
            editedProfiles.push(profile);
        });

        // Send the edited profiles to the Flask endpoint
        fetch('/save-profiles', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(editedProfiles)
        }).then(response => {
            if (!response.ok) {
                console.error('Failed to save edits.');
            }
        }).catch(error => {
            console.error('Error saving edits:', error);
        });
    }

    // Profile Navigation
    window.showNextProfile = function () {
        if (currentProfileIndex < Math.min(9, currentProfiles.length - 1)) {
            currentProfileIndex++;
            showProfile(currentProfileIndex);
        }
    };

    window.showPreviousProfile = function () {
        if (currentProfileIndex > 0) {
            currentProfileIndex--;
            showProfile(currentProfileIndex);
        }
    };

    function showProfile(index) {
        const profile = currentProfiles[index];
        document.getElementById('currentProfileIndex').textContent = index + 1;
        document.getElementById('totalProfiles').textContent = Math.min(10, currentProfiles.length);

        const profileCard = document.getElementById('profileCard');

        profileCard.innerHTML = Object.entries(profile).map(([key, values]) => `
            <div class="profile-attribute">
                <div class="attribute-name">${key}</div>
                <div class="attribute-value">
                    ${Array.isArray(values) ? values.join(",") : values}
                </div>
            </div>
        `).join('');
    }

    // Notifications
    function showError(message) {
        const alert = document.createElement('div');
        alert.className = 'error-alert';
        alert.textContent = message;
        document.body.appendChild(alert);
        setTimeout(() => alert.remove(), 3000);
    }

    function showSuccess(message) {
        const alert = document.createElement('div');
        alert.className = 'success-alert';
        alert.textContent = message;
        document.body.appendChild(alert);
        setTimeout(() => alert.remove(), 3000);
    }

    // Navigation
    window.proceedToExecution = function () {
        let executionCountInput = document.getElementById("executionCountInput");
        let executionCount = executionCountInput ? executionCountInput.value : 1;

        fetch('/sample/settings', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({executions: executionCount})
        }).then(response => {
            if (response.ok) {
                window.location.href = '/execute';
            } else {
                alert("Error saving execution settings.");
            }
        }).catch(error => {
            console.error("Error:", error);
        });
    }

    window.proceedToExecutionAndSendProfiles = function () {
        collectAndSendEditedProfiles();
        proceedToExecution();
    }

    window.goBackToMethodSelection = function() {
        // Hide all views under main-content
        document.querySelectorAll('.main-content .view').forEach(view => {
            view.classList.remove('active');
        });
        // Hide resultsView display
        document.getElementById('resultsView').style.display = '';
        // Only show method selection view
        document.getElementById('methodSelectionView').classList.add('active');
        // Restore generateCard button state
        let generateCard = document.getElementById('generateCardIdThing');
        generateCard.innerHTML = `
            <h3 id="header3text">Generate Samples</h3>
            <p>Create and customize sample dimensions</p>
            <div class="method-icon">⚙️</div>
        `;
        generateCard.style.pointerEvents = 'auto';
        generateCard.style.opacity = '1';
    };
});