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
        selectedFilename.setAttribute('title', filename);
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
            <button class="delete-btn" onclick="deleteFile('${file.filename}', event)">&times;</button>
            <div class="filename" title="${file.filename}">${file.filename}</div>
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
                        <button class="save-examples" style="padding: 0.5rem 1rem; background: #8fa4f3; color: white; border: none; border-radius: 4px; cursor: pointer;">
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
        title.textContent = `Add Individual Instructions for Q${questionId}`;
        textarea.value = fewShotExamples[questionId] || '';

        modal.classList.add('show');
    }

    function saveFewShotExamples(questionId, examples) {
        fewShotExamples[questionId] = examples;

        const questionItem = document.querySelector(`[data-question-id="${questionId}"]`);
        const statusElement = questionItem.querySelector('.examples-status');
        statusElement.textContent = 'Examples added ✓';
    }

    function renderFlowDiagram(flowImagePath) {
        document.getElementById('flowDiagram').innerHTML = `
            <div class="flow-diagram-wrapper">
                <div class="flow-controls">
                    <button class="flow-btn" id="zoomOut" title="Zoom Out" aria-label="Zoom out diagram">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="11" cy="11" r="8"></circle>
                            <path d="M21 21l-4.35-4.35"></path>
                            <line x1="8" y1="11" x2="14" y2="11"></line>
                        </svg>
                    </button>
                    <span class="zoom-level" id="zoomLevel">100%</span>
                    <button class="flow-btn" id="zoomIn" title="Zoom In" aria-label="Zoom in diagram">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="11" cy="11" r="8"></circle>
                            <path d="M21 21l-4.35-4.35"></path>
                            <line x1="11" y1="8" x2="11" y2="14"></line>
                            <line x1="8" y1="11" x2="14" y2="11"></line>
                        </svg>
                    </button>
                    <button class="flow-btn" id="resetZoom" title="Reset Zoom" aria-label="Reset diagram zoom">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
                            <path d="M3 3v5h5"></path>
                        </svg>
                    </button>
                    <button class="flow-btn" id="fullscreen" title="Fullscreen View" aria-label="View diagram in fullscreen">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>
                        </svg>
                    </button>
                </div>
                <div class="flow-image-container loading" id="flowImageContainer">
                    <img src="/${flowImagePath}" alt="Survey Flow Diagram" id="flowImage" draggable="false">
                    <div class="flow-hint">
                        💡 Use mouse wheel to zoom, drag to move view, click fullscreen button for larger view
                    </div>
                </div>
            </div>
        `;

        initializeFlowDiagramControls();
    }

    function initializeFlowDiagramControls() {
        let currentZoom = 1;
        let isDragging = false;
        let startX, startY, scrollLeft, scrollTop;

        const container = document.getElementById('flowImageContainer');
        const image = document.getElementById('flowImage');
        const zoomInBtn = document.getElementById('zoomIn');
        const zoomOutBtn = document.getElementById('zoomOut');
        const resetZoomBtn = document.getElementById('resetZoom');
        const fullscreenBtn = document.getElementById('fullscreen');
        const zoomLevel = document.getElementById('zoomLevel');

        // Zoom functionality
        function updateZoom(newZoom) {
            currentZoom = Math.max(0.25, Math.min(3, newZoom));
            image.style.transform = `scale(${currentZoom})`;
            zoomLevel.textContent = `${Math.round(currentZoom * 100)}%`;

            // Update button states
            zoomOutBtn.disabled = currentZoom <= 0.25;
            zoomInBtn.disabled = currentZoom >= 3;
        }

        zoomInBtn.addEventListener('click', () => updateZoom(currentZoom + 0.25));
        zoomOutBtn.addEventListener('click', () => updateZoom(currentZoom - 0.25));
        resetZoomBtn.addEventListener('click', () => updateZoom(1));

        // Mouse wheel zoom
        container.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? -0.1 : 0.1;
            updateZoom(currentZoom + delta);
        });

        // Drag functionality
        container.addEventListener('mousedown', (e) => {
            if (currentZoom > 1) {
                isDragging = true;
                container.style.cursor = 'grabbing';
                startX = e.pageX - container.offsetLeft;
                startY = e.pageY - container.offsetTop;
                scrollLeft = container.scrollLeft;
                scrollTop = container.scrollTop;
            }
        });

        container.addEventListener('mouseleave', () => {
            isDragging = false;
            container.style.cursor = currentZoom > 1 ? 'grab' : 'default';
        });

        container.addEventListener('mouseup', () => {
            isDragging = false;
            container.style.cursor = currentZoom > 1 ? 'grab' : 'default';
        });

        container.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            e.preventDefault();
            const x = e.pageX - container.offsetLeft;
            const y = e.pageY - container.offsetTop;
            const walkX = (x - startX) * 2;
            const walkY = (y - startY) * 2;
            container.scrollLeft = scrollLeft - walkX;
            container.scrollTop = scrollTop - walkY;
        });

        // Fullscreen functionality
        fullscreenBtn.addEventListener('click', () => {
            openFlowDiagramModal();
        });

        // Image loading handling
        image.addEventListener('load', () => {
            container.classList.remove('loading');
            image.classList.add('loaded');

            // Check image size, auto-scale if too large
            const containerRect = container.getBoundingClientRect();
            const imageRect = image.getBoundingClientRect();

            if (imageRect.width > containerRect.width * 0.9 || imageRect.height > containerRect.height * 0.9) {
                const scaleX = (containerRect.width * 0.9) / imageRect.width;
                const scaleY = (containerRect.height * 0.9) / imageRect.height;
                const autoScale = Math.min(scaleX, scaleY, 1);
                updateZoom(autoScale);
            }
        });

        image.addEventListener('error', () => {
            container.classList.remove('loading');
            container.innerHTML = `
                <div class="flow-error">
                    <div class="flow-error-icon">⚠️</div>
                    <div class="flow-error-message">Unable to load flow diagram</div>
                    <div class="flow-error-hint">Please check if file exists or try again later</div>
                </div>
            `;
        });

        // Initialize
        updateZoom(1);
        container.style.cursor = 'default';
    }

    function openFlowDiagramModal() {
        const image = document.getElementById('flowImage');
        const modal = document.createElement('div');
        modal.className = 'flow-modal';
        modal.innerHTML = `
            <div class="flow-modal-content">
                <div class="flow-modal-header">
                    <h3>Survey Flow Diagram</h3>
                    <button class="flow-modal-close" aria-label="Close fullscreen view">&times;</button>
                </div>
                <div class="flow-modal-body">
                    <img src="${image.src}" alt="Survey Flow Diagram" class="flow-modal-image" id="modalFlowImage">
                    <div class="flow-shortcuts">
                        <div><kbd>ESC</kbd> Close</div>
                        <div><kbd>+</kbd> Zoom In</div>
                        <div><kbd>-</kbd> Zoom Out</div>
                        <div><kbd>0</kbd> Reset</div>
                        <div><kbd>F</kbd> Fit Window</div>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Zoom control within modal
        let modalZoom = 1;
        const modalImage = modal.querySelector('#modalFlowImage');
        const modalBody = modal.querySelector('.flow-modal-body');

        function updateModalZoom(newZoom) {
            modalZoom = Math.max(0.1, Math.min(5, newZoom));
            modalImage.style.transform = `scale(${modalZoom})`;
            modalImage.classList.toggle('zoomed', modalZoom > 1);
        }

        function fitToWindow() {
            const bodyRect = modalBody.getBoundingClientRect();
            const imageRect = modalImage.getBoundingClientRect();
            const scaleX = (bodyRect.width * 0.9) / (imageRect.width / modalZoom);
            const scaleY = (bodyRect.height * 0.9) / (imageRect.height / modalZoom);
            const fitScale = Math.min(scaleX, scaleY, 1);
            updateModalZoom(fitScale);
        }

        // Mouse wheel zoom
        modalBody.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? -0.2 : 0.2;
            updateModalZoom(modalZoom + delta);
        });

        // Drag functionality
        let isDragging = false;
        let startX, startY, scrollLeft, scrollTop;

        modalImage.addEventListener('mousedown', (e) => {
            if (modalZoom > 1) {
                isDragging = true;
                modalImage.style.cursor = 'grabbing';
                startX = e.pageX - modalBody.offsetLeft;
                startY = e.pageY - modalBody.offsetTop;
                scrollLeft = modalBody.scrollLeft;
                scrollTop = modalBody.scrollTop;
                e.preventDefault();
            }
        });

        modalBody.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            e.preventDefault();
            const x = e.pageX - modalBody.offsetLeft;
            const y = e.pageY - modalBody.offsetTop;
            const walkX = (x - startX) * 2;
            const walkY = (y - startY) * 2;
            modalBody.scrollLeft = scrollLeft - walkX;
            modalBody.scrollTop = scrollTop - walkY;
        });

        modalBody.addEventListener('mouseup', () => {
            isDragging = false;
            modalImage.style.cursor = modalZoom > 1 ? 'grab' : 'default';
        });

        modalBody.addEventListener('mouseleave', () => {
            isDragging = false;
            modalImage.style.cursor = modalZoom > 1 ? 'grab' : 'default';
        });

        // Close functionality
        const closeBtn = modal.querySelector('.flow-modal-close');
        const closeModal = () => {
            modal.classList.remove('show');
            setTimeout(() => modal.remove(), 300);
        };

        closeBtn.addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });

        // Keyboard shortcuts
        const handleKeydown = (e) => {
            switch (e.key) {
                case 'Escape':
                    closeModal();
                    break;
                case '+':
                case '=':
                    e.preventDefault();
                    updateModalZoom(modalZoom + 0.2);
                    break;
                case '-':
                    e.preventDefault();
                    updateModalZoom(modalZoom - 0.2);
                    break;
                case '0':
                    e.preventDefault();
                    updateModalZoom(1);
                    break;
                case 'f':
                case 'F':
                    e.preventDefault();
                    fitToWindow();
                    break;
            }
        };

        document.addEventListener('keydown', handleKeydown);

        // Clean up event listeners
        modal.addEventListener('remove', () => {
            document.removeEventListener('keydown', handleKeydown);
        });

        // Show animation and initialization
        requestAnimationFrame(() => {
            modal.classList.add('show');
            // Auto-fit window after image loads
            modalImage.addEventListener('load', () => {
                setTimeout(fitToWindow, 100);
            });
            if (modalImage.complete) {
                setTimeout(fitToWindow, 100);
            }
        });
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
        if (window.toast) {
            window.toast.error(message);
        } else {
            // Fallback for legacy support
            const alert = document.createElement('div');
            alert.className = 'error-alert';
            alert.textContent = message;
            document.body.appendChild(alert);
            setTimeout(() => alert.remove(), 5000);
        }
    }

    // Event Listeners
    dropZone.addEventListener('drop', e => handleFiles(e.dataTransfer.files));
    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', e => handleFiles(e.target.files));

    document.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', () => selectFile(item.dataset.filename));
    });

    // Helper function to determine processing mode based on file extension
    function getProcessingMode(filename) {
        const extension = filename.toLowerCase().split('.').pop();
        // PDF files use multimodal processing, others use text processing
        return extension === 'pdf' ? 'multimodal' : 'text';
    }

    // Process Button Handler
    processButton.addEventListener('click', () => {
        if (!currentSelectedFile) return;

        // Automatically determine mode based on file type
        const mode = getProcessingMode(currentSelectedFile);

        const originalText = processButton.innerHTML;
        processButton.disabled = true;
        processButton.innerHTML = '<span class="spinner"></span> Processing...';
        updateFileStatus(currentSelectedFile, 'preprocessing');

        fetch('/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: currentSelectedFile, mode: mode })
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
                    processButton.disabled = false;
                    processButton.innerHTML = originalText;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showError('Processing error');
                updateFileStatus(currentSelectedFile, 'unprocessed');
                processButton.disabled = false;
                processButton.innerHTML = originalText;
            });
    });

    // Calibration Handling
    document.querySelector('.action-buttons .btn').addEventListener('click', () => {
        document.getElementById('processingView').classList.remove('active');
        document.getElementById('calibrationView').classList.add('active');
        sendFewShotExamples()
    });

    window.handleCalibration = function (enable) {
        localStorage.setItem('currentFile', currentSelectedFile);
        updateFileStatus(currentSelectedFile, 'Attention Check');

        fetch('/calibration', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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

    function sendFewShotExamples() {
        fetch('/few-shot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(fewShotExamples)
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to send few-shot examples');
                }
                return response.json();
            })
            .then(data => {
                console.log('Few-shot examples successfully processed:', data);
            })
            .catch(error => {
                console.error('Error sending few-shot examples:', error);
                showError('Error during few-shot example submission');
            });
    }

    addClickHandlers();

    // On page load, check if there's a file selected from another page.
    const activeFile = localStorage.getItem('currentFile');
    if (activeFile) {
        const historyItem = document.querySelector(`.history-item[data-filename="${activeFile}"]`);
        if (historyItem) {
            selectFile(activeFile);
        }
    }
});

function deleteFile(filename, event) {
    event.stopPropagation(); // Prevent the click from selecting the file

    const modal = document.getElementById('confirmModal');
    const modalTitle = document.getElementById('confirmModalTitle');
    const modalText = document.getElementById('confirmModalText');
    const confirmBtn = document.getElementById('confirmModalConfirm');
    const cancelBtn = document.getElementById('confirmModalCancel');

    modalTitle.textContent = `Delete ${filename}?`;
    modalText.innerHTML = `Are you sure you want to permanently delete this file? <br>This action cannot be undone.`;

    modal.classList.add('show');

    const confirmHandler = () => {
        fetch(`/delete/${filename}`, {
            method: 'DELETE',
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const itemToRemove = document.querySelector(`.history-item[data-filename="${filename}"]`);
                if (itemToRemove) {
                    itemToRemove.remove();
                }
                if (window.toast) {
                    window.toast.success(`${filename} deleted successfully.`);
                }
            } else {
                if (window.toast) {
                    window.toast.error(`Error deleting file: ${data.error}`);
                } else {
                    alert(`Error: ${data.error}`);
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (window.toast) {
                window.toast.error('An error occurred while deleting the file.');
            } else {
                alert('An error occurred.');
            }
        })
        .finally(() => {
            closeModal();
        });
    };

    const closeModal = () => {
        modal.classList.remove('show');
        confirmBtn.removeEventListener('click', confirmHandler);
        cancelBtn.removeEventListener('click', closeModal);
    };

    confirmBtn.addEventListener('click', confirmHandler);
    cancelBtn.addEventListener('click', closeModal);
}