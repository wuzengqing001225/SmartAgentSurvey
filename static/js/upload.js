let fewShotExamples = {};

document.addEventListener('DOMContentLoaded', function () {
    // DOM Elements
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const selectedFileInfo = document.getElementById('selectedFileInfo');
    const selectedFilename = document.querySelector('.selected-filename');
    const processButton = document.getElementById('processButton');
    let currentSelectedFile = null;

    // File Status Management
    function updateFileStatus(filename, status) {
        document.querySelectorAll('.history-item').forEach(item => {
            if (item.dataset.filename === filename) {
                // Update status badge
                const statusBadge = item.querySelector('.status-badge');
                statusBadge.textContent = status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
                statusBadge.className = `status-badge ${status.toLowerCase()}`;

                // Update item state
                item.classList.add('active-processing');

                // Add this status check
                if (['preprocessing', 'preprocessed', 'calibration'].includes(status.toLowerCase())) {
                    disableOtherItems(item);
                    // Remove click handlers from other items
                    document.querySelectorAll('.history-item').forEach(otherItem => {
                        if (otherItem !== item) {
                            otherItem.classList.add('processing');
                            // Remove click event listener
                            const clone = otherItem.cloneNode(true);
                            otherItem.parentNode.replaceChild(clone, otherItem);
                        }
                    });
                }
            }
        });
    }

    function disableOtherItems(activeItem) {
        document.querySelectorAll('.history-item').forEach(item => {
            if (item !== activeItem) {
                item.classList.add('processing');
            }
        });
    }

    // File Selection
    function selectFile(filename) {
        // Check if any file is being processed
        const isProcessing = document.querySelector('.history-item.active-processing');
        if (isProcessing) {
            return; // Don't allow selection when a file is being processed
        }

        currentSelectedFile = filename;
        selectedFilename.textContent = filename;
        selectedFileInfo.style.display = 'block';

        document.querySelectorAll('.history-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.filename === filename) {
                item.classList.add('active');
            }
        });
    }

    // Add click handlers function
    function addClickHandlers() {
        document.querySelectorAll('.history-item').forEach(item => {
            // Only add click handler if the item is not being processed
            if (!item.classList.contains('processing')) {
                item.addEventListener('click', () => selectFile(item.dataset.filename));
            }
        });
    }

    // Drag and Drop Handling
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight(e) {
        dropZone.classList.add('dragover');
    }

    function unhighlight(e) {
        dropZone.classList.remove('dragover');
    }

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    // File Upload Handling
    function handleFiles(files) {
        if (files.length === 0) return;

        const file = files[0];
        const formData = new FormData();
        formData.append('file', file);

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    addNewFileToHistory(data.file);
                    selectFile(data.file.filename);
                } else {
                    showError(data.error || 'Upload failed');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showError('Upload error');
            });
    }

    function addNewFileToHistory(file) {
        const historyList = document.querySelector('.history-list');
        const newItem = document.createElement('div');
        newItem.className = 'history-item';
        newItem.dataset.filename = file.filename;
        newItem.innerHTML = `
            <div class="filename">${file.filename}</div>
            <div class="upload-time">${file.upload_time}</div>
            <div class="file-info">
                <span class="file-size">${(file.size / 1024).toFixed(1)} KB</span>
                <span class="status-badge unprocessed">Unprocessed</span>
            </div>
        `;
        historyList.insertBefore(newItem, historyList.firstChild);
        newItem.addEventListener('click', () => selectFile(file.filename));
    }

    // View Management
    function showProcessingView(questions, flowImagePath) {
        document.getElementById('uploadView').classList.remove('active');
        document.getElementById('processingView').classList.add('active');

        document.getElementById('totalQuestions').textContent = questions.length;
        renderQuestions(questions);
        renderFlowDiagram(flowImagePath);
    }

    function renderQuestions(questions) {
        const questionsList = document.getElementById('questionsList');

        if (!document.getElementById('fewShotModal')) {
            const modalHTML = `
            <div id="fewShotModal" class="modal">
                <div class="modal-content">
                    <button class="close-modal">&times;</button>
                    <h3 class="modal-title">Add Few-Shot Examples</h3>
                    <div class="modal-body">
                        <textarea 
                            id="fewShotExamplesInput"
                            class="examples-textarea" 
                            placeholder="Enter your examples here (one per line)..."
                            rows="6"
                            style="width: 100%; margin: 1rem 0; padding: 0.5rem;"
                        ></textarea>
                    </div>
                    <div class="modal-footer" style="text-align: right; margin-top: 1rem;">
                        <button class="save-examples" style="padding: 0.5rem 1rem; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer;">
                            Save Examples
                        </button>
                    </div>
                </div>
            </div>`;
            document.body.insertAdjacentHTML('beforeend', modalHTML);

            const modal = document.getElementById('fewShotModal');
            const closeBtn = modal.querySelector('.close-modal');
            const saveBtn = modal.querySelector('.save-examples');

            closeBtn.onclick = () => modal.classList.remove('show');
            saveBtn.onclick = () => {
                const examples = document.getElementById('fewShotExamplesInput').value;
                const questionId = modal.dataset.currentQuestionId;
                saveFewShotExamples(questionId, examples);
                modal.classList.remove('show');
            };

            window.onclick = (event) => {
                if (event.target === modal) {
                    modal.classList.remove('show');
                }
            };
        }

        questionsList.innerHTML = questions.map(q => `
        <div class="question-item" data-question-id="${q.id}">
            <button class="question-button" style="width: 100%; text-align: left; padding: 1rem; border: 1px solid #ddd; border-radius: 4px; background: white; cursor: pointer; margin-bottom: 0.5rem;">
                <div class="question-id">Q${q.id}</div>
                <div class="question-text">${q.question}</div>
                <div class="question-type">${formatQuestionType(q.type)}</div>
                <div class="examples-status" style="font-size: 0.875rem; color: #666; margin-top: 0.5rem;">
                    ${fewShotExamples[q.id] ? 'Examples added ✓' : 'No examples yet'}
                </div>
            </button>
        </div>
    `).join('');

        document.querySelectorAll('.question-button').forEach(button => {
            button.addEventListener('click', () => {
                const questionId = button.closest('.question-item').dataset.questionId;
                showFewShotModal(questionId);
            });
        });
    }

    function showFewShotModal(questionId) {
        const modal = document.getElementById('fewShotModal');
        const textarea = document.getElementById('fewShotExamplesInput');
        const title = modal.querySelector('.modal-title');

        modal.dataset.currentQuestionId = questionId;
        title.textContent = `Add Few-Shot Examples for Q${questionId}`;
        textarea.value = fewShotExamples[questionId] || '';

        modal.classList.add('show');
    }

    function saveFewShotExamples(questionId, examples) {
        fewShotExamples[questionId] = examples;

        const questionItem = document.querySelector(`[data-question-id="${questionId}"]`);
        const statusElement = questionItem.querySelector('.examples-status');
        statusElement.textContent = 'Examples added ✓';
    }

    processButton.addEventListener('click', () => {
        if (!currentSelectedFile) return;

        updateFileStatus(currentSelectedFile, 'preprocessing');

        fetch('/process', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                filename: currentSelectedFile,
                fewShotExamples: fewShotExamples
            })
        })
    });

    function renderFlowDiagram(flowImagePath) {
        document.getElementById('flowDiagram').innerHTML =
            `<img src="/${flowImagePath}" alt="Survey Flow Diagram">`;
    }

    function formatQuestionType(type) {
        const typeMap = {
            'single_choice': 'Single Choice',
            'multiple_choice': 'Multiple Choice',
            'rating': 'Rating',
            'text_response': 'Text',
            'table_rating': 'Table Rating'
        };
        return typeMap[type] || type;
    }

    // Error Handling
    function showError(message) {
        const alert = document.createElement('div');
        alert.className = 'error-alert';
        alert.textContent = message;
        document.body.appendChild(alert);
        setTimeout(() => alert.remove(), 5000);
    }

    // Event Listeners
    dropZone.addEventListener('drop', e => handleFiles(e.dataTransfer.files));
    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', e => handleFiles(e.target.files));

    document.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', () => selectFile(item.dataset.filename));
    });

    // Process Button Handler
    processButton.addEventListener('click', () => {
        if (!currentSelectedFile) return;

        updateFileStatus(currentSelectedFile, 'preprocessing');

        fetch('/process', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({filename: currentSelectedFile})
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateFileStatus(currentSelectedFile, 'preprocessed');
                    showProcessingView(data.questions, data.flow_image);
                } else if (data.error === 'DAG_ERROR') {
                    showError('Survey contains cycles and cannot be processed');
                    updateFileStatus(currentSelectedFile, 'DAG_ERROR');
                    document.getElementById('processingView').classList.remove('active');
                    document.getElementById('uploadView').classList.add('active');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showError('Processing error');
                updateFileStatus(currentSelectedFile, 'unprocessed');
            });
    });

    // Calibration Handling
    document.querySelector('.action-buttons .btn').addEventListener('click', () => {
        document.getElementById('processingView').classList.remove('active');
        document.getElementById('calibrationView').classList.add('active');
    });

    window.handleCalibration = function (enable) {
        localStorage.setItem('currentFile', currentSelectedFile);
        updateFileStatus(currentSelectedFile, 'Attention Check');

        fetch('/calibration', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                enable: enable,
                filename: currentSelectedFile
            })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/samplespace';
                } else {
                    showError('Calibration failed');
                }
            })
            .catch(error => {
                showError('Error during calibration');
            });
    };

    addClickHandlers();
});