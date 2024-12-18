document.addEventListener('DOMContentLoaded', function() {
    let currentFile = localStorage.getItem('currentFile');
    let currentDimensions = null;
    let currentProfiles = [];
    let currentProfileIndex = 0;
    
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
    window.selectMethod = function(method) {
        if (method === 'upload') {
            document.getElementById('methodSelectionView').classList.remove('active');
            document.getElementById('uploadView').classList.add('active');
        } else {
            // Generate dimensions
            fetch('/sample/generate_dimensions', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ filename: currentFile })
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
                }
            })
            .catch(error => showError('Error generating dimensions'));
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

    window.addNewDimension = function() {
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

    window.addOption = function(button) {
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

    window.removeOption = function(button) {
        const row = button.closest('.option-row');
        const container = row.closest('.options-container');
        if (container.querySelectorAll('.option-row').length > 1) {
            row.remove();
        }
    };

    window.removeDimension = function(name) {
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

    window.saveDimensions = function() {
        const updatedDimensions = collectDimensionData();
        currentDimensions = updatedDimensions;

        fetch('/sample/save_dimensions', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ dimensions: updatedDimensions })
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

    window.generateSamples = function() {
        const updatedDimensions = collectDimensionData();
        fetch('/sample/update_dimensions', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ dimensions: updatedDimensions })
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

    // Results Display
    function showResults(data, isUpload = false) {
        document.getElementById('uploadView').classList.remove('active');
        document.getElementById('dimensionsView').classList.remove('active');
        document.getElementById('resultsView').classList.add('active');

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

    function renderResults(data) {
        document.querySelectorAll('.history-item').forEach(item => {
            // Remove any existing active classes first
            item.classList.remove('active', 'active-processing');
            
            if (item.dataset.filename === currentFile) {
                item.classList.add('active-processing');
                // Update status badge if needed
                const statusBadge = item.querySelector('.status-badge');
                statusBadge.textContent = 'Sampled';
                statusBadge.className = 'status-badge sampled';
            } else {
                // Disable other items
                item.classList.add('processing');
            }
        });

        if (data.is_upload) {
            const resultsContainer = document.getElementById('resultsView');
            resultsView.style.display = 'flex';

            resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="sample-count">
                        <h2>Total Samples</h2>
                        <div class="count-number">${data.total_samples}</div>
                    </div>
                </div>
                <div class="execution-button">
                    <button class="btn primary" onclick="proceedToExecution()">Proceed to Execution</button>
                </div>
                <div class="container-upload" id="profilesContainerUpload"></div>
            `;
    
            const profilesContainer = document.getElementById('profilesContainerUpload');

            // Uploaded samples: display as text
            profilesContainer.innerHTML = data.samples.map((sample, index) => `
                <div class="text-profile-upload">
                    <span><strong>Profile ${index + 1}:</strong> ${sample}</span>
                </div>
            `).join('');
        }    
        else {
            const resultsContainer = document.getElementById('resultsView');
            resultsView.style.display = 'block';

            resultsContainer.innerHTML = `
                <div class="results-header">
                    <div class="sample-count">
                        <h2>Total Samples</h2>
                        <div class="count-number">${data.total_samples}</div>
                    </div>
                </div>
                <div class="execution-button">
                    <button class="btn primary" onclick="proceedToExecution()">Proceed to Execution</button>
                </div>
                <div class="profiles-container" id="profilesContainer"></div>
            `;
    
            const profilesContainer = document.getElementById('profilesContainer');

            // Generated samples: display as cards
            profilesContainer.innerHTML = data.samples.slice(0, 10).map((sample, index) => `
                <div class="profile-card">
                    <div class="profile-header">Profile ${index + 1}</div>
                    <div class="profile-attributes">
                        ${Object.entries(sample).map(([key, value]) => {
                            const dimensionConfig = data.dimensions[key];
                            return `
                                <div class="attribute-row">
                                    <div class="attribute-name">${key}</div>
                                    <div class="attribute-value">
                                        ${renderAttributeValue(value, dimensionConfig)}
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `).join('');
        }
    }    

    function renderAttributeValue(value, dimensionConfig) {
        if (!dimensionConfig) return value;

        if (dimensionConfig.scale) {
            // Numeric value with scale visualization
            const [min, max] = dimensionConfig.scale;
            const percentage = ((value - min) / (max - min)) * 100;
            return `
                <div class="value-container">
                    <span class="value-text">${value}</span>
                    <div class="value-scale">
                        <div class="scale-track">
                            <div class="scale-marker" style="left: ${percentage}%"></div>
                        </div>
                        <div class="scale-labels">
                            <span>${min}</span>
                            <span>${max}</span>
                        </div>
                    </div>
                </div>
            `;
        } else if (dimensionConfig.options) {
            // Options with position indicator
            const currentIndex = dimensionConfig.options.indexOf(value);
            return `
                <div class="value-container">
                    <span class="value-text">${value}</span>
                    <div class="options-indicator">
                        ${dimensionConfig.options.map((opt, idx) => `
                            <span class="option-marker ${idx === currentIndex ? 'active' : ''}" 
                                title="${opt}"></span>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        return value;
    }
  
    // Profile Navigation
    window.showNextProfile = function() {
        if (currentProfileIndex < Math.min(9, currentProfiles.length - 1)) {
            currentProfileIndex++;
            showProfile(currentProfileIndex);
        }
    };
    
    window.showPreviousProfile = function() {
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
    

    // Navigation
    window.proceedToExecution = function() {
        window.location.href = '/execute';
    };

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
});